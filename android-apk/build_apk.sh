#!/usr/bin/env bash
# Build the offline Android client APK.
#
# Requires: JDK 17+, Android SDK (ANDROID_HOME) and a Gradle wrapper or a
# system `gradle` on PATH. Run from the android-apk/ directory.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f gradlew ]; then
  if command -v gradle >/dev/null 2>&1; then
    echo "Generating Gradle wrapper..."
    gradle wrapper --gradle-version 8.7
  else
    echo "ERROR: no gradlew and no system gradle found." >&2
    echo "Install Gradle 8.x or add a wrapper, then re-run." >&2
    exit 1
  fi
fi

chmod +x gradlew
./gradlew assembleRelease
./gradlew assembleDebug

echo
echo "APKs:"
find . -name "*.apk" -path "*/build/outputs/*"
