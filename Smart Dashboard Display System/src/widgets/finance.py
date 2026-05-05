"""
widgets/finance.py — Stock and crypto ticker using yfinance.
Shows price, change %, and a simple sparkline for each symbol.
Requires: yfinance
"""

import logging
import time
from typing import NamedTuple

try:
    import yfinance as yf
    _YF_OK = True
except ImportError:
    _YF_OK = False

from widgets.base import BaseWidget, draw_header, draw_divider

log = logging.getLogger(__name__)

ROW_H = 42   # height of each ticker row


class TickerData(NamedTuple):
    symbol:    str
    price:     float
    change:    float      # absolute change
    change_pct:float      # percentage change
    sparkline: list[float]  # last N closing prices (oldest → newest)


class FinanceWidget(BaseWidget):
    NAME      = "finance"
    REFRESH_S = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tickers: list[TickerData] = []

    def update(self) -> None:
        if not _YF_OK:
            self._error = "Install yfinance: pip install yfinance"
            return
        from config import FINANCE_SYMBOLS
        results = []
        for sym in FINANCE_SYMBOLS[:5]:   # cap at 5 rows to fit screen
            try:
                ticker = yf.Ticker(sym)
                hist   = ticker.history(period="5d", interval="1h")
                if hist.empty:
                    continue
                closes    = hist["Close"].dropna().tolist()
                latest    = closes[-1]
                prev      = closes[-2] if len(closes) > 1 else latest
                chg       = latest - prev
                chg_pct   = (chg / prev * 100) if prev != 0 else 0
                sparkline = closes[-20:] if len(closes) >= 20 else closes
                results.append(TickerData(sym, latest, chg, chg_pct, sparkline))
            except Exception as exc:
                log.warning("Finance fetch failed for %s: %s", sym, exc)
        self._tickers = results
        self._error   = None if results else "No data fetched"

    def render(self):
        t = self._theme()
        img, draw = self._blank()
        draw_header(draw, "FINANCE", self._font_path(bold=True), t)

        if self._error:
            return self._error_frame(self._error)

        if not self._tickers:
            draw.text((10, 50), "Fetching...", font=self._font(16), fill=t["dim"])
            return img

        y = 36
        for td in self._tickers:
            self._draw_row(draw, t, td, y)
            y += ROW_H
            if y + ROW_H > 238:
                break

        return img

    def _draw_row(self, draw, t, td: TickerData, y: int) -> None:
        positive = td.change >= 0
        chg_color = t["success"] if positive else t["danger"]
        chg_prefix = "+" if positive else ""

        # Symbol
        draw.text((8, y + 2), td.symbol, font=self._font(13, bold=True), fill=t["text"])

        # Price
        price_str = self._fmt_price(td.price)
        price_w   = draw.textbbox((0, 0), price_str, font=self._font(13, bold=True))[2]
        draw.text((8, y + 18), price_str, font=self._font(13, bold=True), fill=t["primary"])

        # Change %
        chg_str = f"{chg_prefix}{td.change_pct:.2f}%"
        draw.text((10 + price_w + 6, y + 20), chg_str, font=self._font(11, bold=True), fill=chg_color)

        # Sparkline (right side)
        self._draw_sparkline(draw, td.sparkline, x=155, y=y + 4, w=78, h=32, color=chg_color)

        draw_divider(draw, y + ROW_H - 2, t)

    @staticmethod
    def _fmt_price(price: float) -> str:
        if price >= 1000:
            return f"${price:,.0f}"
        if price >= 1:
            return f"${price:.2f}"
        return f"${price:.4f}"

    @staticmethod
    def _draw_sparkline(draw, values: list[float], x: int, y: int, w: int, h: int, color) -> None:
        if len(values) < 2:
            return
        mn, mx = min(values), max(values)
        rng = mx - mn if mx != mn else 1
        pts = []
        for i, v in enumerate(values):
            px = x + int(i * w / (len(values) - 1))
            py = y + h - int((v - mn) / rng * h)
            pts.append((px, py))
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i + 1]], fill=color, width=1)
