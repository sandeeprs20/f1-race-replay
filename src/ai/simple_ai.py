"""
Simple AI - uses the fastest lap from the session as AI baseline.
            Basically copies best human performance
"""

import numpy as np


def generate_ai_lap_from_fastest(session):
    """
    Takes the fastest lap and returns it as AI telemetry

    What you're doing:
    1. Find the fastest lap in the session
    2. Get its telemetry
    3. Convert it to the format your replay system expects
    """
    try:
        # Getting fastest lap from session.laps
        fastest_lap = session.laps.pick_fastest()

        # Step 2: Get detailed telemetry for that lap
        # This includes X, Y, Speed, Throttle, Break, etc
        telemetry = fastest_lap.get_telemetry()

        # Step 3: Extract metadata about the lap
        lap_time = fastest_lap["LapTime"].total_seconds()
        driver = fastest_lap["Driver"]

        print(f"\n=== AI RACER GENERATED ===")
        print(f"Based on: {driver}'s fastest lap")
        print(f"Lap time: {lap_time:.3f}s")
        print(f"Telemetry points: {len(telemetry)}")

        # Step 4: Convert to the format the replay system
        # expects from telemetry.py

        ai_telemetry = {
            "time": telemetry["SessionTime"].dt.total_seconds().to_numpy(),
            "x": telemetry["X"].to_numpy(),
            "y": telemetry["Y"].to_numpy(),
            "distance": telemetry["Distance"].to_numpy(),
            "speed": telemetry["Speed"].to_numpy(),
            "gear": telemetry["nGear"].to_numpy(),
            "drs": telemetry["DRS"].to_numpy(),
            "lap": np.ones(len(telemetry), dtype=np.int32),
            "throttle": telemetry["Throttle"].to_numpy(dtype=np.float64),
            "brake": telemetry["Brake"].to_numpy(dtype=np.float64),
        }

        return ai_telemetry
    except Exception as e:
        print(f"Error generating AI lap: {e}")
        print(f"No valid fastest lap was found")
        return None


def generate_ai_lap_from_driver(session, driver_code):
    """
    Creates AI telemetry from a specific driver's fastest lap
    Useful if you want AI to minic a particular driver

    Args:
        session: FastF1 session object
        driver_code: Driver abbreviation
    """

    try:
        # Get all laps from specified driver
        driver_laps = session.laps.pick_drivers(driver_code)

        if driver_laps.empty:
            print(f"No laps found for driver {driver_code}")
            return None

        # find their fastest lap
        fastest_lap = driver_laps.pick_fastest()
        telemetry = fastest_lap.get_telemetry()

        lap_time = fastest_lap["LapTime"].total_seconds()

        print(f"\n=== AI RACER GENERATED ===")
        print(f"Based on: {driver_code}'s fastest lap")
        print(f"Lap time: {lap_time:.3f}s")

        ai_telemetry = {
            "time": telemetry["SessionTime"].dt.total_seconds().to_numpy(),
            "x": telemetry["X"].to_numpy(),
            "y": telemetry["Y"].to_numpy(),
            "distance": telemetry["Distance"].to_numpy(),
            "speed": telemetry["Speed"].to_numpy(),
            "gear": telemetry["nGear"].to_numpy(),
            "drs": telemetry["DRS"].to_numpy(),
            "lap": np.ones(len(telemetry), dtype=np.int32),
            "throttle": telemetry["Throttle"].to_numpy(dtype=np.float64),
            "brake": telemetry["Brake"].to_numpy(dtype=np.float64),
        }
        return ai_telemetry

    except Exception as e:
        print(f"Error generating AI lap from {driver_code}: {e}")
        return None


def get_fastest_lap_info(session):
    """
    Utility function to get information about the fastest lap
    without generating full telemetry. Useful for debugging.

    Returns:
        dict with lap info or None
    """

    try:
        fastest = session.laps.pick_fastest()

        info = {
            "driver": fastest["Driver"],
            "lap_number": fastest["LapNumber"],
            "lap_time": fastest["LapTime"].total_seconds(),
            "team": fastest["Team"],
            "compound": fastest.get("Compound", "Unknown"),
        }

        return info

    except Exception as e:
        print(f"Error getting fastest lap info: {e}")
        return None
