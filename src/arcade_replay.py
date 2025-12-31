# src/arcade_replay.py

import arcade
from src.track import world_to_screen


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

        # IMPORTANT: don't use "self.scale" (Arcade has a read-only property called scale)
        self.world_scale, self.world_tx, self.world_ty = transform

        # Precompute track polyline in screen coordinates (performance)
        self.track_pts_screen = []
        for x, y in zip(self.track_x, self.track_y):
            sx, sy = world_to_screen(
                float(x), float(y), self.world_scale, self.world_tx, self.world_ty
            )
            self.track_pts_screen.append((sx, sy))

        # Pre-create HUD text objects (draw_text is slow)
        self.hud_text = arcade.Text(
            "",
            20,
            self.height - 30,
            arcade.color.WHITE,
            14,
        )

        self.help_text = arcade.Text(
            "Controls: Space=Pause  Up/Down=Speed  Left/Right=Seek  R=Restart",
            20,
            20,
            arcade.color.LIGHT_GRAY,
            12,
        )

        self.driver_colors = driver_colors or {}

        self.frame_idx = 0.0
        self.paused = False

        self.fps = fps  # store fps so seeking uses the right value

        # Playback speed multiplier (in "frames per update")
        self.speed_choices = [0.5, 1.0, 2.0, 4.0]
        self.speed_i = 1  # start at 1.0x

        arcade.set_background_color(arcade.color.BLACK)

    def on_update(self, delta_time: float):
        if self.paused:
            return

        self.frame_idx += self.speed_choices[self.speed_i]

        if self.frame_idx >= self.n_frames - 1:
            self.frame_idx = self.n_frames - 1
            self.paused = True

    def on_draw(self):
        # Clear the window each frame (Arcade 3.x style)
        self.clear()

        i = int(self.frame_idx)
        frame = self.frames[i]

        pts = []
        for x, y in zip(self.track_x, self.track_y):
            sx, sy = world_to_screen(
                float(x), float(y), self.world_scale, self.world_tx, self.world_ty
            )
            pts.append((sx, sy))

        if len(self.track_pts_screen) >= 2:
            arcade.draw_line_strip(self.track_pts_screen, arcade.color.DARK_GRAY, 2)

        for drv, st in frame["drivers"].items():
            sx, sy = world_to_screen(
                st["x"], st["y"], self.world_scale, self.world_tx, self.world_ty
            )
            col = self.driver_colors.get(drv, arcade.color.WHITE)
            arcade.draw_circle_filled(sx, sy, 6, col)

        t = frame["t"]
        speed = self.speed_choices[self.speed_i]
        status = "PAUSED" if self.paused else "PLAYING"
        self.hud_text.text = (
            f"{status}  t={t:.2f}s  speed={speed}x  frame={i}/{self.n_frames - 1}"
        )

        self.hud_text.draw()
        self.help_text.draw()

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

        # Seek ±5 seconds using fps
        elif symbol == arcade.key.RIGHT:
            self.frame_idx = min(self.frame_idx + self.fps * 5, self.n_frames - 1)

        elif symbol == arcade.key.LEFT:
            self.frame_idx = max(self.frame_idx - self.fps * 5, 0)
