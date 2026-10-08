# JD Hub School Management System — Offline Edition

This edition is the same product as the online version, packaged so a school
can run it on its own computer with **no internet connection**, and let phones
connect over the local Wi-Fi/hotspot. The original online version is unchanged
and continues to work.

The offline edition is what you hand to a paying client. Everything below is
about building that package and selling/activating it.

---

## 1. What the client receives

The downloads live on the repository's **Releases** page:

<https://github.com/Mubogi/school-management-system-main/releases>

| Item | Purpose |
| --- | --- |
| `JDHub_SchoolManagement_Offline_1.1.0_Setup.exe` | Windows installer (PC) |
| `JDHubSchoolSystem-windows-portable.zip` | No-install portable copy |
| `JDHubSchool-client.apk` | Android phone client |
| Activation code | One signed key per client (issued separately) |
| This guide | Setup + activation steps |

Nothing requires an internet connection after installation.

### How a release is made

The assets are built automatically by
`.github/workflows/release.yml`. To cut a release:

```bash
git tag -a v1.1.0 -m "Offline edition 1.1.0"
git push origin v1.1.0
```

Pushing a `v*` tag builds the Windows installer (PyInstaller + Inno Setup) and
the Android APK on GitHub runners, then attaches them to the Release. You can
also run the workflow manually (Actions → *Release offline edition* → Run
workflow) to get the same files as build artifacts without publishing a
Release.

The APK produced by CI is **unsigned**, so Android will ask the client to allow
installs from unknown sources. For a signed APK, add `keystore.properties`
(see `android-apk/README.md`) and rebuild — the same file installs without the
warning.

---

## 2. The two editions (how they stay separate)

The edition is decided at startup:

- `JDHUB_EDITION=offline`: the desktop launcher and the APK client set this.
  Debug is off, cloud/sync probes are skipped, and the license must be a signed
  activation code bound to the machine.
- `JDHUB_EDITION=online` (default for a source checkout): the original build.
  Nothing about it changed.

Key files:

- `core/edition.py` — `get_edition()` / `is_offline()`
- `django_sms/settings.py` — reads the edition, keeps data in one folder
- `core/cloud_sync.py` — outbound probes are skipped when offline
- `core/views.py` — `get_lan_ip()` works without internet/ DNS

---

## 3. Activation codes

Codes are **HMAC-signed** so they cannot be edited or invented by a customer.
A code carries: tier, validity, machine binding (optional), feature set, and
the school name.

Format: `SMS-<TIER>-<base64 payload>-<signature>`

- Tiers: `DEMO`, `BASIC`, `STANDARD`, `PREMIUM`
- Feature sets are taken from each tier in `licensing/models.py`.

### The signing secret

The secret must be the **same** on your build machine and in the shipped app
for your codes to validate. Set it with the `JDHUB_LICENSE_SECRET` environment
variable and ship it inside the build; do not use the placeholder default for
real clients.

```
set JDHUB_LICENSE_SECRET=your-long-random-secret
```

(If unset, the code falls back to a development default so local testing
works — see the warning printed by the generator.)

### Generate a code for a client

```bash
# Perpetual PREMIUM, any machine
python manage.py licensekey generate --tier PREMIUM

# One year, bound to one machine, with the school name baked in
python manage.py licensekey generate --tier STANDARD --days 365 \
    --hwid 1E43-B745-72E7-7076 --school "St Mary's Secondary School"

# 30-day trial (shortest tier)
python manage.py licensekey generate --tier BASIC --days 30

# Show this machine's HWID, then issue a bound key
python manage.py licensekey generate --tier STANDARD --show-hwid

# Apply a code locally (normally done in the UI instead)
python manage.py licensekey apply SMS-STANDARD-...-....
```

The school's **HWID** is shown on the activation screen and under
*Settings → License*. Send the matching bound code.

### Activate on the client machine

1. Open the installed app.
2. Go to **License → Activate**.
3. Paste the activation code and click **Activate**.

The activation is stored locally and re-checked at each start.

---

## 4. Building the PC installer (Windows)

Requirements: Windows 10/11, Python 3.11+ (64-bit), and Inno Setup 6 for the
installer step.

```cmd
:: from the project root
python -m pip install -r requirements.txt pyinstaller
python build.py --clean --zip
```

That produces:

- `dist\JDHubSchoolSystem\` — the runnable app folder
- `dist\JDHubSchoolSystem-windows-portable.zip` — portable copy

To make the single Setup `.exe`:

1. Open `installer_setup.iss` in Inno Setup 6 and click **Compile**
   (or run `python build.py --installer`).
2. The installer is written to `installer\`.

The installer:

- copies the app to `C:\Program Files\JD Hub School Management System`
- creates Start-menu and desktop shortcuts
- creates the writable `media\` and `backups\` folders
- offers to keep or remove school data on uninstall

`BUILD_FOR_WINDOWS.bat` runs the whole flow in one double-click.

### A first run

1. The app opens its own window and first-run migration runs automatically.
2. Sign in with the seeded administrator (shown once in the console), then
   change the password immediately.
3. Enter the activation code.
4. Open **Connect a phone** to show the QR code.

---

## 5. Building the Android APK

Requirements: JDK 17 and the Android SDK.

```bash
cd android-apk
./build_apk.sh
```

Output: `android-apk/app/build/outputs/apk/release/`.

For a signed release APK, add `android-apk/keystore.properties` (see
`android-apk/README.md`) and rebuild. A signed APK installs without the
"unknown apps" warning.

The phone app is a thin client: it holds **no** student data, so a lost phone
cannot leak the register.

---

## 6. Connecting phones (QR)

1. On the school computer open **Connect a phone**. It shows a QR code and the
   LAN address (`http://<lan-ip>:<port>/accounts/login/`).
2. On the phone, in **JD Hub School**, tap **Scan QR code**, or type the
   address.
3. The phone must be on the same Wi-Fi network or hotspot as the computer.

The QR code always uses the real port the server is listening on, so it works
even if the port is not the default `8000`.

---

## 7. PDFs

Reports, receipts, broadsheets, lists and certificates are generated locally.
The PDF engine tries, in order, any of: Playwright/Chromium, WeasyPrint,
xhtml2pdf, or the built-in ReportLab fallback — so PDFs keep working even on a
computer that has none of the optional libraries installed.

---

## 8. Data, backups, and safety

- All data lives next to the executable in one folder (`db.sqlite3`, `media/`,
  `backups/`). Copy that folder to move or archive a school.
- The app takes an automatic backup on exit (last 5 kept) in `backups/`.
- Only one copy of the app may run against a data folder at a time; the app
  refuses a second start to protect the database.
- Do not delete `secret_key.txt` in the install folder; it keeps sessions valid
  across restarts.

---

## 9. Support

Jordan Design Hub (JD Hub) — +256 754 687 597 — jordandesignhub@gmail.com
