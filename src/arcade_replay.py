import arcade
from src.track import world_to_screen


def _short_compound(compound: str | None) -> str:
    """
    Convert FastF1 compound strings to short labels.
    Examples: SOFT->S, MEDIUM->M, HARD->H, INTERMEDIATE->I, WET->W
    """
    if not compound:
        return "-"
    c = compound.strip().upper()
    if c.startswith("SOFT"):
        return "S"
    if c.startswith("MED"):
        return "M"
    if c.startswith("HARD"):
        return "H"
    if c.startswith("INTER"):
        return "I"
    if c.startswith("WET"):
        return "W"
    # fallback: first letter
    return c[:1]


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

        # Avoid "self.scale" collision (Arcade has a read-only property named scale)
        self.world_scale, self.world_tx, self.world_ty = transform

        self.driver_colors = driver_colors or {}
        self.fps = fps

        # Playback state
        self.frame_idx = 0.0
        self.paused = False
        self.speed_choices = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
        self.speed_i = 1

        arcade.set_background_color(arcade.color.BLACK)

        # Precompute track polyline in screen coords (performance)
        self.track_pts_screen = []
        for x, y in zip(self.track_x, self.track_y):
            sx, sy = world_to_screen(
                float(x), float(y), self.world_scale, self.world_tx, self.world_ty
            )
            self.track_pts_screen.append((sx, sy))

        # HUD text objects (fast vs draw_text)
        self.hud_text = arcade.Text("", 20, self.height - 30, arcade.color.WHITE, 14)
        self.help_text = arcade.Text(
            "Controls: Space=Pause  Up/Down=Speed  Left/Right=Seek  R=Restart",
            20,
            20,
            arcade.color.LIGHT_GRAY,
            12,
        )

        # ---------------------------
        # Leaderboard panel layout
        # ---------------------------
        self.lb_w = 320
        self.lb_h = self.height - 140
        self.lb_x = self.width - self.lb_w - 30
        self.lb_y = 70

        self.lb_padding = 14
        self.lb_title_h = 34
        self.lb_row_h = 24

        self.hover_index = None
        self.selected_driver = None

        self.lb_title = arcade.Text(
            "Leaderboard",
            self.lb_x + self.lb_padding,
            self.lb_y + self.lb_h - self.lb_title_h,
            arcade.color.WHITE,
            16,
        )

        # Pre-create row text objects (20 drivers max)
        self.lb_rows = [
            arcade.Text("", 0, 0, arcade.color.WHITE, 14) for _ in range(20)
        ]

        # ---------------------------
        # Telemetry panel (left)
        # ---------------------------
        self.tel_w = 360
        self.tel_h = 260
        self.tel_x = 30
        self.tel_y = self.height - self.tel_h - 60

        self.tel_title = arcade.Text(
            "", self.tel_x + 12, self.tel_y + self.tel_h - 32, arcade.color.WHITE, 16
        )
        self.tel_lines = [
            arcade.Text(
                "",
                self.tel_x + 12,
                self.tel_y + self.tel_h - 62 - i * 20,
                arcade.color.LIGHT_GRAY,
                12,
            )
            for i in range(9)
        ]

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
        if not (
            self.lb_x <= x <= self.lb_x + self.lb_w
            and self.lb_y <= y <= self.lb_y + self.lb_h
        ):
            return None

        # Row area starts below title
        row_top = self.lb_y + self.lb_h - self.lb_title_h - 8
        row_bottom = self.lb_y + self.lb_padding

        if y > row_top or y < row_bottom:
            return None

        idx = int((row_top - y) / self.lb_row_h)
        if idx < 0 or idx >= 20:
            return None
        return idx

    # ---------------------------
    # Drawing
    # ---------------------------
    def on_draw(self):
        self.clear()

        frame = self.frames[int(self.frame_idx)]

        # Track style (thick base + thin highlight)
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

        # Leaderboard panel
        self._draw_leaderboard(frame)

        # Telemetry panel (selected driver)
        self._draw_telemetry_panel(frame)

    def _draw_leaderboard(self, frame):
        # Background + border
        arcade.draw_lrbt_rectangle_filled(
            self.lb_x,
            self.lb_x + self.lb_w,
            self.lb_y,
            self.lb_y + self.lb_h,
            (20, 20, 20, 220),
        )
        arcade.draw_lrbt_rectangle_outline(
            self.lb_x,
            self.lb_x + self.lb_w,
            self.lb_y,
            self.lb_y + self.lb_h,
            arcade.color.DARK_GRAY,
            2,
        )

        ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])

        # Default selection to leader
        if self.selected_driver is None and len(ordered) > 0:
            self.selected_driver = ordered[0][0]

        # Lap count (leader lap vs max lap visible)
        leader_lap = int(ordered[0][1].get("lap", 0)) if ordered else 0
        max_lap = max(int(st.get("lap", 0)) for _, st in ordered) if ordered else 0
        self.lb_title.text = f"Leaderboard   Lap {leader_lap}/{max_lap}"
        self.lb_title.draw()

        # Rows region
        row_top = self.lb_y + self.lb_h - self.lb_title_h - 10

        # Column positions inside panel
        x_pos = self.lb_x + self.lb_padding
        x_code = x_pos + 70
        x_tyre = self.lb_x + self.lb_w - 70
        x_drs = self.lb_x + self.lb_w - 28

        for idx, (drv, st) in enumerate(ordered[:20]):
            y = row_top - (idx + 1) * self.lb_row_h

            # Hover highlight
            if self.hover_index == idx:
                arcade.draw_lrbt_rectangle_filled(
                    self.lb_x + 6,
                    self.lb_x + self.lb_w - 6,
                    y - 2,
                    y + self.lb_row_h - 2,
                    (255, 255, 255, 25),
                )

            # Selected highlight
            if self.selected_driver == drv:
                arcade.draw_lrbt_rectangle_filled(
                    self.lb_x + 6,
                    self.lb_x + self.lb_w - 6,
                    y - 2,
                    y + self.lb_row_h - 2,
                    (255, 255, 255, 45),
                )

            # Text row: " 1. VER"
            col = self.driver_colors.get(drv, arcade.color.WHITE)
            self.lb_rows[idx].text = f"{int(st['pos']):>2}. {drv}"
            self.lb_rows[idx].x = x_pos
            self.lb_rows[idx].y = y
            self.lb_rows[idx].color = col
            self.lb_rows[idx].draw()

            # Tyre compound label
            comp = _short_compound(st.get("compound", None))
            arcade.draw_text(
                comp,
                x_tyre,
                y,
                col,
                14,
            )

            # DRS indicator dot
            drs_on = int(st.get("drs", 0)) == 1
            drs_color = arcade.color.LIME_GREEN if drs_on else arcade.color.DARK_GRAY
            arcade.draw_circle_filled(x_drs, y + 8, 5, drs_color)

        # Clear unused row texts
        for j in range(len(ordered), 20):
            self.lb_rows[j].text = ""

    def _draw_telemetry_panel(self, frame):
        if self.selected_driver is None or self.selected_driver not in frame["drivers"]:
            return

        st = frame["drivers"][self.selected_driver]

        # Panel bg
        arcade.draw_lrbt_rectangle_filled(
            self.tel_x,
            self.tel_x + self.tel_w,
            self.tel_y,
            self.tel_y + self.tel_h,
            (20, 20, 20, 220),
        )
        arcade.draw_lrbt_rectangle_outline(
            self.tel_x,
            self.tel_x + self.tel_w,
            self.tel_y,
            self.tel_y + self.tel_h,
            arcade.color.DARK_GRAY,
            2,
        )

        self.tel_title.text = f"Driver: {self.selected_driver}"
        self.tel_title.draw()

        speed = float(st.get("speed", 0.0))
        gear = int(st.get("gear", 0))
        drs = int(st.get("drs", 0))
        lap = int(st.get("lap", 0))
        pos = int(st.get("pos", 0))
        comp = _short_compound(st.get("compound", None))

        throttle = st.get("throttle", None)
        brake = st.get("brake", None)

        lines = [
            f"Position: {pos}",
            f"Lap: {lap}",
            f"Tyre: {comp}",
            f"Speed: {speed:.1f} km/h",
            f"Gear: {gear}",
            f"DRS: {'ON' if drs == 1 else 'OFF'}",
            f"Throttle: {float(throttle):.0f}%"
            if throttle is not None
            else "Throttle: -",
            f"Brake: {float(brake):.0f}%" if brake is not None else "Brake: -",
        ]

        for i, text in enumerate(lines[: len(self.tel_lines)]):
            self.tel_lines[i].text = text
            self.tel_lines[i].draw()

    # ---------------------------
    # Keyboard
    # ---------------------------
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
