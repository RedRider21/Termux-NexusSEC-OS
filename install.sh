#!/data/data/com.termux/files/usr/bin/bash
#
# install.sh - Bootstrap dell'ambiente "Termux-NexusSEC-OS"
#
# Strategia a TRE LIVELLI per ridurre lo spazio (~200-400 MB invece di ~2 GB):
#   1. Tool "native"  : niente da installare (rdap/whois via HTTP dal server).
#   2. Tool "termux"  : pacchetti nativi Termux (nmap, tor, hydra, john,
#                       aircrack-ng, sqlmap...) - eseguiti direttamente, veloci.
#   3. Tool "proot"   : un Debian MINIMALE via proot-distro, solo per i pochi
#                       tool non disponibili in Termux (whatweb, nikto).
#
# Metasploit e' pesante e non e' nei repo Debian standard: disattivato di
# default, abilitalo (installer ufficiale Rapid7 dentro il Debian) con:
#     INSTALL_METASPLOIT=yes ./install.sh
#
# Idempotente: puoi rilanciarlo, salta cio' che e' gia' fatto.

set -euo pipefail

DISTRO="debian"
INSTALL_METASPLOIT="${INSTALL_METASPLOIT:-no}"
ENABLE_KALI_REPO="${ENABLE_KALI_REPO:-no}"    # abilita il repo Kali nel Debian

log()  { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; }

# --- 0. Controllo di essere davvero in Termux -------------------------------
if [ -z "${PREFIX:-}" ] || [ ! -d "/data/data/com.termux" ]; then
    err "Questo script va eseguito dentro Termux."
    exit 1
fi

# Installa un pacchetto Termux "best-effort": avvisa ma non interrompe se manca.
pkg_try() {
    if pkg install -y "$1" >/dev/null 2>&1; then
        log "  ok: $1"
    else
        warn "  non installato: $1 (repo non disponibile su questa versione di Termux)"
        MISSING="${MISSING:-} $1"
    fi
}

# --- 1. Base Termux (repo main: deve funzionare) ----------------------------
log "Aggiorno i pacchetti di Termux..."
pkg update -y && pkg upgrade -y

log "Installo i pacchetti base (proot-distro, python, ttyd, git)..."
pkg install -y proot-distro python ttyd git

log "Installo i tool nativi di rete/anonimato (nmap, tor, proxychains, whois, dig)..."
pkg install -y nmap tor proxychains-ng whois curl dnsutils

# --- 2. Tool Termux "extra" (root-repo: best-effort) ------------------------
log "Abilito root-repo e installo i cracker/scanner nativi..."
pkg install -y root-repo >/dev/null 2>&1 || warn "root-repo non abilitato (continuo)"
MISSING=""
for t in hydra john aircrack-ng sqlmap; do
    pkg_try "$t"
done

# --- 3. Dipendenze Python del ponte (stack LEGGERO per Termux) --------------
# IMPORTANTE: su Termux la libc e' bionic, quindi i wheel "manylinux" di PyPI non
# sono compatibili. Con "uvicorn[standard]" o pydantic v2, pip prova a COMPILARE
# da sorgente (uvloop, httptools, watchfiles e pydantic-core, alcuni in Rust) e
# l'installazione si BLOCCA per minuti/all'infinito.
# A noi basta lo stack puro-Python: fastapi<0.100 + pydantic v1 + uvicorn +
# websockets. Si installa in pochi secondi, senza compilare nulla.
log "Installo il ponte web (FastAPI + uvicorn, stack leggero per Termux)..."
pkg install -y python-pip >/dev/null 2>&1 || true
python -m pip install --no-input --disable-pip-version-check \
    "fastapi<0.100" "pydantic<2" "uvicorn" "websockets"

# sqlmap: se il pacchetto Termux non c'e', ripiego su pip (e' puro Python).
if ! command -v sqlmap >/dev/null 2>&1; then
    warn "sqlmap non trovato come pacchetto: provo via pip..."
    python -m pip install sqlmap >/dev/null 2>&1 && log "  ok: sqlmap (pip)" \
        || warn "  sqlmap non installato: puoi aggiungerlo dopo con 'pip install sqlmap'"
fi

# --- 4. proxychains di Termux (instrada il TCP via Tor su 127.0.0.1:9050) ----
log "Configuro proxychains di Termux..."
cat > "$PREFIX/etc/proxychains.conf" <<EOF
# Generato da install.sh (Termux-NexusSEC-OS) - instrada il TCP via Tor
strict_chain
proxy_dns
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000
[ProxyList]
socks5 127.0.0.1 9050
EOF

# --- 5. Debian minimale in proot (solo per whatweb / nikto) -----------------
if proot-distro login "$DISTRO" -- true >/dev/null 2>&1; then
    log "Debian ($DISTRO) risulta gia' installato, salto il download."
else
    log "Installo Debian minimale ($DISTRO) via proot-distro (~150-300 MB)..."
    proot-distro install "$DISTRO"
fi

log "Aggiorno gli indici dei pacchetti dentro Debian..."
proot-distro login "$DISTRO" -- apt-get update -y

# Best-effort per un SINGOLO pacchetto Debian: avvisa ma NON interrompe lo script
# (fondamentale: con set -e un "unable to locate package X" abortirebbe tutto).
proot_pkg_try() {
    if proot-distro login "$DISTRO" -- apt-get install -y --no-install-recommends "$1" >/dev/null 2>&1; then
        log "  ok: $1"
    else
        warn "  non installato: $1 (non nei repo Debian di questa versione)"
        MISSING="${MISSING:-} $1"
    fi
}

# whatweb/nikto (Ruby/Perl, non nativi in Termux) + proxychains4 (anonimato via Tor)
# + i tool extra. TUTTI best-effort e uno per uno: se nikto/whatweb non sono nei repo
# di questa versione di Debian, il resto viene installato lo stesso.
log "Installo i tool di supporto in Debian (whatweb, nikto, proxychains4, dnsrecon, wafw00f, wfuzz)..."
for t in ca-certificates curl proxychains4 whatweb nikto dnsrecon wafw00f wfuzz; do
    proot_pkg_try "$t"
done

log "Configuro proxychains dentro Debian..."
proot-distro login "$DISTRO" -- bash -c 'cat > /etc/proxychains4.conf <<EOF
# Generato da install.sh (Termux-NexusSEC-OS) - instrada il TCP via Tor
strict_chain
proxy_dns
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000
[ProxyList]
socks5 127.0.0.1 9050
EOF'

# --- 5b. Repo Kali opzionale (per i tool del catalogo, on-demand) -----------
if [ "$ENABLE_KALI_REPO" = "yes" ]; then
    log "Abilito il repo di Kali dentro Debian (per i tool del catalogo)..."
    proot-distro login "$DISTRO" -- bash -c '
        apt-get update || true
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            ca-certificates gnupg curl wget || true
        install -d -m 0755 /usr/share/keyrings
        if [ ! -s /usr/share/keyrings/kali-archive-keyring.gpg ]; then
            (curl -fsSL https://archive.kali.org/archive-key.asc \
                || wget -qO- https://archive.kali.org/archive-key.asc) \
                | gpg --dearmor -o /usr/share/keyrings/kali-archive-keyring.gpg 2>/dev/null || true
        fi
        if [ -s /usr/share/keyrings/kali-archive-keyring.gpg ]; then
            echo "deb [signed-by=/usr/share/keyrings/kali-archive-keyring.gpg] http://http.kali.org/kali kali-rolling main contrib non-free" \
                > /etc/apt/sources.list.d/kali.list
        else
            echo "deb [trusted=yes] http://http.kali.org/kali kali-rolling main contrib non-free" \
                > /etc/apt/sources.list.d/kali.list
        fi
        apt-get update
    ' && log "Repo Kali abilitato: ora 'apt install <tool>' vede il catalogo Kali." \
      || warn "Abilitazione repo Kali fallita (continuo)."
else
    warn "Repo Kali non abilitato. Per i tool del catalogo: ENABLE_KALI_REPO=yes ./install.sh"
fi

# --- 6. Metasploit opzionale (installer ufficiale Rapid7 dentro Debian) -----
if [ "$INSTALL_METASPLOIT" = "yes" ]; then
    log "Installo Metasploit Framework dentro Debian (pesante, puo' fallire su arm64)..."
    proot-distro login "$DISTRO" -- bash -c '
        set -e
        curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb -o /usr/local/bin/msfinstall
        chmod +x /usr/local/bin/msfinstall
        /usr/local/bin/msfinstall
    ' || warn "Installazione di Metasploit fallita (arch non supportata o rete). Puoi riprovare dopo."
else
    warn "Metasploit NON installato. Per aggiungerlo: INSTALL_METASPLOIT=yes ./install.sh"
fi

# --- 6b. Consenti al launcher APK di avviare il server (intent RUN_COMMAND) --
# L'app NexusSEC (WebView) chiede a Termux di eseguire server.py: serve
# "allow-external-apps=true" in ~/.termux/termux.properties.
log "Abilito allow-external-apps in termux.properties (per l'APK launcher)..."
mkdir -p "$HOME/.termux"
TP="$HOME/.termux/termux.properties"
touch "$TP"
if grep -qE '^[[:space:]]*#?[[:space:]]*allow-external-apps' "$TP"; then
    sed -i 's/^[[:space:]]*#\?[[:space:]]*allow-external-apps.*/allow-external-apps=true/' "$TP"
else
    printf '\nallow-external-apps=true\n' >> "$TP"
fi
command -v termux-reload-settings >/dev/null 2>&1 && termux-reload-settings || true

# --- 6c. Comando "nexussec" + avvio automatico all'apertura di Termux --------
# Cartella reale del progetto (dove si trova questo install.sh).
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

log "Creo il comando 'nexussec' (avvia il server da qualunque cartella)..."
cat > "$PREFIX/bin/nexussec" <<'NEXX'
#!/data/data/com.termux/files/usr/bin/bash
# nexussec - avvia (una sola volta) il server NexusSEC. Idempotente.
REPO="__REPO_DIR__"
[ -d "$REPO" ] || REPO="$HOME/Termux-NexusSEC-OS"
if pgrep -f "server\.py" >/dev/null 2>&1; then
    echo "NexusSEC: server gia' attivo -> http://127.0.0.1:8000"
    exit 0
fi
PY="$(command -v python || command -v python3)"
[ -n "$PY" ] || { echo "NexusSEC: python non installato (pkg install python)"; exit 1; }
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock 2>/dev/null
cd "$REPO" 2>/dev/null || { echo "NexusSEC: cartella $REPO non trovata"; exit 1; }
nohup "$PY" server.py >"$HOME/nexussec.log" 2>&1 &
sleep 1
echo "NexusSEC: server avviato -> http://127.0.0.1:8000  (log: ~/nexussec.log)"
NEXX
sed -i "s|__REPO_DIR__|$REPO_DIR|" "$PREFIX/bin/nexussec"
chmod +x "$PREFIX/bin/nexussec"

# Avvia il server quando apri Termux (idempotente: niente se e' gia' attivo).
BRC="$HOME/.bashrc"
if ! grep -q "NexusSEC autostart" "$BRC" 2>/dev/null; then
    log "Aggiungo l'avvio automatico all'apertura di Termux (~/.bashrc)..."
    cat >> "$BRC" <<'BRCEOF'

# >>> NexusSEC autostart >>>
# Avvia il server NexusSEC all'apertura di Termux (non fa nulla se e' gia' attivo).
# Per disattivarlo: rimuovi questo blocco, oppure  export NEXUSSEC_NO_AUTOSTART=1
if [ -z "$NEXUSSEC_NO_AUTOSTART" ] && command -v nexussec >/dev/null 2>&1; then
    nexussec >/dev/null 2>&1
fi
# <<< NexusSEC autostart <<<
BRCEOF
fi

# --- 7. Fine ----------------------------------------------------------------
log "Installazione completata."
if [ -n "${MISSING# }" ]; then
    warn "Tool Termux non installati:${MISSING}. Il resto funziona lo stesso."
fi
echo
echo "Per avviare l'interfaccia, da QUALSIASI cartella, scrivi:"
echo "    nexussec"
echo "Poi apri nel browser del telefono:  http://127.0.0.1:8000"
echo
echo "D'ora in poi il server parte DA SOLO quando apri Termux (e resta attivo)."
echo "L'app NexusSEC (launcher APK) puo' avviarlo da sola; in ogni caso, se tocchi"
echo "'Apri Termux' dall'app, il server parte all'apertura e l'app si collega."
echo
echo "NOTA: se avevi Termux gia' aperto, CHIUDILO e riaprilo una volta (l'avvio"
echo "automatico e allow-external-apps hanno effetto dalla nuova sessione)."
