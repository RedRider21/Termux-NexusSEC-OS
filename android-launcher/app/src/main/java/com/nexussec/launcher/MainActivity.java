package com.nexussec.launcher;

import android.app.Activity;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.ViewGroup;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * Launcher WebView di Termux-NexusSEC-OS.
 *
 * Mostra a schermo intero l'interfaccia servita dal server locale in Termux
 * (http://127.0.0.1:8000). Se il server non e' ancora attivo, presenta una
 * schermata con un pulsante "Riprova". Il backend resta server.py in Termux:
 * questa app e' solo la "faccia" (nessuna dipendenza AndroidX).
 */
public class MainActivity extends Activity {

    private static final String URL = "http://127.0.0.1:8000";
    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

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
                    v.loadDataWithBaseURL(null, errorPage(), "text/html", "utf-8", null);
                }
            }
        });

        setContentView(web);
        web.loadUrl(URL);
    }

    /** Pagina mostrata quando il server locale non risponde ancora. */
    private String errorPage() {
        return "<!doctype html><html><head>"
             + "<meta name='viewport' content='width=device-width,initial-scale=1'>"
             + "<style>body{margin:0;background:#050705;color:#3dff88;"
             + "font-family:monospace;display:flex;min-height:100vh;align-items:center;"
             + "justify-content:center;text-align:center;padding:24px}"
             + "h1{font-size:19px;margin:0 0 6px}"
             + "p{color:#5a7a63;font-size:13px;line-height:1.6;margin:0}"
             + "a{display:inline-block;margin-top:20px;background:#3dff88;color:#04160a;"
             + "padding:12px 22px;border-radius:11px;text-decoration:none;font-weight:700}</style>"
             + "</head><body><div><h1>&gt;_ NexusSEC</h1>"
             + "<p>Il server locale non e' ancora attivo.<br>"
             + "Apri <b>Termux</b> e avvia il server<br>"
             + "(oppure attendi l'autostart), poi riprova.</p>"
             + "<a href='" + URL + "'>&#8635; Riprova</a></div></body></html>";
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
