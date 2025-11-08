# GoodSpeed Route Analyzer

Aplikacja do analizy tras dostaw z wideo i zarządzania trasą na urządzeniach mobilnych.

## 📱 Komponenty

### 1. Aplikacja mobilna (Kivy)
- **Plik:** `goodspeed_route_analyzer.py`
- Aplikacja mobilna z mapą, GPS i odznaczaniem dostaw
- Budowana do APK przez Buildozer

### 2. Aplikacja webowa (Streamlit)
- **Plik:** `goodspeed_cloud_mapper.py`
- Interfejs webowy do przetwarzania wideo i generowania danych trasy
- Uruchomienie: `streamlit run goodspeed_cloud_mapper.py`

### 3. Backend
- **Plik:** `route_backend.py`
- Przetwarzanie wideo i ekstrakcja adresów z użyciem Gemini Vision AI

## 🚀 Szybki start

### Instalacja zależności
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install kivy-garden.mapview
```

### Konfiguracja kluczy API
1. Skopiuj plik `.env.example` do `.env`:
```bash
cp .env.example .env
```

2. Edytuj plik `.env` i uzupełnij swoje klucze API:
```bash
GEMINI_API_KEY=twoj_klucz_gemini
GOOGLE_MAPS_API_KEY=twoj_klucz_google_maps
```

**⚠️ Ważne:** Plik `.env` jest w `.gitignore` i nie będzie commitowany do repozytorium.

### Uruchomienie aplikacji webowej
```bash
streamlit run goodspeed_cloud_mapper.py
```

### Uruchomienie aplikacji mobilnej
```bash
python goodspeed_route_analyzer.py
```

### Budowanie APK
```bash
# Zainstaluj zależności systemowe
sudo ./install_dependencies.sh

# Zbuduj APK
source venv/bin/activate
buildozer android debug
```

## 📋 Wymagania

- Python 3.7+
- Kivy 2.1.0+
- Streamlit
- Buildozer (do budowania APK)
- Android SDK/NDK (pobierane automatycznie przez Buildozer)

## 📖 Dokumentacja

- `README_MOBILE.md` - Dokumentacja aplikacji mobilnej
- `BUILD_APK.md` - Instrukcje budowania APK
- `QUICK_START.md` - Szybki start

## 🔧 Konfiguracja

Plik `buildozer.spec` zawiera konfigurację dla budowania APK.

## 📝 Licencja

[Określ licencję]

