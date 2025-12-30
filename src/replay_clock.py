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
        if len(tel["time"]) == 0:
            continue

        starts.append(tel["time"][0])
        ends.append(tel["time"][-1])

    # Global start time is the earliest telemetry we have
    t0 = float(max(starts))

    # Global end time is the latest telemetry we have
    t1 = float(min(ends))

    # Fixed timestep for FPS
    dt = 1.0 / fps

    # Build timeline from 0 -> (t1 - t0)
    # We subtract t0 so the replay always starts at t = 0
    timeline = np.arange(0.0, (t1 - t0) + dt, dt, dtype=np.float64)

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

        # Discrete values -> stepwise
        out["gear"] = _interp_stepwise(t_src, tel["gear"], t_abs).astype(np.int16)
        out["drs"] = _interp_stepwise(t_src, tel["drs"], t_abs).astype(np.int16)
        out["lap"] = _interp_stepwise(t_src, tel["lap"], t_abs).astype(np.int16)

        # also store absolute and replay time
        out["time_abs"] = t_abs
        out["time"] = timeline

        resampled[drv] = out

    return resampled
