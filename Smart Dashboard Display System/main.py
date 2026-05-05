"""
main.py — Desktop Gadget entry point.

Architecture
------------
  DisplaySlot   — owns one physical screen + one ordered list of widgets.
                  Rotates through them every WIDGET_INTERVAL seconds.
                  Calls widget.update() on a per-widget REFRESH_S cadence.

  GadgetApp     — creates two DisplaySlots, runs the main render loop,
                  handles SIGINT/SIGTERM for a clean shutdown.

Run:
    cd src
    python main.py
"""

import logging
import signal
import sys
import time
import threading
from dataclasses import dataclass, field

# ---- project imports (run from src/) -----------------------------------
import config
from display import create_displays_from_config, DisplayPanel
from widgets import build_widget
from widgets.base import BaseWidget

# ---- logging setup ------------------------------------------------------
logging.basicConfig(
    level   = getattr(logging, config.LOG_LEVEL, logging.INFO),
    format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt = "%H:%M:%S",
)
log = logging.getLogger("main")


# =========================================================================
# DisplaySlot
# =========================================================================

@dataclass
class DisplaySlot:
    """
    Manages one physical display: instantiates its widget sequence,
    rotates them on a timer, and runs the render/update loops.
    """
    name:     str
    panel:    DisplayPanel
    schedule: list[str]           # e.g. ["clock", "weather", "finance"]

    _widgets:  list[BaseWidget]   = field(default_factory=list, init=False)
    _index:    int                = field(default=0, init=False)
    _last_rotate: float           = field(default=0.0, init=False)
    _last_update: dict[int, float]= field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        log.info("[%s] Building widgets: %s", self.name, self.schedule)
        for name in self.schedule:
            try:
                w = build_widget(name, config.DISP_WIDTH, config.DISP_HEIGHT)
                self._widgets.append(w)
                log.info("[%s] + %s", self.name, name)
            except KeyError:
                log.error("[%s] Unknown widget '%s' — skipped", self.name, name)
        if not self._widgets:
            raise RuntimeError(f"DisplaySlot '{self.name}' has no valid widgets")

        # Trigger an immediate first update on all widgets
        now = time.monotonic()
        for i, w in enumerate(self._widgets):
            self._last_update[i] = 0.0   # force update on first tick

    # ------------------------------------------------------------------
    @property
    def current(self) -> BaseWidget:
        return self._widgets[self._index]

    def tick(self, now: float) -> None:
        """Call every frame. Updates data and renders to panel."""
        # Rotate widget?
        if now - self._last_rotate >= config.WIDGET_INTERVAL:
            self._index       = (self._index + 1) % len(self._widgets)
            self._last_rotate = now
            log.info("[%s] Switched to widget '%s'", self.name, self.current.NAME)

        # Update data for current widget if due
        w = self.current
        i = self._index
        if now - self._last_update.get(i, 0) >= w.REFRESH_S:
            try:
                w.update()
            except Exception:
                log.exception("[%s] %s.update() raised", self.name, w.NAME)
            self._last_update[i] = now

        # Render and push frame
        try:
            frame = w.render()
            self.panel.show(frame)
        except Exception:
            log.exception("[%s] %s.render() raised", self.name, w.NAME)

    def blank(self) -> None:
        self.panel.blank()


# =========================================================================
# GadgetApp
# =========================================================================

class GadgetApp:
    TARGET_FPS = 10   # Pi Zero is slow — 10 fps is plenty for this use-case

    def __init__(self) -> None:
        self._running = False
        self._slots: list[DisplaySlot] = []

    def setup(self) -> None:
        log.info("Initialising displays…")
        disp1, disp2 = create_displays_from_config()

        self._slots = [
            DisplaySlot("left",  disp1, list(config.DISP1_SCHEDULE)),
            DisplaySlot("right", disp2, list(config.DISP2_SCHEDULE)),
        ]

        # Register shutdown signals
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._on_signal)

        self._running = True
        log.info("Gadget ready. Press Ctrl+C to exit.")

    def run(self) -> None:
        frame_s = 1.0 / self.TARGET_FPS
        while self._running:
            t0  = time.monotonic()
            now = t0
            for slot in self._slots:
                slot.tick(now)
            elapsed = time.monotonic() - t0
            sleep   = frame_s - elapsed
            if sleep > 0:
                time.sleep(sleep)

    def shutdown(self) -> None:
        log.info("Shutting down…")
        self._running = False
        for slot in self._slots:
            try:
                slot.blank()
            except Exception:
                pass
        log.info("Goodbye.")

    def _on_signal(self, signum, _frame) -> None:
        log.info("Signal %d received", signum)
        self.shutdown()


# =========================================================================
# Entry point
# =========================================================================

def main() -> None:
    app = GadgetApp()
    try:
        app.setup()
        app.run()
    except Exception:
        log.exception("Fatal error in main loop")
        sys.exit(1)
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
