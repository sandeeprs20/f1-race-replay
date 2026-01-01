import numpy as np


def _norm_lap_distance(dist: float, lap_length: float) -> float:
    """
    Keep distance within a lap in [0, lap_length).
    Prevents weird ordering when distance wraps or slightly exceeds lap length.
    """
    if lap_length <= 0:
        return dist
    return dist % lap_length


def build_frames(
    resampled: dict,
    timeline: np.ndarray,
    lap_length: float,
    tyre_map: dict | None = None,
    weather_data=None,
):
    """
    Build per-frame driver states + compute positions.

    Correct position metric (robust across lap resets):
        progress = (lap_i - 1) * lap_length + (distance % lap_length)

    Args:
        resampled: dict[drv] -> arrays (x,y,distance,speed,lap,gear,drs,throttle,brake,...)
        timeline: replay time axis (seconds), shape (N,)
        lap_length: estimated lap length in meters
        tyre_map: dict[drv][lap_number] -> compound string (e.g., "SOFT", "MEDIUM", ...)
        weather_data: pandas DataFrame with weather information (optional)
    """
    n_frames = len(timeline)
    drivers = list(resampled.keys())

    # Pull arrays once (faster than indexing dict repeatedly)
    x_by = {d: resampled[d]["x"] for d in drivers}
    y_by = {d: resampled[d]["y"] for d in drivers}
    speed_by = {d: resampled[d]["speed"] for d in drivers}
    dist_by = {d: resampled[d]["distance"] for d in drivers}
    lap_by = {d: resampled[d]["lap"] for d in drivers}
    gear_by = {d: resampled[d]["gear"] for d in drivers}
    drs_by = {d: resampled[d]["drs"] for d in drivers}

    throttle_by = {d: resampled[d].get("throttle", None) for d in drivers}
    brake_by = {d: resampled[d].get("brake", None) for d in drivers}

    frames = []

    for i in range(n_frames):
        t = float(timeline[i])

        # Compute progress for ordering
        progress_list = []
        for d in drivers:
            lap_i = int(lap_by[d][i])
            if lap_i < 1:
                lap_i = 1

            dist_i = float(dist_by[d][i])
            lap_dist = _norm_lap_distance(dist_i, lap_length)
            progress = float((lap_i - 1) * lap_length + lap_dist)

            progress_list.append((d, progress))

        # Sort leader first
        progress_list.sort(key=lambda x: x[1], reverse=True)

        positions = {drv: pos for pos, (drv, _) in enumerate(progress_list, start=1)}
        prog_map = {drv: prog for drv, prog in progress_list}

        driver_states = {}

        for d in drivers:
            lap_i = int(lap_by[d][i])
            if lap_i < 1:
                lap_i = 1

            compound = None
            if tyre_map is not None:
                compound = tyre_map.get(d, {}).get(lap_i, None)

            st = {
                "x": float(x_by[d][i]),
                "y": float(y_by[d][i]),
                "speed": float(speed_by[d][i]),
                "distance": float(dist_by[d][i]),
                "lap": int(lap_i),
                "gear": int(gear_by[d][i]),
                "drs": int(drs_by[d][i]),
                "progress": float(prog_map[d]),
                "pos": int(positions[d]),
                "compound": compound,  # used by leaderboard tyre icons
            }

            # Optional inputs
            if throttle_by[d] is not None:
                st["throttle"] = float(throttle_by[d][i])
            if brake_by[d] is not None:
                st["brake"] = float(brake_by[d][i])

            driver_states[d] = st

        # Add weather data for this frame if available
        weather_dict = {}
        if weather_data is not None and not weather_data.empty:
            # Find closest weather entry to current time
            import pandas as pd

            t_delta = pd.Timedelta(seconds=t)
            idx = (weather_data["Time"] - t_delta).abs().idxmin()
            weather_row = weather_data.loc[idx]
            weather_dict = {
                "AirTemp": float(weather_row.get("AirTemp", 0)),
                "TrackTemp": float(weather_row.get("TrackTemp", 0)),
                "Humidity": float(weather_row.get("Humidity", 0)),
                "Rainfall": bool(weather_row.get("Rainfall", False)),
            }

        frames.append({"t": t, "drivers": driver_states, "weather": weather_dict})

    return frames
