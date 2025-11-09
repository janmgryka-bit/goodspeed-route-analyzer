#!/bin/bash
# Kompletny skrypt do budowania APK - sprawdza zależności i buduje

echo "🔨 Budowanie APK dla GoodSpeed Route Analyzer"
echo ""

# Sprawdź czy narzędzia są zainstalowane
MISSING_TOOLS=()

if ! command -v autoconf &> /dev/null; then
    MISSING_TOOLS+=("autoconf")
fi

if ! command -v automake &> /dev/null; then
    MISSING_TOOLS+=("automake")
fi

if ! command -v java &> /dev/null; then
    MISSING_TOOLS+=("openjdk-11-jdk")
fi

if ! command -v git &> /dev/null; then
    MISSING_TOOLS+=("git")
fi

if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    echo "❌ Brakuje następujących narzędzi: ${MISSING_TOOLS[*]}"
    echo ""
    echo "Zainstaluj je uruchamiając:"
    echo "  sudo ./install_dependencies.sh"
    echo ""
    echo "Lub ręcznie:"
    echo "  sudo apt install -y autoconf automake build-essential git openjdk-11-jdk"
    exit 1
fi

echo "✅ Wszystkie wymagane narzędzia są zainstalowane"
echo ""

# Aktywuj środowisko wirtualne
if [ ! -d "venv" ]; then
    echo "❌ Środowisko wirtualne nie istnieje. Utwórz je: python3 -m venv venv"
    exit 1
fi

source venv/bin/activate

# Sprawdź czy buildozer jest zainstalowany
if ! command -v buildozer &> /dev/null; then
    echo "📦 Instalowanie buildozer..."
    pip install buildozer cython setuptools
fi

echo "🚀 Uruchamianie buildozer android debug..."
echo "⏳ To może zająć 30-60 minut przy pierwszej kompilacji..."
echo ""

# Uruchom buildozer
buildozer android debug

# Sprawdź wynik
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Budowanie zakończone pomyślnie!"
    echo "📦 APK znajdziesz w folderze bin/"
    ls -lh bin/*.apk 2>/dev/null || echo "   (sprawdź folder bin/ ręcznie)"
else
    echo ""
    echo "❌ Budowanie zakończone z błędami. Sprawdź logi powyżej."
    exit 1
fi


