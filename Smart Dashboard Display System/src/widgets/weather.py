"""
widgets/weather.py — Weather panel via OpenWeatherMap free API.
Shows current conditions + a 3-step hourly forecast.
Requires: requests
"""

import logging
import time
import requests

from widgets.base import BaseWidget, draw_header, draw_divider

log = logging.getLogger(__name__)

# Simple text-art icon map (unicode emoji subset that renders in DejaVu)
CONDITION_ICONS = {
    "Clear":        "SUN",
    "Clouds":       "CLD",
    "Rain":         "RAN",
    "Drizzle":      "DRZ",
    "Thunderstorm": "STM",
    "Snow":         "SNW",
    "Mist":         "MST",
    "Fog":          "FOG",
    "Haze":         "HZE",
}


class WeatherWidget(BaseWidget):
    NAME      = "weather"
    REFRESH_S = 600   # 10 minutes

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current: dict = {}
        self._forecast: list[dict] = []
        self._last_fetch: float = 0

    def update(self) -> None:
        from config import OPENWEATHER_API_KEY, OPENWEATHER_CITY, OPENWEATHER_UNITS
        if OPENWEATHER_API_KEY == "YOUR_OPENWEATHER_API_KEY":
            self._error = "Add OPENWEATHER_API_KEY to config.py"
            return
        try:
            base = "https://api.openweathermap.org/data/2.5"
            params = {"q": OPENWEATHER_CITY, "appid": OPENWEATHER_API_KEY, "units": OPENWEATHER_UNITS}

            r = requests.get(f"{base}/weather", params=params, timeout=8)
            r.raise_for_status()
            raw = r.json()
            self._current = {
                "city":    raw["name"],
                "temp":    raw["main"]["temp"],
                "feels":   raw["main"]["feels_like"],
                "humidity":raw["main"]["humidity"],
                "desc":    raw["weather"][0]["description"].title(),
                "main":    raw["weather"][0]["main"],
                "wind":    raw["wind"]["speed"],
            }

            r2 = requests.get(f"{base}/forecast", params=params, timeout=8)
            r2.raise_for_status()
            items = r2.json()["list"][:4]
            self._forecast = [
                {
                    "time": time.strftime("%H:%M", time.localtime(i["dt"])),
                    "temp": i["main"]["temp"],
                    "main": i["weather"][0]["main"],
                }
                for i in items
            ]
            self._error = None
            log.info("Weather updated: %s", self._current.get("desc"))
        except Exception as exc:
            self._error = str(exc)
            log.error("Weather fetch failed: %s", exc)

    def render(self):
        t = self._theme()
        img, draw = self._blank()
        draw_header(draw, "WEATHER", self._font_path(bold=True), t)

        if self._error:
            return self._error_frame(self._error)

        if not self._current:
            draw.text((10, 50), "Fetching...", font=self._font(16), fill=t["dim"])
            return img

        from config import OPENWEATHER_UNITS
        unit_sym = "°C" if OPENWEATHER_UNITS == "metric" else "°F"

        # City name
        draw.text((10, 36), self._current["city"], font=self._font(14, bold=True), fill=t["secondary"])

        # Large temperature
        temp_str = f"{self._current['temp']:.0f}{unit_sym}"
        draw.text((10, 54), temp_str, font=self._font(52, bold=True), fill=t["primary"])

        # Condition icon + description
        icon = CONDITION_ICONS.get(self._current["main"], "   ")
        draw.text((155, 54), icon, font=self._font(22, bold=True), fill=t["accent"])
        draw.text((155, 80), self._current["desc"], font=self._font(11), fill=t["secondary"])

        # Details row
        y = 120
        details = [
            ("Feels", f"{self._current['feels']:.0f}{unit_sym}"),
            ("Hum",   f"{self._current['humidity']}%"),
            ("Wind",  f"{self._current['wind']:.1f} m/s"),
        ]
        col_w = 80
        for i, (label, val) in enumerate(details):
            x = 10 + i * col_w
            draw.text((x, y),      label, font=self._font(11), fill=t["dim"])
            draw.text((x, y + 14), val,   font=self._font(13, bold=True), fill=t["text"])

        draw_divider(draw, 148, t)

        # Forecast strip
        if self._forecast:
            fw = 240 // len(self._forecast)
            for i, fc in enumerate(self._forecast):
                fx = i * fw + fw // 2
                fy = 154
                icon_f = CONDITION_ICONS.get(fc["main"], "---")
                draw.text((fx - 12, fy),      fc["time"], font=self._font(10), fill=t["dim"])
                draw.text((fx - 12, fy + 14), icon_f,     font=self._font(11, bold=True), fill=t["accent"])
                draw.text((fx - 12, fy + 28), f"{fc['temp']:.0f}{unit_sym}", font=self._font(11), fill=t["text"])

        return img
