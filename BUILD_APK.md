# Instrukcja budowania APK dla GoodSpeed Route Analyzer

## Podsumowanie - Na czym skończyliśmy?

✅ **Aplikacja mobilna jest gotowa!** Mamy:
- `goodspeed_route_analyzer.py` - aplikacja Kivy z mapą, GPS i odznaczaniem dostaw
- `route_backend.py` - backend do przetwarzania wideo
- `goodspeed_cloud_mapper.py` - aplikacja Streamlit do generowania danych
- `optimized_data_for_mobile.py` - plik z danymi trasy (generowany automatycznie)

## Czy możemy wygenerować APK?

**TAK!** Aplikacja jest gotowa do budowania APK. Potrzebujemy tylko Buildozer.

## Wymagania do budowania APK

### 1. System operacyjny
- **Linux** (najlepiej Ubuntu/Debian) - zalecane
- **macOS** - działa, ale może być wolniejsze
- **Windows** - możliwe przez WSL2 (Windows Subsystem for Linux)

### 2. Zależności systemowe

#### Na Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-11-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
```

#### Na macOS:
```bash
brew install autoconf automake libtool pkg-config
brew install openjdk@11
```

### 3. Instalacja Buildozer

```bash
pip install buildozer
```

### 4. Instalacja zależności Python dla aplikacji mobilnej

```bash
pip install kivy plyer
pip install kivy-garden.mapview
```

## Konfiguracja Buildozer

Plik `buildozer.spec` jest już przygotowany! Zawiera:
- ✅ Wszystkie wymagane zależności (kivy, plyer, kivy-garden.mapview)
- ✅ Uprawnienia Android (INTERNET, GPS)
- ✅ Konfigurację dla Android API 33
- ✅ Wsparcie dla architektury ARM (arm64-v8a, armeabi-v7a)

## Budowanie APK

### Krok 1: Przygotuj dane trasy

Najpierw wygeneruj plik z danymi trasy:
```bash
# Uruchom aplikację Streamlit
streamlit run goodspeed_cloud_mapper.py

# Prześlij wideo i wygeneruj optimized_data_for_mobile.py
```

### Krok 2: Sprawdź plik buildozer.spec

Upewnij się, że w `buildozer.spec` jest:
```ini
# Główny plik aplikacji
main = goodspeed_route_analyzer.py

# Wymagania
requirements = python3,kivy==2.1.0,plyer,kivy-garden.mapview,importlib
```

### Krok 3: Zbuduj APK (debug)

```bash
# Pierwsza kompilacja (pobierze Android SDK/NDK - może zająć dużo czasu)
buildozer android debug

# APK będzie w folderze bin/
# Ścieżka: bin/goodspeedrouteanalyzer-0.1-arm64-v8a-debug.apk
```

### Krok 4: Zbuduj APK (release - do dystrybucji)

```bash
# Najpierw skonfiguruj podpisanie (opcjonalne)
# buildozer android release

# Lub bez podpisywania (dla testów)
buildozer android debug
```

## Instalacja APK na telefonie

1. **Włącz opcję "Źródła nieznane"** w ustawieniach Androida
2. **Przenieś plik APK** na telefon (przez USB, email, itp.)
3. **Otwórz plik APK** na telefonie i zainstaluj
4. **Upewnij się, że plik `optimized_data_for_mobile.py` jest w folderze aplikacji**

## Ważne uwagi

### 1. Plik z danymi trasy

Aplikacja potrzebuje pliku `optimized_data_for_mobile.py` w tym samym katalogu co APK. Możesz:
- **Opcja A**: Dołącz plik do APK (zmodyfikuj buildozer.spec):
  ```ini
  source.include_exts = py,png,jpg,kv,atlas,json
  ```
  I upewnij się, że plik jest w katalogu źródłowym.

- **Opcja B**: Użytkownik musi ręcznie skopiować plik na telefon po instalacji.

### 2. Pierwsza kompilacja

Pierwsza kompilacja może zająć **30-60 minut**, ponieważ Buildozer:
- Pobierze Android SDK (około 1GB)
- Pobierze Android NDK (około 500MB)
- Skompiluje wszystkie zależności Python

### 3. Kolejne kompilacje

Kolejne kompilacje będą **znacznie szybsze** (5-15 minut), ponieważ zależności są już pobrane.

## Rozwiązywanie problemów

### Problem: "buildozer: command not found"
**Rozwiązanie:**
```bash
pip install --upgrade buildozer
# Lub użyj pełnej ścieżki:
python -m buildozer android debug
```

### Problem: "Android SDK not found"
**Rozwiązanie:**
Buildozer pobierze SDK automatycznie przy pierwszej kompilacji. Upewnij się, że masz połączenie z internetem.

### Problem: "kivy-garden.mapview not found"
**Rozwiązanie:**
Dodaj do buildozer.spec:
```ini
requirements = python3,kivy==2.1.0,plyer,kivy-garden.mapview
```

### Problem: APK się nie instaluje
**Rozwiązanie:**
- Sprawdź, czy masz włączone "Źródła nieznane"
- Sprawdź, czy APK jest dla odpowiedniej architektury (arm64-v8a dla nowszych telefonów)

## Alternatywa: Użyj Pydroid 3 (szybsze testowanie)

Jeśli chcesz szybko przetestować aplikację bez budowania APK:
1. Zainstaluj **Pydroid 3** na telefonie Android
2. Przenieś pliki `goodspeed_route_analyzer.py` i `optimized_data_for_mobile.py` na telefon
3. W Pydroid 3 zainstaluj: `kivy`, `plyer`, `kivy-garden.mapview`
4. Uruchom aplikację bezpośrednio w Pydroid 3

## Podsumowanie

✅ **Aplikacja jest gotowa do budowania APK!**
✅ **Plik buildozer.spec jest przygotowany**
✅ **Wszystkie zależności są zdefiniowane**

**Następny krok:** Zainstaluj Buildozer i uruchom `buildozer android debug`!

