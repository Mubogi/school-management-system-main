# JD Hub School - Android app (APK)

A **full offline** Android app for the **JD Hub School Management System**.

The phone runs the entire Django application itself (using the Chaquopy Python
runtime) and stores its own SQLite database in the app's private storage. No
computer, no server and no internet are needed, so a school can enrol students,
enter marks, print reports and generate PDFs directly on a phone. The app also
shows a QR code so teachers' phones can connect to a computer's copy over the
local Wi-Fi when preferred.

## How it works

1. Install and open the app. It unpacks its bundled copy of the project and
   starts the school system on the device (a few seconds on first run).
2. Sign in with the seeded administrator, then change the password.
3. Enter the activation code on the licensing page.
4. Use the app exactly like the desktop edition. Reports and receipts are PDFs,
   saved to the Downloads folder and opened in the phone's PDF viewer.

## Build

Install JDK 17, the Android SDK and Python 3.11, then:

```bash
python android-apk/make_icons.py      # launcher icons from images/company-logo.png
cd android-apk
./build_apk.sh
```

The APK is written to `app/build/outputs/apk/release/`.

**A release APK must be signed**, otherwise Android shows "There was a problem
parsing the package" and refuses to install it. The CI release workflow signs it
for you. For a local signed build, create `android-apk/keystore.properties`:

```properties
storeFile=/absolute/path/school-release.jks
storePassword=...
keyAlias=school
keyPassword=...
```

Generate the keystore once with:

```bash
keytool -genkeypair -v -keystore school-release.jks -keyalg RSA \
  -keysize 2048 -validity 10000 -alias school
```

Then re-run `./build_apk.sh`.

## Install on a phone

- Copy the APK to the phone (USB, Bluetooth, or local file share) and open it.
- Allow installation from unknown sources when prompted.
- On first launch the app prepares its own database and opens the login page.

## Notes

- Cleartext HTTP is enabled on purpose: the app serves itself on `127.0.0.1`
  and may also connect to a computer on the local network.
- `minSdk 24` (Android 7.0) and above.
- ReportLab cannot run on Android, so PDFs use a pure-Python engine (fpdf2).
