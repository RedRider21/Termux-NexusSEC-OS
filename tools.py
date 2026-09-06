"""
tools.py - Registry dei tool e validazione, condiviso tra server.py (backend
reale su Termux) e mock_server.py (backend finto per testare la UI sul PC).

Non importa nulla di esterno: cosi' e' usabile anche senza FastAPI installato.
"""

from __future__ import annotations

import re
from pathlib import Path

# Cartella degli script Python "in casa" (girano nativi in Termux, senza proot).
SCRIPTS_DIR = Path(__file__).parent / "scripts"

# Distro minimale in proot: solo per i pochi tool non disponibili nativamente in
# Termux (whatweb, nikto, metasploit). Debian slim pesa ~200-400 MB, contro i
# ~2 GB di Kali completa.
DISTRO = "debian"

# Prefisso per eseguire un comando dentro la distro proot (Debian).
PROOT = ["proot-distro", "login", DISTRO, "--"]

# Prefisso per instradare un comando TCP attraverso Tor (modalita' "anonima").
# -q = silenzioso. proxychains4 funziona solo con connessioni TCP connect().
# Presente sia in Termux (proxychains-ng) sia nel Debian in proot: la stessa
# stringa funziona in entrambi i runtime, e Tor gira in Termux su 127.0.0.1:9050
# (raggiungibile anche da dentro proot, che condivide la rete con Termux).
PROXYCHAINS = ["proxychains4", "-q"]

# Porta SOCKS locale aperta da Tor (girato nativamente in Termux).
TOR_SOCKS_PORT = 9050

# Flag di nmap che costruiscono/leggono pacchetti TCP/IP grezzi (raw socket):
# il kernel Android li riserva a root, quindi su telefono NON rootato falliscono
# sempre con "requires root privileges. QUITTING!". La UI li marca "(solo root)"
# e il server, se rileva root (su), esegue il comando via `su -c`.
#   -O/-A       OS detection (fingerprinting dello stack)
#   -sS/-sU/-sA/-sW/-sM/-sN/-sF/-sX/-sO   scansioni con pacchetti grezzi
#   --traceroute                          traceroute a pacchetti grezzi
#   -PE/-PP/-PM/-PO/-PR                    ping discovery ICMP/IP/ARP
NMAP_ROOT_FLAGS = [
    "-O", "-A", "-sS", "-sU", "-sA", "-sW", "-sM", "-sN", "-sF", "-sX", "-sO",
    "--traceroute", "-PE", "-PP", "-PM", "-PO", "-PR",
]

# --------------------------------------------------------------------------- #
# Registry dei tool
# --------------------------------------------------------------------------- #
# mode:    "oneshot"     -> HTTP + output JSON
#          "interactive" -> terminale web via ttyd
#          "stream"      -> flusso live bidirezionale via WebSocket, reso nel
#                           pannello nativo della PWA (output riga per riga +
#                           input alle domande dello script). Vedi /api/stream.
#          "native"      -> richiesta HTTP diretta dal server (nessun binario)
# runtime: "termux"      -> eseguito direttamente in Termux (pacchetto nativo)
#          "proot"       -> eseguito nel Debian minimale via proot-distro
#          (assente per i tool "native": non eseguono binari)
# target:  None | "host" | "url"
# cmd:     argv base (senza il target), a cui si aggiunge il target validato.

TOOLS: dict[str, dict] = {
    # --- Network -----------------------------------------------------------
    "nmap_quick": {
        "name": "Nmap · scansione rapida",
        "category": "Network", "mode": "oneshot", "runtime": "termux", "target": "host",
        "cmd": ["nmap", "-sT", "-T4", "-F"],   # -sT = connect scan: instradabile via Tor
        "anon_ok": True,
        "help": "Porte comuni di un host o range (es. 192.168.1.1 o 192.168.1.0/24)",
        # OS detection (-O), scansione aggressiva (-A) e --traceroute usano raw
        # socket: la UI li marca "(solo root)" e girano solo se il telefono è
        # rootato (il server li esegue via `su`). La scansione base è -sT.
        "root_flags": NMAP_ROOT_FLAGS,
        "params": [
            {"type": "toggle", "flag": "-Pn", "label": "No ping (-Pn)",
             "help": "Tratta l'host come attivo, salta il discovery"},
            {"type": "toggle", "flag": "-sV", "label": "Versioni servizi (-sV)",
             "help": "Rileva il servizio/versione sulle porte aperte"},
            {"type": "toggle", "flag": "-O", "label": "OS detection (-O)",
             "help": "Riconosce il sistema operativo (raw socket)"},
            {"type": "toggle", "flag": "-A", "label": "Aggressivo (-A)",
             "help": "-sV + -O + script + traceroute (raw socket)"},
            {"type": "text", "flag": "-p", "label": "Porte (-p)",
             "placeholder": "es. 22,80,443 o 1-1000",
             "help": "Sovrascrive le porte comuni (-F)"},
            {"type": "text", "flag": "--script", "join": "eq", "label": "Script NSE (--script)",
             "placeholder": "es. http-title, banner"},
        ],
        "hints": ["-v", "--reason", "--open", "-p-", "--top-ports 100",
                  "-sC", "--traceroute"],
    },
    "nmap_ping": {
        "name": "Nmap · host attivi (ping sweep)",
        "category": "Network", "mode": "oneshot", "runtime": "termux", "target": "host",
        "cmd": ["nmap", "-sn"],
        "help": "Elenca gli host vivi in una rete (es. 192.168.1.0/24). NB: usa ICMP/ARP, non passa da Tor.",
        # -PE/-PR (ping ICMP/ARP) e --traceroute usano raw socket -> "(solo root)".
        # -PS (ping TCP) funziona anche no-root: nmap lo degrada a connect().
        "root_flags": NMAP_ROOT_FLAGS,
        "params": [
            {"type": "toggle", "flag": "-n", "label": "No DNS (-n)",
             "help": "Non risolve i nomi: più veloce"},
            {"type": "toggle", "flag": "-6", "label": "IPv6 (-6)"},
            {"type": "text", "flag": "--exclude", "join": "eq", "label": "Escludi host (--exclude)",
             "placeholder": "es. 192.168.1.1,192.168.1.5"},
        ],
        "hints": ["-PS22,80,443", "-PE", "-PR", "--traceroute", "-R", "--reason"],
    },
    "whois": {
        "name": "Whois",
        "category": "Network", "mode": "oneshot", "runtime": "termux", "target": "host",
        "cmd": ["whois"], "anon_ok": True,
        "help": "Informazioni di registrazione di un dominio (pacchetto nativo Termux)",
        "params": [
            {"type": "text", "flag": "-h", "label": "Server whois (-h)",
             "placeholder": "es. whois.nic.it",
             "help": "Interroga un server whois specifico"},
        ],
        "hints": ["-H", "-h whois.iana.org"],
    },
    "rdap": {
        "name": "Whois RDAP (senza proot)",
        "category": "Network", "mode": "native", "target": "host",
        "cmd": [],   # nativo: nessun comando shell, il server fa una richiesta HTTPS
        "help": "Dati di un dominio o IP via RDAP (API pubblica). Non richiede proot: funziona subito.",
    },
    "dig": {
        "name": "Dig · lookup DNS",
        "category": "Network", "mode": "oneshot", "runtime": "termux", "target": "host",
        "cmd": ["dig", "+noall", "+answer", "+nocmd"], "pkg": "dnsutils",
        "help": "Record DNS (A) di un dominio. Nativo Termux (dnsutils).",
        "params": [
            {"type": "select", "flag": "-t", "join": "space", "label": "Tipo record (-t)",
             "options": [
                 {"value": "", "label": "A (default)"},
                 {"value": "AAAA", "label": "AAAA (IPv6)"},
                 {"value": "MX", "label": "MX (mail)"},
                 {"value": "TXT", "label": "TXT"},
                 {"value": "NS", "label": "NS (name server)"},
                 {"value": "CNAME", "label": "CNAME (alias)"},
                 {"value": "SOA", "label": "SOA"},
                 {"value": "CAA", "label": "CAA"},
                 {"value": "SRV", "label": "SRV"},
                 {"value": "PTR", "label": "PTR (reverse)"},
                 {"value": "ANY", "label": "ANY (tutti)"},
             ]},
            {"type": "text", "flag": "", "label": "Server DNS (@)",
             "placeholder": "es. @1.1.1.1",
             "help": "Interroga un resolver specifico (scrivi con la @)"},
        ],
        "hints": ["+short", "+trace", "+dnssec", "-x", "+tcp"],
    },
    "dnsrecon": {
        "name": "DNSRecon · enumerazione DNS",
        "category": "Network", "mode": "oneshot", "runtime": "proot", "target": "host",
        "cmd": ["dnsrecon", "-d"],
        "help": "Enumera record e prova zone transfer di un dominio (via Debian).",
        "params": [
            {"type": "select", "flag": "-t", "join": "space", "label": "Tipo scansione (-t)",
             "options": [
                 {"value": "", "label": "completa (default)"},
                 {"value": "std", "label": "std (record standard)"},
                 {"value": "axfr", "label": "axfr (zone transfer)"},
                 {"value": "brt", "label": "brt (brute sottodomini)"},
                 {"value": "srv", "label": "srv (record SRV)"},
             ]},
            {"type": "text", "flag": "--threads", "join": "space", "label": "Thread (--threads)",
             "placeholder": "es. 10"},
        ],
        "hints": ["-a", "-s", "-n 8.8.8.8", "-z"],
    },
    # --- Web ---------------------------------------------------------------
    "whatweb": {
        "name": "WhatWeb · fingerprint",
        "category": "Web", "mode": "oneshot", "runtime": "proot", "target": "url",
        "cmd": ["whatweb", "--color=never"], "anon_ok": True,
        "help": "Tecnologie usate da un sito (es. https://esempio.it)",
        "params": [
            {"type": "select", "flag": "-a", "join": "space", "label": "Aggressività (-a)",
             "options": [
                 {"value": "", "label": "1 · passiva (default)"},
                 {"value": "3", "label": "3 · attiva"},
                 {"value": "4", "label": "4 · pesante"},
             ]},
            {"type": "toggle", "flag": "-v", "label": "Verboso (-v)"},
            {"type": "toggle", "flag": "--follow-redirect=always",
             "label": "Segui i redirect"},
        ],
        "hints": ["--no-errors", "--user-agent=Mozilla/5.0", "--max-threads=5"],
    },
    "nikto": {
        "name": "Nikto · scanner web",
        "category": "Web", "mode": "oneshot", "runtime": "proot", "target": "url",
        "cmd": ["nikto", "-nointeractive", "-h"], "anon_ok": True,
        "help": "Vulnerabilita' note di un web server (es. https://esempio.it)",
        "params": [
            {"type": "toggle", "flag": "-ssl", "label": "Forza HTTPS (-ssl)"},
            {"type": "text", "flag": "-Tuning", "join": "space", "label": "Tuning (-Tuning)",
             "placeholder": "es. 1234b oppure x 6",
             "help": "Limita le categorie di test (più veloce)"},
            {"type": "text", "flag": "-maxtime", "join": "space", "label": "Tempo max (-maxtime)",
             "placeholder": "es. 120s"},
            {"type": "text", "flag": "-port", "join": "space", "label": "Porta (-port)",
             "placeholder": "es. 8443"},
        ],
        "hints": ["-Display V", "-Plugins @@ALL", "-timeout 10", "-useragent Mozilla/5.0"],
    },
    "wafw00f": {
        "name": "wafw00f · rileva WAF",
        "category": "Web", "mode": "oneshot", "runtime": "proot", "target": "url",
        "cmd": ["wafw00f"], "anon_ok": True,
        "help": "Rileva il Web Application Firewall davanti a un sito (via Debian).",
        "params": [
            {"type": "toggle", "flag": "-a", "label": "Prova tutti i WAF (-a)",
             "help": "Non si ferma al primo match"},
            {"type": "toggle", "flag": "-v", "label": "Verboso (-v)"},
        ],
        "hints": ["-f json", "-o out.json", "--no-colors"],
    },
    "sqlmap": {
        "name": "sqlmap (interattivo)",
        "category": "Web", "mode": "interactive", "runtime": "termux", "target": None,
        "cmd": ["bash", "-lc", "sqlmap --wizard || bash"],
        "help": "SQL injection; parte in modalita' wizard",
    },
    "wfuzz": {
        "name": "Wfuzz · fuzzing web (interattivo)",
        "category": "Web", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: wfuzz -w wordlist.txt https://sito/FUZZ'; "
                               "echo 'FUZZ = punto da fuzzare, -w = wordlist'; bash"],
        "help": "Fuzzing di parametri/percorsi web con wordlist (via Debian).",
    },
    # --- Exploitation ------------------------------------------------------
    "metasploit": {
        "name": "Metasploit (console)",
        "category": "Exploitation", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "msfconsole || bash"],
        "repo": "kali", "pkg": "metasploit-framework", "catalog": True,
        "help": "Console Metasploit (pacchetto metasploit-framework, repo Kali)",
    },
    "hydra": {
        "name": "Hydra (interattivo)",
        # Non esiste in Termux: si installa dal repo Kali dentro il Debian (proot).
        "category": "Exploitation", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "hydra; bash"], "repo": "kali",
        "help": "Brute-force di login; usa la shell per comporre il comando",
    },
    # --- Cracking offline --------------------------------------------------
    "aircrack": {
        "name": "Aircrack-ng (crack offline)",
        "category": "Cracking", "mode": "interactive", "runtime": "termux", "target": None,
        "cmd": ["bash", "-lc", "echo 'Crack offline di un .cap gia catturato. Esempio:'; "
                               "echo '  aircrack-ng -w wordlist.txt handshake.cap'; bash"],
        "help": "Solo crack offline di handshake gia' catturati (la cattura non e' possibile su telefono stock)",
    },
    "john": {
        "name": "John the Ripper (interattivo)",
        # Non affidabile in Termux: si installa dal repo Kali dentro il Debian (proot).
        "category": "Cracking", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: john --wordlist=rockyou.txt hash.txt'; bash"],
        "repo": "kali",
        "help": "Cracking di hash da file",
    },
    # --- Anonimato ---------------------------------------------------------
    "tor_ip": {
        "name": "Verifica IP di uscita (Tor)",
        "category": "Anonimato", "mode": "oneshot", "runtime": "termux", "target": None,
        "cmd": ["curl", "-s", "--max-time", "25", "https://check.torproject.org/api/ip"],
        "anon_ok": True, "force_anon": True,
        "help": "Mostra l'IP con cui esci verso l'esterno: attiva Tor e controlla che sia un exit node.",
    },
    "shell_anon": {
        "name": "Shell anonima (via Tor)",
        "category": "Anonimato", "mode": "interactive", "runtime": "termux", "target": None,
        "cmd": ["bash", "-lc", "echo 'Ogni comando TCP qui e instradato via Tor (proxychains).'; "
                               "echo 'Esempio:  curl https://check.torproject.org/api/ip'; "
                               "exec proxychains4 bash -l"],
        "help": "Terminale in cui il traffico TCP passa da Tor. Richiede Tor attivo.",
    },
    # --- Sistema -----------------------------------------------------------
    "shell": {
        "name": "Shell Debian (proot)",
        "category": "Sistema", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-l"],
        "help": "Terminale libero dentro il Debian minimale (proot)",
    },
    "shell_live": {
        "name": "Shell (pannello)",
        "category": "Sistema", "mode": "stream", "runtime": "termux", "target": None,
        "cmd": ["bash"],
        "help": "Shell Termux dentro il pannello dell'app: scrivi un comando e premi "
                "Invio, l'output scorre live. Il campo e' della web-app, quindi niente "
                "auto-maiuscola della tastiera (a differenza del terminale ttyd). "
                "Nota: non e' un vero terminale (niente frecce/tab), i comandi che "
                "restano in esecuzione mostrano l'output alla loro fine.",
    },
    "shell_live_anon": {
        "name": "Shell (pannello, via Tor)",
        "category": "Anonimato", "mode": "stream", "runtime": "termux", "target": None,
        "cmd": ["proxychains4", "bash"],
        "anon_ok": True, "force_anon": True,
        "help": "Come la Shell (pannello) ma il traffico TCP passa da Tor "
                "(proxychains). Richiede Tor attivo.",
    },
    "recon_demo": {
        "name": "Recon demo (flusso live)",
        "category": "Sistema", "mode": "stream", "runtime": "termux", "target": None,
        "cmd": ["python3", "-u", str(SCRIPTS_DIR / "recon_demo.py")],
        "help": "Script Python interattivo: mostra il flusso live e le domande "
                "nel pannello nativo (esempio del WebSocket).",
    },

    # ======================================================================= #
    # CATALOGO (catalog=True): tool extra NON installati di default. Compaiono
    # nella UI come "da installare" (toggle 🧰). "repo":"kali" indica che il
    # pacchetto sta nel repo di Kali, non in Debian standard.
    # ======================================================================= #
    # --- Network / OSINT ---------------------------------------------------
    "dnsenum": {
        "name": "DNSenum · enumerazione DNS",
        "category": "Network", "mode": "oneshot", "runtime": "proot", "target": "host",
        "cmd": ["dnsenum"], "catalog": True, "repo": "kali",
        "help": "Tipo: recon DNS. Sottodomini, record e tentativi di zone transfer.",
        "params": [
            {"type": "text", "flag": "--threads", "join": "space", "label": "Thread (--threads)",
             "placeholder": "es. 10"},
            {"type": "toggle", "flag": "--noreverse", "label": "Salta il reverse lookup"},
        ],
        "hints": ["--enum", "-r", "-o out.xml", "-f wordlist.txt", "--dnsserver 8.8.8.8"],
    },
    "theharvester": {
        "name": "theHarvester · OSINT",
        "category": "Network", "mode": "oneshot", "runtime": "proot", "target": "host",
        "cmd": ["theHarvester", "-b", "all", "-d"], "catalog": True, "repo": "kali",
        "pkg": "theharvester",
        "help": "Tipo: OSINT. Raccoglie email, sottodomini e host da fonti pubbliche.",
        "params": [
            {"type": "text", "flag": "-l", "join": "space", "label": "Limite risultati (-l)",
             "placeholder": "es. 500"},
            {"type": "toggle", "flag": "-s", "label": "Cerca IP con Shodan (-s)",
             "help": "Richiede una API key Shodan configurata"},
        ],
        "hints": ["-f report", "-n", "-c"],
    },
    # --- Web ---------------------------------------------------------------
    "wpscan": {
        "name": "WPScan · sicurezza WordPress",
        "category": "Web", "mode": "oneshot", "runtime": "proot", "target": "url",
        "cmd": ["wpscan", "--no-banner", "--url"], "anon_ok": True,
        "catalog": True, "repo": "kali",
        "help": "Tipo: scanner CMS. Vulnerabilita' di siti WordPress (plugin/tema/utenti).",
        "params": [
            {"type": "select", "flag": "--enumerate", "join": "eq", "label": "Enumera (--enumerate)",
             "options": [
                 {"value": "", "label": "niente (default)"},
                 {"value": "vp", "label": "vp · plugin vulnerabili"},
                 {"value": "ap", "label": "ap · tutti i plugin"},
                 {"value": "vt", "label": "vt · temi vulnerabili"},
                 {"value": "u", "label": "u · utenti"},
                 {"value": "vp,vt,u", "label": "vp,vt,u · combinato"},
             ]},
            {"type": "toggle", "flag": "--random-user-agent", "label": "User-agent casuale"},
        ],
        "hints": ["--plugins-detection aggressive", "--api-token TOKEN",
                  "--disable-tls-checks", "-e u1-50"],
    },
    "gobuster": {
        "name": "Gobuster · brute dir/DNS",
        "category": "Web", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: gobuster dir -u https://sito -w wordlist.txt'; bash"],
        "catalog": True, "repo": "kali",
        "help": "Tipo: content discovery. Brute force di directory, DNS e vhost via wordlist.",
    },
    "dirb": {
        "name": "Dirb · scanner directory",
        "category": "Web", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: dirb https://sito /usr/share/wordlists/dirb/common.txt'; bash"],
        "catalog": True, "repo": "kali",
        "help": "Tipo: content discovery. Scanner classico di contenuti/directory web.",
    },
    "commix": {
        "name": "Commix · command injection",
        "category": "Web", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: commix -u \"https://sito/page?id=1\"'; bash"],
        "catalog": True, "repo": "kali",
        "help": "Tipo: exploit web. Rileva e sfrutta vulnerabilita' di command injection.",
    },
    # --- Cracking ----------------------------------------------------------
    "hashcat": {
        "name": "Hashcat · cracking hash",
        "category": "Cracking", "mode": "interactive", "runtime": "termux", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: hashcat -m 0 hash.txt wordlist.txt'; bash"],
        "catalog": True,
        "help": "Tipo: password cracking. Cracking di hash ad alte prestazioni (via CPU).",
    },
    "hashid": {
        "name": "hashID · identifica hash",
        # Preso dal repo Kali (pacchetto firmato) invece che da pip: più affidabile
        # e coerente con gli altri tool del profilo, che già passano dal Debian.
        "category": "Cracking", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: hashid \"5f4dcc3b5aa765d61d8327deb882cf99\"'; bash"],
        "catalog": True, "repo": "kali",
        "help": "Tipo: utility. Riconosce il tipo/algoritmo di un hash sconosciuto.",
    },
    "crunch": {
        "name": "Crunch · generatore wordlist",
        "category": "Cracking", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: crunch 6 8 abc123 -o wordlist.txt'; bash"],
        "catalog": True, "repo": "kali",
        "help": "Tipo: utility. Genera wordlist personalizzate per pattern/charset.",
    },
    "cewl": {
        "name": "CeWL · wordlist da sito",
        "category": "Cracking", "mode": "oneshot", "runtime": "proot", "target": "url",
        "cmd": ["cewl"], "anon_ok": True, "catalog": True, "repo": "kali",
        "help": "Tipo: utility. Crea una wordlist dalle parole presenti in un sito.",
        "params": [
            {"type": "text", "flag": "-d", "join": "space", "label": "Profondità crawl (-d)",
             "placeholder": "es. 2"},
            {"type": "text", "flag": "-m", "join": "space", "label": "Lunghezza minima parola (-m)",
             "placeholder": "es. 5"},
            {"type": "toggle", "flag": "-e", "label": "Estrai anche le email (-e)"},
            {"type": "toggle", "flag": "--with-numbers", "label": "Includi parole con numeri"},
        ],
        "hints": ["-w wordlist.txt", "--lowercase", "-c", "--depth 3"],
    },
    # --- Exploitation ------------------------------------------------------
    "searchsploit": {
        "name": "SearchSploit · Exploit-DB",
        "category": "Exploitation", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: searchsploit apache 2.4'; bash"],
        "catalog": True, "repo": "kali", "pkg": "exploitdb",
        "help": "Tipo: ricerca exploit. Cerca exploit pubblici noti (Exploit-DB), offline.",
    },
    "enum4linux": {
        "name": "enum4linux · enum SMB",
        "category": "Exploitation", "mode": "oneshot", "runtime": "proot", "target": "host",
        "cmd": ["enum4linux", "-a"], "anon_ok": True, "catalog": True, "repo": "kali",
        "help": "Tipo: enumeration. Estrae info da server SMB/Windows (utenti, share). "
                "Il base usa -a (tutto); i suggerimenti mirano test singoli.",
        "params": [
            {"type": "text", "flag": "-u", "join": "space", "label": "Utente (-u)",
             "placeholder": "es. guest"},
            {"type": "text", "flag": "-p", "join": "space", "label": "Password (-p)",
             "placeholder": "opzionale"},
        ],
        "hints": ["-U", "-S", "-G", "-P", "-o", "-v"],
    },
    "medusa": {
        "name": "Medusa · brute force login",
        "category": "Exploitation", "mode": "interactive", "runtime": "proot", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: medusa -h 10.0.0.1 -u admin -P pass.txt -M ssh'; bash"],
        "catalog": True, "repo": "kali",
        "help": "Tipo: brute force. Login su servizi di rete (alternativa a Hydra).",
    },
    # --- Sistema / utility -------------------------------------------------
    "exiftool": {
        "name": "ExifTool · metadati file",
        "category": "Sistema", "mode": "interactive", "runtime": "termux", "target": None,
        "cmd": ["bash", "-lc", "echo 'Esempio: exiftool foto.jpg'; bash"],
        "catalog": True,
        "help": "Tipo: forense/OSINT. Legge e modifica i metadati di foto e file.",
    },
}


# Limiti difensivi sui parametri extra passati dall'utente. Non c'e' rischio di
# shell injection (i comandi sono liste argv, mai passate a una shell), ma teniamo
# comunque i valori entro limiti ragionevoli e senza caratteri di controllo.
_MAX_ARGS = 40
_MAX_ARG_LEN = 256


def validate_args(args: list | None) -> list[str]:
    """Ripulisce e valida i parametri extra (argv). Solleva ValueError se anomali."""
    if not args:
        return []
    if len(args) > _MAX_ARGS:
        raise ValueError(f"Troppi parametri (max {_MAX_ARGS}).")
    out: list[str] = []
    for a in args:
        if not isinstance(a, str):
            raise ValueError("Parametro non valido.")
        if len(a) > _MAX_ARG_LEN:
            raise ValueError(f"Parametro troppo lungo (max {_MAX_ARG_LEN}).")
        if any(c in a for c in ("\x00", "\n", "\r")):
            raise ValueError("Parametro con caratteri non consentiti.")
        if a != "":
            out.append(a)
    return out


def inner_command(tool_id: str, target: str | None, anon: bool,
                  args: list | None = None) -> list[str]:
    """Costruisce il comando "interno" del tool (senza il prefisso di runtime).

    Ordine: comando base + parametri extra (validati come argv) + target validato.
    Se richiesto e supportato, antepone proxychains per instradare via Tor. Il
    prefisso di runtime (nulla per Termux, proot per Debian) lo aggiunge exec_prefix()
    nel server. Solleva ValueError su input non valido o richieste incoerenti.
    """
    tool = TOOLS.get(tool_id)
    if tool is None:
        raise ValueError("Tool sconosciuto.")

    cmd = list(tool["cmd"])
    cmd += validate_args(args)          # parametri extra scelti dall'utente (argv)
    if tool.get("target"):
        cmd.append(validate_target(tool["target"], target or ""))

    use_anon = tool.get("force_anon", False) or (anon and tool.get("anon_ok", False))
    if use_anon:
        if not tool.get("anon_ok"):
            raise ValueError("Questo tool non e' instradabile via Tor.")
        cmd = list(PROXYCHAINS) + cmd
    return cmd


# Binario da verificare per sapere se un tool e' realmente installato.
# I tool "native" non hanno binario: sono sempre disponibili.
BIN = {
    "nmap_quick": "nmap", "nmap_ping": "nmap", "whois": "whois", "dig": "dig",
    "whatweb": "whatweb", "nikto": "nikto", "dnsrecon": "dnsrecon", "wafw00f": "wafw00f",
    "sqlmap": "sqlmap", "wfuzz": "wfuzz", "metasploit": "msfconsole", "hydra": "hydra",
    "aircrack": "aircrack-ng", "john": "john", "tor_ip": "curl",
    "shell_anon": "proxychains4", "shell": "bash",
    # catalogo (extra, on-demand)
    "dnsenum": "dnsenum", "theharvester": "theHarvester", "wpscan": "wpscan",
    "gobuster": "gobuster", "dirb": "dirb", "commix": "commix",
    "hashcat": "hashcat", "hashid": "hashid", "crunch": "crunch", "cewl": "cewl",
    "searchsploit": "searchsploit", "enum4linux": "enum4linux", "medusa": "medusa",
    "exiftool": "exiftool",
}


# ========================================================================= #
# CATALOGO ESTESO (portato dai profili della distro NexusSec-OS).
# Costruito da chiamate compatte per non ripetere la struttura del dict.
#   c(...) = tool che funziona su telefono (interattivo, terminale ttyd).
#   n(...) = tool mostrato ma NON funzionante su stock (root/monitor mode/GUI).
# ========================================================================= #

def _c(tid, name, cat, runtime="proot", *, repo=None, pkg=None, pip=False,
       binn=None, help="", anon=False):
    """Registra un tool del catalogo (funzionante) in TOOLS + BIN."""
    b = binn or tid
    entry = {
        "name": name, "category": cat, "mode": "interactive", "runtime": runtime,
        "target": None, "catalog": True, "help": help,
        "cmd": ["bash", "-lc",
                f"command -v {b} >/dev/null 2>&1 && {b} --help 2>&1 | head -15; echo; exec bash"],
    }
    if repo:
        entry["repo"] = repo
    if pkg:
        entry["pkg"] = pkg
    if pip:
        entry["pip"] = True
    if anon:
        entry["anon_ok"] = True
    TOOLS[tid] = entry
    BIN[tid] = b


def _n(tid, name, cat, *, reason, help=""):
    """Registra un tool NON usabile su telefono stock (solo informativo)."""
    TOOLS[tid] = {
        "name": name, "category": cat, "mode": "oneshot", "runtime": "proot",
        "target": None, "catalog": True, "works": False, "reason": reason,
        "help": help, "cmd": [],
    }


# --- Web ---------------------------------------------------------------------
_c("ffuf", "Ffuf · fuzzing web", "Web", "termux",
   help="Tipo: fuzzing web. Brute force veloce di path e parametri.")
_c("nuclei", "Nuclei · scanner vuln", "Web", repo="kali",
   help="Tipo: scanner vuln. Scansione basata su template della community.")
_c("feroxbuster", "Feroxbuster · content discovery", "Web", repo="kali",
   help="Tipo: content discovery. Brute force ricorsivo di directory.")
_c("wapiti", "Wapiti · scanner web", "Web", repo="kali",
   help="Tipo: scanner vuln web. Trova XSS/SQLi/ecc. via crawling.")
_c("joomscan", "JoomScan · Joomla", "Web", repo="kali",
   help="Tipo: scanner CMS. Sicurezza di siti Joomla.")
_c("sslscan", "SSLScan · TLS", "Web", "termux",
   help="Tipo: TLS. Cifrari e certificati SSL/TLS di un server.")
_c("httrack", "HTTrack · mirror sito", "Web", "termux",
   help="Tipo: mirror. Scarica un intero sito in locale.")
_c("dalfox", "Dalfox · XSS", "Web", repo="kali",
   help="Tipo: XSS. Scanner automatico di cross-site scripting.")
_c("weevely", "Weevely · web shell", "Web", repo="kali",
   help="Tipo: web shell. Genera e gestisce web shell PHP offuscate.")
_c("mitmproxy", "mitmproxy · proxy MITM", "Web", repo="kali",
   help="Tipo: proxy MITM. Intercetta/modifica HTTP(S) come proxy locale.")

# --- Network / recon ---------------------------------------------------------
_c("naabu", "Naabu · port scan", "Network", repo="kali",
   help="Tipo: port scan. Scanner di porte veloce (connect scan).")
_c("dmitry", "DMitry · recon host", "Network", repo="kali",
   help="Tipo: recon. Info su un host: whois, sottodomini, porte.")
_c("nbtscan", "NBTscan · NetBIOS", "Network", repo="kali",
   help="Tipo: enum. Scansione dei nomi NetBIOS in una rete.")
_c("snmpwalk", "snmpwalk · SNMP", "Network", pkg="snmp", binn="snmpwalk",
   help="Tipo: enum SNMP. Interroga i MIB di un dispositivo via SNMP.")
_c("onesixtyone", "onesixtyone · SNMP", "Network", repo="kali",
   help="Tipo: enum SNMP. Scanner di community string SNMP.")
_c("socat", "socat · relay", "Network", "termux",
   help="Tipo: networking. Relay e tunnel tra socket, file e processi.")
_c("ncat", "Ncat · netcat", "Network", "termux", pkg="nmap", binn="ncat",
   help="Tipo: networking. Netcat moderno (connessioni TCP/UDP).")
_c("sipvicious", "SIPVicious · VoIP", "Network", repo="kali", binn="svmap",
   pkg="sipvicious", help="Tipo: VoIP. Scanner di sistemi SIP/VoIP.")

# --- OSINT -------------------------------------------------------------------
_c("recon_ng", "Recon-ng · framework OSINT", "Network", repo="kali", binn="recon-ng",
   help="Tipo: OSINT. Framework modulare di ricognizione.")
_c("shodan", "Shodan CLI", "Network", "termux", pip=True,
   help="Tipo: OSINT. CLI di Shodan (richiede API key).")
_c("holehe", "Holehe · email OSINT", "Network", "termux", pip=True,
   help="Tipo: OSINT. Verifica se un'email e' registrata su vari siti.")
_c("sherlock", "Sherlock · username OSINT", "Network", "termux", pip=True,
   help="Tipo: OSINT. Cerca uno username sui social network.")
_c("subfinder", "Subfinder · sottodomini", "Network", repo="kali",
   help="Tipo: OSINT. Enumerazione passiva di sottodomini.")
_c("amass", "Amass · superficie d'attacco", "Network", repo="kali",
   help="Tipo: OSINT. Mappa i sottodomini e la superficie d'attacco.")
_c("spiderfoot", "SpiderFoot · OSINT auto", "Network", repo="kali",
   help="Tipo: OSINT. Automazione OSINT con interfaccia web locale.")
_c("metagoofil", "Metagoofil · metadati doc", "Network", repo="kali",
   help="Tipo: OSINT. Estrae metadati da documenti pubblici.")

# --- Cracking ----------------------------------------------------------------
_c("ncrack", "Ncrack · brute rete", "Cracking", repo="kali",
   help="Tipo: brute force. Cracking di autenticazioni di rete.")
_c("patator", "Patator · brute multiuso", "Cracking", repo="kali",
   help="Tipo: brute force. Brute forcer modulare multi-protocollo.")
_c("crowbar", "Crowbar · brute", "Cracking", repo="kali",
   help="Tipo: brute force. Brute force per RDP/SSH/OpenVPN.")
_c("fcrackzip", "fcrackzip · ZIP", "Cracking", repo="kali",
   help="Tipo: cracking. Password di archivi ZIP.")
_c("pdfcrack", "pdfcrack · PDF", "Cracking", repo="kali",
   help="Tipo: cracking. Password di file PDF.")
_c("ophcrack", "Ophcrack · Windows", "Cracking", repo="kali",
   pkg="ophcrack-cli", binn="ophcrack",
   help="Tipo: cracking. Password Windows via rainbow table.")

# --- Forensics ---------------------------------------------------------------
_c("binwalk", "Binwalk · firmware", "Forensics", "termux",
   help="Tipo: forense. Analizza ed estrae contenuti da firmware/binari.")
_c("foremost", "Foremost · carving", "Forensics", repo="kali",
   help="Tipo: forense. Recupera file per carving.")
_c("scalpel", "Scalpel · carving", "Forensics", repo="kali",
   help="Tipo: forense. File carving configurabile.")
_c("testdisk", "TestDisk · recupero", "Forensics", "termux",
   help="Tipo: forense. Recupera partizioni e file (da immagini).")
_c("sleuthkit", "Sleuth Kit · filesystem", "Forensics", pkg="sleuthkit", binn="fls",
   help="Tipo: forense. Analisi di filesystem (The Sleuth Kit).")
_c("steghide", "Steghide · stego", "Forensics", pkg="steghide",
   help="Tipo: stego. Nasconde/estrae dati in immagini e audio.")
_c("stegseek", "StegSeek · crack stego", "Forensics", repo="kali",
   help="Tipo: stego. Cracker velocissimo di steghide.")
_c("yara", "YARA · regole malware", "Forensics", "termux",
   help="Tipo: malware. Pattern matching su file con regole YARA.")
_c("clamav", "ClamAV · antivirus", "Forensics", pkg="clamav", binn="clamscan",
   help="Tipo: antivirus. Scansione malware dei file.")
_c("chkrootkit", "chkrootkit", "Forensics", pkg="chkrootkit",
   help="Tipo: hardening. Cerca rootkit noti nel sistema.")
_c("rkhunter", "Rootkit Hunter", "Forensics", pkg="rkhunter",
   help="Tipo: hardening. Rileva rootkit e anomalie.")
_c("lynis", "Lynis · audit", "Forensics", "termux",
   help="Tipo: audit. Audit di sicurezza e hardening del sistema.")
_c("bulk_extractor", "Bulk Extractor", "Forensics", repo="kali", binn="bulk_extractor",
   pkg="bulk-extractor", help="Tipo: forense. Estrae email/URL/carte da immagini disco.")
_c("volatility3", "Volatility 3 · memoria", "Forensics", "termux", pip=True, binn="vol",
   pkg="volatility3", help="Tipo: forense. Analisi di dump di memoria (RAM).")

# --- Reverse -----------------------------------------------------------------
_c("radare2", "Radare2 · RE", "Reverse", "termux", binn="r2", pkg="radare2",
   help="Tipo: reverse. Framework di reverse engineering.")
_c("gdb", "GDB · debugger", "Reverse", "termux",
   help="Tipo: debug. Debugger GNU.")
_c("strace", "strace · syscall", "Reverse", "termux",
   help="Tipo: debug. Traccia le system call di un processo.")
_c("ltrace", "ltrace · librerie", "Reverse", pkg="ltrace",
   help="Tipo: debug. Traccia le chiamate a libreria.")
_c("jadx", "Jadx · decompila APK", "Reverse", "termux",
   help="Tipo: reverse. Decompila APK/DEX in codice Java.")
_c("apktool", "Apktool · APK", "Reverse", "termux",
   help="Tipo: reverse. Decompila e ricostruisce risorse di un APK.")
_c("binutils", "Binutils · objdump", "Reverse", "termux", binn="objdump", pkg="binutils",
   help="Tipo: reverse. objdump/readelf/nm e altri.")
_c("hexedit", "Hexedit", "Reverse", "termux",
   help="Tipo: utility. Editor esadecimale da terminale.")
_c("pev", "pev · analisi PE", "Reverse", pkg="pev",
   help="Tipo: reverse. Analisi di eseguibili PE (Windows).")
_c("floss", "FLARE FLOSS · stringhe", "Reverse", "termux", pip=True, pkg="flare-floss", binn="floss",
   help="Tipo: reverse. Estrae stringhe offuscate da malware.")

# --- Exploitation / Active Directory ----------------------------------------
_c("routersploit", "RouterSploit", "Exploitation", repo="kali",
   help="Tipo: exploit. Framework di exploit per router e IoT.")
_c("set", "SET · social eng", "Exploitation", repo="kali", pkg="set", binn="setoolkit",
   help="Tipo: social engineering. Social-Engineer Toolkit.")
_c("impacket", "Impacket", "Exploitation", repo="kali", pkg="impacket-scripts",
   binn="impacket-smbserver",
   help="Tipo: AD. Script per protocolli Windows/Active Directory.")
_c("netexec", "NetExec (nxc)", "Exploitation", repo="kali", binn="nxc",
   pkg="netexec", help="Tipo: AD. Esecuzione/enum su reti Windows (ex-CrackMapExec).")
_c("evil_winrm", "Evil-WinRM", "Exploitation", repo="kali", binn="evil-winrm",
   help="Tipo: post-exploit. Shell WinRM verso host Windows.")
_c("bloodhound_py", "BloodHound.py", "Exploitation", repo="kali",
   pkg="bloodhound.py", binn="bloodhound-python",
   help="Tipo: AD. Raccoglie dati di Active Directory per BloodHound.")
_c("smbmap", "SMBMap", "Exploitation", repo="kali",
   help="Tipo: enum SMB. Enumera share e permessi SMB.")
_c("beef_xss", "BeEF · browser exploit", "Exploitation", repo="kali", binn="beef-xss",
   help="Tipo: exploit web. Browser Exploitation Framework (server locale).")
_c("autorecon", "AutoRecon", "Exploitation", "termux", pip=True,
   help="Tipo: recon. Ricognizione automatica multi-tool.")

# --- Anonimato ---------------------------------------------------------------
_c("torsocks", "torsocks", "Anonimato", "termux",
   help="Tipo: anonimato. Instrada un singolo comando via Tor.")

# --- Ampliamento catalogo (portabili) ---------------------------------------
_c("sslyze", "SSLyze", "Web", "termux", pip=True,
   help="Tipo: TLS. Analisi configurazione SSL/TLS di un server.", anon=True)
_c("testssl", "testssl.sh", "Web", repo="kali", binn="testssl.sh",
   help="Tipo: TLS. Test approfondito di cifrari, protocolli e vulnerabilità TLS.")
_c("dirsearch", "dirsearch", "Web", "termux", pip=True,
   help="Tipo: web recon. Brute force di percorsi/file su un web server.", anon=True)
_c("arjun", "Arjun", "Web", "termux", pip=True,
   help="Tipo: web recon. Scopre parametri HTTP nascosti.", anon=True)
_c("katana", "Katana", "Web", repo="kali",
   help="Tipo: web crawler. Crawler veloce per URL/endpoint (ProjectDiscovery).")
_c("dnstwist", "dnstwist", "OSINT", "termux", pip=True,
   help="Tipo: OSINT. Trova domini simili/typosquatting (phishing).")
_c("fierce", "fierce", "OSINT", "termux", pip=True,
   help="Tipo: OSINT DNS. Ricognizione DNS e ricerca sottodomini.")
_c("sublist3r", "Sublist3r", "OSINT", "termux", pip=True,
   help="Tipo: OSINT. Enumerazione sottodomini da fonti pubbliche.")
_c("assetfinder", "assetfinder", "OSINT", repo="kali",
   help="Tipo: OSINT. Trova domini e sottodomini collegati a un target.")
_c("waybackurls", "waybackurls", "OSINT", repo="kali",
   help="Tipo: OSINT. URL storici di un dominio dalla Wayback Machine.")
_c("dnsx", "dnsx", "OSINT", repo="kali",
   help="Tipo: OSINT DNS. Toolkit DNS veloce (risoluzione, record, wildcard).")
_c("maigret", "Maigret", "OSINT", "termux", pip=True,
   help="Tipo: OSINT. Cerca un username su centinaia di siti.", anon=True)
_c("photon", "Photon", "OSINT", "termux", pip=True,
   help="Tipo: OSINT crawler. Estrae URL, email, dati da un sito.", anon=True)

# --- NON usabili su telefono stock (informativi) ----------------------------
_n("kismet", "Kismet", "Wireless",
   reason="Sniffing Wi-Fi: richiede monitor mode e root, impossibile su stock.",
   help="Tipo: wireless. Sniffer/IDS Wi-Fi.")
_n("reaver", "Reaver", "Wireless",
   reason="Attacco WPS: richiede monitor mode/injection e root.",
   help="Tipo: wireless. Attacco WPS su router.")
_n("wifite", "Wifite", "Wireless",
   reason="Automazione attacchi Wi-Fi: richiede monitor mode e root.",
   help="Tipo: wireless. Attacchi Wi-Fi automatizzati.")
_n("wifiphisher", "Wifiphisher", "Wireless",
   reason="Rogue AP/phishing Wi-Fi: richiede AP/monitor mode e root.",
   help="Tipo: wireless. Access point malevolo.")
_n("mdk4", "MDK4", "Wireless",
   reason="Attacchi 802.11: richiedono injection e root.",
   help="Tipo: wireless. Stress/attacco su reti Wi-Fi.")
_n("cowpatty", "coWPAtty", "Wireless",
   reason="Serve un handshake catturato; la cattura richiede monitor mode/root.",
   help="Tipo: wireless. Crack WPA-PSK.")
_n("pixiewps", "Pixiewps", "Wireless",
   reason="Attacco Pixie Dust: dipende dalla cattura WPS (monitor mode/root).",
   help="Tipo: wireless. Attacco Pixie Dust WPS.")
_n("macchanger", "MAC Changer", "Wireless",
   reason="Cambiare il MAC dell'interfaccia richiede root.",
   help="Tipo: wireless. Cambia l'indirizzo MAC.")
_n("bettercap", "Bettercap", "Network",
   reason="MITM/sniffing su rete: richiede raw socket e root.",
   help="Tipo: MITM. Attacchi man-in-the-middle.")
_n("ettercap", "Ettercap", "Network",
   reason="MITM/ARP poisoning: richiede raw socket e root.",
   help="Tipo: MITM. Man-in-the-middle su LAN.")
_n("responder", "Responder", "Network",
   reason="Poisoning LLMNR/NBT-NS: richiede bind su porte basse e raw, root.",
   help="Tipo: MITM. Cattura credenziali su LAN.")
_n("tcpdump", "tcpdump", "Network",
   reason="La cattura di pacchetti richiede root (puo' solo leggere file .pcap).",
   help="Tipo: sniffer. Cattura pacchetti di rete.")
_n("tshark", "TShark", "Network",
   reason="La cattura richiede root (puo' leggere .pcap gia' salvati).",
   help="Tipo: sniffer. Wireshark da terminale.")
_n("masscan", "Masscan", "Network",
   reason="Usa raw socket per la velocita': richiede root.",
   help="Tipo: port scan. Scanner di porte ultrarapido.")
_n("hping3", "hping3", "Network",
   reason="Crea pacchetti grezzi: richiede root.",
   help="Tipo: networking. Generatore di pacchetti custom.")
_n("arpscan", "arp-scan", "Network",
   reason="Scansione ARP: richiede raw socket e root.",
   help="Tipo: enum. Scopre host via ARP sulla LAN.")
_n("netdiscover", "Netdiscover", "Network",
   reason="Sniffing ARP passivo: richiede monitor/raw e root.",
   help="Tipo: enum. Scopre host via ARP.")
_n("wireshark", "Wireshark (GUI)", "Reverse",
   reason="Interfaccia grafica: serve un desktop X11 (usa TShark da CLI).",
   help="Tipo: sniffer GUI. Analisi di traffico.")
_n("burpsuite", "Burp Suite (GUI)", "Web",
   reason="Interfaccia grafica Java: serve un desktop X11.",
   help="Tipo: proxy web GUI. Test di web app.")
_n("zaproxy", "OWASP ZAP (GUI)", "Web",
   reason="Interfaccia grafica Java: serve un desktop X11.",
   help="Tipo: scanner web GUI.")
_n("ghidra", "Ghidra (GUI)", "Reverse",
   reason="GUI Java pesante: serve desktop X11 e molta RAM.",
   help="Tipo: reverse GUI. Disassembler/decompiler.")
_n("autopsy", "Autopsy (GUI)", "Forensics",
   reason="Interfaccia grafica/web pesante: serve un desktop.",
   help="Tipo: forense GUI. Analisi disco.")


# ========================================================================= #
# PROFILI (come sec-profile-* della distro): set di tool installabili insieme.
# Elencano solo tool FUNZIONANTI su telefono.
# ========================================================================= #
PROFILES: dict[str, dict] = {
    "pentest": {
        "name": "Pen Testing", "icon": "🎯",
        "desc": "Scansione, exploit, brute force, Active Directory.",
        "tools": ["nmap_quick", "nmap_ping", "dig", "sqlmap", "hydra", "john",
                  "hashcat", "metasploit", "searchsploit", "medusa", "ncrack",
                  "patator", "crowbar", "enum4linux", "smbmap", "impacket",
                  "netexec", "evil_winrm", "bloodhound_py", "routersploit", "set",
                  "naabu", "socat", "ncat", "sipvicious", "nuclei"],
    },
    "pentest_lite": {
        "name": "Pen Testing Lite", "icon": "⚡",
        "desc": "Essenziale e leggero: recon, scan, injection, brute, cracking, "
                "SMB. Senza Metasploit/Exploit-DB.",
        # john sostituisce hashcat (CPU, niente OpenCL); hashid identifica gli hash.
        "tools": ["nmap_quick", "nmap_ping", "dig", "naabu", "sqlmap", "nuclei",
                  "hydra", "john", "hashid", "enum4linux", "smbmap", "netexec",
                  "ncat", "socat"],
    },
    "web": {
        "name": "Web", "icon": "🕸️",
        "desc": "Sicurezza di siti e applicazioni web.",
        # beef_xss escluso dal set di default: è molto pesante (Ruby+Node.js+gem
        # compilate) e poco pratico su telefono. Resta nel catalogo, installabile
        # singolarmente da chi lo vuole davvero.
        "tools": ["whatweb", "nikto", "wafw00f", "wfuzz", "sqlmap", "gobuster",
                  "dirb", "ffuf", "nuclei", "feroxbuster", "wapiti", "joomscan",
                  "sslscan", "dalfox", "wpscan", "commix", "weevely", "mitmproxy",
                  "cewl", "httrack"],
    },
    "osint": {
        "name": "OSINT", "icon": "🔎",
        "desc": "Ricognizione da fonti pubbliche.",
        "tools": ["whois", "rdap", "dig", "dnsrecon", "dnsenum", "theharvester",
                  "recon_ng", "shodan", "holehe", "sherlock", "subfinder", "amass",
                  "spiderfoot", "metagoofil", "exiftool", "dmitry"],
    },
    "forensics": {
        "name": "Forensics", "icon": "🧪",
        "desc": "Analisi forense, steganografia, malware.",
        "tools": ["exiftool", "binwalk", "foremost", "scalpel", "testdisk",
                  "sleuthkit", "steghide", "stegseek", "yara", "clamav",
                  "chkrootkit", "rkhunter", "lynis", "bulk_extractor",
                  "volatility3", "fcrackzip", "pdfcrack", "hashid", "ophcrack"],
    },
    "reverse": {
        "name": "Reverse", "icon": "🧩",
        "desc": "Reverse engineering, debug, analisi APK.",
        "tools": ["radare2", "gdb", "strace", "ltrace", "jadx", "apktool",
                  "binutils", "hexedit", "pev", "floss"],
    },
}


def profiles_list() -> list[dict]:
    """Elenco dei profili per la UI."""
    return [{"key": k, "name": v["name"], "icon": v["icon"],
             "desc": v["desc"], "tools": v["tools"]} for k, v in PROFILES.items()]


# --------------------------------------------------------------------------- #
# Comandi di installazione (usati dalla PWA per installare senza toccare Termux)
# --------------------------------------------------------------------------- #

# I nomi dei pacchetti provengono SOLO dal registry (non dall'utente): questo
# regex e' una difesa in profondita' contro caratteri inattesi nelle stringhe
# passate a "bash -lc".
_PKG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+._-]*$")


def _pkg_of(tool_id: str, t: dict) -> str:
    pkg = t.get("pkg") or BIN.get(tool_id) or tool_id
    if not _PKG_RE.match(pkg):
        raise ValueError(f"Nome pacchetto non valido: {pkg!r}")
    return pkg


# Alcuni pacchetti Termux vivono in repository aggiuntivi (root-repo, tur-repo):
# li abilitiamo come fallback se il primo tentativo non trova il pacchetto.
_TERMUX_EXTRA_REPOS = "root-repo tur-repo"

# Dentro il Debian in proot NON esiste un init (systemd/cron): i postinst che
# provano ad avviare o registrare servizi falliscono (es. "systemd",
# "cron-daemon-common"). policy-rc.d che ritorna 101 dice a dpkg di NON avviare
# alcun demone durante l'installazione, così la configurazione non si blocca.
_PROOT_APT_PREP = (
    'mkdir -p /usr/sbin && printf "#!/bin/sh\\nexit 101\\n" > /usr/sbin/policy-rc.d '
    '&& chmod +x /usr/sbin/policy-rc.d; '
)

# apt in proot: niente Recommends (installazioni più leggere, non trascina
# cron/systemd & co.) e risposta automatica ai conflitti di configurazione.
_APT_INSTALL = (
    'DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends '
    '-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold'
)

# Script (da eseguire DENTRO il Debian in proot) che abilita il repo Kali, così
# diventano installabili i pacchetti di sicurezza di Kali. Idempotente.
_KALI_ENABLE_INNER = (
    'echo "deb https://http.kali.org/kali kali-rolling main contrib non-free" '
    '> /etc/apt/sources.list.d/kali.list; '
    'apt-get update -o Acquire::AllowInsecureRepositories=true '
    '-o Acquire::AllowDowngradeToInsecureRepositories=true || true; '
    'DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-unauthenticated '
    'kali-archive-keyring || true; apt-get update'
)


def install_command(tool_id: str) -> list[str]:
    """argv per installare UN tool, in base a runtime/pip/repo.

    - pip            -> pip install <pkg>
    - runtime termux -> pkg install -y <pkg> (con fallback su root-repo/tur-repo)
    - proot/kali     -> apt-get install -y <pkg> dentro il Debian
    """
    t = TOOLS.get(tool_id)
    if t is None:
        raise ValueError("Tool sconosciuto.")
    if t.get("works") is False:
        raise ValueError(t.get("reason", "Non installabile su questo telefono."))
    if t.get("mode") in ("native", "stream"):
        raise ValueError("Questo elemento non richiede installazione.")
    pkg = _pkg_of(tool_id, t)
    if t.get("pip"):
        # --prefer-binary: usa i wheel pre-compilati quando esistono, evitando
        # build da sorgente che su Termux spesso falliscono.
        return ["pip", "install", "--prefer-binary", pkg]
    if t.get("runtime") == "termux":
        return ["bash", "-lc",
                f"pkg install -y {pkg} || "
                f"(pkg install -y {_TERMUX_EXTRA_REPOS} && pkg install -y {pkg})"]
    # proot: se il tool richiede il repo Kali, abilitalo prima (idempotente).
    pre = (_KALI_ENABLE_INNER + "; ") if t.get("repo") == "kali" else ""
    return list(PROOT) + ["bash", "-lc",
                          f"{_PROOT_APT_PREP}{pre}apt-get update; "
                          f"{_APT_INSTALL} {pkg}"]


def install_profile_command(key: str, skip: set | None = None) -> list[str]:
    """argv (bash -lc) che installa i tool MANCANTI di un profilo, in blocchi
    per runtime (Termux / pip / Debian). `skip` = id gia' installati da saltare.
    """
    prof = PROFILES.get(key)
    if not prof:
        raise ValueError("Profilo sconosciuto.")
    skip = skip or set()
    termux, pip, debian = [], [], []
    needs_kali = False
    for tid in prof["tools"]:
        t = TOOLS.get(tid)
        if not t or t.get("works") is False or tid in skip:
            continue
        if t.get("mode") in ("native", "stream"):
            continue
        pkg = _pkg_of(tid, t)
        if t.get("pip"):
            pip.append(pkg)
        elif t.get("runtime") == "termux":
            termux.append(pkg)
        else:
            debian.append(pkg)
            if t.get("repo") == "kali":
                needs_kali = True

    parts = []
    # Ogni pacchetto è tentato singolarmente: se uno fallisce NON blocca gli altri,
    # e alla fine di ogni blocco viene stampato l'elenco dei non installati.
    if termux:
        pkgs = " ".join(sorted(set(termux)))
        parts.append(
            'echo "== pacchetti Termux =="; '
            f'pkg install -y {_TERMUX_EXTRA_REPOS} >/dev/null 2>&1 || true; '
            f'F=""; for p in {pkgs}; do pkg install -y "$p" || F="$F $p"; done; '
            '[ -n "$F" ] && echo "!! Termux non installati:$F" || echo "Termux: ok"')
    if pip:
        pkgs = " ".join(sorted(set(pip)))
        parts.append(
            'echo "== tool Python (pip) =="; '
            f'F=""; for p in {pkgs}; do pip install --prefer-binary "$p" || F="$F $p"; done; '
            '[ -n "$F" ] && echo "!! pip non installati:$F" || echo "pip: ok"')
    if debian:
        pkgs = " ".join(sorted(set(debian)))
        inner = (
            'apt-get update; F=""; '
            f'for p in {pkgs}; do {_APT_INSTALL} "$p" || F="$F $p"; done; '
            '[ -n "$F" ] && echo "!! Debian non installati:$F" || echo "Debian: ok"')
        if needs_kali:            # abilita il repo Kali prima di installare
            inner = _KALI_ENABLE_INNER + "; " + inner
        inner = _PROOT_APT_PREP + inner   # niente avvio servizi in proot
        # inner tra apici singoli: le sue variabili ($p/$F) le valuta la shell
        # DENTRO proot, non quella esterna.
        parts.append('echo "== nel Debian (proot) =="; '
                     "proot-distro login debian -- bash -lc '" + inner + "'")

    script = " ; ".join(parts) if parts else 'echo "Niente da installare: tutto gia\' presente."'
    return ["bash", "-lc", script]


def uninstall_profile_command(key: str) -> list[str]:
    """argv (bash -lc) che RIMUOVE i tool di un profilo, per avvicinarsi allo
    stato precedente all'installazione. Per sicurezza NON tocca:
      - i tool di BASE (non del catalogo),
      - i pacchetti condivisi con un altro profilo,
      - i tool "native"/"stream" (non installano nulla).
    Su Debian esegue anche `apt-get autoremove` per liberare le dipendenze.
    """
    prof = PROFILES.get(key)
    if not prof:
        raise ValueError("Profilo sconosciuto.")

    # Pacchetti da PRESERVARE: quelli usati da tool di BASE (non del catalogo) e
    # quelli richiesti da un ALTRO profilo. Es.: `ncat` usa il pacchetto `nmap`,
    # condiviso con i tool base nmap_quick/nmap_ping -> non va rimosso.
    keep = set()
    for tid, t in TOOLS.items():
        if t.get("mode") in ("native", "stream") or t.get("works") is False:
            continue
        if not t.get("catalog"):        # tool di base: proteggi il suo pacchetto
            keep.add(_pkg_of(tid, t))
    for k, p in PROFILES.items():
        if k == key:
            continue
        for tid in p["tools"]:
            t = TOOLS.get(tid)
            if t and t.get("mode") not in ("native", "stream") and t.get("works") is not False:
                keep.add(_pkg_of(tid, t))

    termux, pip, debian = [], [], []
    for tid in prof["tools"]:
        t = TOOLS.get(tid)
        if not t or t.get("mode") in ("native", "stream") or t.get("works") is False:
            continue
        if not t.get("catalog"):        # non rimuovere i tool di base
            continue
        pkg = _pkg_of(tid, t)
        if pkg in keep:                 # condiviso con un altro profilo
            continue
        if t.get("pip"):
            pip.append(pkg)
        elif t.get("runtime") == "termux":
            termux.append(pkg)
        else:
            debian.append(pkg)

    parts = []
    if termux:
        pkgs = " ".join(sorted(set(termux)))
        parts.append('echo "== rimuovo (Termux) =="; F=""; '
                     f'for p in {pkgs}; do pkg uninstall -y "$p" || F="$F $p"; done; '
                     '[ -n "$F" ] && echo "!! non rimossi:$F" || echo "Termux: ok"')
    if pip:
        pkgs = " ".join(sorted(set(pip)))
        parts.append('echo "== rimuovo (pip) =="; F=""; '
                     f'for p in {pkgs}; do pip uninstall -y "$p" || F="$F $p"; done; '
                     '[ -n "$F" ] && echo "!! non rimossi:$F" || echo "pip: ok"')
    if debian:
        pkgs = " ".join(sorted(set(debian)))
        inner = ('F=""; '
                 f'for p in {pkgs}; do DEBIAN_FRONTEND=noninteractive '
                 'apt-get remove -y "$p" || F="$F $p"; done; '
                 'DEBIAN_FRONTEND=noninteractive apt-get autoremove -y; '
                 '[ -n "$F" ] && echo "!! non rimossi:$F" || echo "Debian: ok"')
        parts.append('echo "== rimuovo (Debian/proot) =="; '
                     "proot-distro login debian -- bash -lc '" + inner + "'")

    script = (" ; ".join(parts) if parts
              else 'echo "Niente da rimuovere: solo tool di base o condivisi con altri profili."')
    return ["bash", "-lc", script]


def install_package_command(repo: str, pkgs: str) -> list[str]:
    """argv per installare uno o piu' pacchetti QUALSIASI per nome.

    Sblocca l'intero parco pacchetti dei repository gia' presenti, oltre al
    catalogo curato: repo "termux" (pkg), "debian" (apt in proot), "kali"
    (apt in proot col repo Kali abilitato). I nomi sono validati con _PKG_RE.
    """
    names = [p for p in pkgs.split() if p]
    if not names:
        raise ValueError("Nessun pacchetto indicato.")
    for n in names:
        if not _PKG_RE.match(n):
            raise ValueError(f"Nome pacchetto non valido: {n!r}")
    joined = " ".join(names)
    if repo == "termux":
        return ["bash", "-lc",
                f"pkg install -y {joined} || "
                f"(pkg install -y {_TERMUX_EXTRA_REPOS} && pkg install -y {joined})"]
    if repo in ("debian", "kali"):
        # per "kali" abilita prima il repo Kali (idempotente), poi installa.
        pre = (_KALI_ENABLE_INNER + "; ") if repo == "kali" else ""
        return list(PROOT) + ["bash", "-lc",
                              f"{pre}apt-get update; "
                              f"DEBIAN_FRONTEND=noninteractive apt-get install -y {joined}"]
    raise ValueError("Repository sconosciuto (usa termux/debian/kali).")


# Azioni di manutenzione whitelisted (nessun input dall'utente).
def system_command(action: str) -> list[str]:
    """argv per un'azione di sistema whitelisted (aggiornamenti / repo Kali)."""
    if action == "update-termux":
        return ["bash", "-lc", "pkg update -y && pkg upgrade -y"]
    if action == "update-app":
        repo = str(Path(__file__).parent)
        # Prova il fast-forward; se la cronologia è divergente (es. dopo un
        # rewrite/force-push sul repo) NON si blocca: allinea con reset --hard
        # a origin/master (i file non tracciati restano). È un deploy di sola
        # lettura: nessuna modifica locale da preservare.
        return ["bash", "-lc",
                f'cd "{repo}" && git fetch origin && '
                '{ git merge --ff-only origin/master || '
                '(echo "Cronologia divergente: allineo a origin/master…"; '
                'git reset --hard origin/master); }']
    if action == "update-debian":
        return list(PROOT) + ["bash", "-lc",
                              "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade"]
    if action == "enable-kali":
        # Abilita (una volta sola) il repo Kali dentro il Debian in proot, cosi'
        # diventano installabili i pacchetti di sicurezza di Kali.
        script = (
            'set -e; '
            'echo "deb https://http.kali.org/kali kali-rolling main contrib non-free" '
            '> /etc/apt/sources.list.d/kali.list; '
            'apt-get update -o Acquire::AllowInsecureRepositories=true '
            '-o Acquire::AllowDowngradeToInsecureRepositories=true || true; '
            'DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-unauthenticated kali-archive-keyring; '
            'apt-get update; echo "== Repo Kali abilitato =="'
        )
        return list(PROOT) + ["bash", "-lc", script]
    if action == "setup-autostart":
        repo = str(Path(__file__).parent)
        return ["bash", "-lc",
                f'mkdir -p ~/.termux/boot && '
                f'cp "{repo}/boot/start-nexussec.sh" ~/.termux/boot/start-nexussec.sh && '
                f'chmod +x ~/.termux/boot/start-nexussec.sh && '
                f'echo "Autostart ABILITATO. Installa l\'app Termux:Boot (F-Droid) e riavvia il telefono."']
    if action == "disable-autostart":
        return ["bash", "-lc",
                'rm -f ~/.termux/boot/start-nexussec.sh && '
                'echo "Autostart DISABILITATO. Il server non partirà più da solo all\'accensione." || '
                'echo "Nessun autostart configurato."']
    raise ValueError("Azione di sistema sconosciuta.")


def detection_targets() -> tuple[dict, dict]:
    """(termux_bins, proot_bins): {tool_id: binario} da verificare per runtime.

    Esclude i tool "native" (sempre disponibili). Usato dal server per marcare
    quali tool sono installati, cosi' la UI mostra un pulsante attivo per ognuno.
    """
    tb, pb = {}, {}
    for tid, t in TOOLS.items():
        if t.get("mode") == "native":
            continue
        b = BIN.get(tid)
        if not b:
            continue
        (tb if t.get("runtime") == "termux" else pb)[tid] = b
    return tb, pb


def exec_prefix(tool_id: str) -> list[str]:
    """Prefisso di esecuzione in base al runtime del tool.

    - "termux": nessun prefisso, il binario gira direttamente in Termux;
    - "proot" (o assente): il comando gira dentro il Debian minimale.
    I tool "native" non eseguono binari e non devono passare da qui.
    """
    tool = TOOLS.get(tool_id)
    if tool is None:
        raise ValueError("Tool sconosciuto.")
    return [] if tool.get("runtime") == "termux" else list(PROOT)


def tools_by_category() -> dict[str, list]:
    """Elenco dei tool per la UI, raggruppati per categoria."""
    out: dict[str, list] = {}
    for tid, t in TOOLS.items():
        out.setdefault(t["category"], []).append(
            {"id": tid, "name": t["name"], "mode": t["mode"],
             "runtime": t.get("runtime"),      # "termux" | "proot" | None (native)
             "bin": BIN.get(tid),              # binario da rilevare
             "pkg": t.get("pkg"),              # pacchetto da installare (se != bin)
             "repo": t.get("repo"),            # "kali" se serve il repo Kali nel Debian
             "catalog": t.get("catalog", False),   # tool extra, mostrato su richiesta
             "pip": t.get("pip", False),            # installabile via pip
             "works": t.get("works", True),         # False = non usabile su stock
             "reason": t.get("reason"),             # perche' non funziona (se works False)
             "target": t["target"], "help": t.get("help", ""),
             "params": t.get("params"),             # schema opzioni grafiche (opzionale)
             "hints": t.get("hints"),               # suggerimenti di flag (chip tappabili)
             "root_flags": t.get("root_flags"),     # flag che richiedono root ("(solo root)")
             # tool bloccato specificamente perche' richiede root (badge "(solo root)")
             "root_only": t.get("works", True) is False
                          and "root" in (t.get("reason") or "").lower(),
             "cmdline": " ".join(t.get("cmd", [])),  # comando base per l'anteprima
             "anon_ok": t.get("anon_ok", False), "force_anon": t.get("force_anon", False)}
        )
    return out


# --------------------------------------------------------------------------- #
# Validazione input
# --------------------------------------------------------------------------- #

# host / IP / hostname / CIDR
_HOST_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._:-]*[A-Za-z0-9])?(?:/\d{1,3})?$")
# url http(s)
_URL_RE = re.compile(r"^https?://[A-Za-z0-9._:-]+(?:/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*)?$")


def validate_target(kind: str, value: str) -> str:
    """Ritorna il target ripulito o solleva ValueError se non e' valido."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Target mancante.")
    if value.startswith("-"):
        raise ValueError("Target non valido (non puo' iniziare con '-').")
    if kind == "host" and _HOST_RE.match(value):
        return value
    if kind == "url" and _URL_RE.match(value):
        return value
    raise ValueError(f"Target non valido per il tipo '{kind}'.")
