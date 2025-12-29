import numpy as np
import pandas as pd


def extract_driver_telemetry(session):
    """
    Extract and stitch telemetry for each driver in the session
    """

    # Dictionary that will hold telemetry for all drivers
    all_drivers_telemetry = {}

    # loop over driver numbers
    for driver_number in session.drivers:
        # Get driver metadata (name, abbreviation, etc.)
        driver_info = session.get_driver(driver_number)

        # Extract driver abbreviation (VER, HAM)
        driver_code = driver_info["Abbreviation"]

        # Get all laps driven by this driver
        driver_laps = session.laps.pick_drivers(driver_number)

        # If the driver has no laps (DNFF or data issue), skip them
        if driver_laps.empty:
            continue

        # Lists to collect telemetry accross all laps
        times = []
        xs = []
        ys = []
        distances = []
        speeds = []
        gears = []
        drs = []
        laps = []

        # Looping through each lap
        for _, lap in driver_laps.iterrows():
            try:
                # Get telemetry for this lap
                tel = lap.get_telemetry()

                if tel.empty:
                    continue

                # Appending telemetry values
                times.append(tel["SessionTime"].dt.total_seconds().to_numpy())
                xs.append(tel["X"].to_numpy())
                ys.append(tel["Y"].to_numpy())
                distances.append(tel["Distance"].to_numpy())
                speeds.append(tel["Speed"].to_numpy())
                gears.append(tel["nGear"].to_numpy())
                drs.append(tel["DRS"].to_numpy())

                # Lap number must be repeated for each telemetry point
                laps.append(np.full(len(tel), lap["LapNumber"]))

            except Exception:
                # If any lap fails, skip it safely
                continue

        # If no telemetry was collected, skip the driver
        if not times:
            continue

        # Concatenate lap wise arrays into one long array
        driver_data = {
            "time": np.concatenate(times),
            "x": np.concatenate(xs),
            "y": np.concatenate(ys),
            "distance": np.concatenate(distances),
            "speed": np.concatenate(speeds),
            "gear": np.concatenate(gears),
            "drs": np.concatenate(drs),
            "lap": np.concatenate(laps),
        }

        # Sort telemetry by time (CRITICAL)
        order = np.argsort(driver_data["time"])
        for key in driver_data:
            driver_data[key] = driver_data[key][order]

        # Ensure time is strictly non-decreasing (sanity check)
        if (np.diff(driver_data["time"]) < 0).any():
            raise ValueError(f"Time ordering failed for {driver_code}")

        # Store telemetry under driver code
        all_drivers_telemetry[driver_code] = driver_data

    return all_drivers_telemetry
