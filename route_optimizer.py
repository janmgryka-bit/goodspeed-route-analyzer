"""
Modułowa aplikacja do zarządzania trasami z obsługą Time Windows
Zawiera klasy: Order, RouteManager, RouteOptimizer
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from math import radians, sin, cos, sqrt, atan2
import random


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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


def time_to_seconds(time_str: str) -> int:
    """
    Konwertuje czas w formacie 'HH:MM' na sekundy od północy.
    
    Args:
        time_str: Czas w formacie 'HH:MM' (np. '09:30')
        
    Returns:
        Liczba sekund od północy
    """
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 3600 + minutes * 60
    except (ValueError, AttributeError):
        raise ValueError(f"Nieprawidłowy format czasu: {time_str}. Oczekiwany format: 'HH:MM'")


def seconds_to_time(seconds: int) -> str:
    """
    Konwertuje sekundy od północy na format 'HH:MM'.
    
    Args:
        seconds: Liczba sekund od północy
        
    Returns:
        Czas w formacie 'HH:MM'
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


@dataclass
class Order:
    """
    Klasa reprezentująca pojedynczy punkt dostawy.
    
    Attributes:
        id: Unikalny identyfikator zamówienia
        address: Adres dostawy (string)
        latitude: Szerokość geograficzna (float)
        longitude: Długość geograficzna (float)
        time_window_start: Opcjonalny czas rozpoczęcia okna czasowego (format 'HH:MM' lub sekundy)
        time_window_end: Opcjonalny czas zakończenia okna czasowego (wymagany, jeśli start jest podany)
    """
    id: int
    address: str
    latitude: float
    longitude: float
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    
    def __post_init__(self):
        """Walidacja danych po inicjalizacji."""
        if self.time_window_start and not self.time_window_end:
            raise ValueError("Jeśli podano time_window_start, należy również podać time_window_end")
        
        if self.time_window_start and self.time_window_end:
            # Konwertuj na sekundy dla łatwiejszego porównywania
            self._start_seconds = time_to_seconds(self.time_window_start)
            self._end_seconds = time_to_seconds(self.time_window_end)
            
            if self._start_seconds >= self._end_seconds:
                raise ValueError("time_window_start musi być wcześniejszy niż time_window_end")
        else:
            self._start_seconds = None
            self._end_seconds = None
    
    def has_time_window(self) -> bool:
        """Sprawdza, czy zamówienie ma zdefiniowane okno czasowe."""
        return self.time_window_start is not None
    
    def can_be_visited_at(self, arrival_time_seconds: int) -> bool:
        """
        Sprawdza, czy zamówienie może być odwiedzone o podanym czasie.
        
        Args:
            arrival_time_seconds: Czas przybycia w sekundach od północy
            
        Returns:
            True, jeśli czas mieści się w oknie czasowym
        """
        if not self.has_time_window():
            return True
        
        return self._start_seconds <= arrival_time_seconds <= self._end_seconds
    
    def __repr__(self):
        """Reprezentacja tekstowa zamówienia."""
        time_info = ""
        if self.has_time_window():
            time_info = f" [{self.time_window_start}-{self.time_window_end}]"
        return f"Order(id={self.id}, address='{self.address[:30]}...', lat={self.latitude:.4f}, lon={self.longitude:.4f}{time_info})"
    
    @staticmethod
    def generate_sample_orders(count: int = 7) -> List['Order']:
        """
        Generuje przykładowe zamówienia do celów testowych.
        
        Args:
            count: Liczba zamówień do wygenerowania
            
        Returns:
            Lista obiektów Order
        """
        # Fikcyjne współrzędne w okolicy Warszawy
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
            "UL. JANA PAWŁA II 27, Warszawa"
        ]
        
        # Przykładowe okna czasowe
        time_windows = [
            ("09:00", "12:00"),
            ("10:00", "13:00"),
            ("11:00", "14:00"),
            ("12:00", "15:00"),
            (None, None),  # Bez okna czasowego
            ("13:00", "16:00"),
            ("14:00", "17:00"),
        ]
        
        for i in range(min(count, len(addresses))):
            # Dodaj losowe przesunięcie do współrzędnych
            lat = base_lat + random.uniform(-0.05, 0.05)
            lon = base_lon + random.uniform(-0.05, 0.05)
            
            tw_start, tw_end = time_windows[i % len(time_windows)]
            
            order = Order(
                id=i + 1,
                address=addresses[i % len(addresses)],
                latitude=lat,
                longitude=lon,
                time_window_start=tw_start,
                time_window_end=tw_end
            )
            sample_orders.append(order)
        
        return sample_orders


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
        
        print("\n" + "="*80)
        print("AKTUALNA TRASA DOSTAW")
        print("="*80)
        for idx, order in enumerate(self.orders, 1):
            time_info = ""
            if order.has_time_window():
                time_info = f" | Okno czasowe: {order.time_window_start} - {order.time_window_end}"
            print(f"{idx:2d}. [{order.id:2d}] {order.address[:50]:<50} | "
                  f"GPS: ({order.latitude:.4f}, {order.longitude:.4f}){time_info}")
        print("="*80 + "\n")
    
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
    
    def get_orders(self) -> List[Order]:
        """Zwraca listę zamówień."""
        return self.orders.copy()
    
    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Znajduje zamówienie po ID."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None


class RouteOptimizer:
    """
    Klasa optymalizująca trasę z uwzględnieniem Time Windows.
    """
    
    def __init__(self, average_speed_kmh: float = 30.0):
        """
        Inicjalizuje RouteOptimizer.
        
        Args:
            average_speed_kmh: Średnia prędkość pojazdu w km/h (domyślnie 30 km/h)
        """
        self.average_speed_kmh = average_speed_kmh
        self.distance_matrix: Optional[List[List[float]]] = None
    
    def calculate_distance_matrix(self, orders: List[Order]) -> List[List[float]]:
        """
        Oblicza macierz odległości między wszystkimi punktami.
        
        Args:
            orders: Lista zamówień
            
        Returns:
            Macierz odległości (km) - distance_matrix[i][j] = odległość z i do j
        """
        n = len(orders)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = haversine_distance(
                        orders[i].latitude, orders[i].longitude,
                        orders[j].latitude, orders[j].longitude
                    )
        
        self.distance_matrix = matrix
        return matrix
    
    def calculate_travel_time(self, distance_km: float) -> int:
        """
        Oblicza czas podróży w sekundach na podstawie odległości.
        
        Args:
            distance_km: Odległość w kilometrach
            
        Returns:
            Czas podróży w sekundach
        """
        time_hours = distance_km / self.average_speed_kmh
        return int(time_hours * 3600)
    
    def check_time_windows(self, route: List[Order], start_time_seconds: int = 28800) -> Tuple[bool, List[int]]:
        """
        Sprawdza, czy trasa spełnia wszystkie okna czasowe.
        
        Args:
            route: Lista zamówień w kolejności trasy
            start_time_seconds: Czas rozpoczęcia trasy w sekundach od północy (domyślnie 08:00)
            
        Returns:
            Tuple (czy_wszystkie_okna_spełnione, lista_czasów_przybycia)
        """
        current_time = start_time_seconds
        arrival_times = []
        all_valid = True
        
        for i, order in enumerate(route):
            if i > 0:
                # Oblicz czas podróży z poprzedniego punktu
                prev_order = route[i - 1]
                distance = haversine_distance(
                    prev_order.latitude, prev_order.longitude,
                    order.latitude, order.longitude
                )
                travel_time = self.calculate_travel_time(distance)
                current_time += travel_time
            
            arrival_times.append(current_time)
            
            # Sprawdź okno czasowe
            if order.has_time_window():
                # Jeśli przybyliśmy za wcześnie, czekamy do początku okna
                if current_time < order._start_seconds:
                    current_time = order._start_seconds
                    arrival_times[-1] = current_time
                
                # Sprawdź, czy możemy odwiedzić po ewentualnym oczekiwaniu
                if not order.can_be_visited_at(current_time):
                    all_valid = False
                    # Jeśli za późno, nie możemy naprawić (ale zaznaczamy błąd)
        
        return all_valid, arrival_times
    
    def optimize_route(self, orders: List[Order], start_time_seconds: int = 28800) -> Tuple[List[Order], bool, List[int]]:
        """
        Optymalizuje trasę z uwzględnieniem Time Windows.
        Używa heurystyki Nearest Neighbor z modyfikacją dla Time Windows.
        
        Args:
            orders: Lista zamówień do optymalizacji
            start_time_seconds: Czas rozpoczęcia trasy w sekundach od północy (domyślnie 08:00)
            
        Returns:
            Tuple (zoptymalizowana_trasa, czy_wszystkie_okna_spełnione, lista_czasów_przybycia)
        """
        if not orders:
            return [], True, []
        
        if len(orders) == 1:
            return orders.copy(), True, [start_time_seconds]
        
        # Oblicz macierz odległości
        self.calculate_distance_matrix(orders)
        
        # Algorytm: Nearest Neighbor z modyfikacją dla Time Windows
        optimized_route = []
        remaining_orders = orders.copy()
        current_time = start_time_seconds
        
        # Zacznij od pierwszego zamówienia (lub tego z najwcześniejszym oknem czasowym)
        if remaining_orders:
            # Jeśli są zamówienia z oknami czasowymi, zacznij od tego z najwcześniejszym
            orders_with_windows = [o for o in remaining_orders if o.has_time_window()]
            if orders_with_windows:
                first_order = min(orders_with_windows, key=lambda o: o._start_seconds)
            else:
                first_order = remaining_orders[0]
            
            remaining_orders.remove(first_order)
            optimized_route.append(first_order)
            current_time = max(current_time, first_order._start_seconds if first_order.has_time_window() else current_time)
        
        # Znajdź kolejne punkty używając Nearest Neighbor z uwzględnieniem Time Windows
        while remaining_orders:
            best_order = None
            best_score = float('inf')
            best_index = -1
            
            current_order = optimized_route[-1]
            current_idx = orders.index(current_order)
            
            for idx, candidate in enumerate(remaining_orders):
                candidate_idx = orders.index(candidate)
                
                # Odległość do kandydata
                distance = self.distance_matrix[current_idx][candidate_idx]
                travel_time = self.calculate_travel_time(distance)
                arrival_time = current_time + travel_time
                
                # Oblicz "score" - kombinacja odległości i kary za naruszenie Time Window
                score = distance
                
                if candidate.has_time_window():
                    # Jeśli przybywamy za wcześnie, dodajmy małą karę (ale możemy czekać)
                    if arrival_time < candidate._start_seconds:
                        wait_time = candidate._start_seconds - arrival_time
                        score += wait_time / 3600.0  # Kara proporcjonalna do czasu oczekiwania
                    # Jeśli przybywamy za późno, duża kara
                    elif arrival_time > candidate._end_seconds:
                        penalty = (arrival_time - candidate._end_seconds) / 60.0  # Kary w minutach
                        score += penalty * 10  # Duża kara za naruszenie
                
                if score < best_score:
                    best_score = score
                    best_order = candidate
                    best_index = idx
            
            if best_order:
                remaining_orders.remove(best_order)
                optimized_route.append(best_order)
                
                # Aktualizuj czas przybycia
                candidate_idx = orders.index(best_order)
                distance = self.distance_matrix[current_idx][candidate_idx]
                travel_time = self.calculate_travel_time(distance)
                current_time += travel_time
                
                # Jeśli zamówienie ma okno czasowe i przybyliśmy za wcześnie, czekamy
                if best_order.has_time_window() and current_time < best_order._start_seconds:
                    current_time = best_order._start_seconds
        
        # Sprawdź, czy wszystkie Time Windows są spełnione
        all_valid, arrival_times = self.check_time_windows(optimized_route, start_time_seconds)
        
        return optimized_route, all_valid, arrival_times
    
    def fix_time_window_violations(self, route: List[Order], start_time_seconds: int = 28800) -> List[Order]:
        """
        Naprawia naruszenia Time Windows poprzez minimalne przestawienia.
        Używa zaawansowanej heurystyki z priorytetem dla zamówień z Time Windows.
        
        Args:
            route: Trasa do naprawienia
            start_time_seconds: Czas rozpoczęcia trasy
            
        Returns:
            Poprawiona trasa
        """
        # Sprawdź, które zamówienia naruszają Time Windows
        _, arrival_times = self.check_time_windows(route, start_time_seconds)
        violations = []
        
        for i, (order, arrival_time) in enumerate(zip(route, arrival_times)):
            if order.has_time_window() and not order.can_be_visited_at(arrival_time):
                violations.append((i, order, arrival_time))
        
        if not violations:
            return route.copy()
        
        # Sortuj naruszenia według wagi (jak bardzo naruszone)
        violations.sort(key=lambda x: x[2] - x[1]._end_seconds if x[2] > x[1]._end_seconds else 0, reverse=True)
        
        # Próbuj naprawić każde naruszenie
        fixed_route = route.copy()
        
        for violation_idx, violated_order, arrival_time in violations:
            # Znajdź najlepszą pozycję dla tego zamówienia
            best_position = violation_idx
            best_valid = False
            
            # Próbuj przenieść zamówienie wcześniej w trasie
            for new_pos in range(len(fixed_route)):
                if new_pos == violation_idx:
                    continue
                
                test_route = fixed_route.copy()
                test_route.remove(violated_order)
                test_route.insert(new_pos, violated_order)
                
                test_valid, _ = self.check_time_windows(test_route, start_time_seconds)
                
                if test_valid:
                    best_position = new_pos
                    best_valid = True
                    break
                elif not best_valid:
                    # Jeśli nie możemy naprawić, przynajmniej spróbujmy poprawić
                    # Sprawdź, czy nowa pozycja ma mniej naruszeń
                    test_violations = sum(1 for o, at in zip(test_route, self.check_time_windows(test_route, start_time_seconds)[1])
                                         if o.has_time_window() and not o.can_be_visited_at(at))
                    current_violations = sum(1 for o, at in zip(fixed_route, arrival_times)
                                           if o.has_time_window() and not o.can_be_visited_at(at))
                    
                    if test_violations < current_violations:
                        best_position = new_pos
            
            # Przenieś zamówienie na najlepszą pozycję
            if best_position != violation_idx:
                fixed_route.remove(violated_order)
                fixed_route.insert(best_position, violated_order)
                
                # Sprawdź ponownie
                fixed_valid, _ = self.check_time_windows(fixed_route, start_time_seconds)
                if fixed_valid:
                    return fixed_route
        
        # Jeśli nadal są naruszenia, użyj pełnej re-optymalizacji tylko dla zamówień z Time Windows
        orders_with_windows = [o for o in fixed_route if o.has_time_window()]
        orders_without_windows = [o for o in fixed_route if not o.has_time_window()]
        
        if orders_with_windows:
            # Optymalizuj tylko zamówienia z Time Windows
            optimized_with_windows, _, _ = self.optimize_route(orders_with_windows, start_time_seconds)
            
            # Wstaw zamówienia bez Time Windows w odpowiednie miejsca
            final_route = []
            for order in optimized_with_windows:
                final_route.append(order)
                # Wstaw zamówienia bez Time Windows, które są blisko
                for no_tw_order in orders_without_windows[:]:
                    if no_tw_order not in final_route:
                        # Sprawdź, czy możemy wstawić tutaj
                        test_route = final_route + [no_tw_order]
                        test_valid, _ = self.check_time_windows(test_route, start_time_seconds)
                        if test_valid or not any(o.has_time_window() for o in test_route):
                            final_route.append(no_tw_order)
                            orders_without_windows.remove(no_tw_order)
            
            # Dodaj pozostałe zamówienia bez Time Windows na końcu
            final_route.extend(orders_without_windows)
            
            return final_route
        
        return fixed_route


def main():
    """
    Główna funkcja demonstracyjna - symulacja użycia aplikacji.
    """
    print("="*80)
    print("SYMULACJA ZARZĄDZANIA TRASAMI Z TIME WINDOWS")
    print("="*80)
    
    # 1. Generuj przykładowe dane
    print("\n📦 Krok 1: Generowanie przykładowych zamówień...")
    sample_orders = Order.generate_sample_orders(7)
    print(f"✅ Wygenerowano {len(sample_orders)} zamówień")
    
    # 2. Utwórz RouteManager i wczytaj zamówienia
    print("\n📋 Krok 2: Tworzenie RouteManager i wczytywanie zamówień...")
    route_manager = RouteManager()
    route_manager.load_orders(sample_orders)
    
    # 3. Wyświetl trasę początkową
    print("\n🗺️  Krok 3: Wyświetlanie trasy początkowej...")
    route_manager.display_route()
    
    # 4. Zasymuluj ręczne przestawienie zamówienia
    print("🔄 Krok 4: Ręczne przestawienie zamówienia...")
    # Przenieś zamówienie o ID 3 na pozycję 0 (początek trasy)
    route_manager.move_order(order_id=3, new_index=0)
    route_manager.display_route()
    
    # 5. Optymalizuj trasę
    print("⚙️  Krok 5: Optymalizacja trasy z uwzględnieniem Time Windows...")
    optimizer = RouteOptimizer(average_speed_kmh=30.0)
    
    current_orders = route_manager.get_orders()
    optimized_route, all_valid, arrival_times = optimizer.optimize_route(
        current_orders, 
        start_time_seconds=28800  # 08:00
    )
    
    # 6. Wyświetl zoptymalizowaną trasę
    print("\n✨ Krok 6: Zoptymalizowana trasa:")
    print("="*80)
    for idx, (order, arrival_time) in enumerate(zip(optimized_route, arrival_times), 1):
        time_str = seconds_to_time(arrival_time)
        time_info = ""
        if order.has_time_window():
            status = "✅" if order.can_be_visited_at(arrival_time) else "❌"
            time_info = f" | Przybycie: {time_str} | Okno: {order.time_window_start}-{order.time_window_end} {status}"
        else:
            time_info = f" | Przybycie: {time_str}"
        
        print(f"{idx:2d}. [{order.id:2d}] {order.address[:45]:<45} | GPS: ({order.latitude:.4f}, {order.longitude:.4f}){time_info}")
    print("="*80)
    
    # 7. Sprawdź status Time Windows
    print(f"\n📊 Krok 7: Status Time Windows:")
    if all_valid:
        print("✅ Wszystkie okna czasowe zostały spełnione!")
    else:
        print("⚠️  Niektóre okna czasowe zostały naruszone. Próba naprawy...")
        
        # Próbuj naprawić naruszenia
        fixed_route = optimizer.fix_time_window_violations(optimized_route, start_time_seconds=28800)
        fixed_valid, fixed_arrival_times = optimizer.check_time_windows(fixed_route, start_time_seconds=28800)
        
        if fixed_valid:
            print("✅ Trasa została naprawiona!")
            route_manager.load_orders(fixed_route)
            route_manager.display_route()
        else:
            print("❌ Nie udało się całkowicie naprawić naruszeń Time Windows.")
            print("   Może być konieczne ręczne dostosowanie trasy lub rozszerzenie okien czasowych.")
    
    # 8. Podsumowanie
    print("\n" + "="*80)
    print("PODSUMOWANIE")
    print("="*80)
    print(f"Liczba zamówień: {len(optimized_route)}")
    print(f"Wszystkie Time Windows spełnione: {'✅ TAK' if all_valid else '❌ NIE'}")
    
    # Oblicz całkowitą odległość
    total_distance = 0.0
    for i in range(len(optimized_route) - 1):
        total_distance += haversine_distance(
            optimized_route[i].latitude, optimized_route[i].longitude,
            optimized_route[i+1].latitude, optimized_route[i+1].longitude
        )
    print(f"Całkowita odległość trasy: {total_distance:.2f} km")
    print(f"Szacowany czas trasy: {seconds_to_time(int(total_distance / 30.0 * 3600))}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

