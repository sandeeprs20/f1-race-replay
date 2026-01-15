import os
import arcade
from src.track import world_to_screen

# ================================
# F1 TV BROADCAST STYLE PALETTE
# ================================
# Official F1 colors
F1_RED = (225, 6, 0)           # Official F1 red
F1_BLACK = (21, 21, 30)        # Near-black background
F1_DARK_GRAY = (38, 38, 48)    # Panel backgrounds
F1_GRAY = (68, 68, 78)         # Secondary elements
F1_WHITE = (255, 255, 255)     # Primary text
F1_LIGHT_GRAY = (180, 180, 185)  # Secondary text

# Position colors (podium)
P1_GOLD = (255, 215, 0)
P2_SILVER = (192, 192, 200)
P3_BRONZE = (205, 127, 50)

# Status colors
DRS_GREEN = (0, 210, 80)
FASTEST_PURPLE = (170, 0, 255)
INTERVAL_YELLOW = (255, 210, 0)

# Panel colors
PANEL_BG = (28, 28, 38, 240)
PANEL_BG_ALT = (38, 38, 50, 240)


def draw_rounded_rectangle(x, y, width, height, color, radius=10):
    """Draw a filled rectangle with rounded corners."""
    radius = max(0, min(radius, width / 2, height / 2))
    if radius <= 0:
        arcade.draw_lrbt_rectangle_filled(x, x + width, y, y + height, color)
        return
    # Draw main body rectangles
    arcade.draw_lrbt_rectangle_filled(x + radius, x + width - radius, y, y + height, color)
    arcade.draw_lrbt_rectangle_filled(x, x + width, y + radius, y + height - radius, color)
    # Draw corner circles
    arcade.draw_circle_filled(x + radius, y + radius, radius, color)
    arcade.draw_circle_filled(x + width - radius, y + radius, radius, color)
    arcade.draw_circle_filled(x + radius, y + height - radius, radius, color)
    arcade.draw_circle_filled(x + width - radius, y + height - radius, radius, color)


def draw_rounded_rectangle_outline(x, y, width, height, color, radius=10, line_width=1):
    """Draw a rectangle outline with rounded corners."""
    radius = max(0, min(radius, width / 2, height / 2))
    if radius <= 0:
        arcade.draw_lrbt_rectangle_outline(x, x + width, y, y + height, color, line_width)
        return
    # Draw straight lines
    arcade.draw_line(x + radius, y, x + width - radius, y, color, line_width)  # Bottom
    arcade.draw_line(x + radius, y + height, x + width - radius, y + height, color, line_width)  # Top
    arcade.draw_line(x, y + radius, x, y + height - radius, color, line_width)  # Left
    arcade.draw_line(x + width, y + radius, x + width, y + height - radius, color, line_width)  # Right
    # Draw corner arcs
    arcade.draw_arc_outline(x + radius, y + radius, radius * 2, radius * 2, color, 180, 270, line_width)
    arcade.draw_arc_outline(x + width - radius, y + radius, radius * 2, radius * 2, color, 270, 360, line_width)
    arcade.draw_arc_outline(x + radius, y + height - radius, radius * 2, radius * 2, color, 90, 180, line_width)
    arcade.draw_arc_outline(x + width - radius, y + height - radius, radius * 2, radius * 2, color, 0, 90, line_width)


def draw_f1_panel(x, y, width, height, radius=4, show_red_accent=True):
    """Draw an F1 broadcast style panel with optional red accent line."""
    # Main panel background
    draw_rounded_rectangle(x, y, width, height, PANEL_BG, radius)
    # Red accent line on top (F1 signature style)
    if show_red_accent:
        arcade.draw_lrbt_rectangle_filled(x, x + width, y + height - 3, y + height, F1_RED)


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
        total_laps=None,
        driver_status=None,
        fullscreen=False,
    ):
        super().__init__(width, height, title, resizable=True, fullscreen=fullscreen)

        self.frames = frames
        self.n_frames = len(frames)

        self.track_x, self.track_y = track_xy

        # Avoid "self.scale" name collision with Arcade Window properties
        self.world_scale, self.world_tx, self.world_ty = transform

        self.driver_colors = driver_colors or {}
        self.fps = fps
        self.race_info = race_info or "Unknown Race"
        self.session_info = session_info or "Unknown Session"
        self.total_laps = total_laps  # Total laps in race (None for non-race)
        self.driver_status = driver_status or {}  # Driver finishing status from results

        # Playback state
        self.frame_idx = 0.0
        self.paused = False
        self.speed_choices = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
        self.speed_i = 1
        self.show_ui = True  # Toggle for showing/hiding UI panels
        self.show_progress_bar = True  # Toggle for progress bar

        # Track fastest lap driver
        self.fastest_lap_driver = None
        self.fastest_lap_time = float("inf")

        arcade.set_background_color(F1_BLACK)

        # Precompute track polyline in screen coords (performance)
        self.track_pts_screen = []
        for x, y in zip(self.track_x, self.track_y):
            sx, sy = world_to_screen(
                float(x), float(y), self.world_scale, self.world_tx, self.world_ty
            )
            self.track_pts_screen.append((sx, sy))

        # HUD text - Grand Prix / Session info (top center)
        self.gp_title_text = arcade.Text(
            self.race_info,
            self.width // 2,
            self.height - 20,
            F1_WHITE,
            18,
            bold=True,
            anchor_x="center",
            anchor_y="top",
        )
        self.session_text = arcade.Text(
            self.session_info,
            self.width // 2,
            self.height - 42,
            F1_RED,
            14,
            bold=True,
            anchor_x="center",
            anchor_y="top",
        )

        # Lap and Race time (top left)
        self.lap_text = arcade.Text(
            "", 20, self.height - 25, F1_WHITE, 16, bold=True
        )
        self.race_time_text = arcade.Text(
            "", 20, self.height - 48, F1_LIGHT_GRAY, 13
        )

        # Controls text (bottom left, multi-line)
        self.controls_text = arcade.Text(
            "CONTROLS\n[SPACE] Pause/Play\n[←/→] Seek 5s\n[↑/↓] Speed\n[R] Restart\n[H] Toggle UI\n[P] Progress Bar\n[F] Fullscreen",
            20,
            170,
            F1_LIGHT_GRAY,
            11,
            multiline=True,
            width=200,
        )

        # ---------------------------
        # Leaderboard layout (right side)
        # ---------------------------
        self.lb_w = 300
        self.lb_h = self.height - 120
        self.lb_x = self.width - self.lb_w - 20
        self.lb_y = 50

        self.lb_padding = 12
        self.lb_title_h = 32
        self.lb_row_h = 25
        self.lb_radius = 12  # Rounded corner radius

        self.hover_index = None
        self.selected_driver = None

        self.lb_title = arcade.Text(
            "LEADERBOARD",
            self.lb_x + self.lb_padding,
            self.lb_y + self.lb_h - 10,
            F1_WHITE,
            16,
            bold=True,
            anchor_x="left",
            anchor_y="top",
        )

        # We'll reuse these text objects (positions updated each draw)
        self.lb_rows = [
            arcade.Text(
                "",
                0,
                0,
                F1_WHITE,
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
        self.weather_w = 180
        self.weather_h = 140
        self.weather_x = 20
        self.weather_y = self.height - 210
        self.weather_radius = 10  # Rounded corner radius

        self.weather_title = arcade.Text(
            "WEATHER",
            self.weather_x + 12,
            self.weather_y + self.weather_h - 12,
            F1_WHITE,
            13,
            bold=True,
            anchor_x="left",
            anchor_y="top",
        )
        self.weather_lines = [
            arcade.Text(
                "",
                self.weather_x + 12,
                self.weather_y + self.weather_h - 35 - i * 20,
                F1_LIGHT_GRAY,
                10,
                anchor_x="left",
                anchor_y="top",
            )
            for i in range(5)
        ]

        # ---------------------------
        # Driver telemetry box (left side, below weather)
        # ---------------------------
        self.driver_box_w = 250
        self.driver_box_h = 160
        self.driver_box_radius = 10  # Rounded corner radius
        self.max_driver_boxes = 1  # Show only selected driver

        # Create text objects for each driver box
        self.driver_boxes = []
        for i in range(self.max_driver_boxes):
            box = {
                "title": arcade.Text(
                    "",
                    0,
                    0,
                    F1_WHITE,
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
                        F1_LIGHT_GRAY,
                        13,
                        anchor_x="left",
                        anchor_y="top",
                    )
                    for _ in range(5)
                ],
                "throttle_pct": arcade.Text(
                    "", 0, 0, DRS_GREEN, 8, bold=True, anchor_x="center"
                ),
                "brake_pct": arcade.Text(
                    "", 0, 0, F1_RED, 8, bold=True, anchor_x="center"
                ),
            }
            self.driver_boxes.append(box)

        # Interval gap text objects (20 for leaderboard rows)
        self.gap_texts = [
            arcade.Text(
                "",
                0,
                0,
                F1_LIGHT_GRAY,
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

        # Check if clicked on progress bar
        if self.show_progress_bar and hasattr(self, "_progress_bar_rect"):
            bar_x, bar_y, bar_x2, bar_y2 = self._progress_bar_rect
            if bar_x <= x <= bar_x2 and bar_y <= y <= bar_y2:
                # Calculate which frame to jump to
                progress = (x - bar_x) / (bar_x2 - bar_x)
                self.frame_idx = progress * (self.n_frames - 1)
                self.frame_idx = max(0, min(self.frame_idx, self.n_frames - 1))
                return

        # Check leaderboard clicks
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

        # Track - F1 broadcast style (clean, professional)
        if len(self.track_pts_screen) >= 2:
            # Track shadow/outline
            arcade.draw_line_strip(self.track_pts_screen, (30, 30, 35), 12)
            # Main track surface
            arcade.draw_line_strip(self.track_pts_screen, (55, 55, 60), 8)
            # Racing line
            arcade.draw_line_strip(self.track_pts_screen, (100, 100, 105), 3)
            # Center line
            arcade.draw_line_strip(self.track_pts_screen, (140, 140, 145), 1)

        # Cars - clean F1 broadcast style
        for drv, st in frame["drivers"].items():
            sx, sy = world_to_screen(
                st["x"], st["y"], self.world_scale, self.world_tx, self.world_ty
            )
            col = self.driver_colors.get(drv, arcade.color.WHITE)

            r = 6
            if self.selected_driver == drv:
                r = 8
                # Selected driver highlight ring
                arcade.draw_circle_outline(sx, sy, 12, F1_WHITE, 2)

            # Car dot with team color
            arcade.draw_circle_filled(sx, sy, r, col)
            # Small white highlight
            arcade.draw_circle_filled(sx - 1, sy + 1, 2, (255, 255, 255, 120))

        # HUD - Lap counter and race time
        # Calculate current lap from leader
        ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])
        leader_lap = int(ordered[0][1].get("lap", 1)) if ordered else 1

        # Use total_laps if available, otherwise use max lap from current frame
        if self.total_laps:
            display_total = self.total_laps
        else:
            display_total = max(int(st.get("lap", 1)) for _, st in ordered) if ordered else 1

        # Track fastest lap (check all drivers' lap times in current frame)
        for drv, st in frame["drivers"].items():
            lap_time = st.get("lap_time", None)
            if lap_time and lap_time > 0:
                if lap_time < self.fastest_lap_time:
                    self.fastest_lap_time = lap_time
                    self.fastest_lap_driver = drv

        self.lap_text.text = f"LAP {leader_lap}/{display_total}"
        speed = self.speed_choices[self.speed_i]
        t = frame["t"]
        minutes = int(t // 60)
        seconds = int(t % 60)
        self.race_time_text.text = f"Race Time: {minutes:02d}:{seconds:02d} (x{speed})"

        # Draw GP/Session info at top center
        self.gp_title_text.draw()
        self.session_text.draw()

        # Draw lap and race time (top left)
        self.lap_text.draw()
        self.race_time_text.draw()

        # UI panels (can be toggled off)
        if self.show_ui:
            self._draw_leaderboard(frame)
            self._draw_weather(frame)
            self._draw_driver_boxes(frame)
            # Draw controls at bottom left
            self.controls_text.draw()

        # Progress bar (separate toggle)
        if self.show_progress_bar:
            self._draw_progress_bar(frame)

    def _draw_leaderboard(self, frame):
        # F1 Broadcast style panel with red accent
        draw_f1_panel(self.lb_x, self.lb_y, self.lb_w, self.lb_h, 4)

        # Order by position (P1..)
        ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])

        # Default selection = leader
        if self.selected_driver is None and ordered:
            self.selected_driver = ordered[0][0]

        # Title
        self.lb_title.text = "LEADERBOARD"
        self.lb_title.draw()

        # Precompute progress + speed lists matching the ordered list (for interval gaps)
        prog_list = [float(st.get("progress", 0.0)) for _, st in ordered]
        spd_list_kmh = [float(st.get("speed", 0.0)) for _, st in ordered]

        # Build row rects for click detection
        self._lb_rects = []

        # Row start (top anchor)
        top_y = self.lb_y + self.lb_h - self.lb_title_h - 8

        # Columns
        x_text = self.lb_x + self.lb_padding
        x_gap = self.lb_x + self.lb_w - 90
        x_tyre = self.lb_x + self.lb_w - 52
        x_drs = self.lb_x + self.lb_w - 20

        for idx, (drv, st) in enumerate(ordered[:20]):
            row_top = top_y - idx * self.lb_row_h
            row_bottom = row_top - self.lb_row_h
            row_cy = (row_top + row_bottom) / 2

            # Save click rect
            self._lb_rects.append(
                (self.lb_x + 6, row_bottom, self.lb_x + self.lb_w - 6, row_top)
            )

            # F1 broadcast style row backgrounds
            pos = int(st["pos"])

            # Alternating row backgrounds for readability
            if idx % 2 == 0:
                row_bg = (35, 35, 45, 200)
            else:
                row_bg = (28, 28, 38, 200)

            rect = arcade.XYWH(
                (self.lb_x + self.lb_x + self.lb_w) / 2,
                row_cy,
                self.lb_w - 12,
                self.lb_row_h - 2,
            )
            arcade.draw_rect_filled(rect, row_bg)

            # Team color left accent bar (F1 signature style)
            col = self.driver_colors.get(drv, arcade.color.WHITE)
            arcade.draw_lrbt_rectangle_filled(
                self.lb_x + 6,
                self.lb_x + 10,
                row_bottom + 2,
                row_top - 2,
                col,
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

            # Selected highlight (red tint like F1 TV)
            if self.selected_driver == drv:
                rect = arcade.XYWH(
                    (self.lb_x + self.lb_x + self.lb_w) / 2,
                    row_cy,
                    self.lb_w - 12,
                    self.lb_row_h - 2,
                )
                arcade.draw_rect_filled(rect, (*F1_RED[:3], 50))

            # Position number with special colors for podium
            if drv == self.fastest_lap_driver:
                pos_color = FASTEST_PURPLE
            elif pos == 1:
                pos_color = P1_GOLD
            elif pos == 2:
                pos_color = P2_SILVER
            elif pos == 3:
                pos_color = P3_BRONZE
            else:
                pos_color = F1_WHITE

            # Driver text
            self.lb_rows[idx].text = f"{pos:>2}. {drv}"
            self.lb_rows[idx].x = x_text + 6
            self.lb_rows[idx].y = row_top - 4
            self.lb_rows[idx].color = pos_color
            self.lb_rows[idx].draw()

            # Gap/interval
            if idx == 0:
                gap_str = "LEADER"
                self.gap_texts[idx].color = F1_WHITE
            else:
                gap_m = max(0.0, prog_list[idx - 1] - prog_list[idx])
                spd_ahead_mps = max(spd_list_kmh[idx - 1] / 3.6, 1.0)
                spd_this_mps = max(spd_list_kmh[idx] / 3.6, 1.0)
                avg_speed_mps = max(0.5 * (spd_ahead_mps + spd_this_mps), 1.0)
                gap_s = gap_m / avg_speed_mps
                gap_str = f"+{gap_s:.1f}"
                self.gap_texts[idx].color = INTERVAL_YELLOW

            self.gap_texts[idx].text = gap_str
            self.gap_texts[idx].x = x_gap
            self.gap_texts[idx].y = row_cy - 7
            self.gap_texts[idx].draw()

            # Tyre icon
            key = _compound_key(st.get("compound", None))
            tex = self.tyre_textures.get(key) or self.tyre_textures.get("unknown")
            if tex is not None:
                rect = arcade.XYWH(
                    x_tyre, row_cy, self.tyre_icon_size, self.tyre_icon_size,
                )
                arcade.draw_texture_rect(rect=rect, texture=tex, angle=0, alpha=255)

            # DRS indicator
            drs_on = _drs_is_active(int(st.get("drs", 0)))
            if drs_on:
                arcade.draw_circle_filled(x_drs, row_cy, 5, DRS_GREEN)
            else:
                arcade.draw_circle_filled(x_drs, row_cy, 4, F1_GRAY)

        # Clear unused rows
        for j in range(len(ordered), 20):
            self.lb_rows[j].text = ""
            self.gap_texts[j].text = ""

    def _draw_weather(self, frame):
        # F1 broadcast style weather panel
        draw_f1_panel(
            self.weather_x, self.weather_y,
            self.weather_w, self.weather_h, 4
        )

        self.weather_title.draw()

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
            icon_x = self.weather_x + self.weather_w - self.weather_icon_size - 10
            icon_y = self.weather_y + self.weather_h - self.weather_icon_size - 10
            rect = arcade.XYWH(
                icon_x, icon_y, self.weather_icon_size, self.weather_icon_size
            )
            arcade.draw_texture_rect(rect=rect, texture=tex, angle=0, alpha=255)

        # Weather info lines
        lines = [
            f"Track: {track_temp:.1f}C" if track_temp > 0 else "Track: --",
            f"Air: {air_temp:.1f}C" if air_temp > 0 else "Air: --",
            f"Humidity: {humidity:.0f}%" if humidity > 0 else "Humidity: --",
            f"Wind: {wind_speed:.1f} km/h" if wind_speed > 0 else "Wind: --",
            f"Rain: {'WET' if rainfall else 'DRY'}",
        ]

        for i, text in enumerate(lines):
            self.weather_lines[i].text = text
            self.weather_lines[i].draw()

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
        box_x = self.weather_x
        box_y = self.weather_y - self.driver_box_h - 15

        # Driver color
        driver_col = self.driver_colors.get(drv, arcade.color.WHITE)

        # F1 broadcast style driver panel
        draw_f1_panel(
            box_x, box_y,
            self.driver_box_w, self.driver_box_h, 4,
            show_red_accent=False  # Use team color instead
        )

        # Team color accent bar on top (instead of red)
        arcade.draw_lrbt_rectangle_filled(
            box_x, box_x + self.driver_box_w,
            box_y + self.driver_box_h - 3, box_y + self.driver_box_h,
            driver_col,
        )

        # Team color left accent bar
        arcade.draw_lrbt_rectangle_filled(
            box_x + 4,
            box_x + 8,
            box_y + 10,
            box_y + self.driver_box_h - 10,
            driver_col,
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

            # F1 broadcast style throttle and brake bars
            bar_w = 35
            bar_h = 120
            bar_x = box_x + self.driver_box_w - 110
            bar_y = box_y + 20

            # Throttle bar background
            arcade.draw_lrbt_rectangle_filled(
                bar_x, bar_x + bar_w, bar_y, bar_y + bar_h,
                F1_DARK_GRAY,
            )
            if throttle_val > 0:
                fill_h = (throttle_val / 100.0) * bar_h
                arcade.draw_lrbt_rectangle_filled(
                    bar_x, bar_x + bar_w, bar_y, bar_y + fill_h,
                    DRS_GREEN,
                )
            arcade.draw_lrbt_rectangle_outline(
                bar_x, bar_x + bar_w, bar_y, bar_y + bar_h,
                F1_GRAY, 1,
            )

            # Throttle label
            box["throttle_pct"].text = "THR"
            box["throttle_pct"].x = bar_x + bar_w / 2
            box["throttle_pct"].y = bar_y + bar_h + 8
            box["throttle_pct"].draw()

            # Brake bar background
            brake_x = bar_x + bar_w + 15
            arcade.draw_lrbt_rectangle_filled(
                brake_x, brake_x + bar_w, bar_y, bar_y + bar_h,
                F1_DARK_GRAY,
            )
            if brake_val > 0:
                fill_h = (brake_val / 100.0) * bar_h
                arcade.draw_lrbt_rectangle_filled(
                    brake_x, brake_x + bar_w, bar_y, bar_y + fill_h,
                    F1_RED,
                )
            arcade.draw_lrbt_rectangle_outline(
                brake_x, brake_x + bar_w, bar_y, bar_y + bar_h,
                F1_GRAY, 1,
            )

            # Brake label
            box["brake_pct"].text = "BRK"
            box["brake_pct"].x = brake_x + bar_w / 2
            box["brake_pct"].y = bar_y + bar_h + 8
            box["brake_pct"].draw()

    def _draw_progress_bar(self, frame):
        # F1 broadcast style progress bar - clean and simple
        bar_w = 700
        bar_h = 8
        bar_x = (self.width - bar_w) / 2
        bar_y = 20

        # Background
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + bar_w, bar_y, bar_y + bar_h,
            F1_DARK_GRAY,
        )

        # Progress calculation
        progress = self.frame_idx / max(self.n_frames - 1, 1)
        fill_w = progress * bar_w

        # Filled portion (F1 red)
        if fill_w > 0:
            arcade.draw_lrbt_rectangle_filled(
                bar_x, bar_x + fill_w, bar_y, bar_y + bar_h,
                F1_RED,
            )

        # Border
        arcade.draw_lrbt_rectangle_outline(
            bar_x, bar_x + bar_w, bar_y, bar_y + bar_h,
            F1_GRAY, 1,
        )

        # Store bar bounds for click detection
        self._progress_bar_rect = (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h)

    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.SPACE:
            self.paused = not self.paused
        elif symbol == arcade.key.R:
            self.frame_idx = 0.0
            self.paused = False
        elif symbol == arcade.key.H:
            self.show_ui = not self.show_ui
        elif symbol == arcade.key.P:
            self.show_progress_bar = not self.show_progress_bar
        elif symbol == arcade.key.UP:
            self.speed_i = min(self.speed_i + 1, len(self.speed_choices) - 1)
        elif symbol == arcade.key.DOWN:
            self.speed_i = max(self.speed_i - 1, 0)
        elif symbol == arcade.key.RIGHT:
            self.frame_idx = min(self.frame_idx + self.fps * 5, self.n_frames - 1)
        elif symbol == arcade.key.LEFT:
            self.frame_idx = max(self.frame_idx - self.fps * 5, 0)
        elif symbol == arcade.key.F or symbol == arcade.key.F11:
            # Toggle fullscreen
            self.set_fullscreen(not self.fullscreen)

    def on_resize(self, width: int, height: int):
        """Handle window resize - recalculate UI positions."""
        super().on_resize(width, height)

        # Update leaderboard position (right side)
        self.lb_x = width - self.lb_w - 20
        self.lb_h = height - 120
        self.lb_y = 50

        # Update leaderboard title position
        self.lb_title.x = self.lb_x + self.lb_padding
        self.lb_title.y = self.lb_y + self.lb_h - 10

        # Update weather box position (top left, below lap info)
        self.weather_y = height - 210

        # Update weather title and lines positions
        self.weather_title.x = self.weather_x + 12
        self.weather_title.y = self.weather_y + self.weather_h - 12
        for i, line in enumerate(self.weather_lines):
            line.x = self.weather_x + 12
            line.y = self.weather_y + self.weather_h - 35 - i * 20

        # Update HUD text positions
        self.gp_title_text.x = width // 2
        self.gp_title_text.y = height - 20
        self.session_text.x = width // 2
        self.session_text.y = height - 42
        self.lap_text.y = height - 25
        self.race_time_text.y = height - 48

        # Recalculate track transform for new window size
        from src.track import compute_bounds, build_world_to_screen_transform
        xmin, xmax, ymin, ymax = compute_bounds(self.track_x, self.track_y, pad=50.0)
        self.world_scale, self.world_tx, self.world_ty = build_world_to_screen_transform(
            xmin, xmax, ymin, ymax, width, height
        )

        # Recompute track screen coordinates
        from src.track import world_to_screen
        self.track_pts_screen = []
        for x, y in zip(self.track_x, self.track_y):
            sx, sy = world_to_screen(
                float(x), float(y), self.world_scale, self.world_tx, self.world_ty
            )
            self.track_pts_screen.append((sx, sy))
