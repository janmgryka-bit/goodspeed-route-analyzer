"""
GoodSpeed Route Analyzer - Aplikacja mobilna do zarządzania trasą dostaw
Aplikacja ładuje zoptymalizowaną trasę, wyświetla ją na mapie i umożliwia odznaczanie ukończonych dostaw.
"""

import json
import os
import importlib.util
from math import radians, sin, cos, sqrt, atan2
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics import Color, Line, Ellipse
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

try:
    from kivy_garden.mapview import MapView, MapMarker, MapMarkerPopup
    MAPVIEW_AVAILABLE = True
except ImportError:
    MAPVIEW_AVAILABLE = False
    print("⚠️ kivy_garden.mapview nie jest zainstalowane. Użyj: pip install kivy-garden.mapview")

try:
    from plyer import gps
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False
    print("⚠️ plyer nie jest zainstalowane. Użyj: pip install plyer")


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


class DeliveryPoint:
    """Klasa reprezentująca punkt dostawy."""
    
    STATES = {
        'pending': {'color': [0.2, 0.4, 1.0, 1.0], 'name': 'Do zrobienia'},  # Niebieski
        'current': {'color': [1.0, 0.8, 0.0, 1.0], 'name': 'Aktualny cel'},  # Żółty
        'completed': {'color': [0.0, 0.8, 0.0, 1.0], 'name': 'Zrobione'}  # Zielony
    }
    
    def __init__(self, point_data):
        self.id = point_data.get('id', 0)
        self.address = point_data.get('address', '')
        self.lat = point_data.get('lat')
        self.lon = point_data.get('lon')
        self.is_completed = False
        self.state = 'pending'  # pending, current, completed
        self.marker = None  # Referencja do markera na mapie
        
    def get_color(self):
        """Zwraca kolor pinezki w zależności od stanu."""
        return self.STATES[self.state]['color']
    
    def mark_as_completed(self):
        """Oznacza punkt jako ukończony."""
        self.is_completed = True
        self.state = 'completed'
        if self.marker:
            self.marker.source = 'marker_green.png'  # Można użyć ikon
    
    def set_as_current(self):
        """Ustawia punkt jako aktualny cel."""
        if not self.is_completed:
            self.state = 'current'
            if self.marker:
                self.marker.source = 'marker_yellow.png'
    
    def set_as_pending(self):
        """Ustawia punkt jako oczekujący."""
        if not self.is_completed:
            self.state = 'pending'
            if self.marker:
                self.marker.source = 'marker_blue.png'


class RouteManager:
    """Klasa zarządzająca trasą dostaw."""
    
    def __init__(self, route_data):
        self.delivery_points = [DeliveryPoint(point) for point in route_data]
        self.current_index = 0
        self.completed_count = 0
        self.total_count = len(self.delivery_points)
        
        # Ustaw pierwszy punkt jako aktualny cel
        if self.delivery_points:
            self.delivery_points[0].set_as_current()
    
    def get_current_point(self):
        """Zwraca aktualny punkt docelowy."""
        if 0 <= self.current_index < len(self.delivery_points):
            return self.delivery_points[self.current_index]
        return None
    
    def mark_as_completed(self, delivery_id):
        """
        Oznacza punkt jako ukończony i automatycznie ustawia następny jako aktualny.
        
        Args:
            delivery_id: ID punktu dostawy do oznaczenia jako ukończony
        """
        # Znajdź punkt po ID
        point = None
        for p in self.delivery_points:
            if p.id == delivery_id:
                point = p
                break
        
        if not point:
            return False
        
        if point.is_completed:
            return False  # Już ukończony
        
        # Oznacz jako ukończony
        point.mark_as_completed()
        self.completed_count += 1
        
        # Jeśli to był aktualny cel, znajdź następny niewykonany
        if point == self.get_current_point():
            self._set_next_current()
        
        return True
    
    def _set_next_current(self):
        """Ustawia następny niewykonany punkt jako aktualny cel."""
        # Znajdź następny niewykonany punkt
        for i in range(self.current_index + 1, len(self.delivery_points)):
            if not self.delivery_points[i].is_completed:
                # Zmień poprzedni aktualny na pending (jeśli nie był ukończony)
                if self.current_index < len(self.delivery_points):
                    prev_point = self.delivery_points[self.current_index]
                    if not prev_point.is_completed:
                        prev_point.set_as_pending()
                
                self.current_index = i
                self.delivery_points[i].set_as_current()
                return
        
        # Jeśli nie ma więcej punktów, wszystkie są ukończone
        if self.current_index < len(self.delivery_points):
            prev_point = self.delivery_points[self.current_index]
            if not prev_point.is_completed:
                prev_point.set_as_pending()
    
    def get_progress(self):
        """Zwraca postęp w procentach."""
        if self.total_count == 0:
            return 0
        return (self.completed_count / self.total_count) * 100
    
    def get_statistics(self):
        """Zwraca statystyki trasy."""
        return {
            'total': self.total_count,
            'completed': self.completed_count,
            'remaining': self.total_count - self.completed_count,
            'progress': self.get_progress()
        }


class GPSManager:
    """Klasa zarządzająca lokalizacją GPS."""
    
    def __init__(self):
        self.latitude = None
        self.longitude = None
        self.accuracy = None
        self.is_active = False
        
    def start(self, callback):
        """Uruchamia śledzenie GPS."""
        if not GPS_AVAILABLE:
            return False
        
        try:
            gps.configure(on_location=self._on_location)
            gps.start(minTime=1000, minDistance=1)  # Aktualizacja co sekundę lub 1 metr
            self.is_active = True
            self.callback = callback
            return True
        except Exception as e:
            print(f"Błąd uruchomienia GPS: {e}")
            return False
    
    def stop(self):
        """Zatrzymuje śledzenie GPS."""
        if GPS_AVAILABLE and self.is_active:
            try:
                gps.stop()
                self.is_active = False
            except Exception as e:
                print(f"Błąd zatrzymania GPS: {e}")
    
    def _on_location(self, **kwargs):
        """Callback wywoływany przy aktualizacji lokalizacji."""
        self.latitude = kwargs.get('lat')
        self.longitude = kwargs.get('lon')
        self.accuracy = kwargs.get('accuracy')
        
        if self.callback:
            self.callback(self.latitude, self.longitude)
    
    def get_distance_to_point(self, lat, lon):
        """Oblicza odległość do punktu w metrach."""
        if self.latitude is None or self.longitude is None:
            return None
        
        distance_km = haversine_distance(self.latitude, self.longitude, lat, lon)
        return distance_km * 1000  # Konwersja na metry


class RouteMapView(BoxLayout):
    """Główny widok mapy z trasą."""
    
    def __init__(self, route_manager, gps_manager, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.route_manager = route_manager
        self.gps_manager = gps_manager
        self.confirm_button = None
        self.distance_label = None
        
        # Sprawdź dostępność MapView
        if not MAPVIEW_AVAILABLE:
            self._create_fallback_map()
            return
        
        # Utwórz mapę
        self.mapview = MapView(zoom=12, lat=52.2297, lon=21.0122)  # Warszawa domyślnie
        
        # Ustaw centrum mapy na pierwszy punkt
        if route_manager.delivery_points:
            first_point = route_manager.delivery_points[0]
            if first_point.lat and first_point.lon:
                self.mapview.center_on(first_point.lat, first_point.lon)
        
        # Dodaj markery dla wszystkich punktów
        self.markers = []
        for point in route_manager.delivery_points:
            if point.lat and point.lon:
                # Utwórz marker z popup
                marker = MapMarkerPopup(
                    lat=point.lat,
                    lon=point.lon
                )
                
                # Bind event kliknięcia
                def make_click_handler(p):
                    return lambda instance: self._on_marker_click(p)
                marker.bind(on_release=make_click_handler(point))
                
                # Dodaj popup z pełnym adresem
                popup_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
                popup_label = Label(
                    text=f"[b]Punkt {point.id}[/b]\n\n{point.address}\n\nStan: {point.STATES[point.state]['name']}",
                    text_size=(dp(250), None),
                    halign='center',
                    valign='middle',
                    markup=True
                )
                popup_layout.add_widget(popup_label)
                marker.add_widget(popup_layout)
                
                point.marker = marker
                self.mapview.add_marker(marker)
                self.markers.append(marker)
        
        # Dodaj mapę do layoutu
        self.add_widget(self.mapview)
        
        # Panel kontrolny na dole
        self._create_control_panel()
        
        # Uruchom śledzenie GPS
        if GPS_AVAILABLE:
            self.gps_manager.start(self._on_gps_update)
        
        # Uruchom sprawdzanie odległości
        Clock.schedule_interval(self._check_proximity, 1.0)  # Co sekundę
    
    def _get_marker_source(self, state):
        """Zwraca źródło ikony markera w zależności od stanu."""
        # W rzeczywistej aplikacji użyj prawdziwych ikon
        # Na razie zwracamy None, MapView użyje domyślnych
        return None
    
    def _create_fallback_map(self):
        """Tworzy prosty widok zastępczy gdy MapView nie jest dostępne."""
        fallback_label = Label(
            text="⚠️ MapView nie jest dostępne.\n\nZainstaluj: pip install kivy-garden.mapview\n\n"
                 "Aplikacja będzie działać w trybie listy.",
            text_size=(None, None),
            halign='center',
            valign='middle'
        )
        self.add_widget(fallback_label)
        self._create_control_panel()
    
    def _create_control_panel(self):
        """Tworzy panel kontrolny na dole ekranu."""
        control_panel = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(200))
        
        # Statystyki
        stats = self.route_manager.get_statistics()
        stats_label = Label(
            text=f"Postęp: {stats['completed']}/{stats['total']} ({stats['progress']:.1f}%)",
            size_hint_y=None,
            height=dp(40)
        )
        control_panel.add_widget(stats_label)
        
        # Etykieta odległości
        self.distance_label = Label(
            text="Odległość do celu: --",
            size_hint_y=None,
            height=dp(40)
        )
        control_panel.add_widget(self.distance_label)
        
        # Przycisk "Zrobione" dla aktualnego punktu
        current_point = self.route_manager.get_current_point()
        if current_point:
            complete_button = Button(
                text=f"✓ Zrobione: {current_point.address[:50]}...",
                size_hint_y=None,
                height=dp(60),
                background_color=[0.0, 0.8, 0.0, 1.0]  # Zielony
            )
            complete_button.bind(on_press=lambda instance: self._mark_current_completed())
            control_panel.add_widget(complete_button)
        
        # Przycisk potwierdzenia (ukryty na początku)
        self.confirm_button = Button(
            text="🎯 POTWIERDŹ ZAKOŃCZENIE",
            size_hint_y=None,
            height=dp(80),
            background_color=[1.0, 0.0, 0.0, 1.0],  # Czerwony
            opacity=0  # Ukryty
        )
        self.confirm_button.bind(on_press=lambda instance: self._confirm_completion())
        control_panel.add_widget(self.confirm_button)
        
        self.add_widget(control_panel)
    
    def _on_marker_click(self, point):
        """Obsługuje kliknięcie w marker."""
        if point.is_completed:
            return
        
        # Ustaw jako aktualny cel
        current = self.route_manager.get_current_point()
        if current and current != point:
            current.set_as_pending()
        
        self.route_manager.current_index = self.route_manager.delivery_points.index(point)
        point.set_as_current()
        
        # Zaktualizuj przycisk
        self._update_complete_button()
    
    def _mark_current_completed(self):
        """Oznacza aktualny punkt jako ukończony."""
        current = self.route_manager.get_current_point()
        if current:
            self.route_manager.mark_as_completed(current.id)
            self._update_complete_button()
            self._update_statistics()
            self._update_markers()
    
    def _confirm_completion(self):
        """Potwierdza zakończenie dostawy (wywoływane gdy kierowca jest blisko)."""
        self._mark_current_completed()
        self.confirm_button.opacity = 0
    
    def _update_complete_button(self):
        """Aktualizuje przycisk "Zrobione"."""
        current = self.route_manager.get_current_point()
        if current and not current.is_completed:
            # Znajdź przycisk w panelu kontrolnym
            for widget in self.children:
                if isinstance(widget, BoxLayout) and len(widget.children) > 0:
                    for child in widget.children:
                        if isinstance(child, Button) and child.text.startswith("✓"):
                            child.text = f"✓ Zrobione: {current.address[:50]}..."
                            break
        elif current is None or current.is_completed:
            # Wszystkie ukończone
            for widget in self.children:
                if isinstance(widget, BoxLayout) and len(widget.children) > 0:
                    for child in widget.children:
                        if isinstance(child, Button) and child.text.startswith("✓"):
                            child.text = "✓ Wszystkie dostawy ukończone!"
                            child.background_color = [0.0, 0.8, 0.0, 1.0]
                            break
    
    def _update_statistics(self):
        """Aktualizuje statystyki w panelu."""
        stats = self.route_manager.get_statistics()
        for widget in self.children:
            if isinstance(widget, BoxLayout) and len(widget.children) > 0:
                for child in widget.children:
                    if isinstance(child, Label) and child.text.startswith("Postęp:"):
                        child.text = f"Postęp: {stats['completed']}/{stats['total']} ({stats['progress']:.1f}%)"
                        break
    
    def _update_markers(self):
        """Aktualizuje kolory markerów na mapie."""
        if not MAPVIEW_AVAILABLE:
            return
        
        # Zaktualizuj markery na mapie
        for point in self.route_manager.delivery_points:
            if point.marker:
                # W rzeczywistej aplikacji zmień ikonę markera
                # Na razie aktualizujemy tylko stan
                pass
    
    def _on_gps_update(self, lat, lon):
        """Callback wywoływany przy aktualizacji GPS."""
        if not MAPVIEW_AVAILABLE:
            return
        
        # W rzeczywistej aplikacji dodaj marker lokalizacji kierowcy
        # Na razie tylko aktualizujemy centrum mapy
        if lat and lon:
            # Opcjonalnie: wyśrodkuj mapę na lokalizacji kierowcy
            # self.mapview.center_on(lat, lon)
            pass
    
    def _check_proximity(self, dt):
        """Sprawdza, czy kierowca jest w promieniu 50m od aktualnego celu."""
        current = self.route_manager.get_current_point()
        if not current or current.is_completed:
            self.confirm_button.opacity = 0
            return
        
        if not current.lat or not current.lon:
            return
        
        distance = self.gps_manager.get_distance_to_point(current.lat, current.lon)
        
        if distance is not None:
            # Aktualizuj etykietę odległości
            if self.distance_label:
                self.distance_label.text = f"Odległość do celu: {distance:.0f} m"
            
            # Jeśli kierowca jest w promieniu 50m, pokaż przycisk potwierdzenia
            if distance <= 50:
                self.confirm_button.opacity = 1
                self.confirm_button.text = f"🎯 POTWIERDŹ ZAKOŃCZENIE\n({distance:.0f} m)"
            else:
                self.confirm_button.opacity = 0
        else:
            if self.distance_label:
                self.distance_label.text = "Odległość do celu: GPS nieaktywny"


class RouteAnalyzerApp(App):
    """Główna aplikacja."""
    
    def __init__(self, route_file='optimized_data_for_mobile.py', **kwargs):
        super().__init__(**kwargs)
        self.route_file = route_file
        self.route_manager = None
        self.gps_manager = GPSManager()
    
    def build(self):
        """Buduje interfejs aplikacji."""
        # Załaduj trasę z pliku Pythona
        route_data = self._load_route()
        
        if not route_data:
            return self._create_error_view(f"Nie udało się załadować trasy z pliku {self.route_file}!")
        
        # Utwórz RouteManager
        self.route_manager = RouteManager(route_data)
        
        # Utwórz główny widok
        return RouteMapView(self.route_manager, self.gps_manager)
    
    def _load_route(self):
        """Ładuje trasę z pliku Pythona (importuje DELIVERY_POINTS)."""
        if not os.path.exists(self.route_file):
            print(f"⚠️ Plik {self.route_file} nie istnieje!")
            print(f"💡 Upewnij się, że uruchomiłeś goodspeed_cloud_mapper.py i wygenerowałeś plik optimized_data_for_mobile.py")
            return None
        
        try:
            # Importuj moduł Pythona
            import importlib.util
            spec = importlib.util.spec_from_file_location("optimized_data", self.route_file)
            if spec is None or spec.loader is None:
                print(f"❌ Nie udało się załadować specyfikacji modułu z {self.route_file}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Pobierz DELIVERY_POINTS
            if hasattr(module, 'DELIVERY_POINTS'):
                return module.DELIVERY_POINTS
            else:
                print(f"❌ Plik {self.route_file} nie zawiera zmiennej DELIVERY_POINTS!")
                return None
        except Exception as e:
            print(f"❌ Błąd ładowania pliku Pythona: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_error_view(self, message):
        """Tworzy widok błędu."""
        layout = BoxLayout(orientation='vertical', padding=dp(20))
        error_label = Label(text=message, text_size=(None, None), halign='center')
        layout.add_widget(error_label)
        return layout
    
    def on_stop(self):
        """Wywoływane przy zamykaniu aplikacji."""
        self.gps_manager.stop()


def main():
    """Funkcja główna."""
    import sys
    import importlib.util
    
    # Sprawdź argumenty wiersza poleceń
    route_file = 'optimized_data_for_mobile.py'
    if len(sys.argv) > 1:
        route_file = sys.argv[1]
    
    app = RouteAnalyzerApp(route_file=route_file)
    app.run()


if __name__ == '__main__':
    main()

