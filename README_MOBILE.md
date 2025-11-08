# GoodSpeed Route Analyzer - Aplikacja Mobilna

Aplikacja mobilna w Pythonie (Kivy) do zarządzania trasą dostaw z funkcjami odznaczania i śledzenia GPS.

## Funkcjonalności

✅ **Ładowanie trasy z JSON** - Ładuje zoptymalizowaną trasę z pliku JSON  
✅ **Mapa OpenStreetMap** - Lekka mapa z pinezkami dla każdego punktu dostawy  
✅ **Trzy stany pinezek:**
   - 🔵 Niebieski/Czerwony - Do zrobienia (oczekujący)
   - 🟡 Żółty - Aktualny cel
   - 🟢 Zielony - Zrobione (ukończony)

✅ **Odznaczanie dostaw** - Szybkie odznaczanie ukończonych dostaw  
✅ **Śledzenie GPS** - Wyświetla lokalizację kierowcy na mapie  
✅ **Automatyczne wykrywanie bliskości** - Gdy kierowca jest w promieniu 50m od celu, wyświetla się przycisk "POTWIERDŹ ZAKOŃCZENIE"  
✅ **Panel kontrolny** - Statystyki postępu i przyciski sterujące  

## Instalacja

1. Zainstaluj zależności:
```bash
pip install kivy kivy-garden.mapview plyer
```

Lub użyj requirements.txt:
```bash
pip install -r requirements.txt
```

2. Zainstaluj kivy-garden.mapview:
```bash
pip install kivy-garden.mapview
```

## Użycie

### 1. Wygeneruj plik JSON z trasą

Użyj aplikacji `goodspeed_cloud_mapper.py` (Streamlit) do wygenerowania zoptymalizowanej trasy, a następnie pobierz plik `route.json`.

### 2. Uruchom aplikację mobilną

```bash
python goodspeed_route_analyzer.py route.json
```

Lub jeśli plik nazywa się `route.json`:
```bash
python goodspeed_route_analyzer.py
```

## Format pliku JSON

Plik JSON powinien zawierać listę punktów dostaw w formacie:

```json
[
  {
    "id": 1,
    "address": "UL. SZLACHECKA 18A/8, Warszawa",
    "lat": 52.2297,
    "lon": 21.0122
  },
  {
    "id": 2,
    "address": "UL. MARSZAŁKOWSKA 1, Warszawa",
    "lat": 52.2298,
    "lon": 21.0123
  }
]
```

## Funkcje aplikacji

### Panel kontrolny

- **Statystyki postępu** - Wyświetla liczbę ukończonych/pozostałych dostaw
- **Odległość do celu** - Pokazuje odległość w metrach do aktualnego punktu docelowego
- **Przycisk "Zrobione"** - Oznacza aktualny punkt jako ukończony
- **Przycisk "POTWIERDŹ ZAKOŃCZENIE"** - Pojawia się automatycznie, gdy kierowca jest w promieniu 50m od celu

### Interakcja z mapą

- **Kliknięcie w pinezkę** - Ustawia punkt jako aktualny cel
- **Automatyczne przejście** - Po oznaczeniu punktu jako ukończony, następny niewykonany punkt staje się aktualnym celem

### GPS

Aplikacja automatycznie śledzi lokalizację kierowcy i:
- Wyświetla pozycję na mapie
- Oblicza odległość do aktualnego celu
- Automatycznie wykrywa, gdy kierowca jest blisko celu (50m)

## Rozwiązywanie problemów

### MapView nie jest dostępne

Jeśli widzisz komunikat o braku MapView:
```bash
pip install kivy-garden.mapview
```

### GPS nie działa

Upewnij się, że:
- Na urządzeniu mobilnym masz włączone uprawnienia do lokalizacji
- Na komputerze desktop GPS może nie działać (wymaga urządzenia mobilnego)

### Aplikacja nie ładuje trasy

Sprawdź:
- Czy plik JSON istnieje i ma poprawny format
- Czy wszystkie punkty mają współrzędne (lat, lon)

## Struktura kodu

- `RouteAnalyzerApp` - Główna aplikacja Kivy
- `RouteManager` - Zarządza trasą i stanem dostaw
- `DeliveryPoint` - Reprezentuje pojedynczy punkt dostawy
- `GPSManager` - Zarządza lokalizacją GPS
- `RouteMapView` - Główny widok mapy z panelami kontrolnymi

## Wymagania systemowe

- Python 3.7+
- Kivy 2.1.0+
- kivy-garden.mapview
- plyer (dla GPS)
- Urządzenie z GPS (dla pełnej funkcjonalności)

## Uwagi

- Aplikacja działa najlepiej na urządzeniach mobilnych (Android/iOS)
- Na komputerze desktop GPS może nie działać
- MapView wymaga połączenia z internetem do ładowania map OpenStreetMap

