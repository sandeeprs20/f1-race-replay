import numpy as np


def build_frames(resampled: dict, timeline: np.ndarray):
    """
    Convert resampled driver arrays into per-frame state objects

    Args:
        resampled:
          dict like:
            {
              "VER": {"x": array, "y": array, "distance": array, "speed": array, ...},
              ...
            }

        timeline:
          array of replay times (seconds) of shape (N,)
    """
    # Number of frames in the replay
    n_frames = len(timeline)

    # List of driver codes available in resampled data
    drivers = list(resampled.keys())

    x_by_driver = {drv: resampled[drv]["x"] for drv in drivers}
    y_by_driver = {drv: resampled[drv]["y"] for drv in drivers}
    speed_by_driver = {drv: resampled[drv]["speed"] for drv in drivers}
    dist_by_driver = {drv: resampled[drv]["distance"] for drv in drivers}
    lap_by_driver = {drv: resampled[drv]["lap"] for drv in drivers}
    gear_by_driver = {drv: resampled[drv]["gear"] for drv in drivers}
    drs_by_driver = {drv: resampled[drv]["drs"] for drv in drivers}

    # Pre-allocate a list to store each frame's state
    frames = []

    # Looping through each time index in the replay timeline
    for i in range(n_frames):
        # Current replay time in seconds
        t = float(timeline[i])

        # Build list of (driver,distance) for ordering
        dist_list = [(drv, float(dist_by_driver[drv][i])) for drv in drivers]

        # Sort drivers by distance descending (largest distance -> ahead)
        dist_list.sort(key=lambda x: x[1], reverse=True)

        # Assign positions based on sorted order
        positions = {drv: pos for pos, (drv, _) in enumerate(dist_list, start=1)}

        # Build driver state dict for this frame
        driver_states = {}

        for drv in drivers:
            driver_states[drv] = {
                "x": float(x_by_driver[drv][i]),
                "y": float(y_by_driver[drv][i]),
                "speed": float(speed_by_driver[drv][i]),
                "distance": float(dist_by_driver[drv][i]),
                "lap": int(lap_by_driver[drv][i]),
                "gear": int(gear_by_driver[drv][i]),
                "drs": int(drs_by_driver[drv][i]),
                "pos": int(positions[drv]),
            }

        frames.append({"t": t, "drivers": driver_states})

    return frames
