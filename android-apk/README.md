# JD Hub School - Android client APK

A small offline Android app that lets phones connect to a school's
**JD Hub School Management System** desktop server over the local Wi-Fi or a
phone hotspot. No internet connection is used.

The app is intentionally a thin client: it keeps **no** student data on the
phone, so a lost phone cannot leak the school register.

## How it works

1. On the school computer, open **Connect a phone** (QR page) in the app.
2. On the phone, open this app and either:
   - tap **Scan QR code** and scan the code on the school screen, or
   - type the address shown (for example `192.168.1.5:8000`).
3. The phone connects to the school server and shows the normal login page.
   The address is remembered for next time.

Phones must be on the **same Wi-Fi network or hotspot** as the school computer.

## Build

Install JDK 17 and the Android SDK, then:

```bash
cd android-apk
./build_apk.sh
```

The unsigned APK is written to
`app/build/outputs/apk/release/app-release-unsigned.apk` (and a debug APK to
`.../debug/`).

### Signing a release build

Create `keystore.properties` in `android-apk/`:

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

Then re-run `./build_apk.sh`. A signed APK installs without the
"allow unknown apps" warning.

## Install on a phone

- Copy the APK to the phone (USB, Bluetooth, or local file share) and open it.
- Allow installation from unknown sources when prompted.
- On first launch, scan the QR code from the school computer.

## Notes

- Cleartext HTTP to private addresses is enabled on purpose: the school server
  has no TLS certificate and traffic never leaves the local network.
- `minSdk 24` (Android 7.0) and above.
