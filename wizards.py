# -*- coding: utf-8 -*-
# Copyright (C) 2026 RedRider21 — NexusSEC (Termux)
# Distribuito secondo i termini della GNU AGPL-3.0 (vedi LICENSE/COPYRIGHT).
"""Wizard: sequenze automatiche di comandi per profilo.

Un wizard esegue N passi IN SEQUENZA. Ogni passo può:
  - usare variabili prodotte dai passi precedenti — {target}, {ports}, ...;
  - PRODURRE nuove variabili estraendo dati dal proprio output con una regex
    (es. le porte aperte da nmap), che i passi successivi riutilizzano;
  - essere SALTATO se una variabile richiesta è vuota (skip_if_empty);
  - dichiarare `needs` (un binario): se manca, il passo si ferma con un avviso
    chiaro invece di un criptico "command not found".

NB: NON è una pipe stdout->stdin. Il concatenamento è a VARIABILI: ogni passo
estrae ciò che serve (host vivi, porte, url) e lo inietta come argomento del
passo dopo. È questo che rende l'automazione robusta tra tool diversi.

Fase 1: wizard PREDEFINITI (uno per profilo). La modifica/creazione utente
(CRUD, ~/.nexus-wizards/) arriverà in Fase 2 — lo schema è già pensato per quello.
"""
from __future__ import annotations

import re
import shlex

# Il pacchetto che fornisce il binario, quando il nome differisce dall'eseguibile,
# serve solo per i messaggi (qui teniamo i messaggi generici).


def _L(lang: str, it: str, en: str) -> str:
    return en if lang == "en" else it


def _pk(v, lang: str) -> str:
    """Sceglie la lingua da un valore che può essere str o {'it':..,'en':..}."""
    if isinstance(v, dict):
        return v.get(lang) or v.get("it") or v.get("en") or ""
    return v


# --------------------------------------------------------------------------- #
# Definizione dei wizard predefiniti
# --------------------------------------------------------------------------- #
# runtime: "termux" (eseguito in Termux) | "proot" (dentro il Debian/Kali).
# produce: {var: {"regex": r"...", "join": ",", "flags": "m"}} -> group(1).
# skip_if_empty: [var, ...]  -> salta il passo se una è vuota.
# needs: "bin"               -> verifica che il binario esista prima di eseguire.
WIZARDS: list[dict] = [
    {
        "id": "pentest_full",
        "profile": "pentest",
        "icon": "🎯",
        "name": {"it": "Pentest · scansione completa",
                 "en": "Pentest · full scan"},
        "desc": {"it": "Discovery porte → enumerazione servizi (-sC -sV) → script "
                       "di vulnerabilità NSE, tutto sulle porte trovate.",
                 "en": "Port discovery → service enumeration (-sC -sV) → NSE vuln "
                       "scripts, all on the discovered ports."},
        "input": {"type": "host",
                  "label": {"it": "Host / IP / CIDR", "en": "Host / IP / CIDR"}},
        "steps": [
            {"title": {"it": "Discovery porte (top 1000)",
                       "en": "Port discovery (top 1000)"},
             "runtime": "termux", "needs": "nmap",
             "run": "nmap -Pn -T4 --top-ports 1000 --open {target}",
             "produce": {"ports": {"regex": r"^(\d+)/tcp\s+open", "join": ","}}},
            {"title": {"it": "Enumerazione servizi e versioni (-sC -sV)",
                       "en": "Service & version enumeration (-sC -sV)"},
             "runtime": "termux", "needs": "nmap", "skip_if_empty": ["ports"],
             "run": "nmap -Pn -sC -sV -p {ports} {target}"},
            {"title": {"it": "Script di vulnerabilità (NSE vuln)",
                       "en": "Vulnerability scripts (NSE vuln)"},
             "runtime": "termux", "needs": "nmap", "skip_if_empty": ["ports"],
             "run": "nmap -Pn --script vuln -p {ports} {target}"},
        ],
    },
    {
        "id": "pentest_lite",
        "profile": "pentest_lite",
        "icon": "⚡",
        "name": {"it": "Pentest Lite · rapido", "en": "Pentest Lite · quick"},
        "desc": {"it": "Scansione veloce delle porte comuni → versioni servizi → "
                       "contesto whois. Leggero, senza NSE pesanti.",
                 "en": "Fast common-port scan → service versions → whois context. "
                       "Lightweight, no heavy NSE."},
        "input": {"type": "host",
                  "label": {"it": "Host / IP / CIDR", "en": "Host / IP / CIDR"}},
        "steps": [
            {"title": {"it": "Scansione rapida (top 100)",
                       "en": "Fast scan (top 100)"},
             "runtime": "termux", "needs": "nmap",
             "run": "nmap -Pn -T4 -F --open {target}",
             "produce": {"ports": {"regex": r"^(\d+)/tcp\s+open", "join": ","}}},
            {"title": {"it": "Versioni servizi sulle porte trovate",
                       "en": "Service versions on found ports"},
             "runtime": "termux", "needs": "nmap", "skip_if_empty": ["ports"],
             "run": "nmap -Pn -sV -p {ports} {target}"},
            {"title": {"it": "Contesto dominio (whois)",
                       "en": "Domain context (whois)"},
             "runtime": "termux", "needs": "whois",
             "run": "whois {target}"},
        ],
    },
    {
        "id": "web_recon",
        "profile": "web",
        "icon": "🕸️",
        "name": {"it": "Web · ricognizione applicativa",
                 "en": "Web · application recon"},
        "desc": {"it": "Fingerprint tecnologie → WAF → porte web → Nikto sulle "
                       "porte trovate → scansione template Nuclei (sev. ≥ media).",
                 "en": "Tech fingerprint → WAF → web ports → Nikto on found ports "
                       "→ Nuclei template scan (sev. ≥ medium)."},
        "input": {"type": "host",
                  "label": {"it": "Host / dominio", "en": "Host / domain"}},
        "steps": [
            {"title": {"it": "Fingerprint tecnologie (WhatWeb)",
                       "en": "Tech fingerprint (WhatWeb)"},
             "runtime": "proot", "needs": "whatweb",
             "run": "whatweb -a 3 {target}"},
            {"title": {"it": "Rilevazione WAF (wafw00f)",
                       "en": "WAF detection (wafw00f)"},
             "runtime": "proot", "needs": "wafw00f",
             "run": "wafw00f {target}"},
            {"title": {"it": "Porte web aperte",
                       "en": "Open web ports"},
             "runtime": "termux", "needs": "nmap",
             "run": "nmap -Pn -sV -p 80,443,8080,8443,8000,8888,3000,5000 --open {target}",
             "produce": {"web_ports": {"regex": r"^(\d+)/tcp\s+open", "join": ","}}},
            {"title": {"it": "Nikto sulle porte trovate",
                       "en": "Nikto on found ports"},
             "runtime": "proot", "needs": "nikto", "skip_if_empty": ["web_ports"],
             "run": "nikto -h {target} -p {web_ports} -Tuning 123bde"},
            {"title": {"it": "Scansione template (Nuclei)",
                       "en": "Template scan (Nuclei)"},
             "runtime": "proot", "needs": "nuclei",
             "run": "nuclei -u http://{target} -silent -severity medium,high,critical"},
        ],
    },
    {
        "id": "osint_domain",
        "profile": "osint",
        "icon": "🔎",
        "name": {"it": "OSINT · dominio & footprint",
                 "en": "OSINT · domain & footprint"},
        "desc": {"it": "whois → record DNS → sottodomini (subfinder) → email/host "
                       "(theHarvester) → enumerazione DNS (dnsrecon).",
                 "en": "whois → DNS records → subdomains (subfinder) → emails/hosts "
                       "(theHarvester) → DNS enumeration (dnsrecon)."},
        "input": {"type": "host",
                  "label": {"it": "Dominio", "en": "Domain"}},
        "steps": [
            {"title": {"it": "Registrazione (whois)", "en": "Registration (whois)"},
             "runtime": "termux", "needs": "whois",
             "run": "whois {target}"},
            {"title": {"it": "Record DNS (A/MX/NS/TXT)",
                       "en": "DNS records (A/MX/NS/TXT)"},
             "runtime": "termux", "needs": "dig",
             "run": "for t in A MX NS TXT; do echo \"== $t ==\"; "
                    "dig +short {target} $t; done"},
            {"title": {"it": "Sottodomini (subfinder)",
                       "en": "Subdomains (subfinder)"},
             "runtime": "proot", "needs": "subfinder",
             "run": "subfinder -d {target} -silent"},
            {"title": {"it": "Email e host (theHarvester)",
                       "en": "Emails and hosts (theHarvester)"},
             "runtime": "proot", "needs": "theHarvester",
             "run": "theHarvester -d {target} -b duckduckgo,crtsh,bing -l 200"},
            {"title": {"it": "Enumerazione DNS (dnsrecon)",
                       "en": "DNS enumeration (dnsrecon)"},
             "runtime": "proot", "needs": "dnsrecon",
             "run": "dnsrecon -d {target}"},
        ],
    },
    {
        "id": "forensics_triage",
        "profile": "forensics",
        "icon": "🧪",
        "name": {"it": "Forensics · triage file", "en": "Forensics · file triage"},
        "desc": {"it": "hash SHA-256 → tipo file → metadati (exiftool) → firme "
                       "incorporate (binwalk) → stringhe leggibili.",
                 "en": "SHA-256 hash → file type → metadata (exiftool) → embedded "
                       "signatures (binwalk) → readable strings."},
        "note": {"it": "Il file dev'essere accessibile dal Debian in proot.",
                 "en": "The file must be reachable from the proot Debian."},
        "input": {"type": "path",
                  "label": {"it": "Percorso del file", "en": "File path"}},
        "steps": [
            {"title": {"it": "Impronta SHA-256", "en": "SHA-256 hash"},
             "runtime": "proot", "needs": "sha256sum",
             "run": "sha256sum {target}"},
            {"title": {"it": "Tipo file", "en": "File type"},
             "runtime": "proot", "needs": "file",
             "run": "file {target}"},
            {"title": {"it": "Metadati (exiftool)", "en": "Metadata (exiftool)"},
             "runtime": "proot", "needs": "exiftool",
             "run": "exiftool {target}"},
            {"title": {"it": "Firme incorporate (binwalk)",
                       "en": "Embedded signatures (binwalk)"},
             "runtime": "proot", "needs": "binwalk",
             "run": "binwalk {target}"},
            {"title": {"it": "Stringhe leggibili", "en": "Readable strings"},
             "runtime": "proot", "needs": "strings",
             "run": "strings -n 6 {target} | head -120"},
        ],
    },
    {
        "id": "reverse_triage",
        "profile": "reverse",
        "icon": "🧩",
        "name": {"it": "Reverse · triage binario", "en": "Reverse · binary triage"},
        "desc": {"it": "tipo file → info binario/protezioni (rabin2 -I) → import "
                       "(rabin2 -i) → stringhe delle sezioni dati (rabin2 -z).",
                 "en": "file type → binary info/protections (rabin2 -I) → imports "
                       "(rabin2 -i) → data-section strings (rabin2 -z)."},
        "note": {"it": "Il file dev'essere accessibile dal Debian in proot.",
                 "en": "The file must be reachable from the proot Debian."},
        "input": {"type": "path",
                  "label": {"it": "Percorso del binario", "en": "Binary path"}},
        "steps": [
            {"title": {"it": "Tipo file", "en": "File type"},
             "runtime": "proot", "needs": "file",
             "run": "file {target}"},
            {"title": {"it": "Info e protezioni (rabin2 -I)",
                       "en": "Info & protections (rabin2 -I)"},
             "runtime": "proot", "needs": "rabin2",
             "run": "rabin2 -I {target}"},
            {"title": {"it": "Import (rabin2 -i)", "en": "Imports (rabin2 -i)"},
             "runtime": "proot", "needs": "rabin2",
             "run": "rabin2 -i {target}"},
            {"title": {"it": "Stringhe sezioni dati (rabin2 -z)",
                       "en": "Data-section strings (rabin2 -z)"},
             "runtime": "proot", "needs": "rabin2",
             "run": "rabin2 -z {target}"},
        ],
    },
]

_BY_ID = {w["id"]: w for w in WIZARDS}


def list_wizards(lang: str = "it") -> list[dict]:
    """Elenco localizzato per il pannello (drawer)."""
    out = []
    for w in WIZARDS:
        out.append({
            "id": w["id"],
            "profile": w["profile"],
            "icon": w["icon"],
            "name": _pk(w["name"], lang),
            "desc": _pk(w["desc"], lang),
            "note": _pk(w.get("note", ""), lang),
            "input": {"type": w["input"]["type"],
                      "label": _pk(w["input"]["label"], lang)},
            "steps": [{"title": _pk(s["title"], lang), "run": s["run"]}
                      for s in w["steps"]],
        })
    return out


def get_wizard(wid: str) -> dict | None:
    return _BY_ID.get(wid)


# --------------------------------------------------------------------------- #
# Validazione input + chaining a variabili (funzioni pure, testabili)
# --------------------------------------------------------------------------- #
_HOST_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._:-]*[A-Za-z0-9])?(?:/\d{1,3})?$")
_URL_RE = re.compile(r"^https?://[A-Za-z0-9._:-]+(?:/[^\s]*)?$")
# Percorso file: niente newline, non inizia con '-' (evita che sembri un'opzione).
_PATH_RE = re.compile(r"^[^\-\n\r][^\n\r]*$")
# Sanifica i valori ESTRATTI (porte, host…) prima di reiniettarli in un comando.
_SAFE = re.compile(r"[^A-Za-z0-9 ._:,/@=+-]")


def validate_input(itype: str, value: str) -> str:
    """Ritorna il valore ripulito o solleva ValueError. Rispecchia la validazione
    dei tool ma aggiunge il tipo 'path' per i wizard forensics/reverse."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Input mancante.")
    if itype == "host" and _HOST_RE.match(value):
        return value
    if itype == "url" and _URL_RE.match(value):
        return value
    if itype == "path" and _PATH_RE.match(value):
        return value
    raise ValueError(f"Input non valido per il tipo '{itype}'.")


def _san(s: str) -> str:
    return _SAFE.sub("", s)


def extract(text: str, produce: dict) -> dict:
    """Applica gli estrattori regex all'output di un passo e ritorna le variabili
    (deduplicate, ripulite, unite con il separatore indicato)."""
    out = {}
    for var, spec in (produce or {}).items():
        flags = re.MULTILINE
        try:
            rx = re.compile(spec["regex"], flags)
        except re.error:
            out[var] = ""
            continue
        vals, seen = [], set()
        for m in rx.finditer(text):
            v = _san(m.group(1) if m.groups() else m.group(0))
            if v and v not in seen:
                seen.add(v)
                vals.append(v)
        out[var] = spec.get("join", ",").join(vals)
    return out


def subst(template: str, variables: dict) -> str:
    """Sostituisce i segnaposto {var} nel comando. `target` è già quotato per la
    shell; le variabili estratte sono già sanificate a monte."""
    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}",
                  lambda m: variables.get(m.group(1), ""), template)


def initial_vars(clean_target: str) -> dict:
    """Variabili iniziali: {target} quotato per la shell (spazi/percorsi sicuri)."""
    return {"target": shlex.quote(clean_target)}
