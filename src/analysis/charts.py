"""
Chart rendering module for tyre analysis.

Renders Matplotlib/Seaborn charts to Arcade textures with F1 broadcast styling.
"""

import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for rendering to buffer
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
import arcade
from typing import Dict, Optional


# F1 broadcast color palette
F1_COLORS = {
    "background": "#15151E",
    "panel": "#26263E",
    "text": "#FFFFFF",
    "text_secondary": "#B4B4B9",
    "grid": "#3A3A4A",
    "red": "#E10600",
    "purple": "#AA00FF",
    "gold": "#FFD700",
}

# Compound colors (matching F1 TV style)
COMPOUND_COLORS = {
    "SOFT": "#FF3333",      # Red
    "MEDIUM": "#FFD700",    # Yellow
    "HARD": "#FFFFFF",      # White
    "INTERMEDIATE": "#00FF00",  # Green
    "WET": "#00BFFF",       # Blue
    "UNKNOWN": "#808080",   # Gray
}

# Custom matplotlib style for F1 look
F1_CHART_STYLE = {
    "figure.facecolor": F1_COLORS["background"],
    "axes.facecolor": F1_COLORS["panel"],
    "axes.edgecolor": F1_COLORS["text_secondary"],
    "axes.labelcolor": F1_COLORS["text"],
    "axes.titlecolor": F1_COLORS["text"],
    "text.color": F1_COLORS["text"],
    "xtick.color": F1_COLORS["text_secondary"],
    "ytick.color": F1_COLORS["text_secondary"],
    "grid.color": F1_COLORS["grid"],
    "legend.facecolor": F1_COLORS["panel"],
    "legend.edgecolor": F1_COLORS["text_secondary"],
    "legend.labelcolor": F1_COLORS["text"],
}


def _fig_to_texture(fig: plt.Figure, name: str) -> arcade.Texture:
    """Convert matplotlib figure to Arcade texture."""
    # Render to buffer
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    buf.seek(0)

    # Load as PIL Image and create Arcade texture
    img = Image.open(buf)
    texture = arcade.Texture(image=img, name=name)
    buf.close()
    plt.close(fig)

    return texture


def render_degradation_chart(
    actual_data: pd.DataFrame,
    predicted_curve: np.ndarray,
    compound: str,
    driver: str = "",
    stint: int = 1,
    width: int = 600,
    height: int = 400,
) -> arcade.Texture:
    """
    Render degradation curve chart with actual vs predicted.

    Args:
        actual_data: DataFrame with 'tyre_age' and 'lap_time_delta' columns
        predicted_curve: Array of predicted deltas by tyre age
        compound: Tyre compound name
        driver: Driver code for title
        stint: Stint number for title
        width: Chart width in pixels
        height: Chart height in pixels

    Returns:
        Arcade texture containing the rendered chart
    """
    with plt.rc_context(F1_CHART_STYLE):
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

        compound_color = COMPOUND_COLORS.get(compound.upper(), "#808080")

        # Plot actual lap times as scatter
        if actual_data is not None and len(actual_data) > 0:
            valid_data = actual_data[actual_data["is_valid"]] if "is_valid" in actual_data.columns else actual_data
            if len(valid_data) > 0:
                ax.scatter(
                    valid_data["tyre_age"],
                    valid_data["lap_time_delta"],
                    c=compound_color,
                    s=60,
                    alpha=0.8,
                    edgecolors="white",
                    linewidths=0.5,
                    label="Actual",
                    zorder=3,
                )

        # Plot predicted curve
        if predicted_curve is not None and len(predicted_curve) > 0:
            x_pred = np.arange(1, len(predicted_curve) + 1)
            ax.plot(
                x_pred,
                predicted_curve,
                "--",
                color=F1_COLORS["purple"],
                linewidth=2.5,
                label="Predicted",
                zorder=2,
            )

        # Styling
        title = f"Tyre Degradation - {compound}"
        if driver:
            title = f"{driver} Stint {stint} - {compound}"
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Tyre Age (laps)", fontsize=10)
        ax.set_ylabel("Lap Time Delta (s)", fontsize=10)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.3, linestyle="--")

        # Set y-axis to start at 0
        ax.set_ylim(bottom=-0.1)

        # Add subtle x-axis at y=0
        ax.axhline(y=0, color=F1_COLORS["text_secondary"], linewidth=0.5, alpha=0.5)

        fig.tight_layout()

        return _fig_to_texture(fig, f"deg_chart_{driver}_{stint}_{compound}")


def render_compound_comparison(
    model,
    conditions: Dict,
    max_laps: int = 40,
    width: int = 600,
    height: int = 300,
) -> arcade.Texture:
    """
    Render comparison of degradation curves for all compounds.

    Args:
        model: TyreDegradationModel instance
        conditions: Dict with track_temp, air_temp keys
        max_laps: Maximum laps to plot
        width: Chart width in pixels
        height: Chart height in pixels

    Returns:
        Arcade texture containing the rendered chart
    """
    with plt.rc_context(F1_CHART_STYLE):
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

        compounds = ["SOFT", "MEDIUM", "HARD"]
        x = np.arange(1, max_laps + 1)

        for compound in compounds:
            curve = model.predict_stint_curve(compound, conditions, max_laps)
            color = COMPOUND_COLORS.get(compound, "#808080")
            ax.plot(
                x,
                curve,
                color=color,
                linewidth=2.5,
                label=compound.capitalize(),
            )

        ax.set_title("Compound Comparison", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Tyre Age (laps)", fontsize=10)
        ax.set_ylabel("Lap Time Delta (s)", fontsize=10)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_ylim(bottom=-0.1)

        fig.tight_layout()

        return _fig_to_texture(fig, "compound_comparison")


def render_stint_summary(
    stint_data: pd.DataFrame,
    width: int = 400,
    height: int = 250,
) -> arcade.Texture:
    """
    Render stint statistics as a styled bar chart.

    Args:
        stint_data: DataFrame from get_stint_summary()
        width: Chart width in pixels
        height: Chart height in pixels

    Returns:
        Arcade texture containing the rendered chart
    """
    with plt.rc_context(F1_CHART_STYLE):
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

        if stint_data is None or stint_data.empty:
            ax.text(
                0.5, 0.5, "No stint data",
                ha="center", va="center",
                fontsize=12, color=F1_COLORS["text_secondary"]
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
        else:
            x = range(len(stint_data))
            colors = [COMPOUND_COLORS.get(c, "#808080") for c in stint_data["compound"]]

            bars = ax.bar(
                x,
                stint_data["num_laps"],
                color=colors,
                edgecolor="white",
                linewidth=0.5,
            )

            # Add compound labels on bars
            for i, (bar, row) in enumerate(zip(bars, stint_data.itertuples())):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.5,
                    f"{row.compound[0]}",  # First letter
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    fontweight="bold",
                    color=colors[i],
                )

            ax.set_title("Stint Lengths", fontsize=11, fontweight="bold", pad=8)
            ax.set_xlabel("Stint", fontsize=9)
            ax.set_ylabel("Laps", fontsize=9)
            ax.set_xticks(x)
            ax.set_xticklabels([f"S{i+1}" for i in x], fontsize=9)
            ax.grid(True, alpha=0.3, axis="y", linestyle="--")

        fig.tight_layout()

        return _fig_to_texture(fig, "stint_summary")


def render_degradation_heatmap(
    features_df: pd.DataFrame,
    width: int = 500,
    height: int = 400,
) -> arcade.Texture:
    """
    Render heatmap of degradation by compound and tyre age.

    Args:
        features_df: DataFrame from extract_tyre_features()
        width: Chart width in pixels
        height: Chart height in pixels

    Returns:
        Arcade texture containing the rendered chart
    """
    with plt.rc_context(F1_CHART_STYLE):
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

        # Filter valid laps
        valid = features_df[features_df["is_valid"]].copy()

        if valid.empty:
            ax.text(
                0.5, 0.5, "No valid lap data",
                ha="center", va="center",
                fontsize=12, color=F1_COLORS["text_secondary"]
            )
            ax.axis("off")
        else:
            # Create pivot table: compound x tyre_age bins
            valid["age_bin"] = pd.cut(
                valid["tyre_age"],
                bins=[0, 5, 10, 15, 20, 25, 30, 100],
                labels=["1-5", "6-10", "11-15", "16-20", "21-25", "26-30", "30+"]
            )

            pivot = valid.pivot_table(
                values="lap_time_delta",
                index="compound",
                columns="age_bin",
                aggfunc="mean"
            )

            # Reorder compounds
            compound_order = [c for c in ["SOFT", "MEDIUM", "HARD"] if c in pivot.index]
            if compound_order:
                pivot = pivot.reindex(compound_order)

            sns.heatmap(
                pivot,
                ax=ax,
                cmap="YlOrRd",
                annot=True,
                fmt=".2f",
                cbar_kws={"label": "Avg Delta (s)"},
                linewidths=0.5,
                linecolor=F1_COLORS["grid"],
            )

            ax.set_title("Degradation by Compound & Age", fontsize=11, fontweight="bold", pad=8)
            ax.set_xlabel("Tyre Age (laps)", fontsize=9)
            ax.set_ylabel("Compound", fontsize=9)

        fig.tight_layout()

        return _fig_to_texture(fig, "degradation_heatmap")


def render_driver_comparison(
    features_df: pd.DataFrame,
    drivers: list,
    compound: str,
    width: int = 600,
    height: int = 350,
) -> arcade.Texture:
    """
    Render comparison of degradation for multiple drivers on same compound.

    Args:
        features_df: DataFrame from extract_tyre_features()
        drivers: List of driver codes to compare
        compound: Compound to compare
        width: Chart width in pixels
        height: Chart height in pixels

    Returns:
        Arcade texture containing the rendered chart
    """
    with plt.rc_context(F1_CHART_STYLE):
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

        # Filter for compound and valid laps
        data = features_df[
            (features_df["compound"] == compound.upper()) &
            (features_df["is_valid"])
        ]

        if data.empty:
            ax.text(
                0.5, 0.5, f"No data for {compound}",
                ha="center", va="center",
                fontsize=12, color=F1_COLORS["text_secondary"]
            )
            ax.axis("off")
        else:
            # Color palette for drivers
            colors = plt.cm.Set2(np.linspace(0, 1, len(drivers)))

            for i, driver in enumerate(drivers):
                driver_data = data[data["driver"] == driver]
                if not driver_data.empty:
                    ax.scatter(
                        driver_data["tyre_age"],
                        driver_data["lap_time_delta"],
                        c=[colors[i]],
                        s=40,
                        alpha=0.7,
                        label=driver,
                    )

            ax.set_title(f"Driver Comparison - {compound}", fontsize=11, fontweight="bold", pad=8)
            ax.set_xlabel("Tyre Age (laps)", fontsize=9)
            ax.set_ylabel("Lap Time Delta (s)", fontsize=9)
            ax.legend(loc="upper left", fontsize=8, ncol=2)
            ax.grid(True, alpha=0.3, linestyle="--")
            ax.set_ylim(bottom=-0.1)

        fig.tight_layout()

        return _fig_to_texture(fig, f"driver_comparison_{compound}")


def render_model_stats(
    training_stats: Dict,
    width: int = 300,
    height: int = 200,
) -> arcade.Texture:
    """
    Render model training statistics as a text panel.

    Args:
        training_stats: Dict from model.train()
        width: Chart width in pixels
        height: Chart height in pixels

    Returns:
        Arcade texture containing the rendered stats
    """
    with plt.rc_context(F1_CHART_STYLE):
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
        ax.axis("off")

        if not training_stats or "error" in training_stats:
            ax.text(
                0.5, 0.5, "Model not trained",
                ha="center", va="center",
                fontsize=12, color=F1_COLORS["text_secondary"]
            )
        else:
            text_lines = [
                f"Samples: {training_stats.get('n_samples', 'N/A')}",
                f"Train R\u00b2: {training_stats.get('train_r2', 0):.3f}",
                f"Val R\u00b2: {training_stats.get('val_r2', 0):.3f}",
                f"Val RMSE: {training_stats.get('val_rmse', 0):.3f}s",
            ]

            y_pos = 0.85
            for line in text_lines:
                ax.text(
                    0.1, y_pos, line,
                    ha="left", va="top",
                    fontsize=10, color=F1_COLORS["text"],
                    transform=ax.transAxes
                )
                y_pos -= 0.2

        fig.tight_layout()

        return _fig_to_texture(fig, "model_stats")
