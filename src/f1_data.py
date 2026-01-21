# This import allows us to use forward references in type hints, i.e,
# referencing classes that are defined later in the file.
from __future__ import annotations

import os

# dataclass automatically generates __init__, __repr__, etc.
# It helps us store structured data cleanly
from dataclasses import dataclass

# List is used for type hints (List[str], etc.)
# Optional allows a value to be None
from typing import List, Optional

# FastF1 is the library that provides Formula 1 timing and telemetry data
import fastf1

import inspect

"""
This is a dataclass which is a simple container for session metadata.
Just stores information nicely
"""


@dataclass
class SessionInfo:
    # Year of the race
    year: int

    # Round number in the season (eg. 1 for Bahrain)
    round_number: int

    # Name of session (Race, Quali, Sprint)
    session_name: str

    # Name of the event (Bahrain Grand Prix)
    event_name: str

    # Name of location of the circuit
    circuit_name: str

    # List of driver abbreviations (VER, HAM)
    drivers: List[str]

    # Total laps in the race (None for non-race sessions)
    total_laps: Optional[int] = None


"""
This function enables fastf1 caching. 
Required the cache directory to exist before enabling it
"""


def enable_cache(cache_dir: str = ".fastf1-cache") -> str:
    # Create the cache diectory if it does not exist
    os.makedirs(cache_dir, exist_ok=True)

    # Tell fastf1 to use this directory for caching downloaded data
    fastf1.Cache.enable_cache(cache_dir)

    # Return the cache directory path (useful for loggin and debugging)
    return cache_dir


def load_session(
    year: int,
    round_number: int,
    session_type: str = "R",  # (Race)
    *,
    telemetry: bool = True,  # Whether to load telemetry data
    weather: bool = True,  # Whether to load weather data
    messages: bool = True,  # Whether to load race control messages
    force_reload: bool = False,  # Force re-download even if cached
):
    """
    session_type examples:
        R = Race
        S = Sprint
        Q = Qualifying
        FP1, FP2, FP3
    """

    # Get the session object (no download yet)
    session = fastf1.get_session(year, round_number, session_type)

    # Build kwargs we want to pass into session.load()
    load_kwargs = {
        "telemetry": telemetry,
        "weather": weather,
        "messages": messages,
    }

    # Find which parameters session.load() actually supports in YOUR installed version
    supported_params = set(inspect.signature(session.load).parameters.keys())

    # Only pass keys that exist in this version of FastF1
    safe_kwargs = {k: v for k, v in load_kwargs.items() if k in supported_params}

    # NOTE: force reload varies by version, so we DON'T pass force=...
    # We'll just load normally; later we can add a cache-clear option if needed.
    session.load(**safe_kwargs)

    return session


"""
This function extracts readable metadata from a loaded session
"""


def get_driver_status(session) -> dict:
    """
    Get driver finishing status from session results.

    Returns:
        dict[driver_code] = status_string
        e.g. {"VER": "Finished", "HAM": "Retired", "RUS": "+1 Lap"}
    """
    status_map = {}
    try:
        results = session.results
        if results is None or results.empty:
            return status_map

        for _, row in results.iterrows():
            # Get driver abbreviation
            abbrev = row.get("Abbreviation", None)
            if abbrev is None:
                continue

            # Get status
            status = row.get("Status", "Unknown")
            status_map[str(abbrev)] = str(status)
    except Exception:
        pass

    return status_map


def get_session_info(session) -> SessionInfo:
    # Try to get event name safely, some seasons store it differently,
    # so we guard with getattr
    event_name = getattr(session.event, "EventName", None) or getattr(
        session.event, "EventName", "Unknown Event"
    )

    # Try to get circuit name or location
    circuit_name = getattr(session.event, "Location", None) or getattr(
        session.event, "CircuitName", "Unknown Circuit"
    )

    # sessions.drivers gives driver NUMBERS as strings (eg. "1", "44")
    drivers = list(session.drivers)

    # This list will store the driver abbreviations (VER, HAM)
    codes: List[str] = []

    # Loop over each driver number
    for d in drivers:
        try:
            # Convert driver number to driver info dict
            # Then extract abbreviation
            codes.append(session.get_driver(d)["Abbreviation"])
        except Exception:
            # Fall back in case something goes wrong
            codes.append(str(d))

    # Try to get total laps for race sessions
    total_laps = None
    try:
        total_laps = getattr(session, "total_laps", None)
        if total_laps is None:
            # Try alternative attribute names
            total_laps = getattr(session, "TotalLaps", None)
        if total_laps is not None:
            total_laps = int(total_laps)
    except Exception:
        pass

    # Create and return a SessionInfo object
    return SessionInfo(
        # Extract year from the event date
        year=int(session.event["EventDate"].year)
        if "EventDate" in session.event
        else -1,
        # Extract round number
        round_number=int(session.event["RoundNumber"])
        if "RoundNumber" in session.event
        else -1,
        # Name of the session (Race, Qualifying)
        session_name=str(session.name),
        # Event name string
        event_name=str(event_name),
        # Circuit name string
        circuit_name=str(circuit_name),
        # Sorted unique list of driver abbreviations
        drivers=sorted(set(codes)),
        # Total laps
        total_laps=total_laps,
    )


def extract_race_control_messages(session) -> dict:
    """
    Extract race control messages from session.

    Returns:
        dict with keys:
        - "track_status": list of {"t": float, "status": str, "message": str}
        - "blue_flags": list of {"t": float, "driver": str, "message": str}
        - "penalties": list of {"t": float, "driver": str, "message": str}
        - "track_limits": list of {"t": float, "driver": str, "message": str}
    """
    result = {
        "track_status": [],
        "blue_flags": [],
        "penalties": [],
        "track_limits": [],
    }

    try:
        rcm = session.race_control_messages
        if rcm is None or rcm.empty:
            return result

        for _, row in rcm.iterrows():
            # Get time in seconds
            time_val = row.get("Time", None)
            if time_val is None:
                continue
            t = time_val.total_seconds() if hasattr(time_val, "total_seconds") else float(time_val)

            category = str(row.get("Category", "")).upper()
            message = str(row.get("Message", ""))
            flag = str(row.get("Flag", "")).upper()
            driver = row.get("RacingNumber", None)

            # Track status changes (flags, safety car)
            if category == "FLAG" or "SAFETY CAR" in message.upper() or "VSC" in message.upper():
                status = "GREEN"
                if flag == "YELLOW" or "YELLOW" in message.upper():
                    status = "YELLOW"
                elif flag == "RED" or "RED FLAG" in message.upper():
                    status = "RED"
                elif "SAFETY CAR" in message.upper() and "VIRTUAL" not in message.upper():
                    status = "SC"
                elif "VSC" in message.upper() or "VIRTUAL SAFETY CAR" in message.upper():
                    status = "VSC"
                elif flag == "GREEN" or "GREEN" in message.upper():
                    status = "GREEN"

                result["track_status"].append({
                    "t": t,
                    "status": status,
                    "message": message,
                })

            # Blue flags
            if flag == "BLUE" or "BLUE FLAG" in message.upper():
                result["blue_flags"].append({
                    "t": t,
                    "driver": str(driver) if driver else "",
                    "message": message,
                })

            # Penalties
            if "PENALTY" in message.upper() or "TIME PENALTY" in message.upper():
                result["penalties"].append({
                    "t": t,
                    "driver": str(driver) if driver else "",
                    "message": message,
                })

            # Track limits
            if "TRACK LIMITS" in message.upper() or "DELETED" in message.upper():
                result["track_limits"].append({
                    "t": t,
                    "driver": str(driver) if driver else "",
                    "message": message,
                })

    except Exception:
        pass

    # Sort all lists by time
    for key in result:
        result[key].sort(key=lambda x: x["t"])

    return result


def extract_sector_times(session) -> tuple:
    """
    Extract sector times from session laps.

    Returns:
        tuple of (driver_sectors, overall_bests)

        driver_sectors: dict[driver_code][lap_number] = {
            "s1": float | None,
            "s2": float | None,
            "s3": float | None,
            "s1_time": float | None,  # Session time when S1 completed
            "s2_time": float | None,
            "s3_time": float | None,
            "lap_time": float | None,
            "is_pb": bool
        }

        overall_bests: {
            "s1": float | None,
            "s2": float | None,
            "s3": float | None,
            "lap": float | None,
            "fastest_driver": str | None,
            "fastest_lap_num": int | None
        }
    """
    driver_sectors = {}
    overall_bests = {
        "s1": None,
        "s2": None,
        "s3": None,
        "lap": None,
        "fastest_driver": None,
        "fastest_lap_num": None,
    }

    try:
        laps = session.laps
        if laps is None or laps.empty:
            return driver_sectors, overall_bests

        for _, row in laps.iterrows():
            driver = row.get("Driver", None)
            if driver is None:
                continue
            driver = str(driver)

            lap_num = row.get("LapNumber", None)
            if lap_num is None:
                continue
            lap_num = int(lap_num)

            if driver not in driver_sectors:
                driver_sectors[driver] = {}

            # Extract sector times (convert timedelta to seconds)
            def to_seconds(val):
                if val is None or (hasattr(val, "total_seconds") and val != val):  # NaT check
                    return None
                if hasattr(val, "total_seconds"):
                    return val.total_seconds()
                try:
                    return float(val)
                except Exception:
                    return None

            s1 = to_seconds(row.get("Sector1Time", None))
            s2 = to_seconds(row.get("Sector2Time", None))
            s3 = to_seconds(row.get("Sector3Time", None))
            lap_time = to_seconds(row.get("LapTime", None))

            s1_session = to_seconds(row.get("Sector1SessionTime", None))
            s2_session = to_seconds(row.get("Sector2SessionTime", None))
            s3_session = to_seconds(row.get("Sector3SessionTime", None))

            is_pb = bool(row.get("IsPersonalBest", False))

            driver_sectors[driver][lap_num] = {
                "s1": s1,
                "s2": s2,
                "s3": s3,
                "s1_time": s1_session,
                "s2_time": s2_session,
                "s3_time": s3_session,
                "lap_time": lap_time,
                "is_pb": is_pb,
            }

            # Update overall bests
            if s1 is not None and (overall_bests["s1"] is None or s1 < overall_bests["s1"]):
                overall_bests["s1"] = s1
            if s2 is not None and (overall_bests["s2"] is None or s2 < overall_bests["s2"]):
                overall_bests["s2"] = s2
            if s3 is not None and (overall_bests["s3"] is None or s3 < overall_bests["s3"]):
                overall_bests["s3"] = s3
            if lap_time is not None and (overall_bests["lap"] is None or lap_time < overall_bests["lap"]):
                overall_bests["lap"] = lap_time
                overall_bests["fastest_driver"] = driver
                overall_bests["fastest_lap_num"] = lap_num

    except Exception:
        pass

    return driver_sectors, overall_bests


def extract_pit_stops(session) -> dict:
    """
    Extract pit stop data from session laps.

    Returns:
        dict with keys:
        - "pit_stops": list of pit stop events sorted by time
        - "stints": dict[driver] = list of stint info
        - "max_speeds": dict[driver][lap] = max_speed
    """
    result = {
        "pit_stops": [],
        "stints": {},
        "max_speeds": {},
        "top_speeds": [],  # Top speeds overall
    }

    try:
        laps = session.laps
        if laps is None or laps.empty:
            return result

        # Track pit stops and stints per driver
        driver_pits = {}
        driver_stints = {}
        driver_max_speeds = {}

        for _, row in laps.iterrows():
            driver = row.get("Driver", None)
            if driver is None:
                continue
            driver = str(driver)

            lap_num = row.get("LapNumber", None)
            if lap_num is None:
                continue
            lap_num = int(lap_num)

            # Initialize driver data
            if driver not in driver_pits:
                driver_pits[driver] = []
            if driver not in driver_stints:
                driver_stints[driver] = []
            if driver not in driver_max_speeds:
                driver_max_speeds[driver] = {}

            # Check for pit stop (PitInTime or PitOutTime present)
            pit_in = row.get("PitInTime", None)
            pit_out = row.get("PitOutTime", None)

            def to_seconds(val):
                if val is None or (hasattr(val, "total_seconds") and val != val):
                    return None
                if hasattr(val, "total_seconds"):
                    return val.total_seconds()
                try:
                    return float(val)
                except Exception:
                    return None

            pit_in_t = to_seconds(pit_in)
            pit_out_t = to_seconds(pit_out)

            if pit_in_t is not None or pit_out_t is not None:
                compound = str(row.get("Compound", "")) or None
                stint = int(row.get("Stint", 1)) if row.get("Stint") is not None else 1

                duration = None
                if pit_in_t is not None and pit_out_t is not None:
                    duration = pit_out_t - pit_in_t

                driver_pits[driver].append({
                    "t_in": pit_in_t,
                    "t_out": pit_out_t,
                    "duration": duration,
                    "driver": driver,
                    "lap": lap_num,
                    "compound": compound,
                    "stint": stint,
                })

            # Track stint info
            stint_num = int(row.get("Stint", 1)) if row.get("Stint") is not None else 1
            tyre_life = int(row.get("TyreLife", 0)) if row.get("TyreLife") is not None else 0
            compound = str(row.get("Compound", "")) or None

            # Update or add stint
            if stint_num > len(driver_stints[driver]):
                driver_stints[driver].append({
                    "stint": stint_num,
                    "compound": compound,
                    "start_lap": lap_num,
                    "end_lap": lap_num,
                    "tyre_life": tyre_life,
                })
            else:
                idx = stint_num - 1
                if 0 <= idx < len(driver_stints[driver]):
                    driver_stints[driver][idx]["end_lap"] = lap_num
                    driver_stints[driver][idx]["tyre_life"] = tyre_life

            # Track max speed per lap from SpeedST (speed trap) if available
            speed_st = row.get("SpeedST", None)
            if speed_st is not None:
                try:
                    max_spd = float(speed_st)
                    if max_spd > 0:
                        driver_max_speeds[driver][lap_num] = max_spd
                except (ValueError, TypeError):
                    pass

        # Consolidate pit stops
        all_pits = []
        for driver, pits in driver_pits.items():
            all_pits.extend(pits)
        all_pits.sort(key=lambda x: x["t_in"] or x["t_out"] or 0)

        result["pit_stops"] = all_pits
        result["stints"] = driver_stints
        result["max_speeds"] = driver_max_speeds

        # Calculate top speeds
        all_speeds = []
        for driver, laps_speeds in driver_max_speeds.items():
            for lap, speed in laps_speeds.items():
                all_speeds.append({"driver": driver, "lap": lap, "speed": speed})
        all_speeds.sort(key=lambda x: x["speed"], reverse=True)
        result["top_speeds"] = all_speeds[:10]  # Top 10

    except Exception:
        pass

    return result
