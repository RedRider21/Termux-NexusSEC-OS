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

# Vai nella cartella del progetto (adatta il percorso se l'hai clonato altrove).
cd "$HOME/Termux-NexusSEC-OS" 2>/dev/null || exit 1

# Avvia il server solo se non è già in esecuzione.
if ! pgrep -f "python server.py" >/dev/null 2>&1; then
  nohup python server.py >"$HOME/nexussec.log" 2>&1 &
fi

# Opzionale: apri l'app nel browser all'accensione (scommenta se lo vuoi).
# sleep 3
# termux-open-url http://127.0.0.1:8000
