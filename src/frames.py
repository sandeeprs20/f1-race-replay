import numpy as np


def _norm_lap_distance(dist: float, lap_length: float) -> float:
    """
    Keep distance within a lap in [0, lap_length).
    Prevents weird ordering when distance wraps or slightly exceeds lap length.
    """
    if lap_length <= 0:
        return dist
    return dist % lap_length


def _get_track_status_at_time(t: float, track_status_list: list) -> str:
    """
    Get the track status (GREEN/YELLOW/RED/SC/VSC) at a given time.
    Returns the most recent status before or at time t.
    """
    if not track_status_list:
        return "GREEN"

    current_status = "GREEN"
    for status_entry in track_status_list:
        if status_entry["t"] <= t:
            current_status = status_entry["status"]
        else:
            break
    return current_status


def _get_active_messages(t: float, race_control: dict, message_duration: float = 10.0) -> list:
    """
    Get race director messages active at time t (within message_duration seconds).
    """
    messages = []

    # Blue flags
    for msg in race_control.get("blue_flags", []):
        age = t - msg["t"]
        if 0 <= age <= message_duration:
            messages.append({
                "type": "blue_flag",
                "driver": msg.get("driver", ""),
                "message": msg.get("message", "BLUE FLAG"),
                "age": age,
            })

    # Penalties
    for msg in race_control.get("penalties", []):
        age = t - msg["t"]
        if 0 <= age <= message_duration:
            messages.append({
                "type": "penalty",
                "driver": msg.get("driver", ""),
                "message": msg.get("message", "PENALTY"),
                "age": age,
            })

    # Track limits
    for msg in race_control.get("track_limits", []):
        age = t - msg["t"]
        if 0 <= age <= message_duration:
            messages.append({
                "type": "track_limit",
                "driver": msg.get("driver", ""),
                "message": msg.get("message", "TRACK LIMITS"),
                "age": age,
            })

    # Sort by age (most recent first)
    messages.sort(key=lambda x: x["age"])
    return messages[:5]  # Limit to 5 most recent


def build_frames(
    resampled: dict,
    timeline: np.ndarray,
    lap_length: float,
    tyre_map: dict | None = None,
    weather_data=None,
    race_control: dict | None = None,
    sector_data: tuple | None = None,
    pit_data: dict | None = None,
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
        race_control: dict with track_status, blue_flags, penalties, track_limits (optional)
        sector_data: tuple of (driver_sectors, overall_bests) (optional)
        pit_data: dict with pit_stops, stints, max_speeds (optional)
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

    # Unpack sector data
    driver_sectors = {}
    overall_bests = {"s1": None, "s2": None, "s3": None, "lap": None, "fastest_driver": None, "fastest_lap_num": None}
    if sector_data is not None:
        driver_sectors, overall_bests = sector_data

    # Unpack pit data
    stints_data = {}
    if pit_data is not None:
        stints_data = pit_data.get("stints", {})

    # Track status list for lookup
    track_status_list = []
    if race_control is not None:
        track_status_list = race_control.get("track_status", [])

    # Build a list of fastest lap events (when each new fastest lap was set)
    # This tracks the progression of fastest laps during the session
    fastest_lap_events = []  # [(session_time, driver, lap_time, lap_num), ...]
    current_fastest = float("inf")

    if driver_sectors:
        all_lap_completions = []
        for drv, laps in driver_sectors.items():
            for lap_num, lap_data in laps.items():
                lap_time = lap_data.get("lap_time")
                s3_time = lap_data.get("s3_time")  # When lap was completed
                if lap_time is not None and s3_time is not None and lap_time > 0:
                    all_lap_completions.append((s3_time, drv, lap_time, lap_num))

        # Sort by completion time
        all_lap_completions.sort(key=lambda x: x[0])

        # Track when fastest lap improved
        for s3_time, drv, lap_time, lap_num in all_lap_completions:
            if lap_time < current_fastest:
                current_fastest = lap_time
                fastest_lap_events.append({
                    "time": s3_time,
                    "driver": drv,
                    "lap_time": lap_time,
                    "lap_num": lap_num,
                })

    # Track previous positions for overtake detection
    prev_positions = {}

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

        # Detect position changes (overtakes)
        position_changes = []
        if prev_positions:
            for d in drivers:
                curr_pos = positions.get(d, 0)
                prev_pos = prev_positions.get(d, curr_pos)
                if curr_pos < prev_pos:  # Driver gained position
                    # Find who they passed
                    passed_driver = None
                    for other_d, other_pos in positions.items():
                        if other_d != d and other_pos == curr_pos + 1:
                            # Check if this driver was ahead before
                            if prev_positions.get(other_d, 0) < prev_pos:
                                passed_driver = other_d
                                break
                    position_changes.append({
                        "driver": d,
                        "from_pos": prev_pos,
                        "to_pos": curr_pos,
                        "passed": passed_driver,
                        "t": t,
                    })

        prev_positions = positions.copy()

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

            # Add sector times for current lap
            if d in driver_sectors and lap_i in driver_sectors[d]:
                lap_sector_data = driver_sectors[d][lap_i]
                st["sector_times"] = {
                    "s1": lap_sector_data.get("s1"),
                    "s2": lap_sector_data.get("s2"),
                    "s3": lap_sector_data.get("s3"),
                }
                st["lap_time"] = lap_sector_data.get("lap_time")
            else:
                st["sector_times"] = {"s1": None, "s2": None, "s3": None}
                st["lap_time"] = None

            # Add stint/tyre strategy info
            driver_stints = stints_data.get(d, [])
            current_stint = 1
            tyre_life = 0
            pit_count = 0

            for stint_info in driver_stints:
                if stint_info["start_lap"] <= lap_i <= stint_info["end_lap"]:
                    current_stint = stint_info["stint"]
                    # Calculate tyre life as laps since stint start
                    tyre_life = lap_i - stint_info["start_lap"] + 1
                    break
                elif stint_info["start_lap"] > lap_i:
                    break

            pit_count = max(0, current_stint - 1)

            st["stint"] = current_stint
            st["tyre_life"] = tyre_life
            st["pit_count"] = pit_count

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

        # Get track status at this time
        track_status = _get_track_status_at_time(t, track_status_list)

        # Get active race director messages
        race_messages = []
        if race_control is not None:
            race_messages = _get_active_messages(t, race_control)

        # Fastest lap info (for banner)
        # Find the current fastest lap at this point in time
        current_fl_driver = None
        current_fl_time = None
        current_fl_lap = None
        fl_set_time = None

        for event in fastest_lap_events:
            if event["time"] <= t:
                current_fl_driver = event["driver"]
                current_fl_time = event["lap_time"]
                current_fl_lap = event["lap_num"]
                fl_set_time = event["time"]
            else:
                break  # Events are sorted by time

        fastest_lap_info = {
            "driver": current_fl_driver,
            "time": current_fl_time,
            "lap_num": current_fl_lap,
            "is_new": False,  # True if just set (within 5 seconds)
        }

        # Mark as new if the fastest lap was set within the last 5 seconds
        if fl_set_time is not None and 0 <= (t - fl_set_time) <= 5.0:
            fastest_lap_info["is_new"] = True

        frames.append({
            "t": t,
            "drivers": driver_states,
            "weather": weather_dict,
            "track_status": track_status,
            "race_messages": race_messages,
            "fastest_lap": fastest_lap_info,
            "position_changes": position_changes,
            "overall_bests": overall_bests,
        })

    return frames
