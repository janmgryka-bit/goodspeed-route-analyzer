"""
GoodSpeed Route Backend - Moduł backendu do przetwarzania wideo i optymalizacji trasy
Zawiera funkcje core: ekstrakcja adresów, geokodowanie i optymalizacja trasy.
"""

import os
import tempfile
import time
import json
import re
import google.generativeai as genai
import googlemaps
from math import radians, sin, cos, sqrt, atan2

# Ładowanie zmiennych środowiskowych z pliku .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv nie jest wymagany, jeśli zmienne są ustawione w systemie

# Stałe API - wczytaj z zmiennych środowiskowych
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Konfiguracja Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Konfiguracja Google Maps API
gmaps = googlemaps.Client(key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

# Inicjalizacja modelu Gemini
try:
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
    except:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            model = genai.GenerativeModel('gemini-pro-vision')
except Exception as e:
    print(f"⚠️ Uwaga: Nie udało się załadować modelu Gemini. Błąd: {str(e)}")
    model = None


def upload_and_extract_video(video_file, progress_callback=None):
    """
    Przesyła cały plik wideo do Gemini File API i wyodrębnia tylko adresy.
    
    Args:
        video_file: Plik wideo (file-like object)
        progress_callback: Opcjonalna funkcja callback do aktualizacji postępu (message)
        
    Returns:
        Lista adresów w kolejności: ['UL. SZLACHECKA 18A/8, Warszawa', ...]
    """
    if model is None:
        if progress_callback:
            progress_callback("❌ Model Gemini nie jest dostępny!")
        return []
    
    # Zapisanie tymczasowego pliku wideo
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(video_file.read())
    tfile.close()
    video_path = tfile.name
    
    try:
        # Krok 1: Upload pliku do Gemini File API
        if progress_callback:
            progress_callback("📤 Przesyłanie pliku wideo do Gemini API...")
        uploaded_file = genai.upload_file(path=video_path)
        
        if progress_callback:
            progress_callback(f"✅ Plik przesłany: {uploaded_file.name}")
        
        # Czekaj na przetworzenie pliku przez File API
        max_wait_time = 300  # Maksymalnie 5 minut
        wait_time = 0
        
        while uploaded_file.state.name == "PROCESSING":
            if wait_time >= max_wait_time:
                if progress_callback:
                    progress_callback("❌ Przekroczono czas oczekiwania na przetworzenie pliku")
                genai.delete_file(uploaded_file.name)
                return []
            
            if progress_callback:
                progress_callback(f"⏳ Oczekiwanie na przetworzenie pliku... ({wait_time}s)")
            time.sleep(2)
            wait_time += 2
            uploaded_file = genai.get_file(uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            if progress_callback:
                progress_callback("❌ Przetwarzanie pliku nie powiodło się")
            genai.delete_file(uploaded_file.name)
            return []
        
        if progress_callback:
            progress_callback("🤖 Ekstrakcja adresów z wideo przez Gemini AI...")
        
        # Krok 2: Prompt dla Gemini - TYLKO ekstrakcja adresów w formacie JSON
        prompt = """To jest wideo, na którym przewijam listę 63 adresów dostaw w kolejności. Twoim zadaniem jest wyodrębnienie **KAŻDEGO unikalnego adresu dostawy**, zachowując ich kolejność. Zastosuj logikę: **adres (ulica i numer) ma bezwzględny priorytet nad kodem pocztowym**. Kod pocztowy użyj tylko do rozstrzygnięcia konfliktu nazwy ulicy (np. Rembertów vs. Wesoła). Zignoruj godziny i nazwy firm.

Zwróć wynik w czystym formacie JSON (bez dodatkowych komentarzy) jako listę 63 obiektów, zawierających wyłącznie pełny, poprawny adres:

[
  { "address": "[Pełny i poprawny adres: Ulica, Numer, Miasto/Dzielnica, Kod Pocztowy (opcjonalnie)]" },
  // ... pozostałe 62 obiekty
]

Zwróć TYLKO JSON, bez dodatkowych komentarzy przed lub po JSON."""
        
        # Krok 3: JEDNO wywołanie API - przesyłamy CAŁY plik wideo i otrzymujemy listę adresów
        response = model.generate_content([prompt, uploaded_file])
        
        # Krok 4: Pobranie odpowiedzi (lista adresów)
        extracted_text = ""
        if response:
            # Różne sposoby dostępu do tekstu w zależności od wersji API
            if hasattr(response, 'text'):
                extracted_text = response.text.strip()
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content'):
                    extracted_text = response.candidates[0].content.parts[0].text.strip()
            elif hasattr(response, 'parts'):
                extracted_text = response.parts[0].text.strip()
        
        # Krok 5: Parsowanie odpowiedzi JSON z adresami
        addresses = []
        if extracted_text:
            # Usuń markdown code blocks jeśli występują
            extracted_text = re.sub(r'```json\s*', '', extracted_text)
            extracted_text = re.sub(r'```\s*', '', extracted_text)
            extracted_text = extracted_text.strip()
            
            try:
                # Spróbuj sparsować jako JSON
                parsed_data = json.loads(extracted_text)
                
                # Jeśli to lista obiektów z kluczem "address"
                if isinstance(parsed_data, list):
                    for item in parsed_data:
                        if isinstance(item, dict) and 'address' in item:
                            address = item['address'].strip()
                            if address:
                                addresses.append(address)
                        elif isinstance(item, str):
                            # Jeśli lista zawiera bezpośrednio stringi
                            if item.strip():
                                addresses.append(item.strip())
                # Jeśli to pojedynczy obiekt z listą adresów
                elif isinstance(parsed_data, dict):
                    if 'addresses' in parsed_data:
                        addresses = [addr.strip() for addr in parsed_data['addresses'] if addr.strip()]
                    elif 'address' in parsed_data:
                        addresses = [parsed_data['address'].strip()]
                
            except json.JSONDecodeError:
                # Fallback: jeśli JSON nie zadziała, spróbuj parsować jako listę linii (stary format)
                if progress_callback:
                    progress_callback("⚠️ Nie udało się sparsować odpowiedzi jako JSON, próbuję parsować jako listę linii...")
                lines = extracted_text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Usuń numery, kropki na początku linii
                    line = re.sub(r'^\d+\.\s*', '', line)
                    line = line.strip('.,;:- ')
                    line = line.replace('**', '').replace('`', '').strip()
                    
                    if line and len(line) > 5:
                        addresses.append(line)
        
        # Krok 6: Usunięcie pliku z serwerów Gemini (natychmiast po otrzymaniu odpowiedzi)
        try:
            genai.delete_file(uploaded_file.name)
            if progress_callback:
                progress_callback("🗑️ Plik wideo usunięty z serwerów Gemini (prywatność)")
        except Exception as e:
            if progress_callback:
                progress_callback(f"⚠️ Nie udało się usunąć pliku z serwerów: {str(e)}")
        
        return addresses
        
    except Exception as e:
        error_msg = str(e)
        
        # Próba usunięcia pliku z serwerów Gemini
        uploaded_file_name = None
        try:
            if 'uploaded_file' in locals():
                uploaded_file_name = uploaded_file.name
                genai.delete_file(uploaded_file_name)
                if progress_callback:
                    progress_callback("🗑️ Plik wideo usunięty z serwerów Gemini (po błędzie)")
        except Exception as delete_error:
            if uploaded_file_name and progress_callback:
                progress_callback(f"⚠️ Nie udało się usunąć pliku {uploaded_file_name} z serwerów: {str(delete_error)}")
        
        if progress_callback:
            if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                progress_callback("❌ Przekroczono limit API Gemini. Spróbuj ponownie później.")
            elif "429" in error_msg.lower() or "too many requests" in error_msg.lower():
                progress_callback("❌ Zbyt wiele żądań. Poczekaj chwilę i spróbuj ponownie.")
            elif "file size" in error_msg.lower() or "too large" in error_msg.lower():
                progress_callback("❌ Plik wideo jest zbyt duży. Maksymalny rozmiar to zwykle 20MB dla Gemini API.")
            else:
                progress_callback(f"❌ Błąd podczas analizy wideo: {error_msg[:200]}")
        
        return []
    
    finally:
        # Usuń lokalny plik tymczasowy
        if os.path.exists(video_path):
            os.unlink(video_path)


def geocode_address_google(address):
    """
    Konwertuje adres na współrzędne lat/lon używając Google Maps Geocoding API.
    Najdokładniejsze geokodowanie dostępne.
    
    Args:
        address: Adres do geokodowania
        
    Returns:
        Tuple (latitude, longitude) lub None
    """
    if not address or not gmaps:
        return None
    
    try:
        # Dodajemy 'Polska' dla lepszej precyzji w kontekście
        address_query = f"{address}, Polska"
        
        # Wywołanie API
        geocode_result = gmaps.geocode(address_query)
        
        if geocode_result:
            # Bierzemy pierwszy, najbardziej precyzyjny wynik
            location = geocode_result[0]['geometry']['location']
            return (location['lat'], location['lng'])
        else:
            return None
    except Exception as e:
        print(f"⚠️ Wyjątek geokodowania: {str(e)}")
        return None


def geocode_addresses_list(addresses_list, progress_callback=None):
    """
    Geokoduje listę adresów używając Google Maps Geocoding API.
    Najdokładniejsze geokodowanie dostępne.
    
    Args:
        addresses_list: Lista adresów do geokodowania
        progress_callback: Opcjonalna funkcja callback do aktualizacji postępu (idx, total, address)
        
    Returns:
        Lista słowników z adresami i współrzędnymi: [{'id': int, 'address': str, 'coordinates': (lat, lon), 'lat': float, 'lon': float}, ...]
    """
    if not gmaps:
        if progress_callback:
            progress_callback(0, len(addresses_list), "❌ Google Maps API nie jest skonfigurowane!")
        return []
    
    delivery_points = []
    
    for idx, address in enumerate(addresses_list, 1):
        if progress_callback:
            progress_callback(idx, len(addresses_list), address)
        
        # Geokoduj adres przez Google Maps API
        coordinates = geocode_address_google(address)
        
        if coordinates:
            delivery_points.append({
                'id': idx,
                'address': address,
                'coordinates': coordinates,
                'lat': coordinates[0],
                'lon': coordinates[1]
            })
        else:
            # Dodaj adres nawet bez geokodowania (dla wyświetlenia)
            delivery_points.append({
                'id': idx,
                'address': address,
                'coordinates': None,
                'lat': None,
                'lon': None
            })
        
        # Małe opóźnienie, aby uniknąć rate limiting
        time.sleep(0.1)
    
    return delivery_points


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Oblicza odległość haversine między dwoma punktami GPS w kilometrach.
    
    Args:
        lat1, lon1: Współrzędne pierwszego punktu
        lat2, lon2: Współrzędne drugiego punktu
        
    Returns:
        Odległość w kilometrach
    """
    R = 6371  # Promień Ziemi w km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def optimize_route_nearest_neighbor(start_point, all_points):
    """
    Optymalizuje trasę dostaw używając algorytmu Nearest Neighbor (TSP).
    Z obecnego punktu zawsze wybiera ten następny, który jest najbliżej.
    
    Args:
        start_point: Punkt startowy (pierwszy punkt z listy)
        all_points: Lista wszystkich punktów dostaw z współrzędnymi
        
    Returns:
        Posortowana lista punktów w kolejności optymalnej trasy
    """
    if not all_points or len(all_points) < 2:
        return all_points
    
    # Filtruj tylko punkty z geokodowaniem
    valid_points = [p for p in all_points if p.get('coordinates') is not None]
    
    if len(valid_points) < 2:
        return valid_points
    
    # Algorytm Nearest Neighbor (greedy TSP)
    optimized_route = []
    remaining_points = valid_points.copy()
    
    # Zacznij od punktu startowego (Punkt 1 z listy)
    if start_point in remaining_points:
        remaining_points.remove(start_point)
        current_point = start_point
    else:
        # Jeśli punkt startowy nie jest w liście, użyj pierwszego
        current_point = remaining_points.pop(0)
    
    optimized_route.append(current_point)
    
    # Znajdź najbliższy punkt do każdego kolejnego
    while remaining_points:
        min_distance = float('inf')
        nearest_point = None
        nearest_index = -1
        
        current_lat, current_lon = current_point['coordinates']
        
        for idx, point in enumerate(remaining_points):
            point_lat, point_lon = point['coordinates']
            distance = haversine_distance(current_lat, current_lon, point_lat, point_lon)
            
            if distance < min_distance:
                min_distance = distance
                nearest_point = point
                nearest_index = idx
        
        if nearest_point:
            optimized_route.append(nearest_point)
            remaining_points.pop(nearest_index)
            current_point = nearest_point
    
    return optimized_route


def optimize_route(points_data):
    """
    Alias dla optimize_route_nearest_neighbor - używa pierwszego punktu jako startowego.
    
    Args:
        points_data: Lista punktów dostaw
        
    Returns:
        Zoptymalizowana lista punktów
    """
    if not points_data or len(points_data) < 2:
        return points_data
    
    start_point = points_data[0] if points_data[0].get('coordinates') else None
    if start_point:
        return optimize_route_nearest_neighbor(start_point, points_data)
    else:
        return points_data


def generate_final_optimized_data(video_file, progress_callback=None):
    """
    Główna funkcja: przyjmuje wideo, wywołuje sekwencyjnie wszystkie moduły
    i zwraca finalną listę zoptymalizowanych, geokodowanych punktów dostaw.
    
    Args:
        video_file: Plik wideo (file-like object)
        progress_callback: Opcjonalna funkcja callback do aktualizacji postępu
        
    Returns:
        Lista zoptymalizowanych punktów dostaw: [{'id': int, 'address': str, 'lat': float, 'lon': float, 'coordinates': (lat, lon)}, ...]
    """
    # Krok 1: Ekstrakcja adresów z wideo
    if progress_callback:
        progress_callback("🤖 Krok 1: Ekstrakcja adresów z wideo przez Gemini AI...")
    
    def extract_progress(msg):
        if progress_callback:
            progress_callback(f"  {msg}")
    
    addresses_list = upload_and_extract_video(video_file, progress_callback=extract_progress)
    
    if not addresses_list:
        if progress_callback:
            progress_callback("❌ Nie udało się wyodrębnić adresów z wideo!")
        return []
    
    if progress_callback:
        progress_callback(f"✅ Znaleziono {len(addresses_list)} adresów")
    
    # Krok 2: Geokodowanie adresów
    if progress_callback:
        progress_callback("📍 Krok 2: Geokodowanie adresów przez Google Maps API...")
    
    def geocode_progress(idx, total, address):
        if progress_callback:
            progress_callback(f"  Geokodowanie {idx}/{total}: {address[:50]}...")
    
    delivery_points = geocode_addresses_list(addresses_list, progress_callback=geocode_progress)
    
    if not delivery_points:
        if progress_callback:
            progress_callback("❌ Nie udało się geokodować adresów!")
        return []
    
    geocoded_count = sum(1 for p in delivery_points if p.get('coordinates') is not None)
    if progress_callback:
        progress_callback(f"✅ Pomyślnie geokodowano {geocoded_count} z {len(delivery_points)} adresów")
    
    # Krok 3: Optymalizacja trasy
    if progress_callback:
        progress_callback("🛣️ Krok 3: Optymalizacja trasy używając algorytmu Nearest Neighbor...")
    
    optimized_points = optimize_route(delivery_points)
    
    if progress_callback:
        progress_callback(f"✅ Trasa zoptymalizowana! {len(optimized_points)} punktów")
    
    return optimized_points

