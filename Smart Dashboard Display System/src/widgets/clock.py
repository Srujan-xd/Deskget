"""
widgets/clock.py — Full-screen clock with date, day-of-week, and uptime.
"""

import time
import datetime
import math
from PIL import Image, ImageDraw

from widgets.base import BaseWidget, draw_header, draw_divider


class ClockWidget(BaseWidget):
    NAME      = "clock"
    REFRESH_S = 1   # re-render every second

    def update(self) -> None:
        pass  # datetime is read at render time

    def render(self) -> Image.Image:
        now   = datetime.datetime.now()
        t     = self._theme()
        img, draw = self._blank()

        # ---- Analog clock face ----------------------------------------
        cx, cy, r = 120, 110, 70
        # Background circle
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=t["dim"], width=1)

        # Hour ticks
        for i in range(12):
            angle = math.radians(i * 30 - 90)
            length = 8 if i % 3 == 0 else 4
            x1 = cx + (r - 4) * math.cos(angle)
            y1 = cy + (r - 4) * math.sin(angle)
            x2 = cx + (r - 4 - length) * math.cos(angle)
            y2 = cy + (r - 4 - length) * math.sin(angle)
            draw.line([(x1, y1), (x2, y2)], fill=t["dim"], width=2)

        # Clock hands
        def hand(minutes_frac: float, length: int, width: int, color):
            angle = math.radians(minutes_frac * 360 - 90)
            x = cx + length * math.cos(angle)
            y = cy + length * math.sin(angle)
            draw.line([(cx, cy), (x, y)], fill=color, width=width)

        total_minutes = now.hour * 60 + now.minute + now.second / 60
        hand(total_minutes / 720, int(r * 0.55), 4, t["primary"])   # hour
        hand(now.minute / 60 + now.second / 3600, int(r * 0.78), 3, t["text"])  # minute
        hand(now.second / 60, int(r * 0.85), 1, t["accent"])         # second

        draw.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], fill=t["primary"])

        # ---- Digital time below face ----------------------------------
        time_str = now.strftime("%H:%M:%S")
        font_big  = self._font(32, bold=True)
        bbox = draw.textbbox((0, 0), time_str, font=font_big)
        tw = bbox[2] - bbox[0]
        draw.text(((240 - tw) // 2, 192), time_str, font=font_big, fill=t["primary"])

        # ---- Date and day strip at top --------------------------------
        draw_divider(draw, 28, t)
        date_str = now.strftime("%A, %d %B %Y")
        font_sm  = self._font(13)
        bbox2 = draw.textbbox((0, 0), date_str, font=font_sm)
        tw2 = bbox2[2] - bbox2[0]
        draw.text(((240 - tw2) // 2, 10), date_str, font=font_sm, fill=t["secondary"])

        return img
