"""
Feature engineering for tyre degradation prediction.

Extracts per-lap features from a FastF1 session for ML model training.
"""

import pandas as pd
import numpy as np
from typing import Optional


def _to_seconds(val) -> Optional[float]:
    """Convert timedelta or numeric value to seconds."""
    if val is None:
        return None
    if pd.isna(val):
        return None
    if hasattr(val, "total_seconds"):
        return val.total_seconds()
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def extract_tyre_features(session) -> pd.DataFrame:
    """
    Extract per-lap features for tyre degradation prediction.

    Args:
        session: FastF1 session object with loaded laps data

    Returns:
        DataFrame with columns:
        - driver: Driver code (e.g., "VER")
        - lap: Lap number
        - stint: Stint number
        - tyre_age: Laps on current compound
        - compound: SOFT/MEDIUM/HARD/INTERMEDIATE/WET
        - lap_time: Lap time in seconds
        - s1_time, s2_time, s3_time: Sector times in seconds
        - track_temp: Track temperature (C)
        - air_temp: Air temperature (C)
        - humidity: Humidity percentage
        - rainfall: Boolean for rain
        - is_valid: True if not SC/VSC/pit in/out lap
        - lap_time_delta: Delta from stint best (target variable)
        - fuel_load_estimate: Estimated fuel load (normalized 1.0 to 0.0)
    """
    rows = []

    try:
        laps = session.laps
        if laps is None or laps.empty:
            return pd.DataFrame()

        # Get weather data if available
        weather_data = None
        try:
            if hasattr(session, "weather_data") and session.weather_data is not None:
                weather_data = session.weather_data
        except Exception:
            pass

        # Estimate total laps for fuel calculation
        total_laps = None
        try:
            total_laps = getattr(session, "total_laps", None)
            if total_laps is None:
                # Estimate from max lap number
                total_laps = int(laps["LapNumber"].max())
        except Exception:
            total_laps = 60  # Default estimate

        # Group laps by driver and stint to calculate stint-best times
        stint_bests = {}

        for _, row in laps.iterrows():
            driver = row.get("Driver", None)
            if driver is None:
                continue
            driver = str(driver)

            lap_num = row.get("LapNumber", None)
            if lap_num is None:
                continue
            lap_num = int(lap_num)

            # Get stint and compound info
            stint = int(row.get("Stint", 1)) if pd.notna(row.get("Stint")) else 1
            tyre_life = int(row.get("TyreLife", 0)) if pd.notna(row.get("TyreLife")) else 0
            compound = str(row.get("Compound", "UNKNOWN")) if pd.notna(row.get("Compound")) else "UNKNOWN"

            # Get lap time
            lap_time = _to_seconds(row.get("LapTime"))
            if lap_time is None or lap_time <= 0:
                continue

            # Get sector times
            s1 = _to_seconds(row.get("Sector1Time"))
            s2 = _to_seconds(row.get("Sector2Time"))
            s3 = _to_seconds(row.get("Sector3Time"))

            # Check if lap is valid (not pit in/out, not under safety car)
            is_pit_in = pd.notna(row.get("PitInTime"))
            is_pit_out = pd.notna(row.get("PitOutTime"))
            track_status = str(row.get("TrackStatus", "1"))

            # Track status: 1=Green, 2=Yellow, 4=SC, 6=VSC, 7=Red
            is_green = track_status in ("1", "")
            is_valid = not is_pit_in and not is_pit_out and is_green

            # Get weather for this lap (approximate by time)
            track_temp = None
            air_temp = None
            humidity = None
            rainfall = False

            if weather_data is not None and not weather_data.empty:
                try:
                    lap_start_time = row.get("LapStartTime")
                    if lap_start_time is not None and pd.notna(lap_start_time):
                        # Find closest weather reading
                        weather_times = weather_data["Time"]
                        idx = (weather_times - lap_start_time).abs().idxmin()
                        wx = weather_data.loc[idx]
                        track_temp = float(wx.get("TrackTemp", 0))
                        air_temp = float(wx.get("AirTemp", 0))
                        humidity = float(wx.get("Humidity", 0))
                        rainfall = bool(wx.get("Rainfall", False))
                except Exception:
                    pass

            # Estimate fuel load (assumes linear consumption, 1.0 at lap 1, ~0.0 at end)
            fuel_load_estimate = max(0.0, 1.0 - (lap_num / total_laps)) if total_laps else 0.5

            # Track stint best for delta calculation
            stint_key = (driver, stint)
            if is_valid:
                if stint_key not in stint_bests or lap_time < stint_bests[stint_key]:
                    stint_bests[stint_key] = lap_time

            rows.append({
                "driver": driver,
                "lap": lap_num,
                "stint": stint,
                "tyre_age": tyre_life,
                "compound": compound.upper(),
                "lap_time": lap_time,
                "s1_time": s1,
                "s2_time": s2,
                "s3_time": s3,
                "track_temp": track_temp,
                "air_temp": air_temp,
                "humidity": humidity,
                "rainfall": rainfall,
                "is_valid": is_valid,
                "fuel_load_estimate": fuel_load_estimate,
                "_stint_key": stint_key,
            })

    except Exception as e:
        print(f"Error extracting tyre features: {e}")
        return pd.DataFrame()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Calculate lap time delta from stint best
    df["lap_time_delta"] = df.apply(
        lambda r: r["lap_time"] - stint_bests.get(r["_stint_key"], r["lap_time"]),
        axis=1
    )

    # Drop internal column
    df = df.drop(columns=["_stint_key"])

    # Fill missing weather with session averages
    for col in ["track_temp", "air_temp", "humidity"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].mean())

    return df


def get_stint_summary(features_df: pd.DataFrame, driver: str) -> pd.DataFrame:
    """
    Get summary statistics for each stint of a driver.

    Args:
        features_df: DataFrame from extract_tyre_features
        driver: Driver code

    Returns:
        DataFrame with columns: stint, compound, start_lap, end_lap,
        num_laps, avg_deg_rate, best_time, worst_time
    """
    driver_data = features_df[features_df["driver"] == driver].copy()
    if driver_data.empty:
        return pd.DataFrame()

    stints = []
    for stint_num in sorted(driver_data["stint"].unique()):
        stint_data = driver_data[driver_data["stint"] == stint_num]
        valid_stint = stint_data[stint_data["is_valid"]]

        if valid_stint.empty:
            continue

        compound = valid_stint["compound"].iloc[0]
        start_lap = int(stint_data["lap"].min())
        end_lap = int(stint_data["lap"].max())
        num_laps = end_lap - start_lap + 1

        # Calculate degradation rate (slope of lap_time_delta vs tyre_age)
        deg_rate = 0.0
        if len(valid_stint) >= 3:
            try:
                x = valid_stint["tyre_age"].values
                y = valid_stint["lap_time_delta"].values
                if len(x) > 1:
                    # Simple linear regression slope
                    deg_rate = np.polyfit(x, y, 1)[0]
            except Exception:
                pass

        stints.append({
            "stint": stint_num,
            "compound": compound,
            "start_lap": start_lap,
            "end_lap": end_lap,
            "num_laps": num_laps,
            "avg_deg_rate": deg_rate,
            "best_time": valid_stint["lap_time"].min(),
            "worst_time": valid_stint["lap_time"].max(),
        })

    return pd.DataFrame(stints)


def get_compound_data(features_df: pd.DataFrame, compound: str) -> pd.DataFrame:
    """
    Get all data for a specific compound across all drivers.

    Args:
        features_df: DataFrame from extract_tyre_features
        compound: Compound name (SOFT, MEDIUM, HARD, etc.)

    Returns:
        Filtered DataFrame for the compound
    """
    return features_df[
        (features_df["compound"] == compound.upper()) &
        (features_df["is_valid"])
    ].copy()
