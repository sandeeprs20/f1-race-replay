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
        race_info=None,
        session_info=None,
    ):
        super().__init__(width, height, title)

        self.frames = frames
        self.n_frames = len(frames)

        self.track_x, self.track_y = track_xy

        # Avoid "self.scale" name collision with Arcade Window properties
        self.world_scale, self.world_tx, self.world_ty = transform

        self.driver_colors = driver_colors or {}
        self.fps = fps
        self.race_info = race_info or "Unknown Race"
        self.session_info = session_info or "Unknown Session"

        # Playback state
        self.frame_idx = 0.0
        self.paused = False
        self.speed_choices = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
        self.speed_i = 1
        self.show_ui = True  # Toggle for showing/hiding UI panels

        arcade.set_background_color(arcade.color.BLACK)

        # Precompute track polyline in screen coords (performance)
        self.track_pts_screen = []
        for x, y in zip(self.track_x, self.track_y):
            sx, sy = world_to_screen(
                float(x), float(y), self.world_scale, self.world_tx, self.world_ty
            )
            self.track_pts_screen.append((sx, sy))

        # HUD text - Lap and Race time (top left)
        self.lap_text = arcade.Text(
            "", 20, self.height - 25, arcade.color.WHITE, 16, bold=True
        )
        self.race_time_text = arcade.Text(
            "", 20, self.height - 48, arcade.color.LIGHT_GRAY, 13
        )

        self.help_text = arcade.Text(
            "[SPACE] Pause/Resume  [←/→] Rewind / Fast-Forward  [↑/↓] Speed ++/--  [R] Restart  [H] Hide/Show UI",
            20,
            20,
            arcade.color.LIGHT_GRAY,
            11,
        )

        # ---------------------------
        # Leaderboard layout (right)
        # ---------------------------
        self.lb_w = 400
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
        # Compact Weather box (top left, below lap info)
        # ---------------------------
        self.compact_weather_w = 190
        self.compact_weather_h = 145
        self.compact_weather_x = 20
        self.compact_weather_y = self.height - 220

        self.compact_weather_title = arcade.Text(
            "Weather",
            self.compact_weather_x + 10,
            self.compact_weather_y + self.compact_weather_h - 10,
            arcade.color.WHITE,
            14,
            bold=True,
            anchor_x="left",
            anchor_y="top",
        )
        self.compact_weather_lines = [
            arcade.Text(
                "",
                self.compact_weather_x + 10,
                self.compact_weather_y + self.compact_weather_h - 35 - i * 20,
                arcade.color.LIGHT_GRAY,
                11,
                anchor_x="left",
                anchor_y="top",
            )
            for i in range(5)
        ]

        # ---------------------------
        # Multiple compact driver telemetry boxes (left side, stacked)
        # ---------------------------
        self.driver_box_w = 270
        self.driver_box_h = 170
        self.max_driver_boxes = 1  # Show only selected driver

        # Create text objects for each driver box
        self.driver_boxes = []
        for i in range(self.max_driver_boxes):
            box = {
                "title": arcade.Text(
                    "",
                    0,
                    0,
                    arcade.color.WHITE,
                    16,
                    bold=True,
                    anchor_x="left",
                    anchor_y="top",
                ),
                "lines": [
                    arcade.Text(
                        "",
                        0,
                        0,
                        arcade.color.LIGHT_GRAY,
                        13,
                        anchor_x="left",
                        anchor_y="top",
                    )
                    for _ in range(5)
                ],
                "throttle_pct": arcade.Text(
                    "", 0, 0, arcade.color.WHITE, 8, bold=True, anchor_x="center"
                ),
                "brake_pct": arcade.Text(
                    "", 0, 0, arcade.color.WHITE, 8, bold=True, anchor_x="center"
                ),
            }
            self.driver_boxes.append(box)

        # Interval gap text objects (20 for leaderboard rows)
        self.gap_texts = [
            arcade.Text(
                "",
                0,
                0,
                arcade.color.LIGHT_GRAY,
                12,
                anchor_x="right",
            )
            for _ in range(20)
        ]

        # Load weather icons for compact display
        weather_dir = os.path.join(base_dir, "images", "weather")
        self.weather_textures = {}
        for name in ["clear", "rain", "cloudy"]:
            path = os.path.join(weather_dir, f"{name}.png")
            if os.path.exists(path):
                self.weather_textures[name] = arcade.load_texture(path)
        self.weather_icon_size = 24

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

        # Track look (enhanced multi-layer racing line)
        if len(self.track_pts_screen) >= 2:
            # Outer glow (subtle depth effect)
            arcade.draw_line_strip(self.track_pts_screen, (40, 40, 45), 16)
            # Base layer (dark foundation)
            arcade.draw_line_strip(self.track_pts_screen, (25, 25, 30), 12)
            # Mid layer (provides depth)
            arcade.draw_line_strip(self.track_pts_screen, (80, 80, 90), 6)
            # Highlight line (crisp center line)
            arcade.draw_line_strip(self.track_pts_screen, (220, 220, 230), 2)

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

        # HUD - Lap counter and race time
        # Calculate current lap from leader
        ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])
        leader_lap = int(ordered[0][1].get("lap", 1)) if ordered else 1
        max_lap = max(int(st.get("lap", 1)) for _, st in ordered) if ordered else 1

        self.lap_text.text = f"Lap: {leader_lap}/{max_lap}"
        speed = self.speed_choices[self.speed_i]
        t = frame["t"]
        minutes = int(t // 60)
        seconds = int(t % 60)
        self.race_time_text.text = f"Race Time: {minutes:02d}:{seconds:02d} (x{speed})"

        self.lap_text.draw()
        self.race_time_text.draw()
        self.help_text.draw()

        # UI panels (can be toggled off)
        if self.show_ui:
            self._draw_leaderboard(frame)
            self._draw_compact_weather(frame)
            self._draw_driver_boxes(frame)
            self._draw_progress_bar(frame)

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
        self.lb_title.text = f"Leaderboard"
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
                gap_str = "LEADER"
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

            self.gap_texts[idx].text = gap_str
            self.gap_texts[idx].x = x_gap
            self.gap_texts[idx].y = row_cy - 7
            self.gap_texts[idx].draw()

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
            self.gap_texts[j].text = ""

    def _draw_compact_weather(self, frame):
        # Compact weather box background
        arcade.draw_lrbt_rectangle_filled(
            self.compact_weather_x,
            self.compact_weather_x + self.compact_weather_w,
            self.compact_weather_y,
            self.compact_weather_y + self.compact_weather_h,
            (20, 20, 24, 230),
        )
        arcade.draw_lrbt_rectangle_outline(
            self.compact_weather_x,
            self.compact_weather_x + self.compact_weather_w,
            self.compact_weather_y,
            self.compact_weather_y + self.compact_weather_h,
            (80, 80, 90),
            2,
        )

        self.compact_weather_title.draw()

        # Get weather data
        weather = frame.get("weather", {})
        track_temp = weather.get("TrackTemp", 0)
        air_temp = weather.get("AirTemp", 0)
        humidity = weather.get("Humidity", 0)
        rainfall = weather.get("Rainfall", False)
        wind_speed = weather.get("WindSpeed", 0) if "WindSpeed" in weather else 0

        # Weather icon
        icon_key = "rain" if rainfall else ("cloudy" if humidity > 70 else "clear")
        tex = self.weather_textures.get(icon_key)
        if tex is not None:
            icon_x = (
                self.compact_weather_x
                + self.compact_weather_w
                - self.weather_icon_size
                - 10
            )
            icon_y = (
                self.compact_weather_y
                + self.compact_weather_h
                - self.weather_icon_size
                - 8
            )
            rect = arcade.XYWH(
                icon_x, icon_y, self.weather_icon_size, self.weather_icon_size
            )
            arcade.draw_texture_rect(rect=rect, texture=tex, angle=0, alpha=255)

        # Weather info
        lines = [
            f"🌡️ Track: {track_temp:.1f}°C" if track_temp > 0 else "🌡️ Track: --",
            f"🌡️ Air: {air_temp:.1f}°C" if air_temp > 0 else "🌡️ Air: --",
            f"💧 Humidity: {humidity:.0f}%" if humidity > 0 else "💧 Humidity: --",
            f"💨 Wind: {wind_speed:.1f} km/h S" if wind_speed > 0 else "💨 Wind: --",
            f"🌧️ Rain: {'DRY' if not rainfall else 'WET'}",
        ]

        for i, text in enumerate(lines):
            self.compact_weather_lines[i].text = text
            self.compact_weather_lines[i].draw()

    def _draw_driver_boxes(self, frame):
        # Only show selected driver's telemetry
        if self.selected_driver is None:
            # Default to leader if none selected
            ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])
            if ordered:
                self.selected_driver = ordered[0][0]
            else:
                return

        if self.selected_driver not in frame["drivers"]:
            return

        # Get selected driver data
        st = frame["drivers"][self.selected_driver]
        drv = self.selected_driver
        box = self.driver_boxes[0]

        # Get all drivers ordered by position for gap calculations
        ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])
        driver_idx = next((i for i, (d, _) in enumerate(ordered) if d == drv), -1)

        # Calculate box position (below weather)
        box_x = self.compact_weather_x
        box_y = self.compact_weather_y - self.driver_box_h - 10

        # Driver color
        driver_col = self.driver_colors.get(drv, arcade.color.WHITE)

        # Box background
        arcade.draw_lrbt_rectangle_filled(
            box_x,
            box_x + self.driver_box_w,
            box_y,
            box_y + self.driver_box_h,
            (20, 20, 24, 230),
        )

        # Colored left border
        arcade.draw_lrbt_rectangle_filled(
            box_x,
            box_x + 4,
            box_y,
            box_y + self.driver_box_h,
            driver_col,
        )

        # Box outline
        arcade.draw_lrbt_rectangle_outline(
            box_x,
            box_x + self.driver_box_w,
            box_y,
            box_y + self.driver_box_h,
            (80, 80, 90),
            2,
        )

        # Driver info
        speed = float(st.get("speed", 0.0))
        gear = int(st.get("gear", 0))
        drs = int(st.get("drs", 0))
        pos = int(st.get("pos", 0))

        throttle_val = min(max(float(st.get("throttle", 0)), 0.0), 100.0)
        # Brake can be 0-100 percentage or boolean (0/1), normalize to 0-100
        raw_brake = float(st.get("brake", 0))
        brake_val = min(
            max(raw_brake * 100.0 if raw_brake <= 1.0 else raw_brake, 0.0), 100.0
        )

        # Calculate gaps
        prog_list = [float(s.get("progress", 0)) for _, s in ordered]
        spd_list = [float(s.get("speed", 1)) for _, s in ordered]

        gap_ahead = ""
        gap_behind = ""
        ahead_driver = ""
        behind_driver = ""

        if driver_idx > 0:
            ahead_driver = ordered[driver_idx - 1][0]
            gap_m = max(0.0, prog_list[driver_idx - 1] - prog_list[driver_idx])
            spd_ahead = max(spd_list[driver_idx - 1] / 3.6, 1.0)
            spd_this = max(spd_list[driver_idx] / 3.6, 1.0)
            avg_spd = max(0.5 * (spd_ahead + spd_this), 1.0)
            gap_s = gap_m / avg_spd
            gap_ahead = f"+{gap_s:.1f}s"

        if driver_idx < len(ordered) - 1:
            behind_driver = ordered[driver_idx + 1][0]
            gap_m = max(0.0, prog_list[driver_idx] - prog_list[driver_idx + 1])
            spd_behind = max(spd_list[driver_idx + 1] / 3.6, 1.0)
            spd_this = max(spd_list[driver_idx] / 3.6, 1.0)
            avg_spd = max(0.5 * (spd_behind + spd_this), 1.0)
            gap_s = gap_m / avg_spd
            gap_behind = f"-{gap_s:.1f}s"
            # Title
            box["title"].text = f"Driver: {drv}"
            box["title"].color = driver_col
            box["title"].x = box_x + 15
            box["title"].y = box_y + self.driver_box_h - 10
            box["title"].draw()

            # Info lines
            lines = [
                f"Speed: {speed:.0f} km/h",
                f"Gear: {gear}",
                f"DRS: {'OFF' if not _drs_is_active(drs) else 'ON'}",
                f"Ahead: {gap_ahead}" if gap_ahead else "Ahead: N/A",
                f"Behind: {gap_behind}" if gap_behind else "Behind: N/A",
            ]

            for i, text in enumerate(lines):
                box["lines"][i].text = text
                box["lines"][i].x = box_x + 15
                box["lines"][i].y = box_y + self.driver_box_h - 35 - i * 24
                box["lines"][i].draw()

            # Throttle and brake bars (vertical, on the right)
            bar_w = 35
            bar_h = 120
            bar_x = box_x + self.driver_box_w - 110
            bar_y = box_y + 20

            # Throttle bar (green)
            arcade.draw_lrbt_rectangle_filled(
                bar_x,
                bar_x + bar_w,
                bar_y,
                bar_y + bar_h,
                (30, 30, 35),
            )
            if throttle_val > 0:
                fill_h = (throttle_val / 100.0) * bar_h
                green_intensity = min(int(100 + (throttle_val / 100.0) * 155), 255)
                arcade.draw_lrbt_rectangle_filled(
                    bar_x,
                    bar_x + bar_w,
                    bar_y,
                    bar_y + fill_h,
                    (0, green_intensity, 50),
                )
            arcade.draw_lrbt_rectangle_outline(
                bar_x,
                bar_x + bar_w,
                bar_y,
                bar_y + bar_h,
                (80, 80, 90),
                1,
            )

            # Throttle label
            box["throttle_pct"].text = "THR"
            box["throttle_pct"].x = bar_x + bar_w / 2
            box["throttle_pct"].y = bar_y + bar_h + 8
            box["throttle_pct"].draw()

            # Brake bar (red)
            brake_x = bar_x + bar_w + 15
            arcade.draw_lrbt_rectangle_filled(
                brake_x,
                brake_x + bar_w,
                bar_y,
                bar_y + bar_h,
                (30, 30, 35),
            )
            if brake_val > 0:
                fill_h = (brake_val / 100.0) * bar_h
                red_intensity = min(int(150 + (brake_val / 100.0) * 105), 255)
                arcade.draw_lrbt_rectangle_filled(
                    brake_x,
                    brake_x + bar_w,
                    bar_y,
                    bar_y + fill_h,
                    (red_intensity, 30, 30),
                )
            arcade.draw_lrbt_rectangle_outline(
                brake_x,
                brake_x + bar_w,
                bar_y,
                bar_y + bar_h,
                (80, 80, 90),
                1,
            )

            # Brake label
            box["brake_pct"].text = "BRK"
            box["brake_pct"].x = brake_x + bar_w / 2
            box["brake_pct"].y = bar_y + bar_h + 8
            box["brake_pct"].draw()

    def _draw_progress_bar(self, frame):
        # Progress bar at bottom showing race progress
        bar_w = self.width - 40
        bar_h = 8
        bar_x = 20
        bar_y = 50

        # Background
        arcade.draw_lrbt_rectangle_filled(
            bar_x,
            bar_x + bar_w,
            bar_y,
            bar_y + bar_h,
            (40, 40, 45),
        )

        # Progress fill
        progress = self.frame_idx / max(self.n_frames - 1, 1)
        fill_w = progress * bar_w

        # Gradient from green to yellow to red
        if progress < 0.5:
            color = (int(progress * 2 * 255), 200, 50)
        else:
            color = (255, int((1 - progress) * 2 * 200), 50)

        arcade.draw_lrbt_rectangle_filled(
            bar_x,
            bar_x + fill_w,
            bar_y,
            bar_y + bar_h,
            color,
        )

        # Border
        arcade.draw_lrbt_rectangle_outline(
            bar_x,
            bar_x + bar_w,
            bar_y,
            bar_y + bar_h,
            (100, 100, 105),
            2,
        )

    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.SPACE:
            self.paused = not self.paused
        elif symbol == arcade.key.R:
            self.frame_idx = 0.0
            self.paused = False
        elif symbol == arcade.key.H:
            self.show_ui = not self.show_ui
        elif symbol == arcade.key.UP:
            self.speed_i = min(self.speed_i + 1, len(self.speed_choices) - 1)
        elif symbol == arcade.key.DOWN:
            self.speed_i = max(self.speed_i - 1, 0)
        elif symbol == arcade.key.RIGHT:
            self.frame_idx = min(self.frame_idx + self.fps * 5, self.n_frames - 1)
        elif symbol == arcade.key.LEFT:
            self.frame_idx = max(self.frame_idx - self.fps * 5, 0)
