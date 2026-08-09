# NexusSEC · Launcher WebView (APK)

App Android minimale che mostra l'interfaccia di **Termux-NexusSEC-OS** a schermo
intero, come se fosse un'app nativa. È solo la "faccia": il motore resta
**`server.py`** dentro Termux (modello a server locale, `http://127.0.0.1:8000`).

> ⚠️ Serve comunque **Termux** con il progetto installato e il server avviato
> (idealmente in **autostart** via Termux:Boot). Il launcher non sostituisce Termux:
> lo affianca. Per un unico APK con tutto preinstallato serve il "Livello B" (fork di
> Termux con bootstrap personalizzato), un lavoro a parte.

## Come ottenere l'APK (senza PC)

1. Vai su **Actions → build-launcher-apk** nel repository GitHub.
2. Apri l'ultima esecuzione riuscita e scarica l'artifact **NexusSEC-launcher-debug**
   (contiene `app-debug.apk`).
3. Sul telefono, apri l'APK e consenti l'installazione da origini sconosciute.

In alternativa, pubblicando una **Release** su GitHub l'APK viene allegato in automatico.

## Come compilarlo tu (con Android Studio o a riga di comando)

Requisiti: JDK 17 + Android SDK (platform 34, build-tools 34).

```bash
cd android-launcher
gradle wrapper --gradle-version 8.7      # una volta sola (crea ./gradlew)
./gradlew assembleDebug
# APK in: app/build/outputs/apk/debug/app-debug.apk
```

Con **Android Studio**: apri la cartella `android-launcher/` e premi *Run*.

## Cosa fa

- WebView a schermo intero su `http://127.0.0.1:8000` (JavaScript + DOM storage
  abilitati, così temi/guida/storico funzionano).
- Tasto **Indietro** = naviga indietro nella PWA.
- Se il server non è ancora attivo, mostra una schermata con **Riprova**.

## Dettagli tecnici

- `applicationId` = `com.nexussec.launcher`, nome app **NexusSEC**.
- `usesCleartextTraffic=true` (necessario per `http`/`ws` verso localhost).
- Nessuna dipendenza AndroidX: usa la `WebView` del framework → build leggera.
- `minSdk 24`, `targetSdk 34`.
