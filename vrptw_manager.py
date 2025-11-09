"""
Modułowa aplikacja do interaktywnego zarządzania i optymalizacji tras dostaw
Vehicle Routing Problem with Time Windows (VRPTW)
Z wykorzystaniem realnych czasów przejazdu i biblioteki folium do wizualizacji
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import folium
from folium import plugins
import random
from datetime import datetime, timedelta


def time_to_minutes(time_str: str) -> int:
    """
    Konwertuje czas w formacie 'HH:MM' na minuty od północy.
    
    Args:
        time_str: Czas w formacie 'HH:MM' (np. '15:00')
        
    Returns:
        Liczba minut od północy
    """
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    except (ValueError, AttributeError):
        raise ValueError(f"Nieprawidłowy format czasu: {time_str}. Oczekiwany format: 'HH:MM'")


def minutes_to_time(minutes: int) -> str:
    """
    Konwertuje minuty od północy na format 'HH:MM'.
    
    Args:
        minutes: Liczba minut od północy
        
    Returns:
        Czas w formacie 'HH:MM'
    """
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


@dataclass
class Order:
    """
    Klasa reprezentująca pojedynczy punkt dostawy.
    
    Attributes:
        id: Unikalny identyfikator zamówienia
        address: Adres dostawy (string)
        latitude: Szerokość geograficzna (float)
        longitude: Długość geograficzna (float)
        time_window_end: Limit czasowy w formacie 'HH:MM' (opcjonalny, kluczowy limit)
        is_delivered: Czy zamówienie zostało dostarczone (domyślnie False)
    """
    id: int
    address: str
    latitude: float
    longitude: float
    time_window_end: Optional[str] = None
    is_delivered: bool = False
    
    def __post_init__(self):
        """Walidacja danych po inicjalizacji."""
        if self.time_window_end:
            # Konwertuj na minuty dla łatwiejszego porównywania
            self._end_minutes = time_to_minutes(self.time_window_end)
        else:
            self._end_minutes = None
    
    def has_time_window(self) -> bool:
        """Sprawdza, czy zamówienie ma zdefiniowany limit czasowy."""
        return self.time_window_end is not None
    
    def can_be_visited_before(self, arrival_minutes: int) -> bool:
        """
        Sprawdza, czy zamówienie może być odwiedzone przed limitem czasowym.
        
        Args:
            arrival_minutes: Czas przybycia w minutach od północy
            
        Returns:
            True, jeśli czas mieści się przed limitem
        """
        if not self.has_time_window():
            return True
        
        return arrival_minutes <= self._end_minutes
    
    def __repr__(self):
        """Reprezentacja tekstowa zamówienia."""
        status = "✅ DOSTARCZONE" if self.is_delivered else "⏳ OCZEKUJĄCE"
        time_info = f" | Limit: {self.time_window_end}" if self.time_window_end else ""
        return f"Order(id={self.id}, address='{self.address[:30]}...', {status}{time_info})"
    
    @staticmethod
    def generate_sample_orders(count: int = 8) -> List['Order']:
        """
        Generuje przykładowe zamówienia do celów testowych.
        Minimum 6 punktów, w tym 2 z pilnym time_window_end (np. '15:00').
        
        Args:
            count: Liczba zamówień do wygenerowania
            
        Returns:
            Lista obiektów Order
        """
        # Fikcyjne współrzędne w okolicy Warszawy (blisko siebie)
        base_lat = 52.2297
        base_lon = 21.0122
        
        sample_orders = []
        
        # Przykładowe adresy
        addresses = [
            "UL. MARSZAŁKOWSKA 1, Warszawa",
            "UL. NOWY ŚWIAT 15, Warszawa",
            "PL. ZAMKOWY 1, Warszawa",
            "UL. KRAKOWSKIE PRZEDMIEŚCIE 26/28, Warszawa",
            "UL. CHMIELNA 73, Warszawa",
            "UL. ŚWIĘTOKRZYSKA 31, Warszawa",
            "UL. JANA PAWŁA II 27, Warszawa",
            "UL. PIĘKNA 20, Warszawa"
        ]
        
        # Przykładowe limity czasowe (2 pilne z '15:00', reszta opcjonalna)
        time_windows = [
            "15:00",  # Pilne
            "15:00",  # Pilne
            "17:00",
            None,
            "18:00",
            None,
            "16:00",
            None
        ]
        
        for i in range(min(count, len(addresses))):
            # Dodaj małe przesunięcie do współrzędnych (punkty blisko siebie)
            lat = base_lat + random.uniform(-0.03, 0.03)
            lon = base_lon + random.uniform(-0.03, 0.03)
            
            tw_end = time_windows[i % len(time_windows)]
            
            order = Order(
                id=i + 1,
                address=addresses[i % len(addresses)],
                latitude=lat,
                longitude=lon,
                time_window_end=tw_end,
                is_delivered=False
            )
            sample_orders.append(order)
        
        return sample_orders


class GoogleMapsIntegration:
    """
    Klasa symulująca integrację z Google Distance Matrix API.
    Generuje realistyczne czasy przejazdu między punktami.
    """
    
    def __init__(self, base_time_min: int = 5, base_time_max: int = 30):
        """
        Inicjalizuje symulator Google Maps API.
        
        Args:
            base_time_min: Minimalny czas przejazdu w minutach
            base_time_max: Maksymalny czas przejazdu w minutach
        """
        self.base_time_min = base_time_min
        self.base_time_max = base_time_max
    
    def _calculate_base_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Oblicza przybliżoną odległość między punktami (uproszczona metryka).
        
        Args:
            lat1, lon1: Współrzędne pierwszego punktu
            lat2, lon2: Współrzędne drugiego punktu
            
        Returns:
            Przybliżona odległość
        """
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5
    
    def get_distance_matrix(self, orders: List[Order]) -> np.ndarray:
        """
        Symuluje zapytanie do Google Distance Matrix API.
        Zwraca macierz czasów przejazdu w minutach (int) między każdym punktem.
        Macierz jest asymetryczna (czasy mogą się różnić w zależności od kierunku).
        
        Args:
            orders: Lista zamówień
            
        Returns:
            Macierz czasów przejazdu w minutach (numpy array, shape: (n, n))
        """
        n = len(orders)
        matrix = np.zeros((n, n), dtype=int)
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 0
                else:
                    # Oblicz bazową odległość
                    base_dist = self._calculate_base_distance(
                        orders[i].latitude, orders[i].longitude,
                        orders[j].latitude, orders[j].longitude
                    )
                    
                    # Generuj realistyczny czas przejazdu (5-30 minut)
                    # Czas zależy od odległości + losowa zmienność + asymetria
                    base_time = int(base_dist * 1000)  # Skalowanie
                    base_time = max(self.base_time_min, min(self.base_time_max, base_time))
                    
                    # Dodaj losową zmienność
                    time_variation = random.randint(-3, 3)
                    travel_time = max(1, base_time + time_variation)
                    
                    # Asymetria: czas powrotu może być inny (np. korki, jednokierunkowe)
                    if j < i:  # Powrót - może być dłuższy
                        travel_time += random.randint(0, 5)
                    
                    matrix[i][j] = travel_time
        
        return matrix


class RouteOptimizer:
    """
    Klasa optymalizująca trasę z uwzględnieniem Time Windows (VRPTW).
    Priorytetem jest przestrzeganie limitów czasowych.
    """
    
    def __init__(self, start_time_minutes: int = 480):  # 08:00
        """
        Inicjalizuje RouteOptimizer.
        
        Args:
            start_time_minutes: Czas rozpoczęcia trasy w minutach od północy (domyślnie 08:00)
        """
        self.start_time_minutes = start_time_minutes
    
    def optimize_route(self, orders: List[Order], travel_time_matrix: np.ndarray) -> List[Order]:
        """
        Optymalizuje trasę z uwzględnieniem Time Windows.
        Minimalizuje całkowity czas podróży, ale priorytetem jest przestrzeganie limitów czasowych.
        
        Args:
            orders: Lista zamówień do optymalizacji
            travel_time_matrix: Macierz czasów przejazdu w minutach
            
        Returns:
            Zoptymalizowana lista zamówień w kolejności trasy
        """
        if not orders:
            return []
        
        if len(orders) == 1:
            return orders.copy()
        
        # Filtruj tylko niedostarczone zamówienia
        undelivered = [o for o in orders if not o.is_delivered]
        if not undelivered:
            return orders.copy()
        
        # Indeksy zamówień w oryginalnej liście
        order_indices = {o.id: i for i, o in enumerate(orders)}
        undelivered_indices = [order_indices[o.id] for o in undelivered]
        
        # Utwórz podmacierz dla niedostarczonych zamówień
        n_undelivered = len(undelivered)
        if n_undelivered == 1:
            return orders.copy()
        
        # Algorytm: Nearest Neighbor z priorytetem dla Time Windows
        optimized_route = []
        remaining_orders = undelivered.copy()
        remaining_indices = undelivered_indices.copy()
        current_time = self.start_time_minutes
        
        # Zacznij od zamówienia z najwcześniejszym limitem czasowym (jeśli są)
        orders_with_windows = [o for o in remaining_orders if o.has_time_window()]
        if orders_with_windows:
            first_order = min(orders_with_windows, key=lambda o: o._end_minutes)
        else:
            first_order = remaining_orders[0]
        
        first_idx = remaining_orders.index(first_order)
        optimized_route.append(first_order)
        remaining_orders.pop(first_idx)
        remaining_indices.pop(first_idx)
        
        current_idx = order_indices[first_order.id]
        
        # Znajdź kolejne punkty
        while remaining_orders:
            best_order = None
            best_score = float('inf')
            best_order_idx = -1
            best_remaining_idx = -1
            
            for idx, candidate in enumerate(remaining_orders):
                candidate_original_idx = remaining_indices[idx]
                
                # Czas przejazdu z obecnego punktu do kandydata
                travel_time = travel_time_matrix[current_idx][candidate_original_idx]
                arrival_time = current_time + travel_time
                
                # Oblicz "score" - kombinacja czasu i kary za naruszenie Time Window
                score = travel_time
                
                if candidate.has_time_window():
                    # Jeśli przybywamy za późno, duża kara
                    if arrival_time > candidate._end_minutes:
                        penalty = (arrival_time - candidate._end_minutes) * 100  # Bardzo duża kara
                        score += penalty
                    # Jeśli przybywamy w ostatniej chwili, mała kara (priorytet)
                    elif arrival_time > candidate._end_minutes - 30:  # W ciągu 30 minut przed limitem
                        score -= 5  # Bonus za pilność
                
                if score < best_score:
                    best_score = score
                    best_order = candidate
                    best_order_idx = candidate_original_idx
                    best_remaining_idx = idx
            
            if best_order:
                optimized_route.append(best_order)
                remaining_orders.pop(best_remaining_idx)
                remaining_indices.pop(best_remaining_idx)
                
                current_time += travel_time_matrix[current_idx][best_order_idx]
                current_idx = best_order_idx
        
        # Wstaw dostarczone zamówienia na końcu (dla kompletności)
        delivered_orders = [o for o in orders if o.is_delivered]
        optimized_route.extend(delivered_orders)
        
        return optimized_route


class RouteManager:
    """
    Klasa zarządzająca trasą dostaw (listą zamówień).
    """
    
    def __init__(self, orders: Optional[List[Order]] = None):
        """
        Inicjalizuje RouteManager.
        
        Args:
            orders: Opcjonalna lista zamówień do załadowania
        """
        self.orders: List[Order] = orders.copy() if orders else []
        self.optimizer: Optional[RouteOptimizer] = None
        self.travel_time_matrix: Optional[np.ndarray] = None
    
    def load_orders(self, data: List[Order]) -> None:
        """
        Wczytuje listę zamówień.
        
        Args:
            data: Lista obiektów Order
        """
        self.orders = data.copy()
    
    def display_route(self) -> None:
        """Wyświetla bieżącą kolejność dostaw."""
        if not self.orders:
            print("Trasa jest pusta.")
            return
        
        print("\n" + "="*90)
        print("AKTUALNA TRASA DOSTAW")
        print("="*90)
        for idx, order in enumerate(self.orders, 1):
            status = "✅ DOSTARCZONE" if order.is_delivered else "⏳ OCZEKUJĄCE"
            time_info = f" | Limit czasowy: {order.time_window_end} ⚠️ PILNE" if order.time_window_end else ""
            print(f"{idx:2d}. [{order.id:2d}] {order.address[:50]:<50} | "
                  f"GPS: ({order.latitude:.4f}, {order.longitude:.4f}) | {status}{time_info}")
        print("="*90 + "\n")
    
    def move_order(self, order_id: int, new_index: int) -> bool:
        """
        Przenosi zamówienie o podanym ID na nową pozycję w liście.
        
        Args:
            order_id: ID zamówienia do przeniesienia
            new_index: Nowa pozycja (0-based index)
            
        Returns:
            True, jeśli operacja się powiodła, False w przeciwnym razie
        """
        # Znajdź zamówienie po ID
        order_to_move = None
        current_index = -1
        
        for idx, order in enumerate(self.orders):
            if order.id == order_id:
                order_to_move = order
                current_index = idx
                break
        
        if order_to_move is None:
            print(f"❌ Nie znaleziono zamówienia o ID: {order_id}")
            return False
        
        if new_index < 0 or new_index >= len(self.orders):
            print(f"❌ Nieprawidłowy indeks: {new_index}. Dozwolony zakres: 0-{len(self.orders)-1}")
            return False
        
        if current_index == new_index:
            print(f"ℹ️ Zamówienie {order_id} jest już na pozycji {new_index}")
            return True
        
        # Usuń zamówienie z obecnej pozycji
        self.orders.pop(current_index)
        
        # Wstaw na nową pozycję
        self.orders.insert(new_index, order_to_move)
        
        print(f"✅ Zamówienie {order_id} przeniesione z pozycji {current_index} na pozycję {new_index}")
        return True
    
    def mark_order_as_delivered(self, order_id: int) -> bool:
        """
        Oznacza zamówienie jako dostarczone.
        
        Args:
            order_id: ID zamówienia do oznaczenia jako dostarczone
            
        Returns:
            True, jeśli operacja się powiodła, False w przeciwnym razie
        """
        for order in self.orders:
            if order.id == order_id:
                if order.is_delivered:
                    print(f"ℹ️ Zamówienie {order_id} jest już oznaczone jako dostarczone")
                    return True
                
                order.is_delivered = True
                print(f"✅ Zamówienie {order_id} oznaczone jako dostarczone")
                return True
        
        print(f"❌ Nie znaleziono zamówienia o ID: {order_id}")
        return False
    
    def re_optimize(self, travel_time_matrix: np.ndarray, start_time_minutes: int = 480) -> None:
        """
        Ponownie uruchamia optymalizator po ręcznej zmianie lub dostarczeniu zamówienia.
        
        Args:
            travel_time_matrix: Macierz czasów przejazdu
            start_time_minutes: Czas rozpoczęcia trasy w minutach od północy
        """
        if not self.optimizer:
            self.optimizer = RouteOptimizer(start_time_minutes=start_time_minutes)
        
        self.travel_time_matrix = travel_time_matrix
        optimized_route = self.optimizer.optimize_route(self.orders, travel_time_matrix)
        self.orders = optimized_route
        print("🔄 Trasa została ponownie zoptymalizowana")
    
    def get_orders(self) -> List[Order]:
        """Zwraca listę zamówień."""
        return self.orders.copy()


def create_route_map(orders: List[Order], filename: str = "route_map.html") -> None:
    """
    Tworzy interaktywną mapę trasy używając folium.
    
    Args:
        orders: Lista zamówień w zoptymalizowanej kolejności
        filename: Nazwa pliku wyjściowego HTML
    """
    if not orders:
        print("❌ Brak zamówień do wizualizacji")
        return
    
    # Oblicz centrum mapy
    avg_lat = sum(o.latitude for o in orders) / len(orders)
    avg_lon = sum(o.longitude for o in orders) / len(orders)
    
    # Inicjalizuj mapę
    route_map = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Lista współrzędnych dla PolyLine
    coordinates = []
    
    # Dodaj markery dla każdego zamówienia
    for idx, order in enumerate(orders, 1):
        # Określ kolor markera
        if order.is_delivered:
            color = 'green'
            icon = 'check-circle'
            status_text = "✅ DOSTARCZONE"
        elif order.time_window_end:
            color = 'red'
            icon = 'exclamation-circle'
            status_text = f"⚠️ PILNE (Limit: {order.time_window_end})"
        else:
            color = 'blue'
            icon = 'info-circle'
            status_text = "⏳ OCZEKUJĄCE"
        
        # Utwórz popup z informacjami
        popup_text = f"""
        <b>Zamówienie #{order.id}</b><br>
        <b>Adres:</b> {order.address}<br>
        <b>Status:</b> {status_text}<br>
        <b>Pozycja w trasie:</b> {idx}/{len(orders)}<br>
        <b>Współrzędne:</b> ({order.latitude:.6f}, {order.longitude:.6f})
        """
        
        if order.time_window_end:
            popup_text += f"<br><b>Limit czasowy:</b> {order.time_window_end}"
        
        # Dodaj marker
        folium.Marker(
            location=[order.latitude, order.longitude],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"Zamówienie #{order.id}: {order.address[:30]}...",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(route_map)
        
        coordinates.append([order.latitude, order.longitude])
    
    # Narysuj linię łączącą wszystkie punkty
    folium.PolyLine(
        locations=coordinates,
        color='blue',
        weight=3,
        opacity=0.7,
        popup=f"Trasa: {len(orders)} punktów"
    ).add_to(route_map)
    
    # Dodaj legendę
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4>Legenda</h4>
    <p><i class="fa fa-check-circle" style="color:green"></i> Dostarczone</p>
    <p><i class="fa fa-exclamation-circle" style="color:red"></i> Pilne (Limit czasowy)</p>
    <p><i class="fa fa-info-circle" style="color:blue"></i> Oczekujące</p>
    </div>
    '''
    route_map.get_root().html.add_child(folium.Element(legend_html))
    
    # Zapisz mapę
    route_map.save(filename)
    print(f"🗺️  Mapa zapisana do pliku: {filename}")


def main():
    """
    Główna funkcja demonstracyjna - pełna symulacja użycia aplikacji VRPTW.
    """
    print("="*90)
    print("SYMULACJA ZARZĄDZANIA TRASAMI VRPTW (Vehicle Routing Problem with Time Windows)")
    print("="*90)
    
    # 1. Generuj przykładowe dane
    print("\n📦 Krok 1: Generowanie przykładowych zamówień...")
    sample_orders = Order.generate_sample_orders(8)
    print(f"✅ Wygenerowano {len(sample_orders)} zamówień")
    print(f"   - Zamówienia z limitem czasowym: {sum(1 for o in sample_orders if o.has_time_window())}")
    print(f"   - Pilne zamówienia (limit 15:00): {sum(1 for o in sample_orders if o.time_window_end == '15:00')}")
    
    # 2. Utwórz RouteManager i wczytaj zamówienia
    print("\n📋 Krok 2: Tworzenie RouteManager i wczytywanie zamówień...")
    route_manager = RouteManager()
    route_manager.load_orders(sample_orders)
    
    # 3. Generuj macierz czasów przejazdu
    print("\n🚗 Krok 3: Generowanie macierzy czasów przejazdu (symulacja Google Maps API)...")
    google_maps = GoogleMapsIntegration(base_time_min=5, base_time_max=30)
    travel_time_matrix = google_maps.get_distance_matrix(sample_orders)
    print(f"✅ Wygenerowano macierz {travel_time_matrix.shape[0]}x{travel_time_matrix.shape[1]}")
    print(f"   Przykładowe czasy przejazdu: {travel_time_matrix[0][1]} min, {travel_time_matrix[1][0]} min (asymetryczne)")
    
    # 4. Optymalizuj i wyświetl trasę początkową
    print("\n⚙️  Krok 4: Optymalizacja trasy początkowej...")
    route_manager.re_optimize(travel_time_matrix, start_time_minutes=480)  # 08:00
    route_manager.display_route()
    
    # 5. Wygeneruj mapę początkową
    print("\n🗺️  Krok 5: Generowanie mapy początkowej...")
    create_route_map(route_manager.get_orders(), "route_map_initial.html")
    
    # 6. Zasymuluj ręczne przestawienie zamówienia
    print("\n🔄 Krok 6: Ręczne przestawienie zamówienia...")
    # Przenieś zamówienie o ID 3 na pozycję 0 (początek trasy)
    route_manager.move_order(order_id=3, new_index=0)
    route_manager.display_route()
    
    # 7. Ponownie zoptymalizuj i wygeneruj nową mapę
    print("\n⚙️  Krok 7: Ponowna optymalizacja po ręcznej zmianie...")
    route_manager.re_optimize(travel_time_matrix, start_time_minutes=480)
    route_manager.display_route()
    create_route_map(route_manager.get_orders(), "route_map_after_reorder.html")
    
    # 8. Zasymuluj dostarczenie 2 zamówień
    print("\n✅ Krok 8: Symulacja dostarczenia zamówień...")
    # Oznacz pierwsze 2 zamówienia jako dostarczone
    first_two_ids = [route_manager.get_orders()[0].id, route_manager.get_orders()[1].id]
    for order_id in first_two_ids:
        route_manager.mark_order_as_delivered(order_id)
    
    route_manager.display_route()
    
    # 9. Ponownie wygeneruj mapę, aby pokazać zmianę kolorów
    print("\n🗺️  Krok 9: Generowanie mapy po dostarczeniu zamówień...")
    create_route_map(route_manager.get_orders(), "route_map_final.html")
    
    # 10. Podsumowanie
    print("\n" + "="*90)
    print("PODSUMOWANIE")
    print("="*90)
    total_orders = len(route_manager.get_orders())
    delivered = sum(1 for o in route_manager.get_orders() if o.is_delivered)
    pending = total_orders - delivered
    urgent = sum(1 for o in route_manager.get_orders() if o.has_time_window() and not o.is_delivered)
    
    print(f"Liczba zamówień: {total_orders}")
    print(f"  - Dostarczone: {delivered} ✅")
    print(f"  - Oczekujące: {pending} ⏳")
    print(f"  - Pilne (z limitem czasowym): {urgent} ⚠️")
    print(f"\nWygenerowane mapy:")
    print(f"  - route_map_initial.html - Trasa początkowa")
    print(f"  - route_map_after_reorder.html - Po ręcznej zmianie i re-optymalizacji")
    print(f"  - route_map_final.html - Po dostarczeniu zamówień")
    print("="*90 + "\n")


if __name__ == "__main__":
    main()


