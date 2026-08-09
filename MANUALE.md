# Manuale d'uso — Termux-NexusSEC-OS

Guida semplice, passo per passo, per un utente medio. Ti serve solo un telefono
**Android** (senza root). Tutto il resto lo fai una volta e poi comandi dall'app.

> ⚠️ **Uso legale.** Usa questi strumenti **solo** su reti, siti e dispositivi
> tuoi o per cui hai un permesso scritto. L'uso non autorizzato è reato.

---

## In breve (cosa stai per fare)

1. Installi **Termux** (un'app che dà un terminale Linux su Android).
2. Con 6 righe incollate una sola volta, scarichi e installi NexusSEC-OS.
3. Apri l'app nel browser: da lì fai **tutto** (aggiornamenti, installazioni,
   avvio degli strumenti) **senza più scrivere comandi** in Termux.

---

## Passo 1 — Installa Termux (l'app terminale)

⚠️ **Non usare la versione del Play Store** (è vecchia e non si aggiorna).

Scegli **uno** di questi modi:

- **Consigliato — pagina download del progetto:**
  apri sul telefono → **https://dplusos21.github.io/Termux-NexusSEC-OS/**
  e tocca il pulsante giusto (di solito **arm64-v8a**).
- **Oppure F-Droid:** https://f-droid.org/en/packages/com.termux/
- **Oppure APK ufficiale GitHub:** https://github.com/termux/termux-app/releases/latest

Dopo il download, Android chiederà il permesso di installare da "origini
sconosciute": **accetta**. Poi apri **Termux**.

---

## Passo 2 — Installa NexusSEC-OS (una volta sola)

Apri Termux e **incolla queste righe** (tieni premuto nello schermo → *Incolla*).
Premi Invio dopo l'ultima. Scarica ~700 MB–1 GB: **meglio sotto Wi-Fi**.

```bash
pkg update -y && pkg upgrade -y
termux-setup-storage
pkg install -y git python
git clone https://github.com/dPlusOS21/Termux-NexusSEC-OS.git
cd Termux-NexusSEC-OS
bash install.sh
```

`install.sh` fa tutto da solo: installa gli strumenti base, prepara il piccolo
Debian di supporto e Tor. Aspetta che finisca (qualche minuto).

---

## Passo 3 — Avvia l'app

Sempre in Termux, dalla cartella del progetto:

```bash
python server.py
```

Vedrai una riga tipo *"Uvicorn running on http://127.0.0.1:8000"*.
**Lascia Termux aperto** e apri il **browser** del telefono su:

> **http://127.0.0.1:8000**

Questa è l'interfaccia (una web-app). Da qui in poi comandi da qui.

> 💡 **Come funziona (in una frase):** Termux fa girare un piccolo *server locale*
> sul telefono (solo sul telefono, `127.0.0.1`); l'app nel browser gli parla e lui
> lancia gli strumenti per te e ti mostra i risultati.

---

## Passo 4 — Usa l'app

- **Home:** le schede degli strumenti, divise per categoria.
- **Ogni scheda** ha un'etichetta che dice cosa fa il tocco:
  - `» run` → esegue e mostra il risultato;
  - `▮ terminale` → apre un terminale interattivo;
  - `◈ flusso live` → **output in diretta** con possibilità di **rispondere**
    (prova la scheda **"Recon demo (flusso live)"**);
  - `＋ da installare` → non è installato: tocca per installarlo (vedi sotto);
  - `❌ non su stock` → non funziona su telefono senza root (spiegato al tocco).
- **🧅 Tor:** instrada il traffico via Tor (per i tool che lo supportano).
- **🧰 Catalogo:** mostra anche i tool non ancora installati.
- **🎨 Tema:** cambia l'aspetto (Terminale, Glass, Neon, Minimal chiaro/scuro).
- **Barra in basso (stile desktop):** pulsante **NexusSEC** = menu, ⌨️ terminale,
  🧅 Tor, orologio.

---

## Passo 5 — Fai tutto dall'app (senza toccare Termux)

Tocca **NexusSEC** (in basso a sinistra) per aprire il menu:

- **MANUTENZIONE**
  - **⟳ Aggiorna Termux** — aggiorna i pacchetti di sistema.
  - **⬇ Aggiorna app** — scarica l'ultima versione del progetto (`git pull`).
  - **🐧 Aggiorna Debian** — aggiorna il Debian di supporto.
  - **⏻ Riavvia server** — riavvia l'app (usalo **dopo "Aggiorna app"**).
- **Installare uno strumento:** tocca una scheda `＋ da installare` → **⬇ Installa
  ora**. Vedi l'installazione **in diretta**; a fine, il pulsante diventa attivo.
- **Installare un profilo intero** (es. *web*, *osint*): scegli il profilo dal menu
  → banner **⬇ Installa profilo** → **Installa ora**. Installa in blocco i mancanti.

Ogni operazione mostra il suo output live: se qualcosa va storto, lo vedi subito.

---

## Passo 6 (consigliato) — Rendila comoda come un'app vera

- **Icona in Home:** nel browser, menu → *"Aggiungi a schermata Home"*. Così apri
  NexusSEC come un'app a schermo intero.

### Avvio automatico all'accensione (autostart)

Così `server.py` parte da solo e non devi più aprire Termux a mano.

1. Installa l'app **Termux:Boot** (dalla pagina download del progetto o da F-Droid).
2. Nell'app NexusSEC: menu **NexusSEC → MANUTENZIONE → 🚀 Abilita autostart**.
3. **Riavvia il telefono.** Da ora il server parte da solo; apri il browser (o
   l'icona in Home) su `http://127.0.0.1:8000`.

> In alternativa a mano, una volta sola:
> ```bash
> mkdir -p ~/.termux/boot
> cp ~/Termux-NexusSEC-OS/boot/start-nexussec.sh ~/.termux/boot/
> chmod +x ~/.termux/boot/start-nexussec.sh
> ```

### Come **fermare** l'autostart

- **Dall'app:** menu **MANUTENZIONE → 🛑 Disabilita autostart** (rimuove lo script
  di avvio). Al prossimo riavvio il server non parte più da solo.
- **A mano** (equivalente): `rm ~/.termux/boot/start-nexussec.sh`
- Per fermare il server **adesso** (senza riavviare): menu **⏻ Riavvia server** non
  lo spegne; per spegnerlo del tutto, in Termux premi **Ctrl+C** nella finestra dove
  gira, oppure: `pkill -f "python server.py"`.
- Per togliere del tutto l'avvio automatico puoi anche **disinstallare l'app
  Termux:Boot**.

## Passo 7 — Installare altri strumenti (oltre al catalogo)

Non sei limitato ai tool in elenco: menu **MANUTENZIONE → ＋ Installa pacchetto**,
scrivi il nome e scegli il repository (**📦 Termux**, **🐧 Debian**, **🐉 Kali**).
Per i pacchetti Kali, la prima volta usa **🐉 Abilita repo Kali**.

---

## Domande frequenti

- **La pagina non si apre / "server non raggiungibile".**
  Torna in Termux: è ancora in esecuzione `python server.py`? Se l'hai chiuso,
  rilancialo. Controlla di aver scritto **http://127.0.0.1:8000**.
- **Ho aggiornato l'app ma non vedo le novità.**
  Menu → **⏻ Riavvia server**, poi ricarica la pagina (a volte serve ricaricare
  due volte per via della cache).
- **Un tool dice "❌ non su stock".**
  Alcuni strumenti (Wi-Fi in monitor mode, attacchi MITM, programmi grafici) non
  possono funzionare su Android senza root: sono elencati solo per completezza.
- **Serve tanto spazio?**
  L'installazione completa occupa ~700 MB–1 GB. Puoi installare solo i profili che
  ti servono.

---

## Nota di sicurezza

Il server ascolta **solo** su `127.0.0.1` (il telefono stesso): non è raggiungibile
da altri sul Wi-Fi. I comandi vengono costruiti dall'app in modo sicuro (nessun
testo libero passato alla shell) e solo gli strumenti in elenco possono partire.

Buon lavoro — e ricorda: **solo test autorizzati**.
