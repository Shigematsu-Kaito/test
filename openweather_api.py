import requests

class Weatherapi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, lat, lon):
        """座標から現在の天気を取得し、分かりやすい絵文字を返す"""
        params = {
            "lat": lat, "lon": lon, "appid": self.api_key,
            "units": "metric", "lang": "ja"
        }
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            weather_data = data["weather"][0]
            condition_id = weather_data["id"] # 天気条件ID

            # IDに基づいて分かりやすい絵文字を選択
            emoji = self._get_weather_emoji(condition_id)

            return {
                "temp": int(data["main"]["temp"]),
                "description": weather_data["description"],
                "emoji": emoji  # URLではなく絵文字を返す
            }
        except Exception as e:
            print(f"Weather Error: {e}")
            return None

    def _get_weather_emoji(self, condition_id):
        """天気IDから視認性の高い絵文字を返す"""
        # https://openweathermap.org/weather-conditions
        if 200 <= condition_id < 300: return "⛈️"  # 雷雨（雷と雨）
        if 300 <= condition_id < 400: return "🌧️"  # 霧雨（雲と雨粒）
        if 500 <= condition_id < 600: return "☔"   # 雨（分かりやすく傘マーク！）
        if 600 <= condition_id < 700: return "❄️"   # 雪
        if 700 <= condition_id < 800: return "🌫️"   # 霧など
        if condition_id == 800: return "☀️"        # 快晴
        if 800 < condition_id < 900: return "☁️"   # 曇り
        return "❓"