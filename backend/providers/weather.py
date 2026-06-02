"""Weather panel via Open-Meteo (free, no API key). Reads a location from
settings (lat/lon, or a place name we geocode). Always live."""
import datetime

import httpx

from backend.envelope import ok, setup, run_provider

ID, TITLE = "today_weather", "Weather"

# WMO weather codes -> (label, emoji)
_CODES = {
    0: ("Clear sky", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"), 45: ("Fog", "🌫️"), 48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Heavy drizzle", "🌦️"),
    56: ("Freezing drizzle", "🌧️"), 57: ("Freezing drizzle", "🌧️"),
    61: ("Light rain", "🌧️"), 63: ("Rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
    66: ("Freezing rain", "🌧️"), 67: ("Freezing rain", "🌧️"),
    71: ("Light snow", "🌨️"), 73: ("Snow", "🌨️"), 75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "🌨️"), 80: ("Light showers", "🌦️"), 81: ("Showers", "🌦️"),
    82: ("Violent showers", "⛈️"), 85: ("Snow showers", "🌨️"), 86: ("Snow showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm, hail", "⛈️"), 99: ("Thunderstorm, hail", "⛈️"),
}


def code_info(code):
    label, emoji = _CODES.get(code, ("—", "🌡️"))
    return {"label": label, "emoji": emoji}


def _r(x):
    return round(x) if isinstance(x, (int, float)) else None


def parse_current(data, place, unit_symbol):
    cur = data.get("current", {})
    daily = data.get("daily", {})
    code = cur.get("weather_code")
    info = code_info(code)
    highs = daily.get("temperature_2m_max") or [None]
    lows = daily.get("temperature_2m_min") or [None]
    return {
        "place": place,
        "temp": _r(cur.get("temperature_2m")),
        "feels_like": _r(cur.get("apparent_temperature")),
        "code": code, "label": info["label"], "emoji": info["emoji"],
        "high": _r(highs[0]), "low": _r(lows[0]),
        "wind": _r(cur.get("wind_speed_10m")),
        "unit": unit_symbol,
    }


def parse_hourly(data, count=6, now=None):
    h = data.get("hourly") or {}
    times = h.get("time") or []
    temps = h.get("temperature_2m") or []
    codes = h.get("weather_code") or []
    now = now or datetime.datetime.now()
    cur_key = now.strftime("%Y-%m-%dT%H:00")
    out = []
    for i, t in enumerate(times):
        if t >= cur_key:
            info = code_info(codes[i] if i < len(codes) else None)
            out.append({"time": t[11:16],
                        "temp": _r(temps[i]) if i < len(temps) else None,
                        "emoji": info["emoji"]})
        if len(out) >= count:
            break
    return out


def _geocode(place):
    r = httpx.get("https://geocoding-api.open-meteo.com/v1/search",
                  params={"name": place, "count": 1}, timeout=8)
    r.raise_for_status()
    res = r.json().get("results") or []
    if not res:
        return None
    g = res[0]
    return g["latitude"], g["longitude"], g.get("name", place)


def provider(cfg):
    w = cfg.get("weather") or {}
    lat, lon, place = w.get("latitude"), w.get("longitude"), w.get("place")
    fahrenheit = str(w.get("units", "celsius")).lower().startswith("f")
    if (lat is None or lon is None) and not place:
        return setup(ID, TITLE, 'Set your location in settings — weather.place, e.g. "London".')

    def _do():
        nonlocal lat, lon, place
        if lat is None or lon is None:
            g = _geocode(place)
            if not g:
                return setup(ID, TITLE, f'Couldn’t find "{place}". Try a different place name or set lat/lon.')
            lat, lon, place = g
        params = {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "hourly": "temperature_2m,weather_code",
            "forecast_days": 1, "timezone": "auto",
            "temperature_unit": "fahrenheit" if fahrenheit else "celsius",
        }
        r = httpx.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        value = parse_current(data, place, "°F" if fahrenheit else "°C")
        return ok(ID, TITLE, items=parse_hourly(data, 6), value=value)

    return run_provider(ID, TITLE, _do)
