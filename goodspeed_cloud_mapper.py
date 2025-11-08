"""
GoodSpeed Cloud Mapper - Aplikacja do analizy tras dostaw z wideo (Frontend Streamlit)
Aplikacja używa route_backend do przetwarzania wideo i zapisuje dane do pliku Pythona dla aplikacji mobilnej.
"""

import streamlit as st
import os
import tempfile
import folium
from folium import plugins
import route_backend
from route_backend import haversine_distance

# Ładowanie zmiennych środowiskowych z pliku .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv nie jest wymagany, jeśli zmienne są ustawione w systemie

# Konfiguracja Streamlit
st.set_page_config(
    page_title="GoodSpeed Cloud Mapper",
    page_icon="🧭",
    layout="wide"
)


def save_optimized_data_to_python(optimized_points, filename='optimized_data_for_mobile.py'):
    """
    Zapisuje zoptymalizowane dane do pliku Pythona dla aplikacji mobilnej.
    
    Args:
        optimized_points: Lista zoptymalizowanych punktów dostaw
        filename: Nazwa pliku wyjściowego
        
    Returns:
        Ścieżka do zapisanego pliku
    """
    # Przygotuj dane do zapisu
    data_list = []
    for point in optimized_points:
        data_list.append({
            'id': point.get('id', 0),
            'address': point.get('address', ''),
            'lat': point.get('lat'),
            'lon': point.get('lon')
        })
    
    # Generuj kod Pythona
    python_code = f"""# Automatycznie wygenerowany plik z zoptymalizowanymi danymi trasy
# Nie edytuj tego pliku ręcznie - jest generowany przez goodspeed_cloud_mapper.py

DELIVERY_POINTS = {repr(data_list)}
"""
    
    # Zapisz do pliku
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(python_code)
    
    return filename


def _old_extract_addresses_from_video(video_file):
    """
    Przesyła cały plik wideo do Gemini File API i wyodrębnia tylko adresy.
    
    Args:
        video_file: Plik wideo przesłany przez użytkownika
        
    Returns:
        Lista adresów w kolejności: ['UL. SZLACHECKA 18A/8, Warszawa', ...]
    """
    if model is None:
        st.error("❌ Model Gemini nie jest dostępny!")
        return []
    
    # Zapisanie tymczasowego pliku wideo
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(video_file.read())
    tfile.close()
    video_path = tfile.name
    
    try:
        # Krok 1: Upload pliku do Gemini File API
        st.info("📤 Przesyłanie pliku wideo do Gemini API...")
        uploaded_file = genai.upload_file(path=video_path)
        
        st.success(f"✅ Plik przesłany: {uploaded_file.name}")
        
        # Czekaj na przetworzenie pliku przez File API
        status_text = st.empty()
        max_wait_time = 300  # Maksymalnie 5 minut
        wait_time = 0
        
        while uploaded_file.state.name == "PROCESSING":
            if wait_time >= max_wait_time:
                st.error("❌ Przekroczono czas oczekiwania na przetworzenie pliku")
                genai.delete_file(uploaded_file.name)
                return []
            
            status_text.text(f"⏳ Oczekiwanie na przetworzenie pliku... ({wait_time}s)")
            time.sleep(2)
            wait_time += 2
            uploaded_file = genai.get_file(uploaded_file.name)
        
        if uploaded_file.state.name == "FAILED":
            st.error("❌ Przetwarzanie pliku nie powiodło się")
            genai.delete_file(uploaded_file.name)
            return []
        
        status_text.empty()
        st.info("🤖 Ekstrakcja adresów z wideo przez Gemini AI...")
        st.info("💡 **Cały plik wideo jest analizowany jednorazowo - otrzymasz listę adresów!**")
        
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
                st.warning("⚠️ Nie udało się sparsować odpowiedzi jako JSON, próbuję parsować jako listę linii...")
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
            st.info("🗑️ Plik wideo usunięty z serwerów Gemini (prywatność)")
        except Exception as e:
            st.warning(f"⚠️ Nie udało się usunąć pliku z serwerów: {str(e)}")
        
        return addresses
        
    except Exception as e:
        error_msg = str(e)
        
        # Krok 6 (w przypadku błędu): Próba usunięcia pliku z serwerów Gemini
        uploaded_file_name = None
        try:
            if 'uploaded_file' in locals():
                uploaded_file_name = uploaded_file.name
                genai.delete_file(uploaded_file_name)
                st.info("🗑️ Plik wideo usunięty z serwerów Gemini (po błędzie)")
        except Exception as delete_error:
            if uploaded_file_name:
                st.warning(f"⚠️ Nie udało się usunąć pliku {uploaded_file_name} z serwerów: {str(delete_error)}")
        
        # Obsługa różnych typów błędów
        if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            st.error("❌ Przekroczono limit API Gemini. Spróbuj ponownie później.")
        elif "429" in error_msg.lower() or "too many requests" in error_msg.lower():
            st.error("❌ Zbyt wiele żądań. Poczekaj chwilę i spróbuj ponownie.")
        elif "file size" in error_msg.lower() or "too large" in error_msg.lower():
            st.error("❌ Plik wideo jest zbyt duży. Maksymalny rozmiar to zwykle 20MB dla Gemini API.")
        else:
            st.error(f"❌ Błąd podczas analizy wideo: {error_msg[:200]}")
        
        return []
    
    finally:
        # Usuń lokalny plik tymczasowy
        if os.path.exists(video_path):
            os.unlink(video_path)


def _old_geocode_address_google(address):
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
            st.warning(f"⚠️ Błąd geokodowania dla adresu: {address}")
            return None
    except Exception as e:
        st.warning(f"⚠️ Wyjątek geokodowania: {str(e)}")
        return None


def _old_geocode_addresses_list(addresses_list):
    """
    Geokoduje listę adresów używając Google Maps Geocoding API.
    Najdokładniejsze geokodowanie dostępne.
    
    Args:
        addresses_list: Lista adresów do geokodowania
        
    Returns:
        Lista słowników z adresami i współrzędnymi: [{'id': int, 'address': str, 'coordinates': (lat, lon)}, ...]
    """
    if not gmaps:
        st.error("❌ Google Maps API nie jest skonfigurowane! Sprawdź klucz API.")
        return []
    
    delivery_points = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, address in enumerate(addresses_list, 1):
        status_text.text(f"Geokodowanie adresu {idx}/{len(addresses_list)}: {address}")
        
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
            st.warning(f"⚠️ Nie udało się geokodować: {address}")
        
        progress_bar.progress(idx / len(addresses_list))
        
        # Małe opóźnienie, aby uniknąć rate limiting (Google Maps ma wyższy limit niż Nominatim)
        time.sleep(0.1)
    
    progress_bar.empty()
    status_text.empty()
    
    return delivery_points


# Funkcje optimize_route i haversine_distance są importowane z route_backend


def create_delivery_map(delivery_points, optimized_order=True):
    """
    Tworzy interaktywną mapę Folium z punktami dostaw.
    Używa współrzędnych z Google Maps Geocoding API i zoptymalizowanej trasy.
    
    Args:
        delivery_points: Lista punktów dostaw z współrzędnymi (z Google Maps API)
        optimized_order: Czy użyć zoptymalizowanej kolejności trasy
        
    Returns:
        Ścieżka do zapisanego pliku HTML z mapą lub None
    """
    # Filtruj tylko punkty z geokodowaniem
    geocoded_points = [p for p in delivery_points if p.get('coordinates') is not None]
    
    if not geocoded_points:
        st.warning("⚠️ Brak punktów z geokodowaniem do wyświetlenia na mapie!")
        return None
    
    # Optymalizuj trasę jeśli wymagane
    if optimized_order and len(geocoded_points) > 1:
        geocoded_points = route_backend.optimize_route(geocoded_points)
    
    # Wyznacz centrum mapy (pierwszy punkt)
    center_lat, center_lon = geocoded_points[0]['coordinates']
    
    # Utwórz mapę
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Dodaj punkty dostaw (numerowane od 1 do 63 w zoptymalizowanej kolejności)
    for idx, point in enumerate(geocoded_points, 1):
        lat, lon = point['coordinates']
        address = point['address']
        original_id = point.get('id', idx)  # Oryginalne ID z wideo
        
        # Kolor pinezki - pierwsza jest zielona, ostatnia czerwona, pozostałe niebieskie
        if idx == 1:
            color = 'green'
            icon = 'play'
        elif idx == len(geocoded_points):
            color = 'red'
            icon = 'stop'
        else:
            color = 'blue'
            icon = 'info-sign'
        
        # Dodaj marker z numerem kolejności w zoptymalizowanej trasie
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"<b>Punkt {idx} (zoptymalizowana trasa)</b><br>"
                f"Oryginalne ID: {original_id}<br>"
                f"{address}",
                max_width=300
            ),
            tooltip=f"Punkt {idx}: {address}",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
    
    # Dodaj linię łączącą punkty (trasa)
    if len(geocoded_points) > 1:
        route_coordinates = [[point['coordinates'][0], point['coordinates'][1]] 
                            for point in geocoded_points]
        folium.PolyLine(
            route_coordinates,
            color='blue',
            weight=3,
            opacity=0.7,
            tooltip="Trasa dostaw"
        ).add_to(m)
    
    # Dodaj kontrolkę pełnego ekranu
    plugins.Fullscreen().add_to(m)
    
    # Zapisz mapę do pliku HTML
    temp_map_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
    m.save(temp_map_file.name)
    temp_map_file.close()
    
    return temp_map_file.name


def main():
    """Główna funkcja aplikacji Streamlit."""
    
    # Nagłówek
    st.title("🧭 GoodSpeed Cloud Mapper")
    st.markdown("---")
    st.markdown("""
    **Aplikacja do analizy tras dostaw z wideo z wykorzystaniem Gemini AI + Google Maps Geocoding API**
    
    Prześlij plik wideo zawierający adresy dostaw. Aplikacja:
    1. Przesyła cały plik wideo do Gemini API (ekstrakcja adresów w formacie JSON)
    2. Geokoduje adresy przez Google Maps Geocoding API (najdokładniejsze geokodowanie)
    3. Optymalizuje trasę używając algorytmu Nearest Neighbor (TSP)
    4. Wygeneruje interaktywną mapę z zoptymalizowaną trasą dostaw
    
    **Zalety:** 
    - Szybka ekstrakcja adresów przez Gemini AI (chmura)
    - Najdokładniejsze geokodowanie przez Google Maps API
    - Zoptymalizowana trasa minimalizująca dystans
    """)
    
    
    # Upload pliku wideo
    st.subheader("📹 Przesyłanie wideo")
    uploaded_file = st.file_uploader(
        "Wybierz plik wideo (.mp4)",
        type=['mp4'],
        help="Obsługiwany format: MP4 (maksymalny rozmiar zwykle 20MB dla Gemini API)"
    )
    
    if uploaded_file is not None:
        file_size_mb = uploaded_file.size / (1024*1024)
        st.success(f"✅ Załadowano plik: {uploaded_file.name}")
        st.info(f"Rozmiar pliku: {file_size_mb:.2f} MB")
        
        if file_size_mb > 20:
            st.warning("⚠️ Plik może być zbyt duży dla Gemini API (maksymalny rozmiar to zwykle 20MB)")
    
    # Opcje
    st.markdown("---")
    st.subheader("⚙️ Opcje")
    show_raw_response = st.checkbox("📄 Pokaż surową odpowiedź Gemini AI (lista adresów)", value=False)
    
    # Przycisk analizy
    st.markdown("---")
    if st.button("🚀 Analizuj Wideo i Generuj Mapę", type="primary", use_container_width=True):
        
        if uploaded_file is None:
            st.error("❌ Proszę najpierw przesłać plik wideo!")
            return
        
        with st.spinner("🔄 Przetwarzanie wideo..."):
            # Użyj backendu do przetworzenia wideo
            status_container = st.container()
            
            def progress_callback(message):
                """Callback do aktualizacji postępu w Streamlit."""
                with status_container:
                    if message.startswith("  "):
                        st.info(message.strip())
                    elif "✅" in message or "❌" in message:
                        if "✅" in message:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.info(message)
            
            # Wywołaj główną funkcję backendu
            optimized_points = route_backend.generate_final_optimized_data(
                uploaded_file,
                progress_callback=progress_callback
            )
            
            if not optimized_points:
                st.error("❌ Nie udało się przetworzyć wideo!")
                return
            
            # Wyświetl listę adresów
            st.subheader(f"📋 Lista adresów - kolejność oryginalna ({len(optimized_points)} adresów)")
            for idx, point in enumerate(optimized_points, 1):
                st.write(f"**{idx}.** {point['address']}")
            
            if show_raw_response:
                with st.expander("📄 Zobacz wszystkie adresy"):
                    for idx, point in enumerate(optimized_points, 1):
                        st.text(f"{idx}. {point['address']}")
            
            st.markdown("---")
            
            # Podsumowanie geokodowania
            geocoded_count = sum(1 for p in optimized_points if p.get('coordinates') is not None)
            not_geocoded_count = len(optimized_points) - geocoded_count
            
            if geocoded_count > 0:
                st.success(f"✅ Pomyślnie geokodowano {geocoded_count} z {len(optimized_points)} adresów")
            else:
                st.warning(f"⚠️ Nie udało się geokodować żadnego adresu ({len(optimized_points)} adresów tekstowych znalezionych)")
            
            if not_geocoded_count > 0:
                st.info(f"ℹ️ {not_geocoded_count} adresów nie zostało geokodowanych (będą widoczne na liście, ale nie na mapie)")
            
            # Wyświetl listę punktów z współrzędnymi
            st.subheader(f"📋 Lista punktów dostaw z geokodowaniem ({len(optimized_points)} punktów)")
            for idx, point in enumerate(optimized_points, 1):
                if point.get('coordinates'):
                    lat, lon = point['coordinates']
                    st.write(f"**{idx}.** {point['address']} → ({lat:.6f}, {lon:.6f})")
                else:
                    st.write(f"**{idx}.** {point['address']} → ❌ Brak geokodowania")
            
            st.markdown("---")
            
            # Oblicz całkowity dystans
            if len(optimized_points) > 1:
                total_distance = 0
                for i in range(len(optimized_points) - 1):
                    if optimized_points[i].get('coordinates') and optimized_points[i + 1].get('coordinates'):
                        lat1, lon1 = optimized_points[i]['coordinates']
                        lat2, lon2 = optimized_points[i + 1]['coordinates']
                        total_distance += haversine_distance(lat1, lon1, lat2, lon2)
                
                st.success(f"✅ Trasa zoptymalizowana! Całkowity dystans: {total_distance:.2f} km")
                st.info(f"📊 Punkty w kolejności optymalnej: {len(optimized_points)}")
            
            st.markdown("---")
            
            # Krok 4: Zapisanie danych do pliku Pythona dla aplikacji mobilnej
            st.subheader("📱 Krok 4: Zapisanie danych do pliku Pythona (dla aplikacji mobilnej)")
            st.info("💡 Zapisuję zoptymalizowane dane do pliku optimized_data_for_mobile.py!")
            
            try:
                saved_file = save_optimized_data_to_python(optimized_points)
                st.success(f"✅ Dane zapisane do pliku: {saved_file}")
                st.info("💡 Aplikacja mobilna może teraz zaimportować dane z tego pliku!")
            except Exception as e:
                st.error(f"❌ Błąd podczas zapisywania pliku: {str(e)}")
            
            st.markdown("---")
            
            # Krok 5: Generowanie mapy (używamy współrzędnych z Google Maps API + zoptymalizowanej trasy)
            st.subheader("🗺️ Krok 5: Generowanie mapy z zoptymalizowaną trasą")
            st.info("💡 Używam współrzędnych z Google Maps API + zoptymalizowanej kolejności!")
            
            map_file = create_delivery_map(optimized_points, optimized_order=False)  # Już zoptymalizowane
            
            if map_file:
                st.success("✅ Mapa została wygenerowana!")
                
                # Wyświetl mapę
                st.subheader("🗺️ Interaktywna Mapa Trasy Dostaw")
                with open(map_file, 'r', encoding='utf-8') as f:
                    map_html = f.read()
                
                st.components.v1.html(map_html, height=600)
                
                # Przycisk do pobrania mapy
                with open(map_file, 'rb') as f:
                    st.download_button(
                        label="💾 Pobierz mapę (HTML)",
                        data=f.read(),
                        file_name="delivery_map.html",
                        mime="text/html"
                    )
                
                # Usuń tymczasowy plik po wyświetleniu
                try:
                    os.unlink(map_file)
                except:
                    pass
            else:
                st.warning("⚠️ Nie udało się wygenerować mapy (brak punktów z geokodowaniem)")


if __name__ == '__main__':
    main()
