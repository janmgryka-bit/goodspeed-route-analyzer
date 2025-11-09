#!/bin/bash
# Szybki build APK - tylko podstawowe zależności

set -e

cd "$(dirname "$0")"

echo "🚀 Szybki build APK (minimalne zależności)..."

source venv/bin/activate

# Upewnij się że buildozer jest zainstalowany
if ! command -v buildozer &> /dev/null; then
    echo "❌ Buildozer nie jest zainstalowany!"
    exit 1
fi

# Build tylko dla jednej architektury (szybsze)
export P4A_BUILD_ARCH=arm64-v8a

echo "📦 Budowanie APK (może zająć 15-30 minut)..."
echo "   (Pierwsza kompilacja pobierze SDK/NDK)"

# Uruchom buildozer z timeoutem - jeśli trwa dłużej niż 45 minut, przerwij
timeout 2700 buildozer android debug || {
    echo ""
    echo "⏱️ Build przekroczył 45 minut lub wystąpił błąd"
    echo "Sprawdź logi w build_log.txt"
    exit 1
}

# Sprawdź czy APK został utworzony
if ls bin/*.apk 1> /dev/null 2>&1; then
    echo ""
    echo "✅ APK gotowy!"
    ls -lh bin/*.apk
    echo ""
    echo "📱 Zainstaluj na telefonie:"
    echo "   adb install bin/*.apk"
    echo "   lub przenieś plik na telefon"
else
    echo ""
    echo "❌ APK nie został utworzony. Sprawdź błędy powyżej."
    exit 1
fi


