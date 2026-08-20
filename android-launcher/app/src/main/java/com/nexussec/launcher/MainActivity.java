package com.nexussec.launcher;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Launcher WebView di Termux-NexusSEC-OS.
 *
 * A schermo intero (niente barre di sistema). Splash con logo, avviso d'uso legale e
 * un pannello di comandi in basso (Apri Termux, Installa Termux da F-Droid,
 * Installa/Aggiorna NexusSEC). Prova ad avviare il server locale in Termux (intent
 * com.termux.RUN_COMMAND); con "Entra" si accede alla PWA. Lo splash usa la palette
 * del TEMA scelto nella PWA (salvato via ponte JS). "Esci" (dal menu PWA) chiude l'app.
 *
 * Nessuna dipendenza AndroidX: solo il framework Android.
 */
public class MainActivity extends Activity {

    private static final String URL = "http://127.0.0.1:8000";
    private static final String TERMUX_PKG = "com.termux";
    private static final String PREFS = "nexus";
    private static final String SETUP_CMD =
            "pkg install -y curl && curl -fsSL "
          + "https://raw.githubusercontent.com/dPlusOS21/Termux-NexusSEC-OS/master/"
          + "nexussec-setup.sh | bash";
    private static final String UPDATE_CMD =
            "cd ~/Termux-NexusSEC-OS && git pull && bash install.sh";
    private static final long POLL_TIMEOUT_MS = 30000;   // attesa massima avvio server

    // Palette dello splash: rispecchia il tema scelto nella PWA.
    private int cBg = 0xFF050705, cAccent = 0xFF3DFF88, cDim = 0xFF5A7A63,
                cCard = 0xFF0D120D, cBorder = 0xFF16321F, cOnAccent = 0xFF04160A,
                cAmber = 0xFFFFB454;

    private WebView web;
    private TextView status;
    private boolean loaded = false;
    private boolean serverReady = false;
    private boolean pendingEnter = false;
    private boolean wasPaused = false;
    private volatile boolean bootstrapping = false;
    private volatile boolean triedForegroundLaunch = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        loadTheme();
        hideSystemBars();
        setContentView(buildSplash());
        new Thread(this::bootstrap).start();
    }

    /** Carica la palette dal tema salvato dalla PWA (SharedPreferences). */
    private void loadTheme() {
        String t = getSharedPreferences(PREFS, MODE_PRIVATE).getString("theme", "terminal");
        switch (t) {
            case "glass":
                cBg = 0xFF0A0D12; cAccent = 0xFF7FE7D0; cDim = 0xFF93A6BB;
                cCard = 0xFF18202C; cBorder = 0xFF2E3A48; cOnAccent = 0xFF06222A;
                cAmber = 0xFFF4C06A; break;
            case "neon":
                cBg = 0xFF05060A; cAccent = 0xFF39F5C8; cDim = 0xFF6A7BA0;
                cCard = 0xFF0C1120; cBorder = 0xFF1C2B4A; cOnAccent = 0xFF04121A;
                cAmber = 0xFFFFCF5C; break;
            case "minimal-dark":
                cBg = 0xFF131417; cAccent = 0xFF5AA0FF; cDim = 0xFF8B95A3;
                cCard = 0xFF1C1E23; cBorder = 0xFF2C2F36; cOnAccent = 0xFFFFFFFF;
                cAmber = 0xFFE0A63A; break;
            case "minimal-light":
                cBg = 0xFFF4F6F9; cAccent = 0xFF2563EB; cDim = 0xFF5B6675;
                cCard = 0xFFFFFFFF; cBorder = 0xFFE3E6EC; cOnAccent = 0xFFFFFFFF;
                cAmber = 0xFFB7791F; break;
            default: // terminal
                cBg = 0xFF050705; cAccent = 0xFF3DFF88; cDim = 0xFF5A7A63;
                cCard = 0xFF0D120D; cBorder = 0xFF16321F; cOnAccent = 0xFF04160A;
                cAmber = 0xFFFFB454; break;
        }
    }

    // -------------------------------------------------- schermo intero --------
    private void hideSystemBars() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
              | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
              | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
              | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
              | View.SYSTEM_UI_FLAG_FULLSCREEN
              | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemBars();
    }

    // ---------------------------------------------------------------- SPLASH --
    private View buildSplash() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setBackgroundColor(cBg);
        root.setPadding(dp(22), dp(22), dp(22), dp(20));

        root.addView(spacer());

        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.nexus_logo);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(108), dp(108));
        lp.bottomMargin = dp(14);
        logo.setLayoutParams(lp);
        root.addView(logo);

        TextView title = new TextView(this);
        title.setText("NexusSEC");
        title.setTextColor(cAccent);
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 30);
        title.setGravity(Gravity.CENTER);
        title.setTypeface(title.getTypeface(), Typeface.BOLD);
        root.addView(title);

        TextView sub = new TextView(this);
        sub.setText("x Android");
        sub.setTextColor(cDim);
        sub.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
        sub.setGravity(Gravity.CENTER);
        sub.setLetterSpacing(0.25f);
        root.addView(sub);

        status = new TextView(this);
        status.setText("avvio in corso…");
        status.setTextColor(cDim);
        status.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        status.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams stp = wrap();
        stp.topMargin = dp(20);
        status.setLayoutParams(stp);
        root.addView(status);

        // Avviso d'uso legale.
        TextView warn = new TextView(this);
        warn.setText("⚠  Solo per test di sicurezza AUTORIZZATI: usa questi strumenti "
                + "esclusivamente su sistemi tuoi o per cui hai un permesso scritto. "
                + "L'uso non autorizzato è illegale.");
        warn.setTextColor(cAmber);
        warn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        warn.setGravity(Gravity.CENTER);
        warn.setLineSpacing(dp(2), 1f);
        warn.setPadding(dp(16), dp(11), dp(16), dp(11));
        GradientDrawable warnBg = new GradientDrawable();
        warnBg.setColor((cAmber & 0x00FFFFFF) | 0x22000000);
        warnBg.setCornerRadius(dp(12));
        warn.setBackground(warnBg);
        LinearLayout.LayoutParams wp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        wp.topMargin = dp(20);
        warn.setLayoutParams(wp);
        root.addView(warn);

        // Pulsante primario "Entra".
        Button enter = styledButton("Entra  ▸", true, v -> enterApp());
        LinearLayout.LayoutParams ep = wrap();
        ep.topMargin = dp(22);
        enter.setLayoutParams(ep);
        root.addView(enter);

        root.addView(spacer());

        // Pannello comandi in basso (griglia 2x2), stile "desktop".
        root.addView(commandGrid());
        return root;
    }

    /** Griglia 2x2 di comandi in stile pulsante NexusSEC. */
    private View commandGrid() {
        LinearLayout grid = new LinearLayout(this);
        grid.setOrientation(LinearLayout.VERTICAL);
        grid.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout row1 = row();
        row1.addView(cell("⌨  Apri Termux", v -> openTermux()));
        row1.addView(cell("⬇  Installa Termux", v -> installTermux()));

        LinearLayout row2 = row();
        LinearLayout.LayoutParams r2p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        r2p.topMargin = dp(10);
        row2.setLayoutParams(r2p);
        row2.addView(cell("⇩  Installa NexusSEC",
                v -> runInTermux(SETUP_CMD, "Comando copiato. In Termux: tieni premuto → Incolla → Invio.")));
        row2.addView(cell("↻  Aggiorna NexusSEC",
                v -> runInTermux(UPDATE_CMD, "Comando copiato. In Termux: tieni premuto → Incolla → Invio.")));

        grid.addView(row1);
        grid.addView(row2);
        return grid;
    }

    private LinearLayout row() {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return r;
    }

    /** Un pulsante di comando a larghezza uguale nella riga. */
    private Button cell(String label, View.OnClickListener cl) {
        Button b = styledButton(label, false, cl);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        lp.setMargins(dp(4), 0, dp(4), 0);
        b.setLayoutParams(lp);
        return b;
    }

    /** Bottone in stile "NexusSEC": primario = verde pieno, altrimenti pill scura. */
    private Button styledButton(String label, boolean primary, View.OnClickListener cl) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setOnClickListener(cl);
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, primary ? 17 : 13);
        b.setTextColor(primary ? cOnAccent : cAccent);
        b.setTypeface(b.getTypeface(), primary ? Typeface.BOLD : Typeface.NORMAL);
        b.setMinHeight(0);
        b.setMinimumHeight(0);
        b.setPadding(dp(primary ? 28 : 12), dp(primary ? 13 : 11),
                     dp(primary ? 28 : 12), dp(primary ? 13 : 11));
        GradientDrawable g = new GradientDrawable();
        g.setCornerRadius(dp(primary ? 13 : 11));
        if (primary) {
            g.setColor(cAccent);
        } else {
            g.setColor(cCard);
            g.setStroke(dp(1), cBorder);
        }
        b.setBackground(g);
        return b;
    }

    private View spacer() {
        View v = new View(this);
        v.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        return v;
    }

    private LinearLayout.LayoutParams wrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    // ------------------------------------------------------------- BOOTSTRAP --
    /**
     * Avvia il server in autonomia. Strategia a due stadi:
     *   1) tentativo SILENZIOSO via intent RUN_COMMAND (background), ~6 s;
     *   2) FALLBACK affidabile: apre Termux in primo piano — così parte l'hook
     *      .bashrc (comando `nexussec`) che accende il server. Al rientro nell'app
     *      il server viene rilevato ed entro da solo.
     */
    private void bootstrap() {
        bootstrapping = true;
        try {
            if (ping()) { onServerReady(); return; }

            if (!termuxInstalled()) {
                setStatus("Termux non è installato.\nTocca «Installa Termux» per iniziare.");
                return;
            }

            // 1) Tentativo silenzioso (Termux già in memoria).
            setStatus("avvio del server in corso…");
            startServerViaTermux();
            if (waitServer(6000)) { onServerReady(); return; }

            // 2) Fallback: apri Termux una sola volta per far partire il server.
            if (!triedForegroundLaunch) {
                triedForegroundLaunch = true;
                pendingEnter = true;   // appena pronto, entro senza altri tocchi
                setStatus("apro Termux per accendere il server…\n"
                        + "Lascia fare: torno da solo appena è pronto.");
                openTermux();
            }
            if (waitServer(POLL_TIMEOUT_MS)) { onServerReady(); return; }

            setStatus("Server non ancora attivo.\n"
                    + "Torna qui e tocca «Entra».");
        } finally {
            bootstrapping = false;
        }
    }

    /** Attende fino a {@code ms} che il server risponda; true se è salito. */
    private boolean waitServer(long ms) {
        long deadline = SystemClock.elapsedRealtime() + ms;
        while (SystemClock.elapsedRealtime() < deadline) {
            if (ping()) return true;
            sleep(900);
        }
        return false;
    }

    /** True se il pacchetto Termux è installato sul dispositivo. */
    private boolean termuxInstalled() {
        return getPackageManager().getLaunchIntentForPackage(TERMUX_PKG) != null;
    }

    @Override
    protected void onPause() {
        super.onPause();
        wasPaused = true;
    }

    /** Al ritorno nell'app (es. dopo aver aperto Termux) ricontrolla il server ~12s. */
    @Override
    protected void onResume() {
        super.onResume();
        if (wasPaused && !loaded && !serverReady) {
            wasPaused = false;
            new Thread(() -> {
                long deadline = SystemClock.elapsedRealtime() + 12000;
                while (SystemClock.elapsedRealtime() < deadline) {
                    if (ping()) { onServerReady(); return; }
                    sleep(900);
                }
            }).start();
        }
    }

    private void onServerReady() {
        serverReady = true;
        setStatus("server pronto ✓  —  tocca Entra");
        if (pendingEnter) showWeb();
    }

    /** Tocco su "Entra": entra se pronto, altrimenti riprova ad avviare e attende. */
    private void enterApp() {
        if (serverReady) {
            showWeb();
        } else {
            pendingEnter = true;
            setStatus("avvio del server… entro appena è pronto");
            if (!bootstrapping) new Thread(this::bootstrap).start();
        }
    }

    /** True se http://127.0.0.1:8000 risponde con un qualunque codice HTTP. */
    private boolean ping() {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(URL).openConnection();
            c.setConnectTimeout(800);
            c.setReadTimeout(800);
            c.setRequestMethod("GET");
            return c.getResponseCode() > 0;
        } catch (IOException e) {
            return false;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    /** Chiede a Termux di eseguire il server in background (intent RUN_COMMAND). */
    private void startServerViaTermux() {
        try {
            Intent i = new Intent();
            i.setComponent(new ComponentName(TERMUX_PKG, "com.termux.app.RunCommandService"));
            i.setAction("com.termux.RUN_COMMAND");
            i.putExtra("com.termux.RUN_COMMAND_PATH",
                    "/data/data/com.termux/files/usr/bin/bash");
            i.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", new String[]{
                    "-lc",
                    "command -v nexussec >/dev/null 2>&1 && nexussec || "
                  + "(cd \"$HOME/Termux-NexusSEC-OS\" 2>/dev/null && "
                  + "(pgrep -f 'server\\.py' >/dev/null || "
                  + "nohup python server.py >\"$HOME/nexussec.log\" 2>&1 &))"
            });
            i.putExtra("com.termux.RUN_COMMAND_WORKDIR",
                    "/data/data/com.termux/files/home");
            i.putExtra("com.termux.RUN_COMMAND_BACKGROUND", true);
            i.putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0");
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(i);
            } else {
                startService(i);
            }
        } catch (Exception ignored) {
        }
    }

    /** Porta Termux in primo piano. */
    private void openTermux() {
        Intent i = getPackageManager().getLaunchIntentForPackage(TERMUX_PKG);
        if (i != null) {
            startActivity(i);
        } else {
            setStatus("Termux non è installato. Tocca «Installa Termux».");
            toast("Termux non installato: installalo da F-Droid.");
        }
    }

    /** Apre la pagina F-Droid di Termux per installarlo. */
    private void installTermux() {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW,
                    Uri.parse("https://f-droid.org/packages/com.termux/")));
        } catch (Exception e) {
            toast("Apri: f-droid.org/packages/com.termux");
        }
    }

    /**
     * Copia il comando negli appunti e apre Termux: l'utente lo incolla ed esegue.
     * Metodo affidabile su tutti i telefoni (non dipende da allow-external-apps).
     */
    private void runInTermux(String cmd, String msg) {
        try {
            ClipboardManager cb = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (cb != null) cb.setPrimaryClip(ClipData.newPlainText("NexusSEC", cmd));
        } catch (Exception ignored) {
        }
        openTermux();
        toast(msg);
    }

    // ------------------------------------------------------------- WEBVIEW ----
    private void showWeb() {
        if (loaded) return;
        loaded = true;
        runOnUiThread(() -> {
            web = new WebView(this);
            web.setLayoutParams(new ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT));
            WebSettings s = web.getSettings();
            s.setJavaScriptEnabled(true);          // la PWA e' interattiva
            s.setDomStorageEnabled(true);          // localStorage: temi, storico, guida
            s.setDatabaseEnabled(true);
            s.setMediaPlaybackRequiresUserGesture(false);
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            s.setCacheMode(WebSettings.LOAD_NO_CACHE);
            // Ponte JS: window.NexusHost.exit() chiude l'app; setTheme() salva il tema.
            web.addJavascriptInterface(new JsBridge(), "NexusHost");
            web.setWebChromeClient(new WebChromeClient());
            web.setWebViewClient(new WebViewClient() {
                @Override
                public void onReceivedError(WebView v, WebResourceRequest req, WebResourceError err) {
                    if (req != null && req.isForMainFrame()) {
                        loaded = false;
                        setContentView(buildSplash());
                        setStatus("Connessione persa col server.\nApri Termux, poi Entra.");
                    }
                }
            });
            setContentView(web);
            web.loadUrl(URL);
        });
    }

    /** Interfaccia JS esposta alla PWA (solo dentro l'APK). */
    private class JsBridge {
        @JavascriptInterface
        public void exit() {
            runOnUiThread(() -> finishAndRemoveTask());
        }

        @JavascriptInterface
        public void setTheme(String id) {
            if (id == null) return;
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString("theme", id).apply();
        }
    }

    // -------------------------------------------------------------- UTILS -----
    private void setStatus(String t) {
        runOnUiThread(() -> { if (status != null) status.setText(t); });
    }

    private void toast(String t) {
        runOnUiThread(() -> Toast.makeText(this, t, Toast.LENGTH_LONG).show());
    }

    private int dp(int v) {
        return (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, v, getResources().getDisplayMetrics());
    }

    private void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException ignored) {}
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && web != null && web.canGoBack()) {
            web.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }
}
