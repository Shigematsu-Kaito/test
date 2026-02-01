# mapbox_api.py
import requests
import urllib.parse

class Mapboxapi:
    def __init__(self, access_token):
        self.access_token = access_token

    def get_coordinates(self, place_name):
        """地名から座標(lon, lat)を取得 (Geocoding API)"""
        query = urllib.parse.quote(place_name)
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"
        params = {
            "access_token": self.access_token,
            "limit": 1,
            "language": "ja"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data["features"]:
                # Mapboxは [lon, lat] の順で返す
                return data["features"][0]["center"]
            return None
        except Exception as e:
            print(f"Geocoding Error: {e}")
            return None

    def get_route(self, start_coords, end_coords, profile="driving"):
        """2点間のルートを取得 (Directions API)"""
        # coordsは [lon, lat]
        coords_str = f"{start_coords[0]},{start_coords[1]};{end_coords[0]},{end_coords[1]}"
        url = f"https://api.mapbox.com/directions/v5/mapbox/{profile}/{coords_str}"
        
        params = {
            "access_token": self.access_token,
            "geometries": "geojson", # 地図描画用にGeoJSON形式で取得
            "overview": "full"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data["routes"]:
                route = data["routes"][0]
                return {
                    "geometry": route["geometry"], # 線のデータ
                    "duration": route["duration"], # 所要時間(秒)
                    "distance": route["distance"]  # 距離(m)
                }
            return None
        except Exception as e:
            print(f"Directions API Error: {e}")
            return None