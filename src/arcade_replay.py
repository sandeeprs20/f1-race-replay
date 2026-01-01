import os
import arcade
from src.track import world_to_screen


def _compound_key(compound: str | None) -> str:
    """
    Normalize FastF1 compound strings to our tyre texture keys.
    """
    if not compound:
        return "unknown"
    c = compound.strip().upper()
    if c.startswith("SOFT"):
        return "soft"
    if c.startswith("MED"):
        return "medium"
    if c.startswith("HARD"):
        return "hard"
    if c.startswith("INTER"):
        return "intermediate"
    if c.startswith("WET"):
        return "wet"
    return "unknown"


def _drs_is_active(drs_val: int) -> bool:
    """
    FastF1 DRS values often use >=10 to mean open/active (common convention in telemetry streams).
    """
    try:
        return int(drs_val) >= 10
    except Exception:
        return False


class F1ReplayWindow(arcade.Window):
    def __init__(
        self,
        frames,
        track_xy,
        transform,
        driver_colors=None,
        fps=25,
        width=1280,
        height=720,
        title="F1 Replay",
    ):
        super().__init__(width, height, title)

        self.frames = frames
        self.n_frames = len(frames)

        self.track_x, self.track_y = track_xy

        # Avoid "self.scale" name collision with Arcade Window properties
        self.world_scale, self.world_tx, self.world_ty = transform

        self.driver_colors = driver_colors or {}
        self.fps = fps

        # Playback state
        self.frame_idx = 0.0
        self.paused = False
        self.speed_choices = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
        self.speed_i = 1

        arcade.set_background_color(arcade.color.BLACK)

        # Precompute track polyline in screen coords (performance)
        self.track_pts_screen = []
        for x, y in zip(self.track_x, self.track_y):
            sx, sy = world_to_screen(
                float(x), float(y), self.world_scale, self.world_tx, self.world_ty
            )
            self.track_pts_screen.append((sx, sy))

        # HUD text
        self.hud_text = arcade.Text("", 20, self.height - 30, arcade.color.WHITE, 14)
        self.help_text = arcade.Text(
            "Controls: Space=Pause  Up/Down=Speed  Left/Right=Seek  R=Restart",
            20,
            20,
            arcade.color.LIGHT_GRAY,
            12,
        )

        # ---------------------------
        # Leaderboard layout (right)
        # ---------------------------
        self.lb_w = 280
        self.lb_h = self.height - 140
        self.lb_x = self.width - self.lb_w - 16
        self.lb_y = 90

        self.lb_padding = 14
        self.lb_title_h = 34
        self.lb_row_h = 26

        self.hover_index = None
        self.selected_driver = None

        self.lb_title = arcade.Text(
            "Leaderboard",
            self.lb_x + self.lb_padding,
            self.lb_y + self.lb_h - 10,
            arcade.color.WHITE,
            16,
            anchor_x="left",
            anchor_y="top",
        )

        # We’ll reuse these text objects (positions updated each draw)
        self.lb_rows = [
            arcade.Text(
                "",
                0,
                0,
                arcade.color.WHITE,
                14,
                anchor_x="left",
                anchor_y="top",
            )
            for _ in range(20)
        ]

        # ---------------------------
        # Tyre textures (images/tyres)
        # ---------------------------
        base_dir = os.path.dirname(os.path.dirname(__file__))  # project root
        tyres_dir = os.path.join(base_dir, "images", "tyres")

        tyre_files = {
            "soft": "soft.png",
            "medium": "medium.png",
            "hard": "hard.png",
            "intermediate": "intermediate.png",
            "wet": "wet.png",
            "unknown": "unknown.png",
        }

        self.tyre_textures = {}
        for key, fname in tyre_files.items():
            path = os.path.join(tyres_dir, fname)
            if os.path.exists(path):
                self.tyre_textures[key] = arcade.load_texture(path)

        self.tyre_icon_size = 16  # px

        # ---------------------------
        # Telemetry panel (left) — smaller so it doesn't cover track
        # ---------------------------
        self.tel_w = 220
        self.tel_h = 200
        self.tel_x = 16
        self.tel_y = self.height - self.tel_h - 60

        self.tel_title = arcade.Text(
            "",
            self.tel_x + 10,
            self.tel_y + self.tel_h - 10,
            arcade.color.WHITE,
            14,
            anchor_x="left",
            anchor_y="top",
        )
        self.tel_lines = [
            arcade.Text(
                "",
                self.tel_x + 10,
                self.tel_y + self.tel_h - 36 - i * 18,
                arcade.color.LIGHT_GRAY,
                11,
                anchor_x="left",
                anchor_y="top",
            )
            for i in range(8)
        ]

        # Click rects for leaderboard rows (rebuilt each draw)
        self._lb_rects = []

    # ---------------------------
    # Playback
    # ---------------------------
    def on_update(self, delta_time: float):
        if self.paused:
            return

        self.frame_idx += self.speed_choices[self.speed_i]

        if self.frame_idx >= self.n_frames - 1:
            self.frame_idx = self.n_frames - 1
            self.paused = True

    # ---------------------------
    # Mouse interactions
    # ---------------------------
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        self.hover_index = self._leaderboard_row_at(x, y)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        idx = self._leaderboard_row_at(x, y)
        if idx is None:
            return

        frame = self.frames[int(self.frame_idx)]
        ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])

        if 0 <= idx < len(ordered):
            self.selected_driver = ordered[idx][0]

    def _leaderboard_row_at(self, x: float, y: float):
        for idx, (l, b, r, t) in enumerate(self._lb_rects):
            if l <= x <= r and b <= y <= t:
                return idx
        return None

    # ---------------------------
    # Drawing
    # ---------------------------
    def on_draw(self):
        self.clear()

        frame = self.frames[int(self.frame_idx)]

        # Track look (thick base + thin highlight)
        if len(self.track_pts_screen) >= 2:
            arcade.draw_line_strip(self.track_pts_screen, arcade.color.DIM_GRAY, 10)
            arcade.draw_line_strip(self.track_pts_screen, arcade.color.LIGHT_GRAY, 2)

        # Cars
        for drv, st in frame["drivers"].items():
            sx, sy = world_to_screen(
                st["x"], st["y"], self.world_scale, self.world_tx, self.world_ty
            )
            col = self.driver_colors.get(drv, arcade.color.WHITE)

            r = 6
            if self.selected_driver == drv:
                r = 8
                arcade.draw_circle_outline(sx, sy, 12, arcade.color.WHITE, 2)

            arcade.draw_circle_filled(sx, sy, r, col)

        # HUD
        t = frame["t"]
        speed = self.speed_choices[self.speed_i]
        status = "PAUSED" if self.paused else "PLAYING"
        self.hud_text.text = f"{status}  t={t:.2f}s  speed={speed}x  frame={int(self.frame_idx)}/{self.n_frames - 1}"
        self.hud_text.draw()
        self.help_text.draw()

        # UI panels
        self._draw_leaderboard(frame)
        self._draw_telemetry_panel(frame)

    def _draw_leaderboard(self, frame):
        # Panel background
        arcade.draw_lrbt_rectangle_filled(
            self.lb_x,
            self.lb_x + self.lb_w,
            self.lb_y,
            self.lb_y + self.lb_h,
            (18, 18, 18, 225),
        )
        arcade.draw_lrbt_rectangle_outline(
            self.lb_x,
            self.lb_x + self.lb_w,
            self.lb_y,
            self.lb_y + self.lb_h,
            arcade.color.DARK_GRAY,
            2,
        )

        # Order by position (P1..)
        ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])

        # Default selection = leader
        if self.selected_driver is None and ordered:
            self.selected_driver = ordered[0][0]

        # Lap header
        leader_lap = int(ordered[0][1].get("lap", 0)) if ordered else 0
        max_lap = max(int(st.get("lap", 0)) for _, st in ordered) if ordered else 0
        self.lb_title.text = f"Leaderboard   Lap {leader_lap}/{max_lap}"
        self.lb_title.draw()

        # Precompute progress + speed lists matching the ordered list (for interval gaps)
        prog_list = [float(st.get("progress", 0.0)) for _, st in ordered]
        spd_list_kmh = [float(st.get("speed", 0.0)) for _, st in ordered]

        # Build row rects for click detection
        self._lb_rects = []

        # Row start (top anchor)
        top_y = self.lb_y + self.lb_h - self.lb_title_h - 8

        # Columns (tuned for narrower leaderboard)
        x_text = self.lb_x + self.lb_padding
        x_gap = self.lb_x + self.lb_w - 108  # NEW: interval column (right-aligned)
        x_tyre = self.lb_x + self.lb_w - 64
        x_drs = self.lb_x + self.lb_w - 26

        for idx, (drv, st) in enumerate(ordered[:20]):
            row_top = top_y - idx * self.lb_row_h
            row_bottom = row_top - self.lb_row_h
            row_cy = (row_top + row_bottom) / 2

            # Save click rect
            self._lb_rects.append(
                (self.lb_x + 6, row_bottom, self.lb_x + self.lb_w - 6, row_top)
            )

            # Hover highlight
            if self.hover_index == idx:
                rect = arcade.XYWH(
                    (self.lb_x + self.lb_x + self.lb_w) / 2,
                    row_cy,
                    self.lb_w - 12,
                    self.lb_row_h - 2,
                )
                arcade.draw_rect_filled(rect, (255, 255, 255, 25))

            # Selected highlight
            if self.selected_driver == drv:
                rect = arcade.XYWH(
                    (self.lb_x + self.lb_x + self.lb_w) / 2,
                    row_cy,
                    self.lb_w - 12,
                    self.lb_row_h - 2,
                )
                arcade.draw_rect_filled(rect, (255, 255, 255, 45))

            # Driver text
            col = self.driver_colors.get(drv, arcade.color.WHITE)
            self.lb_rows[idx].text = f"{int(st['pos']):>2}. {drv}"
            self.lb_rows[idx].x = x_text
            self.lb_rows[idx].y = row_top - 4
            self.lb_rows[idx].color = col
            self.lb_rows[idx].draw()

            # Interval gap to car ahead (seconds), using avg speed of (ahead + this)
            if idx == 0:
                gap_str = "—"
            else:
                gap_m = max(0.0, prog_list[idx - 1] - prog_list[idx])

                spd_ahead_mps = max(spd_list_kmh[idx - 1] / 3.6, 1.0)
                spd_this_mps = max(spd_list_kmh[idx] / 3.6, 1.0)
                avg_speed_mps = max(0.5 * (spd_ahead_mps + spd_this_mps), 1.0)

                gap_s = gap_m / avg_speed_mps

                # Optional: avoid ugly "+0.0" flicker
                # if gap_s < 0.05:
                #     gap_s = 0.0

                gap_str = f"+{gap_s:.1f}"

            arcade.draw_text(
                gap_str,
                x_gap,
                row_cy - 7,
                arcade.color.LIGHT_GRAY,
                12,
                anchor_x="right",
            )

            # Tyre icon
            key = _compound_key(st.get("compound", None))
            tex = self.tyre_textures.get(key) or self.tyre_textures.get("unknown")
            if tex is not None:
                rect = arcade.XYWH(
                    x_tyre,
                    row_cy,
                    self.tyre_icon_size,
                    self.tyre_icon_size,
                )
                arcade.draw_texture_rect(rect=rect, texture=tex, angle=0, alpha=255)

            # DRS indicator dot
            drs_on = _drs_is_active(int(st.get("drs", 0)))
            drs_col = arcade.color.LIME_GREEN if drs_on else arcade.color.DARK_GRAY
            arcade.draw_circle_filled(x_drs, row_cy, 5, drs_col)

        # Clear unused rows
        for j in range(len(ordered), 20):
            self.lb_rows[j].text = ""

    def _draw_telemetry_panel(self, frame):
        if self.selected_driver is None:
            return
        if self.selected_driver not in frame["drivers"]:
            return

        st = frame["drivers"][self.selected_driver]

        arcade.draw_lrbt_rectangle_filled(
            self.tel_x,
            self.tel_x + self.tel_w,
            self.tel_y,
            self.tel_y + self.tel_h,
            (18, 18, 18, 225),
        )
        arcade.draw_lrbt_rectangle_outline(
            self.tel_x,
            self.tel_x + self.tel_w,
            self.tel_y,
            self.tel_y + self.tel_h,
            arcade.color.DARK_GRAY,
            2,
        )

        self.tel_title.text = f"{self.selected_driver}"
        self.tel_title.draw()

        speed = float(st.get("speed", 0.0))
        gear = int(st.get("gear", 0))
        drs = int(st.get("drs", 0))
        lap = int(st.get("lap", 0))
        pos = int(st.get("pos", 0))

        throttle = st.get("throttle", None)
        brake = st.get("brake", None)

        comp = st.get("compound", None)
        comp_key = _compound_key(comp).upper()

        lines = [
            f"P{pos}   Lap {lap}",
            f"Speed: {speed:.0f} km/h",
            f"Gear: {gear}",
            f"DRS: {'ON' if _drs_is_active(drs) else 'OFF'}",
            f"Tyre: {comp_key}",
            f"Thr: {float(throttle):.0f}%" if throttle is not None else "Thr: -",
            f"Brk: {float(brake):.0f}%" if brake is not None else "Brk: -",
        ]

        for i, text in enumerate(lines[: len(self.tel_lines)]):
            self.tel_lines[i].text = text
            self.tel_lines[i].draw()

    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.SPACE:
            self.paused = not self.paused
        elif symbol == arcade.key.R:
            self.frame_idx = 0.0
            self.paused = False
        elif symbol == arcade.key.UP:
            self.speed_i = min(self.speed_i + 1, len(self.speed_choices) - 1)
        elif symbol == arcade.key.DOWN:
            self.speed_i = max(self.speed_i - 1, 0)
        elif symbol == arcade.key.RIGHT:
            self.frame_idx = min(self.frame_idx + self.fps * 5, self.n_frames - 1)
        elif symbol == arcade.key.LEFT:
            self.frame_idx = max(self.frame_idx - self.fps * 5, 0)
