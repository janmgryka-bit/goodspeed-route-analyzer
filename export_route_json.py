"""
Skrypt pomocniczy do eksportu zoptymalizowanej trasy do pliku JSON
dla aplikacji mobilnej GoodSpeed Route Analyzer.
"""

import json
import sys
from goodspeed_cloud_mapper import optimize_route, geocode_addresses_list

def export_route_to_json(delivery_points, output_file='route.json'):
    """
    Eksportuje zoptymalizowaną trasę do pliku JSON.
    
    Args:
        delivery_points: Lista punktów dostaw z goodspeed_cloud_mapper
        output_file: Nazwa pliku wyjściowego
    """
    # Optymalizuj trasę
    optimized_points = optimize_route(delivery_points)
    
    # Przygotuj dane do eksportu
    route_data = []
    for point in optimized_points:
        route_data.append({
            'id': point.get('id', 0),
            'address': point.get('address', ''),
            'lat': point.get('lat'),
            'lon': point.get('lon')
        })
    
    # Zapisz do pliku JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(route_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Trasa wyeksportowana do pliku: {output_file}")
    print(f"📊 Liczba punktów: {len(route_data)}")
    
    return output_file


if __name__ == '__main__':
    # Przykład użycia - można zintegrować z goodspeed_cloud_mapper.py
    print("Użyj tego skryptu z goodspeed_cloud_mapper.py do eksportu trasy.")
    print("Przykład: Po wygenerowaniu trasy w goodspeed_cloud_mapper, wywołaj:")
    print("  export_route_to_json(optimized_points, 'route.json')")

