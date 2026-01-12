"""
REPLAY TIME RESAMPLING DESIGN NOTES
==================================

FastF1 telemetry is sampled at irregular timestamps and differs per driver.
However, a replay/animation system requires a fixed-rate global clock
(e.g. 25 frames per second), where every driver has exactly one state
at every frame.

To solve this, we resample all telemetry onto a shared timeline.

---------------------------------------------------------------------------
WHY INTERPOLATION IS REQUIRED (CONTINUOUS VALUES)
---------------------------------------------------------------------------

Some telemetry values represent continuous, smoothly changing quantities:
  - X, Y position on track
  - Speed
  - Distance traveled along the lap

Between two telemetry samples, these values change gradually in the real
world. If we were to simply select the nearest telemetry point for each
frame, cars would appear to "teleport" and motion would be jerky.

For these values, we use linear interpolation:
  - Given values at t1 and t2, estimate the value at any time t in between
  - This produces smooth, physically reasonable motion

These values are interpolated using numpy.interp().

---------------------------------------------------------------------------
WHY STEPWISE RESAMPLING IS REQUIRED (DISCRETE STATES)
---------------------------------------------------------------------------

Other telemetry values represent discrete states, not continuous quantities:
  - Gear (integer)
  - DRS (on/off)
  - Lap number

Interpolating these values would produce invalid states
(e.g. gear = 6.7, lap = 1.4), which do not make sense physically.

For discrete states, the correct behavior is:
  - The value remains constant until a change occurs
  - At any given time, use the most recent known value

This is implemented using a stepwise ("last known value") strategy:
  - For each replay frame time t, select the telemetry value whose timestamp
    is the latest time <= t


Continuous values:
  - Interpolated linearly for smooth motion

Discrete values:
  - Resampled stepwise to preserve valid states

This separation is critical for:
  - Smooth and realistic replay animation
  - Correct lap counting and DRS behavior
  - Accurate race order computation
  - Reliable downstream analysis (strategy, ML features, etc.)

Mixing these approaches (e.g. interpolating gears or stepwise positions)
would break realism and correctness.
"""

import numpy as np


def build_global_timeline(all_driver_tel: dict, fps: int = 25):
    """
    Build a shared time axis for the whole session.

    Args:
        all_driver_tel (dict)
        fps (int, optional): Defaults to 25.
    """
    # Collect each driver's start and end time
    starts = []
    ends = []

    for drv, tel in all_driver_tel.items():
        t = tel.get("time", None)
        if t is None or len(t) < 2:
            continue

        t0 = float(t[0])
        t1 = float(t[-1])

        if not np.isfinite(t0) or not np.isfinite(t1):
            continue
        if t1 <= t0:
            continue

        starts.append(t0)
        ends.append(t1)

    if not starts:
        raise ValueError("No valid driver telemetry ranges found to build timeline.")

    # UNION window
    t0 = float(min(starts))
    t1 = float(max(ends))

    dt = 1.0 / fps
    duration = t1 - t0

    # If duration is extremely tiny, still build at least 1 frame
    if duration <= 0:
        return np.array([0.0], dtype=np.float64), t0, t1

    timeline = np.arange(0.0, duration + dt, dt, dtype=np.float64)
    return timeline, t0, t1


def _interp_float(t_src, v_src, t_dst):
    """
    Interpolate continuous values (s, y, speed, distance)
    Uses linear interpolation
    """

    return np.interp(t_dst, t_src, v_src).astype(np.float64)


def _interp_stepwise(t_src, v_src, t_dst):
    """
    Resample discrete balues (gear, drs, lap) in a 'last know value' manner.
    This avoids wierd fractional gears (like 4.6).

    For each t in t_dst, take the value from the latest t_src <= t
    """

    # Find insertion indices
    idx = np.searchsorted(t_src, t_dst, side="right") - 1

    # Clamp indices to valid range
    idx = np.clip(idx, 0, len(v_src) - 1)

    # Pick values
    return v_src[idx]


# We need to add this to src/replay_clock.py if it doesn't exist


def resample_driver(driver_telemetry, timeline, t0):
    """
    Resample a single driver's telemetry to the global timeline.

    Args:
        driver_telemetry: dict with keys 'time', 'x', 'y', 'speed', etc.
        timeline: global timeline array (seconds)
        t0: time offset (usually min start time)

    Returns:
        dict: resampled telemetry matching timeline
    """

    # Adjust driver's time to be relative to t0
    driver_time = driver_telemetry["time"] - t0

    resampled = {}

    for key in driver_telemetry.keys():
        if key == "time":
            continue  # Don't resample time itself

        # Interpolate each channel to the global timeline
        resampled[key] = np.interp(
            timeline, driver_time, driver_telemetry[key], left=np.nan, right=np.nan
        )

    return resampled


def resample_all_drivers(all_driver_tel: dict, timeline: np.ndarray, t0: float):
    """
    Resample every driver's telemetry onto the global timeline

    timeline starts at 0
    t0: global start tiem in orginal session time seconds

    """

    # Convert replay timeline back into absolute session time
    t_abs = timeline + t0

    resampled = {}

    for drv, tel in all_driver_tel.items():
        t_src = tel["time"]

        # If a driver has too little data, skip
        if len(t_src) < 2:
            continue

        # Create a new dict for this driver
        out = {}

        # Continuous values -> linear interpolation
        out["x"] = _interp_float(t_src, tel["x"], t_abs)
        out["y"] = _interp_float(t_src, tel["y"], t_abs)
        out["distance"] = _interp_float(t_src, tel["distance"], t_abs)
        out["speed"] = _interp_float(t_src, tel["speed"], t_abs)
        out["throttle"] = _interp_float(t_src, tel["throttle"], t_abs)
        out["brake"] = _interp_float(t_src, tel["brake"], t_abs)

        # Discrete values -> stepwise
        out["gear"] = _interp_stepwise(t_src, tel["gear"], t_abs).astype(np.int16)
        out["drs"] = _interp_stepwise(t_src, tel["drs"], t_abs).astype(np.int16)
        out["lap"] = _interp_stepwise(t_src, tel["lap"], t_abs).astype(np.int16)

        # also store absolute and replay time
        out["time_abs"] = t_abs
        out["time"] = timeline

        resampled[drv] = out

    return resampled
