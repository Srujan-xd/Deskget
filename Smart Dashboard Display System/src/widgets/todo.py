"""
widgets/todo.py — To-do list panel.
Reads tasks from a plain-text file (one task per line).
Completed tasks are prefixed with 'x ' or 'X '.
"""

import logging
import os

from widgets.base import BaseWidget, draw_header, draw_divider

log = logging.getLogger(__name__)

LINE_H  = 28   # pixels per task row
MAX_VIS = 6    # max tasks visible at once (fits 240 px minus header)


class TodoWidget(BaseWidget):
    NAME      = "todo"
    REFRESH_S = 10   # re-read file every 10 s to pick up edits

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tasks: list[dict] = []   # [{"text": str, "done": bool}]
        self._scroll: int = 0          # first visible task index
        self._mtime: float = 0

    def update(self) -> None:
        from config import TODO_FILE
        path = os.path.abspath(TODO_FILE)
        if not os.path.exists(path):
            # Create an example file so the user sees something
            try:
                with open(path, "w") as f:
                    f.write("Buy ST7789 displays\n")
                    f.write("Flash Raspberry Pi OS\n")
                    f.write("Enable SPI in raspi-config\n")
                    f.write("x Set up Python venv\n")
                    f.write("Add API keys to config.py\n")
                    f.write("Design enclosure\n")
            except OSError:
                pass

        try:
            mtime = os.path.getmtime(path)
            if mtime == self._mtime and self._tasks:
                return  # file unchanged
            with open(path, "r") as f:
                lines = [l.rstrip("\n") for l in f if l.strip()]
            self._tasks = [
                {"text": l[2:] if l[:2].lower() in ("x ", "X ") else l,
                 "done": l[:2].lower() in ("x ", "X ")}
                for l in lines
            ]
            self._mtime  = mtime
            self._error  = None
            # Auto-scroll past completed items to show pending ones first
            first_pending = next((i for i, t in enumerate(self._tasks) if not t["done"]), 0)
            self._scroll  = max(0, first_pending)
            log.info("Todo: loaded %d tasks", len(self._tasks))
        except Exception as exc:
            self._error = str(exc)
            log.error("Todo load failed: %s", exc)

    def render(self):
        t = self._theme()
        img, draw = self._blank()
        draw_header(draw, "TO-DO", self._font_path(bold=True), t)

        if self._error:
            return self._error_frame(self._error)

        total  = len(self._tasks)
        done_n = sum(1 for tk in self._tasks if tk["done"])

        # Progress subtitle
        sub = f"{done_n}/{total} done"
        draw.text((10, 36), sub, font=self._font(11), fill=t["dim"])

        # Thin progress bar
        if total:
            bx, by, bw, bh = 10, 50, 220, 6
            draw.rectangle([(bx, by), (bx + bw, by + bh)], fill=t["card"])
            draw.rectangle([(bx, by), (bx + int(bw * done_n / total), by + bh)], fill=t["success"])

        if not self._tasks:
            draw.text((10, 70), "No tasks — edit todos.txt", font=self._font(13), fill=t["dim"])
            return img

        # Render visible window
        visible = self._tasks[self._scroll: self._scroll + MAX_VIS]
        y = 62
        for task in visible:
            self._draw_task(draw, t, task, y)
            y += LINE_H

        # Scroll indicator dots
        pages = max(1, (total + MAX_VIS - 1) // MAX_VIS)
        cur_page = self._scroll // MAX_VIS
        if pages > 1:
            dot_y = 232
            total_w = pages * 10
            start_x = (240 - total_w) // 2
            for p in range(pages):
                color = t["primary"] if p == cur_page else t["dim"]
                draw.ellipse([(start_x + p * 10, dot_y), (start_x + p * 10 + 6, dot_y + 6)], fill=color)

        return img

    def _draw_task(self, draw, t, task: dict, y: int) -> None:
        done = task["done"]
        # Checkbox
        box_x, box_y, box_s = 8, y + 6, 14
        draw.rectangle([(box_x, box_y), (box_x + box_s, box_y + box_s)],
                       outline=t["success"] if done else t["dim"], width=1)
        if done:
            draw.line([(box_x + 2, box_y + 7), (box_x + 5, box_y + 10),
                       (box_x + 12, box_y + 3)], fill=t["success"], width=2)

        # Task text
        text  = task["text"]
        color = t["dim"] if done else t["text"]
        font  = self._font(12)
        # Truncate if too long
        while draw.textbbox((0, 0), text, font=font)[2] > 205 and len(text) > 5:
            text = text[:-1]
        if text != task["text"]:
            text = text[:-1] + "…"

        draw.text((28, y + 6), text, font=font, fill=color)
        if done:
            # Strikethrough
            tw = draw.textbbox((0, 0), text, font=font)[2]
            mid_y = y + 6 + 7
            draw.line([(28, mid_y), (28 + tw, mid_y)], fill=t["dim"], width=1)

    def scroll_down(self) -> None:
        """Advance visible window by one page. Called by the scheduler."""
        max_scroll = max(0, len(self._tasks) - MAX_VIS)
        self._scroll = min(self._scroll + MAX_VIS, max_scroll)

    def scroll_up(self) -> None:
        self._scroll = max(0, self._scroll - MAX_VIS)
