package com.jordandesignhub.school;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Full offline JD Hub School Management System for Android.
 *
 * Unlike the earlier "thin client" (which needed a PC on the same Wi-Fi), this
 * app runs the entire Django application on the phone: a Python interpreter
 * (Chaquopy) boots the project from assets and serves it on 127.0.0.1, and the
 * WebView displays it. Nothing is downloaded at runtime and no network is
 * required, so a school can manage data directly on a phone.
 */
public class MainActivity extends AppCompatActivity {

    private static final String TAG = "JDHubSchool";
    private static final String ASSETS_ROOT = "jdhub";

    private WebView webView;
    private TextView statusText;
    private final Handler main = new Handler(Looper.getMainLooper());

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webview);
        statusText = findViewById(R.id.statusText);
        statusText.setText(R.string.starting);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setMediaPlaybackRequiresUserGesture(false);

        CookieManager.getInstance().setAcceptCookie(true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, WebResourceRequest request,
                                        WebResourceError error) {
                if (request.isForMainFrame()) {
                    showStatus(getString(R.string.start_error));
                }
            }
        });
        webView.setWebChromeClient(new WebChromeClient());

        // PDFs and other downloads are written to app storage, then opened in
        // whatever viewer the phone provides.
        webView.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition,
                                        String mimeType, long contentLength) {
                downloadAndOpen(url, mimeType, contentDisposition);
            }
        });

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack();
                } else {
                    finish();
                }
            }
        });

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState);
        }

        startBackend();
    }

    private void startBackend() {
        // Chaquopy requires the interpreter to be started before any Python
        // call; doing it here (main thread) then doing the heavy boot on a
        // worker keeps the UI alive.
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(getApplicationContext()));
        }
        new Thread(() -> {
            try {
                final File bundleDir = extractAssets();
                System.setProperty("jdhub.bundledir", bundleDir.getAbsolutePath());

                Python py = Python.getInstance();
                final PyObject app = py.getModule("jdhub_app");
                final int port = app.callAttr("start").toInt();

                if (port <= 0) {
                    final String err = app.callAttr("last_error").toString();
                    Log.e(TAG, "Backend failed: " + err);
                    main.post(() -> showStatus(getString(R.string.start_error)));
                    return;
                }

                final String base = app.callAttr("base_url").toString();
                main.post(() -> webView.loadUrl(base + "/accounts/login/"));
            } catch (Throwable t) {
                Log.e(TAG, "Startup crashed", t);
                main.post(() -> showStatus(getString(R.string.start_error)));
            }
        }, "jdhub-backend").start();
    }

    /** Copy the bundled project tree from assets into a real folder so that
     * Django can import it and locate templates/static via file paths. */
    private File extractAssets() throws IOException {
        File target = new File(getFilesDir(), "app");
        copyAssetDir(ASSETS_ROOT, target);
        return target;
    }

    private void copyAssetDir(String assetPath, File targetDir) throws IOException {
        String[] children;
        try {
            children = getAssets().list(assetPath);
        } catch (IOException e) {
            children = null;
        }
        if (children == null || children.length == 0) {
            // A file, not a directory.
            copyAssetFile(assetPath, targetDir);
            return;
        }
        if (!targetDir.exists() && !targetDir.mkdirs()) {
            throw new IOException("Could not create " + targetDir);
        }
        for (String child : children) {
            copyAssetDir(assetPath + "/" + child, new File(targetDir, child));
        }
    }

    private void copyAssetFile(String assetPath, File targetFile) throws IOException {
        File parent = targetFile.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("Could not create " + parent);
        }
        try (InputStream in = getAssets().open(assetPath);
             OutputStream out = new FileOutputStream(targetFile)) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) {
                out.write(buf, 0, n);
            }
        }
    }

    private void downloadAndOpen(String url, String mimeType, String contentDisposition) {
        new Thread(() -> {
            try {
                java.net.HttpURLConnection conn =
                        (java.net.HttpURLConnection) new java.net.URL(url).openConnection();
                conn.connect();
                String name = android.webkit.URLUtil.guessFileName(url, contentDisposition, mimeType);
                File dir = new File(getExternalFilesDir(null), "downloads");
                if (!dir.exists()) dir.mkdirs();
                File out = new File(dir, name);
                try (InputStream in = conn.getInputStream();
                     OutputStream os = new FileOutputStream(out)) {
                    byte[] buf = new byte[8192];
                    int n;
                    while ((n = in.read(buf)) > 0) os.write(buf, 0, n);
                }
                openFile(out, mimeType);
            } catch (Exception e) {
                Log.e(TAG, "Download failed", e);
                main.post(() -> Toast.makeText(this, R.string.download_error, Toast.LENGTH_LONG).show());
            }
        }).start();
    }

    private void openFile(File file, String mimeType) {
        main.post(() -> {
            try {
                Uri uri = FileProvider.getUriForFile(this,
                        getPackageName() + ".fileprovider", file);
                Intent intent = new Intent(Intent.ACTION_VIEW);
                intent.setDataAndType(uri, mimeType == null ? "application/pdf" : mimeType);
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                startActivity(intent);
            } catch (Exception e) {
                Log.e(TAG, "Open failed", e);
                Toast.makeText(this, R.string.no_pdf_viewer, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void showStatus(String message) {
        statusText.setText(message);
        statusText.setVisibility(View.VISIBLE);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }
}
