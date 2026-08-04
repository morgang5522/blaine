import logging
import asyncio
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional
from src.tools.base import BaseTool
from src.memory import memory_manager

logger = logging.getLogger("blaine.tools.weather")

WMO_WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌧️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌦️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow fall", "🌨️"),
    73: ("Moderate snow fall", "🌨️"),
    75: ("Heavy snow fall", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌧️"),
    82: ("Violent rain showers", "🌧️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}

class WeatherTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "Fetches current weather conditions and daily forecast for a location name or latitude/longitude coordinates."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City, area, or address name (e.g. 'London', 'San Francisco, CA', 'Tokyo')."
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude coordinate if available."
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude coordinate if available."
                }
            }
        }

    def _fetch_geo_results(self, query_str: str, count: int = 10) -> list:
        query_params = urllib.parse.urlencode({"name": query_str, "count": count, "language": "en", "format": "json"})
        url = f"https://geocoding-api.open-meteo.com/v1/search?{query_params}"
        req = urllib.request.Request(url, headers={"User-Agent": "BlaineAssistant/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("results", [])
        except Exception as e:
            logger.error(f"Geocoding network error for '{query_str}': {e}")
            return []

    def _geocode(self, location_name: str) -> Optional[Dict[str, Any]]:
        if not location_name or not location_name.strip():
            return None

        clean_name = location_name.strip()

        # Attempt 1: Direct search with full string
        results = self._fetch_geo_results(clean_name, count=1)
        if not results and "," in clean_name:
            # Attempt 2: Split by comma if present (e.g. "Birmingham, UK")
            parts = [p.strip() for p in clean_name.split(",") if p.strip()]
            city_query = parts[0]
            qualifiers = [p.lower() for p in parts[1:]]

            candidates = self._fetch_geo_results(city_query, count=10)
            if candidates:
                country_aliases = {
                    "uk": ["gb", "united kingdom", "england", "scotland", "wales"],
                    "usa": ["us", "united states"],
                    "us": ["us", "united states"],
                    "ca": ["canada", "california"],
                    "au": ["australia"],
                }
                # Check candidates for matching country, country_code, or admin1
                for cand in candidates:
                    c_country = (cand.get("country") or "").lower()
                    c_code = (cand.get("country_code") or "").lower()
                    c_admin = (cand.get("admin1") or "").lower()

                    for qual in qualifiers:
                        aliases = country_aliases.get(qual, [qual])
                        if any(a == c_code or a in c_country or a in c_admin for a in aliases):
                            results = [cand]
                            break
                    if results:
                        break

                if not results:
                    results = [candidates[0]]

        if results and len(results) > 0:
            res = results[0]
            city = res.get("name", clean_name)
            country = res.get("country", "")
            admin1 = res.get("admin1", "")
            parts = [p for p in [city, admin1, country] if p]
            full_name = ", ".join(parts)
            return {
                "latitude": res.get("latitude"),
                "longitude": res.get("longitude"),
                "name": full_name or city
            }

        return None

    def _fetch_weather(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        query_string = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "auto"
        })
        url = f"https://api.open-meteo.com/v1/forecast?{query_string}"
        req = urllib.request.Request(url, headers={"User-Agent": "BlaineAssistant/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Weather API error for lat={lat}, lon={lon}: {e}")
            return None

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        location_input = kwargs.get("location")
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")

        display_name = None

        if latitude is not None and longitude is not None:
            lat, lon = float(latitude), float(longitude)
            display_name = location_input or f"{lat:.2f}, {lon:.2f}"
        elif location_input:
            geo_res = await asyncio.to_thread(self._geocode, location_input)
            if not geo_res:
                return {
                    "status": "ERROR",
                    "message": f"Could not find coordinates for location '{location_input}'."
                }
            lat = geo_res["latitude"]
            lon = geo_res["longitude"]
            display_name = geo_res["name"]
        else:
            # Fallback to user saved location fact from memory
            user_facts = memory_manager.get_user_facts(user_id) if user_id else []
            loc_fact = next((f for f in user_facts if any(k in f["fact_key"].lower() for k in ["location", "city", "home"])), None)
            if loc_fact:
                saved_loc = loc_fact["fact_value"]
                geo_res = await asyncio.to_thread(self._geocode, saved_loc)
                if geo_res:
                    lat = geo_res["latitude"]
                    lon = geo_res["longitude"]
                    display_name = geo_res["name"]
                else:
                    return {
                        "status": "ERROR",
                        "message": f"Saved location '{saved_loc}' could not be geocoded."
                    }
            else:
                return {
                    "status": "ERROR",
                    "message": "No location specified and no saved location found in user memory. Please specify a city or share your location."
                }

        weather_data = await asyncio.to_thread(self._fetch_weather, lat, lon)
        if not weather_data or "current" not in weather_data:
            return {
                "status": "ERROR",
                "message": f"Failed to retrieve weather data for {display_name}."
            }

        curr = weather_data["current"]
        daily = weather_data.get("daily", {})

        temp_c = curr.get("temperature_2m")
        feels_c = curr.get("apparent_temperature")
        humidity = curr.get("relative_humidity_2m")
        wind_kmh = curr.get("wind_speed_10m")
        w_code = curr.get("weather_code", 0)

        condition_text, emoji = WMO_WEATHER_CODES.get(w_code, ("Unknown", "🌡️"))

        max_temp = daily.get("temperature_2m_max", [None])[0]
        min_temp = daily.get("temperature_2m_min", [None])[0]

        temp_f = round((temp_c * 9/5) + 32, 1) if temp_c is not None else None
        feels_f = round((feels_c * 9/5) + 32, 1) if feels_c is not None else None
        max_f = round((max_temp * 9/5) + 32, 1) if max_temp is not None else None
        min_f = round((min_temp * 9/5) + 32, 1) if min_temp is not None else None

        msg_lines = [
            f"{emoji} <b>Weather for {display_name}</b>",
            f"• <b>Condition</b>: {condition_text}",
            f"• <b>Temperature</b>: {temp_c}°C ({temp_f}°F)" if temp_c is not None else "",
            f"• <b>Feels Like</b>: {feels_c}°C ({feels_f}°F)" if feels_c is not None else "",
        ]
        if min_temp is not None and max_temp is not None:
            msg_lines.append(f"• <b>Today's Range</b>: Low {min_temp}°C / High {max_temp}°C ({min_f}°F / {max_f}°F)")
        if humidity is not None:
            msg_lines.append(f"• <b>Humidity</b>: {humidity}%")
        if wind_kmh is not None:
            msg_lines.append(f"• <b>Wind Speed</b>: {wind_kmh} km/h")

        formatted_msg = "\n".join([line for line in msg_lines if line])

        return {
            "status": "SUCCESS",
            "location_name": display_name,
            "latitude": lat,
            "longitude": lon,
            "current_temp_c": temp_c,
            "current_temp_f": temp_f,
            "feels_like_c": feels_c,
            "condition": condition_text,
            "emoji": emoji,
            "message": formatted_msg
        }
