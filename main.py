import argparse
import numpy as np
import arcade

from src.telemetry import extract_driver_telemetry
from src.replay_clock import build_global_timeline, resample_all_drivers
from src.frames import build_frames
from src.cache import load_replay_cache, save_replay_cache
from src.track import (
    get_reference_track_xy,
    compute_bounds,
    build_world_to_screen_transform,
)
from src.arcade_replay import F1ReplayWindow
from src.f1_data import enable_cache, load_session, get_session_info


# ---------------------------
# TEAM COLORS (EDIT THESE)
# ---------------------------
TEAM_COLORS = {
    "RED_BULL": (0, 47, 108),
    "FERRARI": (220, 0, 0),
    "MERCEDES": (0, 210, 190),
    "MCLAREN": (255, 135, 0),
    "ASTON_MARTIN": (0, 110, 100),
    "ALPINE": (0, 120, 255),
    "WILLIAMS": (0, 90, 255),
    "RB": (70, 90, 255),
    "SAUBER": (0, 190, 0),
    "HAAS": (220, 220, 220),
}

# Map driver codes -> team (EDIT if needed for your season)
DRIVER_TEAM = {
    "VER": "RED_BULL",
    "PER": "RED_BULL",
    "LEC": "FERRARI",
    "SAI": "FERRARI",
    "HAM": "MERCEDES",
    "RUS": "MERCEDES",
    "NOR": "MCLAREN",
    "PIA": "MCLAREN",
    "ALO": "ASTON_MARTIN",
    "STR": "ASTON_MARTIN",
    "GAS": "ALPINE",
    "OCO": "ALPINE",
    "ALB": "WILLIAMS",
    "SAR": "WILLIAMS",
    "TSU": "RB",
    "RIC": "RB",
    "BOT": "SAUBER",
    "ZHO": "SAUBER",
    "MAG": "HAAS",
    "HUL": "HAAS",
}


def driver_color(drv: str):
    team = DRIVER_TEAM.get(drv)
    if team and team in TEAM_COLORS:
        return TEAM_COLORS[team]
    return (255, 255, 255)


def build_tyre_map(session) -> dict:
    """
    tyre_map[DRV_CODE][lap_number] = compound_string
    Uses session.laps (FastF1).
    """
    tyre_map: dict[str, dict[int, str]] = {}

    for driver_number in session.drivers:
        info = session.get_driver(driver_number)
        code = info["Abbreviation"]

        laps = session.laps.pick_drivers(driver_number)
        if laps is None or laps.empty:
            continue

        if "LapNumber" not in laps.columns or "Compound" not in laps.columns:
            continue

        dmap: dict[int, str] = {}
        for _, row in laps.iterrows():
            try:
                ln = int(row["LapNumber"])
                comp = row["Compound"]
                if comp is not None and str(comp).strip() != "":
                    dmap[ln] = str(comp)
            except Exception:
                continue

        tyre_map[code] = dmap

    return tyre_map


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--session", type=str, default="R")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--refresh", action="store_true")

    args = parser.parse_args()

    cache_dir = enable_cache(".fastf1-cache")
    print(f"FastF1 cache enabled: {cache_dir}")

    cached = None
    if not args.refresh:
        cached = load_replay_cache(args.year, args.round, args.session, args.fps)

    if cached is not None:
        print("\nCache hit! Loaded replay from computed_data.")
        print("Cache meta:", cached.meta)

        timeline = cached.timeline
        frames = cached.frames

        print("\n=== CACHED REPLAY SUMMARY ===")
        print(f"Frames: {len(frames)} at {args.fps} FPS")
        print(f"Duration: {timeline[-1]:.2f} seconds")

        # We still need a session for track + tyre map
        session = load_session(args.year, args.round, args.session, force_reload=False)

    else:
        print("\nCache miss (or --refresh). Computing replay...")

        session = load_session(
            args.year, args.round, args.session, force_reload=args.force
        )
        info = get_session_info(session)

        print("\n=== SESSION LOADED ===")
        print(f"Event:   {info.event_name}")
        print(f"Session: {info.session_name}")
        print(f"Circuit: {info.circuit_name}")
        print(f"Drivers ({len(info.drivers)}): {', '.join(info.drivers)}")
        print(f"Laps loaded: {len(session.laps)}")

        telemetry = extract_driver_telemetry(session)
        print(f"\nTelemetry extracted for {len(telemetry)} drivers")

        timeline, t0, t1 = build_global_timeline(telemetry, fps=args.fps)

        print(f"Timeline frames: {len(timeline)} at {args.fps} FPS")
        if len(timeline) == 0:
            raise ValueError(
                "Timeline is empty even after union timeline build. Telemetry may be missing."
            )
        print(f"Replay duration: {timeline[-1]:.2f} seconds")

        resampled = resample_all_drivers(telemetry, timeline, t0)

        # Lap length estimate
        try:
            example_lap = session.laps.pick_fastest()
            tel = example_lap.get_telemetry()
            lap_length = float(tel["Distance"].max())
        except Exception:
            any_drv = next(iter(resampled.keys()))
            lap_length = float(np.max(resampled[any_drv]["distance"]))

        tyre_map = build_tyre_map(session)

        print("\n=== REPLAY CLOCK BUILT ===")
        print(f"Timeline frames: {len(timeline)} at {args.fps} FPS")
        print(f"Replay duration: {timeline[-1]:.2f} seconds")

        frames = build_frames(resampled, timeline, lap_length, tyre_map=tyre_map)

        print("\n=== FRAMES BUILT ===")
        print(f"Total frames: {len(frames)}")

        meta = {
            "year": args.year,
            "round": args.round,
            "session": args.session,
            "fps": args.fps,
            "event_name": info.event_name,
            "session_name": info.session_name,
            "circuit_name": info.circuit_name,
            "drivers": info.drivers,
        }

        save_replay_cache(
            args.year, args.round, args.session, args.fps, meta, timeline, frames
        )

    # Track geometry
    x_track, y_track, _speed_track = get_reference_track_xy(session)
    xmin, xmax, ymin, ymax = compute_bounds(x_track, y_track, pad=50.0)

    screen_w, screen_h = 1280, 720
    scale, tx, ty = build_world_to_screen_transform(
        xmin, xmax, ymin, ymax, screen_w, screen_h
    )

    # Team colors -> driver colors
    sample_frame = frames[0]["drivers"]
    driver_colors = {drv: driver_color(drv) for drv in sample_frame.keys()}

    window = F1ReplayWindow(
        frames=frames,
        track_xy=(x_track, y_track),
        transform=(scale, tx, ty),
        driver_colors=driver_colors,
        fps=args.fps,
        width=screen_w,
        height=screen_h,
        title=f"F1 Replay {args.year} R{args.round:02d} {args.session}",
    )

    arcade.run()


if __name__ == "__main__":
    main()
