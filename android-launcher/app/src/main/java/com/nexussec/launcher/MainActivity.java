package com.nexussec.launcher;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
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

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Launcher WebView di Termux-NexusSEC-OS.
 *
 * All'avvio mostra uno SPLASH (logo + "NexusSEC x Android") e prova a far partire
 * il server locale dentro Termux tramite l'intent ufficiale com.termux.RUN_COMMAND
 * (richiede allow-external-apps=true in ~/.termux/termux.properties, impostato da
 * install.sh). Quando http://127.0.0.1:8000 risponde, carica l'interfaccia PWA a
 * schermo intero. Se Termux non risponde, offre "Apri Termux" e "Riprova".
 *
 * Nessuna dipendenza AndroidX: solo il framework Android.
 */
public class MainActivity extends Activity {

    private static final String URL = "http://127.0.0.1:8000";
    private static final String TERMUX_PKG = "com.termux";
    private static final long   POLL_TIMEOUT_MS = 30000;   // attesa massima avvio server
    private static final int    ACCENT = 0xFF3DFF88;       // verde terminale
    private static final int    BG     = 0xFF050705;
    private static final int    DIM    = 0xFF5A7A63;

    private WebView web;
    private TextView status;
    private LinearLayout buttons;
    private boolean loaded = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildSplash());
        // Parti in background: prima controlla se e' gia' su, altrimenti avvia Termux.
        new Thread(this::bootstrap).start();
    }

    // ---------------------------------------------------------------- SPLASH --
    private View buildSplash() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setBackgroundColor(BG);
        root.setPadding(dp(28), dp(28), dp(28), dp(28));

        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.nexus_logo);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(120), dp(120));
        lp.bottomMargin = dp(18);
        logo.setLayoutParams(lp);
        root.addView(logo);

        TextView title = new TextView(this);
        title.setText("NexusSEC");
        title.setTextColor(ACCENT);
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 30);
        title.setGravity(Gravity.CENTER);
        title.setTypeface(title.getTypeface(), android.graphics.Typeface.BOLD);
        root.addView(title);

        TextView sub = new TextView(this);
        sub.setText("x Android");
        sub.setTextColor(DIM);
        sub.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
        sub.setGravity(Gravity.CENTER);
        sub.setLetterSpacing(0.25f);
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        sp.topMargin = dp(2);
        sub.setLayoutParams(sp);
        root.addView(sub);

        status = new TextView(this);
        status.setText("avvio in corso…");
        status.setTextColor(DIM);
        status.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        status.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams stp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        stp.topMargin = dp(28);
        status.setLayoutParams(stp);
        root.addView(status);

        buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setGravity(Gravity.CENTER);
        buttons.setVisibility(View.GONE);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        bp.topMargin = dp(22);
        buttons.setLayoutParams(bp);
        buttons.addView(makeButton("Apri Termux", true, v -> openTermux()));
        buttons.addView(makeButton("↻ Riprova", false, v -> retry()));
        root.addView(buttons);

        return root;
    }

    private Button makeButton(String label, boolean filled, View.OnClickListener cl) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setOnClickListener(cl);
        b.setTextColor(filled ? BG : ACCENT);
        b.setBackgroundColor(filled ? ACCENT : 0x22000000);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(dp(6), 0, dp(6), 0);
        b.setLayoutParams(lp);
        return b;
    }

    // ------------------------------------------------------------- BOOTSTRAP --
    /** Se il server e' gia' su, carica subito; altrimenti prova ad avviarlo in Termux. */
    private void bootstrap() {
        if (ping()) { showWeb(); return; }
        setStatus("avvio di Termux e del server…");
        boolean asked = startServerViaTermux();
        if (!asked) setStatus("Termux non raggiunto: aprilo a mano, poi Riprova.");

        long deadline = SystemClock.elapsedRealtime() + POLL_TIMEOUT_MS;
        while (SystemClock.elapsedRealtime() < deadline) {
            sleep(900);
            if (ping()) { showWeb(); return; }
        }
        runOnUiThread(() -> {
            setStatus("Il server non risponde ancora.\nApri Termux (o attendi l'autostart), poi Riprova.");
            buttons.setVisibility(View.VISIBLE);
        });
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

    /**
     * Chiede a Termux di eseguire server.py in background (intent RUN_COMMAND).
     * Ritorna false se Termux non c'e' o l'intent viene rifiutato (permesso o
     * allow-external-apps mancante).
     */
    private boolean startServerViaTermux() {
        try {
            Intent i = new Intent();
            i.setComponent(new ComponentName(TERMUX_PKG, "com.termux.app.RunCommandService"));
            i.setAction("com.termux.RUN_COMMAND");
            i.putExtra("com.termux.RUN_COMMAND_PATH",
                    "/data/data/com.termux/files/usr/bin/bash");
            i.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", new String[]{
                    "-lc",
                    "cd \"$HOME/Termux-NexusSEC-OS\" 2>/dev/null && "
                  + "(pgrep -f 'python .*server.py' >/dev/null || exec python server.py)"
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
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /** Porta Termux in primo piano (fallback se l'avvio automatico non e' permesso). */
    private void openTermux() {
        Intent i = getPackageManager().getLaunchIntentForPackage(TERMUX_PKG);
        if (i != null) {
            startActivity(i);
        } else {
            setStatus("Termux non installato. Installalo da F-Droid.");
        }
    }

    private void retry() {
        buttons.setVisibility(View.GONE);
        setStatus("nuovo tentativo…");
        new Thread(this::bootstrap).start();
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
            web.setWebChromeClient(new WebChromeClient());
            web.setWebViewClient(new WebViewClient() {
                @Override
                public void onReceivedError(WebView v, WebResourceRequest req, WebResourceError err) {
                    if (req != null && req.isForMainFrame()) {
                        // Il server e' caduto: torna allo splash con Riprova.
                        loaded = false;
                        setContentView(buildSplash());
                        buttons.setVisibility(View.VISIBLE);
                        setStatus("Connessione persa col server.\nApri Termux, poi Riprova.");
                    }
                }
            });
            setContentView(web);
            web.loadUrl(URL);
        });
    }

    // -------------------------------------------------------------- UTILS -----
    private void setStatus(String t) {
        runOnUiThread(() -> { if (status != null) status.setText(t); });
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
