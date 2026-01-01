# src/team_colors.py

# You control these colors.
# Format: (R, G, B)
TEAM_COLORS = {
    "RED_BULL": (30, 90, 220),
    "FERRARI": (220, 30, 30),
    "MCLAREN": (255, 140, 0),
    "MERCEDES": (60, 220, 200),
    "ASTON_MARTIN": (0, 140, 110),
    "ALPINE": (80, 120, 255),
    "WILLIAMS": (0, 120, 255),
    "RB": (80, 80, 220),
    "SAUBER": (40, 220, 40),
    "HAAS": (200, 200, 200),
    "CADILLAC": (255, 255, 255),
}

# Map driver -> team key
DRIVER_TEAM = {
    # Red Bull
    "VER": "RED_BULL",
    "PER": "RED_BULL",
    # Ferrari
    "LEC": "FERRARI",
    "SAI": "FERRARI",
    # McLaren
    "NOR": "MCLAREN",
    "PIA": "MCLAREN",
    # Mercedes
    "HAM": "MERCEDES",
    "RUS": "MERCEDES",
    # Aston Martin
    "ALO": "ASTON_MARTIN",
    "STR": "ASTON_MARTIN",
    # Alpine
    "GAS": "ALPINE",
    "OCO": "ALPINE",
    # Williams
    "ALB": "WILLIAMS",
    "SAR": "WILLIAMS",
    # RB (Visa Cash App RB)
    "TSU": "RB",
    "RIC": "RB",
    # Sauber
    "BOT": "SAUBER",
    "ZHO": "SAUBER",
    # Haas
    "HUL": "HAAS",
    "MAG": "HAAS",
}


def build_driver_colors(drivers: list[str]) -> dict:
    out = {}
    for d in drivers:
        team = DRIVER_TEAM.get(d, "UNKNOWN")
        out[d] = TEAM_COLORS.get(team, TEAM_COLORS["UNKNOWN"])
    return out
