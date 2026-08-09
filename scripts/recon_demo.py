#!/usr/bin/env python3
"""
recon_demo.py - Script dimostrativo di recon INTERATTIVO.

Serve a mostrare le "dinamiche" del pannello streaming della PWA:
  - l'output esce riga per riga (flusso live) mentre lo script lavora;
  - lo script fa DOMANDE (input()) e la UI ti fa rispondere -> bidirezionale.

Usa solo la libreria standard (socket): niente dipendenze, niente root.
Fa solo lookup DNS e TCP-connect su porte comuni: usalo SOLO su target
autorizzati (tuoi, o con permesso esplicito).

Girando dietro il server, stdout NON deve restare bufferizzato: il server
imposta PYTHONUNBUFFERED=1, ma stampiamo comunque con flush=True per sicurezza.
"""

import socket
import sys

COMMON_PORTS = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 443: "https", 445: "smb",
    3306: "mysql", 3389: "rdp", 5432: "postgres", 8080: "http-alt",
    8443: "https-alt",
}


def out(msg=""):
    print(msg, flush=True)


def ask(prompt):
    """input() con flush esplicito del prompt (fondamentale dietro una pipe)."""
    print(prompt, end="", flush=True)
    try:
        return input().strip()
    except EOFError:
        return ""


def resolve(target):
    out(f"[*] Risolvo {target} ...")
    try:
        ip = socket.gethostbyname(target)
        out(f"[+] Indirizzo IP: {ip}")
    except socket.gaierror as e:
        out(f"[!] Risoluzione fallita: {e}")
        return None
    try:
        host, *_ = socket.gethostbyaddr(ip)
        out(f"[+] Reverse DNS: {host}")
    except OSError:
        out("[-] Nessun reverse DNS.")
    return ip


def scan(ip):
    out("")
    out("[*] Scansione TCP connect delle porte comuni (timeout 1s)...")
    open_ports = []
    for port, name in COMMON_PORTS.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            if s.connect_ex((ip, port)) == 0:
                out(f"    [+] {port:>5}/tcp  APERTA   ({name})")
                open_ports.append(port)
            else:
                out(f"    [-] {port:>5}/tcp  chiusa   ({name})")
    out("")
    if open_ports:
        out(f"[=] Riepilogo: {len(open_ports)} porte aperte -> "
            + ", ".join(str(p) for p in open_ports))
    else:
        out("[=] Nessuna porta comune aperta (o host filtrato).")


def one_round(target=None):
    if not target:
        target = ask("Target da analizzare (host o IP): ")
    if not target:
        out("[!] Nessun target. Salto.")
        return
    ip = resolve(target)
    if not ip:
        return
    ans = ask("\nVuoi eseguire la scansione porte? [s/N]: ").lower()
    if ans in ("s", "si", "sì", "y", "yes"):
        scan(ip)
    else:
        out("[-] Scansione porte saltata.")


def main():
    out("=" * 46)
    out("   NexusSEC recon demo  ·  flusso interattivo")
    out("=" * 46)
    out("Digita un target, rispondi alle domande. 'exit' per uscire.")
    out("Solo su bersagli autorizzati.\n")

    # Se passato come argomento, primo giro automatico su quello.
    first = sys.argv[1] if len(sys.argv) > 1 else None
    one_round(first)

    while True:
        out("")
        again = ask("Analizzare un altro target? [s/N]: ").lower()
        if again not in ("s", "si", "sì", "y", "yes"):
            out("[*] Chiusura. Buona giornata.")
            break
        one_round()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        out("\n[*] Interrotto dall'utente.")
