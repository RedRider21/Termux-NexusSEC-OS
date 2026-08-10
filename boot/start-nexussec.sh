#!/data/data/com.termux/files/usr/bin/sh
#
# start-nexussec.sh — avvio automatico all'accensione via Termux:Boot.
#
# Installazione (una volta sola), fatta anche dal menu della PWA
# (Manutenzione → ⏻ Abilita autostart):
#   mkdir -p ~/.termux/boot
#   cp ~/Termux-NexusSEC-OS/boot/start-nexussec.sh ~/.termux/boot/
#   chmod +x ~/.termux/boot/start-nexussec.sh
# Serve l'app **Termux:Boot** installata; poi riavvia il telefono.

# Tiene la CPU sveglia così il server resta attivo (richiede termux-api opzionale).
termux-wake-lock 2>/dev/null

# Usa il comando "nexussec" (creato da install.sh): avvia il server in modo
# idempotente da qualunque cartella. Fallback se il comando non c'è ancora.
if command -v nexussec >/dev/null 2>&1; then
  nexussec
else
  cd "$HOME/Termux-NexusSEC-OS" 2>/dev/null || exit 1
  if ! pgrep -f "server\.py" >/dev/null 2>&1; then
    nohup python server.py >"$HOME/nexussec.log" 2>&1 &
  fi
fi
