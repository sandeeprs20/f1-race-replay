# src/team_colors.py

# You control these colors.
# Format: (R, G, B)
TEAM_COLORS = {
    "RED_BULL": (6, 0, 239),
    "FERRARI": (220, 0, 0),
    "MCLAREN": (255, 135, 0),
    "MERCEDES": (0, 210, 190),
    "ASTON_MARTIN": (0, 111, 98),
    "ALPINE": (0, 144, 255),
    "WILLIAMS": (0, 90, 255),
    "RB": (50, 70, 200),
    "SAUBER": (0, 255, 135),
    "HAAS": (230, 0, 30),
    "UNKNOWN": (150, 150, 150),  # Gray for unknown drivers
}

# Map driver -> team key
DRIVER_TEAM = {
    # Red Bull
    "VER": "RED_BULL",
    "PER": "RED_BULL",
    "TSU": "RED_BULL",
    # Ferrari
    "LEC": "FERRARI",
    "HAM": "FERRARI",
    # McLaren
    "NOR": "MCLAREN",
    "PIA": "MCLAREN",
    # Mercedes
    "ANT": "MERCEDES",
    "RUS": "MERCEDES",
    # Aston Martin
    "ALO": "ASTON_MARTIN",
    "STR": "ASTON_MARTIN",
    # Alpine
    "GAS": "ALPINE",
    "COL": "ALPINE",
    # Williams
    "ALB": "WILLIAMS",
    "SAI": "WILLIAMS",
    # RB (Visa Cash App RB)
    "HAD": "RB",
    "LAW": "RB",
    # Sauber
    "HUL": "SAUBER",
    "ZHO": "SAUBER",
    "BOR": "SAUBER",
    "BOT": "SAUBER",
    # Haas
    "MAG": "HAAS",
    "OCO": "HAAS",
    "BEA": "HAAS",
}


def build_driver_colors(drivers: list[str]) -> dict:
    out = {}
    for d in drivers:
        team = DRIVER_TEAM.get(d, "UNKNOWN")
        out[d] = TEAM_COLORS.get(team, TEAM_COLORS["UNKNOWN"])
    return out
