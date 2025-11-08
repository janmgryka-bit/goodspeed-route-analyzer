"""
GoodSpeed Route Analyzer - Aplikacja mobilna do analizy tras dostaw z wideo
Aplikacja przetwarza wideo, wykorzystuje Gemini Vision AI do ekstrakcji adresów i generuje interaktywną mapę dostaw.
"""

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import tempfile
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import folium
from folium import plugins
import time
import re
import google.generativeai as genai

# Ładowanie zmiennych środowiskowych z pliku .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv nie jest wymagany, jeśli zmienne są ustawione w systemie

# Konfiguracja Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("❌ Błąd: GEMINI_API_KEY nie jest ustawiony w zmiennych środowiskowych!")
    st.stop()
genai.configure(api_key=GEMINI_API_KEY)

# Konfiguracja Streamlit
st.set_page_config(
    page_title="GoodSpeed Route Analyzer",
    page_icon="🧭",
    layout="wide"
)

# Inicjalizacja geokodera
geolocator = Nominatim(user_agent="goodspeed_route_analyzer")

# Inicjalizacja modelu Gemini
try:
    # Użyj gemini-2.0-flash-exp (najnowszy) lub fallback do gemini-1.5-flash
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
    except:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            model = genai.GenerativeModel('gemini-pro-vision')
except Exception as e:
    st.warning(f"Uwaga: Nie udało się załadować modelu Gemini. Błąd: {str(e)}")
    model = None


def analyze_video_frames(video_file):
    """
    Analizuje wideo i zwraca listę unikalnych klatek do analizy przez AI.
    
    Args:
        video_file: Plik wideo przesłany przez użytkownika
        
    Returns:
        Lista unikalnych klatek (obiekty PIL Image)
    """
    # Zapisanie tymczasowego pliku wideo
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(video_file.read())
    tfile.close()
    
    # Otwarcie wideo
    cap = cv2.VideoCapture(tfile.name)
    
    unique_frames = []
    frame_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Analizuj co 10. klatkę
            if frame_count % 10 == 0:
                # Konwersja BGR na RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Zapisz klatkę jako obraz PIL
                unique_frames.append({
                    'frame': Image.fromarray(frame_rgb),
                    'frame_number': frame_count
                })
            
            frame_count += 1
            
            # Aktualizuj pasek postępu
            if total_frames > 0:
                progress = min(frame_count / total_frames, 1.0)
                progress_bar.progress(progress)
                status_text.text(f"Ekstrakcja klatek: {frame_count}/{total_frames}")
        
        cap.release()
        status_text.text(f"Wyodrębniono {len(unique_frames)} klatek do analizy")
        
    finally:
        # Usuń tymczasowy plik
        if os.path.exists(tfile.name):
            os.unlink(tfile.name)
    
    progress_bar.empty()
    status_text.empty()
    
    return unique_frames


def extract_addresses_with_ai(frame_list, max_frames=None, delay_between_calls=1.0):
    """
    Wyodrębnia adresy z klatek używając Gemini Vision AI.
    
    Args:
        frame_list: Lista unikalnych klatek
        max_frames: Maksymalna liczba klatek do analizy (None = wszystkie)
        delay_between_calls: Opóźnienie w sekundach między wywołaniami API
        
    Returns:
        Lista unikalnych adresów w kolejności pojawienia się
    """
    if model is None:
        st.error("❌ Model Gemini nie jest dostępny!")
        return []
    
    unique_addresses = []
    seen_addresses = set()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Ogranicz liczbę klatek jeśli podano limit
    frames_to_process = frame_list[:max_frames] if max_frames else frame_list
    
    prompt = """Zidentyfikuj i wyodrębnij tylko polskie adresy dostawy (kod pocztowy + ulica + numer) widoczne na tej karcie z aplikacji GoodSpeed. Zignoruj wszystkie godziny, nazwy firm i wskaźniki (np. P3-22). Zwróć tylko surowy tekst adresów, jeden adres w osobnej linii."""

    consecutive_errors = 0
    max_consecutive_errors = 5
    
    for idx, frame_data in enumerate(frames_to_process):
        frame = frame_data['frame']
        frame_number = frame_data['frame_number']
        
        status_text.text(f"Analiza klatki {idx + 1}/{len(frames_to_process)} przez Gemini AI...")
        
        # Opóźnienie między wywołaniami API (rate limiting)
        if idx > 0:
            time.sleep(delay_between_calls)
        
        # Retry logic z exponential backoff
        max_retries = 3
        retry_delay = 2.0
        success = False
        
        for retry in range(max_retries):
            try:
                # Wywołaj Gemini Vision API
                response = model.generate_content([prompt, frame])
                success = True
                consecutive_errors = 0
                break
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Sprawdź typ błędu
                if "quota" in error_msg or "rate limit" in error_msg:
                    if retry < max_retries - 1:
                        # Exponential backoff dla rate limit
                        wait_time = retry_delay * (2 ** retry)
                        status_text.text(f"⏳ Limit API - czekam {wait_time:.1f}s przed ponowną próbą...")
                        time.sleep(wait_time)
                    else:
                        st.error(f"❌ Przekroczono limit API Gemini dla klatki {frame_number}. Pomijam tę klatkę.")
                        consecutive_errors += 1
                        break
                        
                elif "429" in error_msg or "too many requests" in error_msg:
                    # Rate limit - dłuższe oczekiwanie
                    wait_time = retry_delay * (2 ** retry) * 2
                    if retry < max_retries - 1:
                        status_text.text(f"⏳ Zbyt wiele żądań - czekam {wait_time:.1f}s...")
                        time.sleep(wait_time)
                    else:
                        st.warning(f"⚠️ Zbyt wiele żądań dla klatki {frame_number}. Pomijam.")
                        consecutive_errors += 1
                        break
                        
                elif "safety" in error_msg or "blocked" in error_msg:
                    st.warning(f"⚠️ Zawartość klatki {frame_number} została zablokowana przez filtry bezpieczeństwa")
                    break
                    
                else:
                    # Inny błąd - krótsze oczekiwanie
                    if retry < max_retries - 1:
                        wait_time = retry_delay * (2 ** retry) / 2
                        status_text.text(f"⏳ Błąd - ponawiam za {wait_time:.1f}s...")
                        time.sleep(wait_time)
                    else:
                        st.warning(f"Błąd podczas analizy klatki {frame_number}: {str(e)[:100]}")
                        consecutive_errors += 1
                        break
        
        # Jeśli zbyt wiele kolejnych błędów, przerwij
        if consecutive_errors >= max_consecutive_errors:
            st.error(f"❌ Zbyt wiele kolejnych błędów ({consecutive_errors}). Przerywam analizę.")
            break
        
        if not success:
            continue
        
        try:
            
            # Pobierz tekst odpowiedzi
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
            
            if extracted_text:
                # Podziel na linie i wyczyść
                lines = extracted_text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    # Pomiń puste linie
                    if not line:
                        continue
                    
                    # Usuń numery, kropki na początku linii (np. "1. ", "2. ")
                    line = re.sub(r'^\d+\.\s*', '', line)
                    # Usuń znaki specjalne na początku/końcu
                    line = line.strip('.,;:- ')
                    # Usuń markdown formatting jeśli występuje
                    line = re.sub(r'^\*\*|\*\*$', '', line)
                    line = re.sub(r'^`|`$', '', line)
                    
                    # Sprawdź czy to wygląda na adres (zawiera kod pocztowy lub ulicę z numerem)
                    if line and len(line) > 5:
                        # Normalizuj adres (małe litery dla porównania)
                        normalized = line.lower().strip()
                        
                        # Sprawdź unikalność (proste porównanie)
                        is_duplicate = False
                        for seen in seen_addresses:
                            # Sprawdź podobieństwo (jeśli >80% podobne, uznaj za duplikat)
                            similarity = calculate_text_similarity(normalized, seen)
                            if similarity > 0.8:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            unique_addresses.append({
                                'address': line,
                                'frame_number': frame_number,
                                'raw_response': extracted_text
                            })
                            seen_addresses.add(normalized)
                            
        except Exception as e:
            # Błąd podczas przetwarzania odpowiedzi (nie podczas wywołania API)
            st.warning(f"Błąd podczas przetwarzania odpowiedzi dla klatki {frame_number}: {str(e)[:100]}")
            continue
        
        progress_bar.progress((idx + 1) / len(frames_to_process))
    
    progress_bar.empty()
    status_text.empty()
    
    return unique_addresses


def calculate_text_similarity(text1, text2):
    """
    Oblicza podobieństwo między dwoma tekstami (0-1, gdzie 1 to identyczne).
    
    Args:
        text1: Pierwszy tekst
        text2: Drugi tekst
        
    Returns:
        Wartość podobieństwa (0-1)
    """
    if not text1 or not text2:
        return 0.0
    
    # Prosta metoda - porównanie słów
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0


def geocode_address(address, max_retries=3):
    """
    Geokoduje adres na współrzędne geograficzne.
    Dodaje sufiks ", Warszawa, Polska" dla zwiększenia precyzji.
    
    Args:
        address: Adres do geokodowania
        max_retries: Maksymalna liczba prób
        
    Returns:
        Tuple (latitude, longitude) lub None
    """
    if not address:
        return None
    
    # Dodaj sufiks dla precyzji geokodowania
    full_address = f"{address}, Warszawa, Polska"
    
    for attempt in range(max_retries):
        try:
            location = geolocator.geocode(full_address, timeout=10, country_codes='pl')
            if location:
                return (location.latitude, location.longitude)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # Czekaj przed ponowną próbą
            else:
                st.warning(f"Nie udało się geokodować adresu: {address}")
        except Exception as e:
            st.warning(f"Błąd geokodowania: {str(e)}")
            break
    
    return None


def process_addresses_to_map_data(address_list):
    """
    Geokoduje listę adresów na dane mapy.
    
    Args:
        address_list: Lista adresów tekstowych
        
    Returns:
        Lista słowników z danymi dostaw: [{'address': str, 'coordinates': (lat, lon), 'frame_number': int}, ...]
    """
    delivery_points = []
    
    if not address_list:
        return delivery_points
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, address_data in enumerate(address_list):
        address = address_data['address']
        frame_number = address_data['frame_number']
        
        status_text.text(f"Geokodowanie adresu {idx + 1}/{len(address_list)}: {address}")
        
        # Geokoduj adres
        coordinates = geocode_address(address)
        
        if coordinates:
            delivery_points.append({
                'address': address,
                'coordinates': coordinates,
                'frame_number': frame_number,
                'raw_response': address_data.get('raw_response', '')
            })
        else:
            # Dodaj adres nawet bez geokodowania (dla wyświetlenia)
            delivery_points.append({
                'address': address,
                'coordinates': None,
                'frame_number': frame_number,
                'raw_response': address_data.get('raw_response', '')
            })
            st.warning(f"⚠️ Nie udało się geokodować: {address}")
        
        progress_bar.progress((idx + 1) / len(address_list))
    
    progress_bar.empty()
    status_text.empty()
    
    return delivery_points


def create_delivery_map(delivery_points):
    """
    Tworzy interaktywną mapę Folium z punktami dostaw.
    
    Args:
        delivery_points: Lista punktów dostaw z współrzędnymi (może zawierać None dla coordinates)
        
    Returns:
        Ścieżka do zapisanego pliku HTML z mapą lub None
    """
    # Filtruj tylko punkty z geokodowaniem
    geocoded_points = [p for p in delivery_points if p.get('coordinates') is not None]
    
    if not geocoded_points:
        st.warning("⚠️ Brak punktów z geokodowaniem do wyświetlenia na mapie!")
        return None
    
    # Wyznacz centrum mapy (pierwszy punkt)
    center_lat, center_lon = geocoded_points[0]['coordinates']
    
    # Utwórz mapę
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Dodaj punkty dostaw
    for idx, point in enumerate(geocoded_points, 1):
        lat, lon = point['coordinates']
        address = point['address']
        
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
        
        # Dodaj marker
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"<b>Punkt {idx}</b><br>{address}",
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
    st.title("🧭 GoodSpeed Route Analyzer")
    st.markdown("---")
    st.markdown("""
    **Aplikacja do analizy tras dostaw z wideo z wykorzystaniem Gemini Vision AI**
    
    Prześlij plik wideo zawierający adresy dostaw. Aplikacja automatycznie:
    1. Przetworzy wideo i wyodrębni klatki
    2. Wykorzysta Gemini AI do ekstrakcji adresów
    3. Geokoduje adresy
    4. Wygeneruje interaktywną mapę z trasą dostaw
    """)
    
    # Sprawdź dostępność Gemini API
    if model is None:
        st.error("""
        ❌ **Błąd: Gemini API nie jest dostępne!**
        
        Upewnij się, że:
        - Klucz API jest poprawnie skonfigurowany
        - Masz dostęp do internetu
        - Biblioteka google-generativeai jest zainstalowana
        """)
        return
    
    # Upload pliku wideo
    st.subheader("📹 Przesyłanie wideo")
    uploaded_file = st.file_uploader(
        "Wybierz plik wideo (.mp4, .mov)",
        type=['mp4', 'mov'],
        help="Obsługiwane formaty: MP4, MOV"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ Załadowano plik: {uploaded_file.name}")
        st.info(f"Rozmiar pliku: {uploaded_file.size / (1024*1024):.2f} MB")
    
    # Opcje
    st.markdown("---")
    st.subheader("⚙️ Opcje")
    show_debug = st.checkbox("🔍 Tryb debugowania (pokaż klatki)", value=False)
    show_raw_response = st.checkbox("📄 Pokaż surowe odpowiedzi Gemini AI", value=False)
    
    # Opcje API Gemini
    with st.expander("⚙️ Zaawansowane ustawienia API"):
        st.info("""
        **Wskazówki dotyczące limitów API:**
        - Jeśli otrzymujesz błędy "Przekroczono limit API", zwiększ opóźnienie między wywołaniami
        - Ograniczenie liczby klatek pomaga uniknąć przekroczenia limitów
        - Domyślne opóźnienie 1s jest bezpieczne dla większości przypadków
        - W przypadku wielu błędów, zwiększ opóźnienie do 2-3 sekund
        """)
        max_frames_input = st.number_input(
            "Maksymalna liczba klatek do analizy (0 = wszystkie)",
            min_value=0,
            max_value=500,
            value=0,
            help="Ogranicza liczbę klatek analizowanych przez Gemini AI. Pomaga uniknąć limitów API."
        )
        delay_input = st.slider(
            "Opóźnienie między wywołaniami API (sekundy)",
            min_value=0.5,
            max_value=5.0,
            value=1.5,
            step=0.1,
            help="Większe opóźnienie zmniejsza ryzyko przekroczenia limitów API, ale wydłuża czas analizy. Zalecane: 1.5-2.0s"
        )
        max_frames = None if max_frames_input == 0 else max_frames_input
    
    # Przycisk analizy
    st.markdown("---")
    if st.button("🚀 Analizuj Wideo i Generuj Mapę", type="primary", use_container_width=True):
        
        if uploaded_file is None:
            st.error("❌ Proszę najpierw przesłać plik wideo!")
            return
        
        with st.spinner("🔄 Przetwarzanie wideo..."):
            # Krok 1: Analiza klatek wideo
            st.subheader("📊 Krok 1: Ekstrakcja klatek z wideo")
            unique_frames = analyze_video_frames(uploaded_file)
            
            if not unique_frames:
                st.error("❌ Nie udało się wyodrębnić żadnych klatek z wideo!")
                return
            
            st.success(f"✅ Wyodrębniono {len(unique_frames)} klatek do analizy")
            
            # Tryb debugowania - pokaż klatki
            if show_debug and unique_frames:
                st.subheader("🔍 Debug: Wyodrębnione klatki")
                debug_cols = st.columns(min(3, len(unique_frames)))
                
                for idx, frame_data in enumerate(unique_frames[:9]):  # Maksymalnie 9 klatek
                    col_idx = idx % 3
                    with debug_cols[col_idx]:
                        frame = frame_data['frame']
                        frame_number = frame_data['frame_number']
                        st.image(frame, caption=f"Klatka {frame_number}", use_container_width=True)
            
            # Krok 2: Ekstrakcja adresów przez Gemini AI
            st.subheader("🤖 Krok 2: Ekstrakcja adresów przez Gemini Vision AI")
            if max_frames:
                st.info(f"ℹ️ Analizuję maksymalnie {max_frames} klatek z {len(unique_frames)} dostępnych")
            st.info(f"⏱️ Opóźnienie między wywołaniami: {delay_input}s")
            all_addresses = extract_addresses_with_ai(unique_frames, max_frames=max_frames, delay_between_calls=delay_input)
            
            if not all_addresses:
                st.error("❌ Nie udało się wyodrębnić żadnych adresów z klatek!")
                st.warning("""
                **Możliwe przyczyny:**
                - Adresy nie są wyraźnie widoczne w wideo
                - Niska jakość wideo
                - Adresy nie są w formacie polskim (kod pocztowy + ulica + numer)
                
                **Wskazówki:**
                - Włącz tryb debugowania, aby zobaczyć klatki
                - Upewnij się, że adresy są wyraźnie widoczne
                - Spróbuj nagrać wideo w wyższej rozdzielczości
                """)
                return
            
            # Wyświetl listę adresów tekstowych na początku
            st.success(f"✅ Znaleziono {len(all_addresses)} unikalnych adresów")
            st.subheader(f"📋 Lista znalezionych adresów ({len(all_addresses)} adresów)")
            
            # Wyświetl adresy w czytelnej formie
            for idx, addr_data in enumerate(all_addresses, 1):
                st.write(f"**{idx}.** {addr_data['address']}")
                if show_raw_response and addr_data.get('raw_response'):
                    with st.expander(f"Odpowiedź Gemini dla adresu {idx}"):
                        st.text(addr_data['raw_response'])
            
            st.markdown("---")
            
            # Krok 3: Geokodowanie adresów
            st.subheader("📍 Krok 3: Geokodowanie adresów")
            delivery_points = process_addresses_to_map_data(all_addresses)
            
            if not delivery_points:
                st.error("❌ Brak punktów dostaw!")
                return
            
            # Podsumowanie geokodowania
            geocoded_count = sum(1 for p in delivery_points if p.get('coordinates') is not None)
            not_geocoded_count = len(delivery_points) - geocoded_count
            
            if geocoded_count > 0:
                st.success(f"✅ Pomyślnie geokodowano {geocoded_count} z {len(delivery_points)} adresów")
            else:
                st.warning(f"⚠️ Nie udało się geokodować żadnego adresu ({len(delivery_points)} adresów tekstowych znalezionych)")
            
            if not_geocoded_count > 0:
                st.info(f"ℹ️ {not_geocoded_count} adresów nie zostało geokodowanych (będą widoczne na liście, ale nie na mapie)")
            
            # Wyświetl szczegółową listę adresów
            st.subheader("📋 Szczegółowa lista adresów (w kolejności dostaw)")
            for idx, point in enumerate(delivery_points, 1):
                coordinates_status = f"✅ {point['coordinates']}" if point.get('coordinates') else "❌ Brak geokodowania"
                with st.expander(f"Punkt {idx}: {point['address']}"):
                    st.write(f"**Współrzędne:** {coordinates_status}")
                    st.write(f"**Klatka wideo:** {point['frame_number']}")
                    if show_raw_response and point.get('raw_response'):
                        st.text_area("Odpowiedź Gemini AI:", point['raw_response'], height=100, disabled=True, key=f"raw_response_{idx}")
            
            # Krok 4: Generowanie mapy
            st.subheader("🗺️ Krok 4: Generowanie mapy")
            map_file = create_delivery_map(delivery_points)
            
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
