#!/data/data/com.termux/files/usr/bin/bash
#
# nexussec-setup.sh — installazione "tutto in uno" di Termux-NexusSEC-OS.
#
# Uso rapido (dentro Termux, una volta sola):
#   pkg install -y curl && \
#   curl -fsSL https://raw.githubusercontent.com/RedRider21/Termux-NexusSEC-OS/master/nexussec-setup.sh | bash
#
# Oppure, se hai già il repo:  bash nexussec-setup.sh
#
# Variabili opzionali:
#   AUTOSTART=1   configura l'avvio automatico (serve l'app Termux:Boot)
#   KALI=1        abilita anche il repo Kali nel Debian
#   NOSTART=1     non avviare il server alla fine
#
set -e

REPO_URL="https://github.com/RedRider21/Termux-NexusSEC-OS.git"
DEST="$HOME/Termux-NexusSEC-OS"
PORT=8000

say(){ printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }

say "1/5 · Aggiorno Termux"
yes | pkg update -y || pkg update -y
yes | pkg upgrade -y || pkg upgrade -y

say "2/5 · Installo gli strumenti base (git, python, curl)"
pkg install -y git python curl

# Permesso storage (mostra un dialog una volta): non blocca se già concesso.
termux-setup-storage 2>/dev/null || true

say "3/5 · Scarico/aggiorno il progetto"
if [ -d "$DEST/.git" ]; then
  git -C "$DEST" pull --ff-only || true
else
  git clone "$REPO_URL" "$DEST"
fi
cd "$DEST"

say "4/5 · Installo tool e Debian minimale (può richiedere qualche minuto)"
if [ "${KALI:-0}" = "1" ]; then
  ENABLE_KALI_REPO=yes bash install.sh
else
  bash install.sh
fi

# Autostart opzionale.
if [ "${AUTOSTART:-0}" = "1" ]; then
  say "Configuro l'autostart (serve l'app Termux:Boot installata)"
  mkdir -p "$HOME/.termux/boot"
  cp "$DEST/boot/start-nexussec.sh" "$HOME/.termux/boot/start-nexussec.sh"
  chmod +x "$HOME/.termux/boot/start-nexussec.sh"
fi

if [ "${NOSTART:-0}" = "1" ]; then
  say "Fatto. Avvia quando vuoi con:  cd $DEST && python server.py"
  exit 0
fi

say "5/5 · Avvio il server su http://127.0.0.1:$PORT"
if pgrep -f "python server.py" >/dev/null 2>&1; then
  echo "Server già in esecuzione."
else
  nohup python server.py >"$HOME/nexussec.log" 2>&1 &
  sleep 2
fi

# Prova ad aprire il browser sull'app (richiede termux-api, altrimenti apri a mano).
termux-open-url "http://127.0.0.1:$PORT" 2>/dev/null || true

cat <<EOF

  ✅ Pronto!  Apri nel browser:  http://127.0.0.1:$PORT
     (log del server: ~/nexussec.log)

  Da qui in poi fai tutto dall'app: aggiornamenti, installazioni, profili.
  Solo per test autorizzati.
EOF
