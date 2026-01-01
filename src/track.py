import numpy as np


def get_reference_track_xy(session, driver_code: str = None):
    """
    Build a reference track polyline (x_points, y_points) from a fast lap.

    Strategy:
      - If driver_code is provided, use that driver's fastest lap
      - Otherwise use the overall session fastest lap

    Returns:
      x: np.ndarray
      y: np.ndarray
    """

    # Pick an example lap to define the track shape
    if driver_code is not None:
        lap = session.laps.pick_drivers([driver_code]).pick_fastest()
    else:
        lap = session.laps.pick_fastest()

    # Get telemetry for the lap and extract X/Y points
    tel = lap.get_telemetry()

    x = tel["X"].to_numpy(dtype=np.float64)
    y = tel["Y"].to_numpy(dtype=np.float64)
    speed = tel["Speed"].to_numpy(dtype=np.float64)
    return x, y, speed


def compute_bounds(x: np.ndarray, y: np.ndarray, pad: float = 0.0):
    """
    Compute bounding box of the track polyline.
    pad expands the bounds outward in world units.
    """

    xmin = float(np.min(x)) - pad
    xmax = float(np.max(x)) + pad
    ymin = float(np.min(y)) - pad
    ymax = float(np.max(y)) + pad

    return xmin, xmax, ymin, ymax


def build_world_to_screen_transform(
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    screen_w: int,
    screen_h: int,
    margin: int = 60,
):
    """
    Create an affine transform from world coordinates (FastF1 X/Y)
    into screen coordinates (pixels).

    Returns:
      scale: float
      tx: float
      ty: float

    Mapping:
      sx = (x * scale) + tx
      sy = (y * scale) + ty

    Notes:
      - We flip Y so "up" in world appears "up" on screen
        (Arcade's y-axis increases upward, but world coords may differ)
    """

    # Compute available drawing area after margins
    avail_w = screen_w - 2 * margin
    avail_h = screen_h - 2 * margin

    # Track width/height in world units
    world_w = xmax - xmin
    world_h = ymax - ymin

    # Scale so track fits inside available width/height
    scale = min(avail_w / world_w, avail_h / world_h)

    # Compute center of world bounds
    world_cx = (xmin + xmax) / 2.0
    world_cy = (ymin + ymax) / 2.0

    # Compute screen center
    screen_cx = screen_w / 2.0
    screen_cy = screen_h / 2.0

    # Translate so world center maps to screen center
    tx = screen_cx - (world_cx * scale)
    ty = screen_cy - (world_cy * scale)

    return scale, tx, ty


def world_to_screen(x: float, y: float, scale: float, tx: float, ty: float):
    """
    Apply the world->screen transform to a single point.
    """
    sx = (x * scale) + tx
    sy = (y * scale) + ty
    return sx, sy
