"""
Tyre Analysis Window - Arcade UI with embedded Matplotlib charts.

Provides interactive visualization of tyre degradation data and ML predictions.
"""

import arcade
import pandas as pd
import numpy as np
from typing import Dict, Optional, List

from .charts import (
    render_degradation_chart,
    render_compound_comparison,
    render_stint_summary,
    render_degradation_heatmap,
    render_driver_comparison,
    render_model_stats,
    COMPOUND_COLORS,
)
from ..ml.feature_engineering import get_stint_summary

# F1 TV broadcast style colors (matching arcade_replay.py)
F1_RED = (225, 6, 0)
F1_BLACK = (21, 21, 30)
F1_DARK_GRAY = (38, 38, 48)
F1_GRAY = (68, 68, 78)
F1_WHITE = (255, 255, 255)
F1_LIGHT_GRAY = (180, 180, 185)
FASTEST_PURPLE = (170, 0, 255)

PANEL_BG = (28, 28, 38, 240)
PANEL_BG_ALT = (38, 38, 50, 240)


def draw_rounded_rectangle(x, y, width, height, color, radius=10):
    """Draw a filled rectangle with rounded corners."""
    radius = max(0, min(radius, width / 2, height / 2))
    if radius <= 0:
        arcade.draw_lrbt_rectangle_filled(x, x + width, y, y + height, color)
        return
    arcade.draw_lrbt_rectangle_filled(
        x + radius, x + width - radius, y, y + height, color
    )
    arcade.draw_lrbt_rectangle_filled(
        x, x + width, y + radius, y + height - radius, color
    )
    arcade.draw_circle_filled(x + radius, y + radius, radius, color)
    arcade.draw_circle_filled(x + width - radius, y + radius, radius, color)
    arcade.draw_circle_filled(x + radius, y + height - radius, radius, color)
    arcade.draw_circle_filled(x + width - radius, y + height - radius, radius, color)


def draw_f1_panel(x, y, width, height, radius=4, show_red_accent=True):
    """Draw an F1 broadcast style panel with optional red accent line."""
    draw_rounded_rectangle(x, y, width, height, PANEL_BG, radius)
    if show_red_accent:
        arcade.draw_lrbt_rectangle_filled(
            x, x + width, y + height - 3, y + height, F1_RED
        )


class Button:
    """Simple clickable button for the UI."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        text: str,
        callback,
        selected: bool = False,
        color_normal=F1_DARK_GRAY,
        color_selected=F1_RED,
        color_hover=F1_GRAY,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.callback = callback
        self.selected = selected
        self.hovered = False
        self.color_normal = color_normal
        self.color_selected = color_selected
        self.color_hover = color_hover
        # Pre-created Text object for performance
        self._text_obj = arcade.Text(
            text,
            x + width / 2,
            y + height / 2,
            F1_WHITE,
            font_size=11,
            anchor_x="center",
            anchor_y="center",
            bold=selected,
        )

    def contains(self, px: float, py: float) -> bool:
        """Check if point is inside button."""
        return (
            self.x <= px <= self.x + self.width and
            self.y <= py <= self.y + self.height
        )

    def draw(self):
        """Draw the button."""
        if self.selected:
            color = self.color_selected
        elif self.hovered:
            color = self.color_hover
        else:
            color = self.color_normal

        draw_rounded_rectangle(self.x, self.y, self.width, self.height, color, radius=4)

        # Text (using pre-created Text object)
        self._text_obj.x = self.x + self.width / 2
        self._text_obj.y = self.y + self.height / 2
        self._text_obj.text = self.text
        self._text_obj.bold = self.selected
        self._text_obj.draw()


class TyreAnalysisWindow(arcade.Window):
    """
    Arcade window for tyre degradation analysis.

    Features:
    - F1 broadcast-style UI shell
    - Embedded Matplotlib/Seaborn charts
    - Driver and stint selection
    - Model predictions and statistics
    """

    def __init__(
        self,
        session,
        features_df: pd.DataFrame,
        model,
        session_info,
        width: int = 1400,
        height: int = 900,
    ):
        super().__init__(width, height, "Tyre Degradation Analysis", resizable=True)

        self.session = session
        self.features_df = features_df
        self.model = model
        self.session_info = session_info

        # Get unique drivers and sort
        self.drivers = sorted(features_df["driver"].unique().tolist())
        self.selected_driver_idx = 0
        self.selected_driver = self.drivers[0] if self.drivers else None

        # Get stints for selected driver
        self._update_stints()
        self.selected_stint_idx = 0
        self.selected_stint = self.stints[0] if self.stints else 1

        # Chart textures (lazy loaded)
        self.deg_chart_texture = None
        self.comparison_texture = None
        self.stint_summary_texture = None
        self.heatmap_texture = None
        self.model_stats_texture = None

        # UI buttons
        self.driver_buttons: List[Button] = []
        self.stint_buttons: List[Button] = []
        self.nav_buttons: List[Button] = []

        # Get average conditions for predictions
        self.conditions = self._get_average_conditions()

        # Build UI and render initial charts
        self._build_ui()
        self._update_charts()

        arcade.set_background_color(F1_BLACK)

        # ---------------------------
        # Pre-created Text objects for performance (avoid draw_text)
        # ---------------------------
        # Header texts
        self.header_title_text = arcade.Text(
            "TYRE DEGRADATION ANALYSIS", 0, 0, F1_WHITE, 16,
            anchor_x="center", anchor_y="center", bold=True
        )
        self.header_session_text = arcade.Text(
            "", 0, 0, F1_LIGHT_GRAY, 11, anchor_x="right", anchor_y="center"
        )

        # Sidebar labels
        self.driver_label_text = arcade.Text(
            "DRIVER", 0, 0, F1_LIGHT_GRAY, 10, anchor_x="center", bold=True
        )
        self.stint_label_text = arcade.Text(
            "STINT", 0, 0, F1_LIGHT_GRAY, 10, anchor_x="center", bold=True
        )

        # Panel titles
        self.stint_summary_title_text = arcade.Text(
            "STINT SUMMARY", 0, 0, F1_WHITE, 11, anchor_x="center", bold=True
        )
        self.model_stats_title_text = arcade.Text(
            "MODEL STATS", 0, 0, F1_WHITE, 11, anchor_x="center", bold=True
        )
        self.prediction_title_text = arcade.Text(
            "PREDICTION", 0, 0, F1_WHITE, 12, bold=True
        )

        # Prediction panel texts
        self.prediction_placeholder_text = arcade.Text(
            "Select a driver to see predictions", 0, 0, F1_LIGHT_GRAY, 11, anchor_x="center"
        )
        self.compound_text = arcade.Text("", 0, 0, F1_WHITE, 14, bold=True)
        self.deg_rate_label_text = arcade.Text("Degradation Rate:", 0, 0, F1_LIGHT_GRAY, 11)
        self.deg_rate_value_text = arcade.Text("", 0, 0, F1_WHITE, 11, bold=True)
        self.cliff_label_text = arcade.Text("Cliff Point:", 0, 0, F1_LIGHT_GRAY, 11)
        self.cliff_value_text = arcade.Text("", 0, 0, F1_WHITE, 11, bold=True)
        self.optimal_label_text = arcade.Text("Optimal Stint:", 0, 0, F1_LIGHT_GRAY, 11)
        self.optimal_value_text = arcade.Text("", 0, 0, F1_WHITE, 11, bold=True)
        self.loss_label_text = arcade.Text("", 0, 0, F1_LIGHT_GRAY, 11)
        self.loss_value_text = arcade.Text("", 0, 0, FASTEST_PURPLE, 11, bold=True)

    def _update_stints(self):
        """Update available stints for selected driver."""
        if self.selected_driver is None:
            self.stints = []
            return

        driver_data = self.features_df[self.features_df["driver"] == self.selected_driver]
        self.stints = sorted(driver_data["stint"].unique().tolist())

    def _get_average_conditions(self) -> Dict:
        """Get average track conditions from the session."""
        conditions = {
            "track_temp": 30.0,
            "air_temp": 25.0,
        }

        if "track_temp" in self.features_df.columns:
            avg_track = self.features_df["track_temp"].mean()
            if not pd.isna(avg_track):
                conditions["track_temp"] = avg_track

        if "air_temp" in self.features_df.columns:
            avg_air = self.features_df["air_temp"].mean()
            if not pd.isna(avg_air):
                conditions["air_temp"] = avg_air

        return conditions

    def _build_ui(self):
        """Build UI buttons and panels."""
        self._rebuild_driver_buttons()
        self._rebuild_stint_buttons()
        self._rebuild_nav_buttons()

    def _rebuild_driver_buttons(self):
        """Rebuild driver selection buttons."""
        self.driver_buttons = []
        sidebar_x = 20
        start_y = self.height - 150
        btn_width = 60
        btn_height = 28
        spacing = 32

        for i, driver in enumerate(self.drivers[:15]):  # Max 15 drivers in sidebar
            y = start_y - i * spacing
            btn = Button(
                x=sidebar_x,
                y=y,
                width=btn_width,
                height=btn_height,
                text=driver,
                callback=lambda idx=i: self._select_driver(idx),
                selected=(i == self.selected_driver_idx),
            )
            self.driver_buttons.append(btn)

    def _rebuild_stint_buttons(self):
        """Rebuild stint selection buttons."""
        self.stint_buttons = []
        sidebar_x = 20
        start_y = self.height - 150 - len(self.driver_buttons) * 32 - 60
        btn_width = 45
        btn_height = 28
        spacing = 32

        for i, stint in enumerate(self.stints[:5]):  # Max 5 stints
            y = start_y - i * spacing
            btn = Button(
                x=sidebar_x,
                y=y,
                width=btn_width,
                height=btn_height,
                text=f"S{stint}",
                callback=lambda idx=i: self._select_stint(idx),
                selected=(i == self.selected_stint_idx),
            )
            self.stint_buttons.append(btn)

    def _rebuild_nav_buttons(self):
        """Rebuild navigation buttons."""
        self.nav_buttons = []
        btn_width = 120
        btn_height = 35
        bottom_y = 30

        # Previous driver button
        prev_btn = Button(
            x=self.width / 2 - btn_width - 20,
            y=bottom_y,
            width=btn_width,
            height=btn_height,
            text="< Prev Driver",
            callback=self._prev_driver,
        )
        self.nav_buttons.append(prev_btn)

        # Next driver button
        next_btn = Button(
            x=self.width / 2 + 20,
            y=bottom_y,
            width=btn_width,
            height=btn_height,
            text="Next Driver >",
            callback=self._next_driver,
        )
        self.nav_buttons.append(next_btn)

    def _select_driver(self, idx: int):
        """Select driver by index."""
        if 0 <= idx < len(self.drivers):
            self.selected_driver_idx = idx
            self.selected_driver = self.drivers[idx]
            self._update_stints()
            self.selected_stint_idx = 0
            self.selected_stint = self.stints[0] if self.stints else 1
            self._rebuild_driver_buttons()
            self._rebuild_stint_buttons()
            self._update_charts()

    def _select_stint(self, idx: int):
        """Select stint by index."""
        if 0 <= idx < len(self.stints):
            self.selected_stint_idx = idx
            self.selected_stint = self.stints[idx]
            self._rebuild_stint_buttons()
            self._update_charts()

    def _prev_driver(self):
        """Select previous driver."""
        if self.selected_driver_idx > 0:
            self._select_driver(self.selected_driver_idx - 1)

    def _next_driver(self):
        """Select next driver."""
        if self.selected_driver_idx < len(self.drivers) - 1:
            self._select_driver(self.selected_driver_idx + 1)

    def _update_charts(self):
        """Re-render charts for current selection."""
        if self.selected_driver is None:
            return

        # Get driver/stint data
        driver_data = self.features_df[
            (self.features_df["driver"] == self.selected_driver) &
            (self.features_df["stint"] == self.selected_stint)
        ]

        if driver_data.empty:
            return

        # Get compound for this stint
        compound = driver_data["compound"].iloc[0] if len(driver_data) > 0 else "UNKNOWN"

        # Predict degradation curve
        predicted = None
        if self.model.is_trained:
            max_laps = int(driver_data["tyre_age"].max()) + 10 if len(driver_data) > 0 else 30
            predicted = self.model.predict_stint_curve(compound, self.conditions, max_laps)

        # Render degradation chart
        self.deg_chart_texture = render_degradation_chart(
            actual_data=driver_data,
            predicted_curve=predicted,
            compound=compound,
            driver=self.selected_driver,
            stint=self.selected_stint,
            width=600,
            height=400,
        )

        # Render compound comparison
        self.comparison_texture = render_compound_comparison(
            model=self.model,
            conditions=self.conditions,
            max_laps=40,
            width=600,
            height=280,
        )

        # Render stint summary
        stint_df = get_stint_summary(self.features_df, self.selected_driver)
        self.stint_summary_texture = render_stint_summary(
            stint_data=stint_df,
            width=200,
            height=180,
        )

        # Render model stats
        self.model_stats_texture = render_model_stats(
            training_stats=self.model.training_stats,
            width=200,
            height=150,
        )

    def on_resize(self, width: int, height: int):
        """Handle window resize."""
        super().on_resize(width, height)
        self._build_ui()

    def on_draw(self):
        """Render the analysis UI."""
        self.clear()

        # Draw header
        self._draw_header()

        # Draw sidebar
        self._draw_sidebar()

        # Draw main chart area
        self._draw_chart_area()

        # Draw stats panel
        self._draw_stats_panel()

        # Draw prediction panel
        self._draw_prediction_panel()

        # Draw navigation buttons
        for btn in self.nav_buttons:
            btn.draw()

    def _draw_header(self):
        """Draw header panel with session info."""
        header_height = 50
        draw_f1_panel(0, self.height - header_height, self.width, header_height, radius=0)

        # Title (using pre-created Text object)
        self.header_title_text.x = self.width / 2
        self.header_title_text.y = self.height - 30
        self.header_title_text.draw()

        # Session info (using pre-created Text object)
        if self.session_info:
            self.header_session_text.text = f"{self.session_info.event_name} - {self.session_info.session_name}"
            self.header_session_text.x = self.width - 20
            self.header_session_text.y = self.height - 30
            self.header_session_text.draw()

    def _draw_sidebar(self):
        """Draw sidebar with driver and stint selection."""
        sidebar_width = 100
        sidebar_x = 10
        sidebar_y = 80
        sidebar_height = self.height - 150

        draw_f1_panel(sidebar_x, sidebar_y, sidebar_width, sidebar_height, show_red_accent=False)

        # "DRIVER" label (using pre-created Text object)
        label_y = self.height - 120
        self.driver_label_text.x = sidebar_x + sidebar_width / 2
        self.driver_label_text.y = label_y
        self.driver_label_text.draw()

        # Draw driver buttons
        for btn in self.driver_buttons:
            btn.draw()

        # "STINT" label (using pre-created Text object)
        if self.stint_buttons:
            stint_label_y = self.stint_buttons[0].y + 40
            self.stint_label_text.x = sidebar_x + sidebar_width / 2
            self.stint_label_text.y = stint_label_y
            self.stint_label_text.draw()

        # Draw stint buttons
        for btn in self.stint_buttons:
            btn.draw()

    def _draw_chart_area(self):
        """Draw main chart area with embedded textures."""
        chart_x = 130
        chart_y = 320
        chart_width = 620
        chart_height = 420

        # Degradation chart panel
        draw_f1_panel(chart_x, chart_y, chart_width, chart_height)

        # Draw degradation chart texture
        if self.deg_chart_texture:
            # Center the texture in the panel
            tex_x = chart_x + chart_width / 2
            tex_y = chart_y + chart_height / 2 - 10
            arcade.draw_texture_rect(
                self.deg_chart_texture,
                arcade.LRBT(
                    tex_x - 300,
                    tex_x + 300,
                    tex_y - 195,
                    tex_y + 195,
                ),
            )

        # Compound comparison panel
        comp_y = 80
        comp_height = 220
        draw_f1_panel(chart_x, comp_y, chart_width, comp_height)

        # Draw comparison chart texture
        if self.comparison_texture:
            tex_x = chart_x + chart_width / 2
            tex_y = comp_y + comp_height / 2 - 5
            arcade.draw_texture_rect(
                self.comparison_texture,
                arcade.LRBT(
                    tex_x - 300,
                    tex_x + 300,
                    tex_y - 135,
                    tex_y + 135,
                ),
            )

    def _draw_stats_panel(self):
        """Draw statistics panel on the right side."""
        panel_x = 770
        panel_y = 480
        panel_width = 220
        panel_height = 260

        draw_f1_panel(panel_x, panel_y, panel_width, panel_height)

        # Title (using pre-created Text object)
        self.stint_summary_title_text.x = panel_x + panel_width / 2
        self.stint_summary_title_text.y = panel_y + panel_height - 20
        self.stint_summary_title_text.draw()

        # Draw stint summary texture
        if self.stint_summary_texture:
            tex_x = panel_x + panel_width / 2
            tex_y = panel_y + panel_height / 2 - 20
            arcade.draw_texture_rect(
                self.stint_summary_texture,
                arcade.LRBT(
                    tex_x - 100,
                    tex_x + 100,
                    tex_y - 85,
                    tex_y + 85,
                ),
            )

        # Model stats panel below
        stats_y = 320
        stats_height = 140
        draw_f1_panel(panel_x, stats_y, panel_width, stats_height)

        # Title (using pre-created Text object)
        self.model_stats_title_text.x = panel_x + panel_width / 2
        self.model_stats_title_text.y = stats_y + stats_height - 20
        self.model_stats_title_text.draw()

        # Draw model stats texture
        if self.model_stats_texture:
            tex_x = panel_x + panel_width / 2
            tex_y = stats_y + stats_height / 2 - 15
            arcade.draw_texture_rect(
                self.model_stats_texture,
                arcade.LRBT(
                    tex_x - 100,
                    tex_x + 100,
                    tex_y - 65,
                    tex_y + 65,
                ),
            )

    def _draw_prediction_panel(self):
        """Draw prediction info panel."""
        panel_x = 770
        panel_y = 80
        panel_width = 410
        panel_height = 220

        draw_f1_panel(panel_x, panel_y, panel_width, panel_height)

        # Title (using pre-created Text object)
        self.prediction_title_text.x = panel_x + 15
        self.prediction_title_text.y = panel_y + panel_height - 25
        self.prediction_title_text.draw()

        if self.selected_driver is None or not self.model.is_trained:
            self.prediction_placeholder_text.x = panel_x + panel_width / 2
            self.prediction_placeholder_text.y = panel_y + panel_height / 2
            self.prediction_placeholder_text.draw()
            return

        # Get current stint info
        driver_data = self.features_df[
            (self.features_df["driver"] == self.selected_driver) &
            (self.features_df["stint"] == self.selected_stint)
        ]

        if driver_data.empty:
            return

        compound = driver_data["compound"].iloc[0]
        compound_color = COMPOUND_COLORS.get(compound.upper(), (128, 128, 128))
        # Convert hex string to RGB tuple if needed
        if isinstance(compound_color, str):
            compound_color = tuple(int(compound_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        # Predictions
        deg_rate = self.model.get_degradation_rate(compound, self.conditions)
        cliff_point = self.model.get_cliff_point(compound, self.conditions, threshold=1.0)
        optimal_length = self.model.get_optimal_stint_length(compound, self.conditions, target_delta=0.5)

        y_offset = panel_y + panel_height - 60

        # Compound indicator (using pre-created Text object)
        self.compound_text.text = f"Running {compound} tyres"
        self.compound_text.x = panel_x + 15
        self.compound_text.y = y_offset
        self.compound_text.color = compound_color
        self.compound_text.draw()
        y_offset -= 35

        # Degradation rate (using pre-created Text objects)
        self.deg_rate_label_text.x = panel_x + 15
        self.deg_rate_label_text.y = y_offset
        self.deg_rate_label_text.draw()
        self.deg_rate_value_text.text = f"{deg_rate:.3f} s/lap"
        self.deg_rate_value_text.x = panel_x + 150
        self.deg_rate_value_text.y = y_offset
        self.deg_rate_value_text.draw()
        y_offset -= 28

        # Cliff point (using pre-created Text objects)
        self.cliff_label_text.x = panel_x + 15
        self.cliff_label_text.y = y_offset
        self.cliff_label_text.draw()
        self.cliff_value_text.text = f"Lap {cliff_point}"
        self.cliff_value_text.x = panel_x + 150
        self.cliff_value_text.y = y_offset
        self.cliff_value_text.draw()
        y_offset -= 28

        # Optimal stint length (using pre-created Text objects)
        self.optimal_label_text.x = panel_x + 15
        self.optimal_label_text.y = y_offset
        self.optimal_label_text.draw()
        self.optimal_value_text.text = f"{optimal_length} laps"
        self.optimal_value_text.x = panel_x + 150
        self.optimal_value_text.y = y_offset
        self.optimal_value_text.draw()
        y_offset -= 28

        # Estimated total time loss for 35 laps (using pre-created Text objects)
        test_laps = 35
        curve = self.model.predict_stint_curve(compound, self.conditions, test_laps)
        total_loss = sum(curve)
        self.loss_label_text.text = f"Est. loss ({test_laps} laps):"
        self.loss_label_text.x = panel_x + 15
        self.loss_label_text.y = y_offset
        self.loss_label_text.draw()
        self.loss_value_text.text = f"+{total_loss:.1f}s"
        self.loss_value_text.x = panel_x + 150
        self.loss_value_text.y = y_offset
        self.loss_value_text.draw()

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        """Handle mouse hover for buttons."""
        for btn in self.driver_buttons + self.stint_buttons + self.nav_buttons:
            btn.hovered = btn.contains(x, y)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        """Handle mouse clicks."""
        if button == arcade.MOUSE_BUTTON_LEFT:
            for btn in self.driver_buttons + self.stint_buttons + self.nav_buttons:
                if btn.contains(x, y):
                    btn.callback()
                    break

    def on_key_press(self, key: int, modifiers: int):
        """Handle keyboard input."""
        if key == arcade.key.ESCAPE:
            arcade.close_window()
        elif key == arcade.key.LEFT:
            self._prev_driver()
        elif key == arcade.key.RIGHT:
            self._next_driver()
        elif key == arcade.key.UP:
            # Previous stint
            if self.selected_stint_idx > 0:
                self._select_stint(self.selected_stint_idx - 1)
        elif key == arcade.key.DOWN:
            # Next stint
            if self.selected_stint_idx < len(self.stints) - 1:
                self._select_stint(self.selected_stint_idx + 1)
