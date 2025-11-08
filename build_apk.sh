#!/bin/bash
# Skrypt do budowania APK

echo "🔨 Budowanie APK dla GoodSpeed Route Analyzer..."
echo ""

# Aktywuj środowisko wirtualne
source venv/bin/activate

# Uruchom buildozer
buildozer android debug

echo ""
echo "✅ Budowanie zakończone!"
echo "📦 APK znajdziesz w folderze bin/"



