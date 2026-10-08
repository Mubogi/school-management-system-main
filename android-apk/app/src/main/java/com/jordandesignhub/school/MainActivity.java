package com.jordandesignhub.school;

import android.annotation.SuppressLint;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;

import com.journeyapps.barcodescanner.ScanContract;
import com.journeyapps.barcodescanner.ScanOptions;

import androidx.activity.result.ActivityResultLauncher;

/**
 * Offline mobile client for the JD Hub School Management System.
 *
 * The phone connects to the school's own computer over the local Wi-Fi or
 * hotspot; the address is entered once or scanned from the QR code shown in the
 * app's "Connect a phone" page. No internet is required.
 */
public class MainActivity extends AppCompatActivity {

    private static final String PREFS = "jdhub";
    private static final String KEY_SERVER = "server_url";

    private WebView webView;
    private ScrollView setupPanel;
    private EditText serverAddress;
    private TextView statusText;
    private SharedPreferences prefs;

    private final ActivityResultLauncher<ScanOptions> qrLauncher =
            registerForActivityResult(new ScanContract(), result -> {
                if (result.getContents() != null) {
                    String url = normalizeAddress(result.getContents());
                    serverAddress.setText(url);
                    connect(url);
                }
            });

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        webView = findViewById(R.id.webview);
        setupPanel = findViewById(R.id.setupPanel);
        serverAddress = findViewById(R.id.serverAddress);
        statusText = findViewById(R.id.statusText);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setAllowFileAccess(true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                showWebView();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request,
                                        WebResourceError error) {
                if (request.isForMainFrame()) {
                    showSetup(getString(R.string.cannot_connect));
                }
            }
        });

        Button connectButton = findViewById(R.id.connectButton);
        connectButton.setOnClickListener(v -> {
            String raw = serverAddress.getText().toString().trim();
            if (!raw.isEmpty()) {
                connect(normalizeAddress(raw));
            }
        });

        Button scanButton = findViewById(R.id.scanButton);
        scanButton.setOnClickListener(v -> {
            ScanOptions options = new ScanOptions();
            options.setDesiredBarcodeFormats(ScanOptions.QR_CODE);
            options.setPrompt(getString(R.string.scan_prompt));
            options.setBeepEnabled(false);
            options.setOrientationLocked(false);
            qrLauncher.launch(options);
        });

        // System back navigates the web app; the setup panel closes the app.
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (webView.getVisibility() == View.VISIBLE) {
                    if (webView.canGoBack()) {
                        webView.goBack();
                    } else {
                        showSetup(null);
                    }
                } else {
                    finish();
                }
            }
        });

        String saved = prefs.getString(KEY_SERVER, null);
        if (saved != null) {
            serverAddress.setText(saved);
            connect(saved);
        } else {
            showSetup(null);
        }
    }

    /** Accept full URLs or bare host[:port] and return a usable http URL. */
    private String normalizeAddress(String raw) {
        String value = raw.trim();
        if (value.isEmpty()) {
            return "";
        }
        if (!value.startsWith("http://") && !value.startsWith("https://")) {
            value = "http://" + value;
        }
        // Drop any path/query: we only want scheme + host + port.
        try {
            java.net.URL url = new java.net.URL(value);
            String port = url.getPort() == -1 ? "" : ":" + url.getPort();
            return url.getProtocol() + "://" + url.getHost() + port;
        } catch (Exception e) {
            return value;
        }
    }

    private void connect(String baseUrl) {
        statusText.setText(R.string.connecting);
        prefs.edit().putString(KEY_SERVER, baseUrl).apply();
        webView.setVisibility(View.VISIBLE);
        setupPanel.setVisibility(View.GONE);
        webView.loadUrl(baseUrl + "/accounts/login/");
    }

    private void showWebView() {
        webView.setVisibility(View.VISIBLE);
        setupPanel.setVisibility(View.GONE);
    }

    private void showSetup(String message) {
        webView.setVisibility(View.GONE);
        setupPanel.setVisibility(View.VISIBLE);
        statusText.setText(message == null ? "" : message);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }
}
