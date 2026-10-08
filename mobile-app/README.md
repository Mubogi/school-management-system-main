# JD Hub School - Mobile (Flutter)

Standalone offline mobile edition of the school management system.

## Why Flutter

The previous Android build ran the whole Django project on the phone through an
embedded Python interpreter (Chaquopy). It installed but failed to start on
Android 15 ("The school system could not start"). This edition has no embedded
interpreter and no server: it is a native app backed by a local SQLite file, so
it opens instantly and cannot fail to boot. The download is also much smaller
(~10-15 MB vs ~32 MB).

The Windows installer and the web edition remain on Django and are unchanged.

## Features

- Students: add, search, delete
- Teachers: add, delete
- Fees: amounts due, paid and balance per student
- Reports: native PDF export (student register, fees report) via print/share
- Connect / QR: render a scannable QR code on-device
- All data stored locally in SQLite - no internet required

## Build

```bash
cd mobile-app
flutter pub get
flutter build apk --release --split-per-abi   # arm64 / arm32
flutter build apk --release                   # universal fallback
```

Tag `mobile-v*` to publish APKs via `.github/workflows/mobile-release.yml`.
