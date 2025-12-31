import colorsys
import hashlib


def driver_code_to_color(driver_code: str):
    """
    Deterministically convert a driver code into an RGB color

    """

    # Hash driver code to a stable integer
    h = int(hashlib.md5(driver_code.encode()).hexdigest(), 16)

    # Hue in range [0, 1)
    hue = (h % 360) / 360.0

    # Fixed saturation/value for good contrast
    saturation = 0.85
    value = 0.95

    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)

    # Convert to 0 - 255 integer for arcade
    return int(r * 255), int(g * 255), int(b * 255)
