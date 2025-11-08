#!/bin/bash
# Skrypt do instalacji zależności wymaganych do budowania APK

echo "🔧 Instalowanie zależności systemowych dla Buildozer..."

# Aktualizacja pakietów
sudo apt update

# Instalacja Git i Java JDK oraz narzędzi do kompilacji
sudo apt install -y git openjdk-11-jdk zip unzip autoconf automake libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev build-essential

echo "✅ Zależności zainstalowane!"
echo ""
echo "Następny krok: uruchom 'source venv/bin/activate && buildozer android debug'"

