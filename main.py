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
from src.f1_data import (
    enable_cache,
    load_session,
    get_session_info,
    get_driver_status,
    extract_race_control_messages,
    extract_sector_times,
    extract_pit_stops,
)
from src.team_colors import build_driver_colors


def build_tyre_map(session):
    """
    Build tyre map:
      tyre_map[driver_code][lap_number] = compound string
    Uses FastF1 laps columns: 'LapNumber' and 'Compound' (when available).
    """
    tyre_map = {}

    try:
        laps = session.laps
        if laps is None or laps.empty:
            return tyre_map

        # Expect columns: Driver, LapNumber, Compound
        for _, row in laps.iterrows():
            drv = row.get("Driver", None)
            lap_no = row.get("LapNumber", None)
            comp = row.get("Compound", None)

            if drv is None or lap_no is None:
                continue

            try:
                lap_i = int(lap_no)
            except Exception:
                continue

            tyre_map.setdefault(str(drv), {})[lap_i] = (
                None if comp is None else str(comp)
            )
    except Exception:
        return tyre_map

    return tyre_map


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--session", type=str, default="Q")

    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode")

    args = parser.parse_args()

    cache_dir = enable_cache(".fastf1-cache")
    print(f"FastF1 cache enabled: {cache_dir}")

    # Try computed replay cache first
    cached = None
    if not args.refresh:
        cached = load_replay_cache(args.year, args.round, args.session, args.fps)

    session = None
    info = None
    timeline = None
    frames = None

    if cached is not None:
        print("\nCache hit! Loaded replay from computed_data.")
        print("Cache meta:", cached.meta)

        timeline = cached.timeline
        frames = cached.frames

        print("\n=== CACHED REPLAY SUMMARY ===")
        print(f"Frames: {len(frames)} at {args.fps} FPS")
        print(f"Duration: {timeline[-1]:.2f} seconds")

        # Need session for track + tyre map (FastF1 cache makes this fast)
        session = load_session(args.year, args.round, args.session, force_reload=False)
        info = get_session_info(session)

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

        # Build timeline + resample
        timeline, t0, t1 = build_global_timeline(telemetry, fps=args.fps)

        if len(timeline) == 0:
            raise ValueError(
                "Timeline is empty. Fix replay_clock.build_global_timeline to use min(starts) and max(ends)."
            )

        resampled = resample_all_drivers(telemetry, timeline, t0)

        # Lap length estimate (best effort)
        try:
            example_lap = session.laps.pick_fastest()
            tel = example_lap.get_telemetry()
            lap_length = float(tel["Distance"].max())
        except Exception:
            any_drv = next(iter(resampled.keys()))
            lap_length = float(np.max(resampled[any_drv]["distance"]))

        print("\n=== REPLAY CLOCK BUILT ===")
        print(f"Timeline frames: {len(timeline)} at {args.fps} FPS")
        print(f"Replay duration: {timeline[-1]:.2f} seconds")
        print(f"Lap length estimate: {lap_length:.2f} m")

        tyre_map = build_tyre_map(session)

        # Get weather data
        weather_data = None
        try:
            if hasattr(session, "weather_data") and not session.weather_data.empty:
                weather_data = session.weather_data
        except Exception:
            pass

        # Extract race control messages (flags, safety car, penalties, etc.)
        print("\nExtracting race control messages...")
        race_control = extract_race_control_messages(session)
        print(f"  Track status events: {len(race_control.get('track_status', []))}")
        print(f"  Blue flags: {len(race_control.get('blue_flags', []))}")
        print(f"  Penalties: {len(race_control.get('penalties', []))}")
        print(f"  Track limits: {len(race_control.get('track_limits', []))}")

        # Extract sector times
        print("\nExtracting sector times...")
        sector_data = extract_sector_times(session)
        driver_sectors, overall_bests = sector_data
        print(f"  Drivers with sector data: {len(driver_sectors)}")
        if overall_bests.get("lap"):
            print(f"  Fastest lap: {overall_bests['fastest_driver']} - {overall_bests['lap']:.3f}s (Lap {overall_bests['fastest_lap_num']})")

        # Extract pit stop data
        print("\nExtracting pit stop data...")
        pit_data = extract_pit_stops(session)
        print(f"  Pit stops: {len(pit_data.get('pit_stops', []))}")
        print(f"  Top speeds recorded: {len(pit_data.get('top_speeds', []))}")

        frames = build_frames(
            resampled,
            timeline,
            lap_length,
            tyre_map=tyre_map,
            weather_data=weather_data,
            race_control=race_control,
            sector_data=sector_data,
            pit_data=pit_data,
        )

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

        cache_path = save_replay_cache(
            args.year, args.round, args.session, args.fps, meta, timeline, frames
        )
        print(f"\nSaved replay cache to: {cache_path}")

    # Track geometry
    x_track, y_track, _speed_track = get_reference_track_xy(session)
    xmin, xmax, ymin, ymax = compute_bounds(x_track, y_track, pad=50.0)

    # Use larger window size (close to fullscreen)
    screen_w, screen_h = 1400, 700

    scale, tx, ty = build_world_to_screen_transform(
        xmin, xmax, ymin, ymax, screen_w, screen_h
    )

    driver_colors = build_driver_colors(frames[0]["drivers"].keys())

    # Get driver finishing status (Finished, Retired, DNF, etc.)
    driver_status = get_driver_status(session)
    print(f"Driver status: {driver_status}")

    # Extract pit data for UI (need to do this even on cache hit)
    pit_data = extract_pit_stops(session)

    window = F1ReplayWindow(
        frames=frames,
        track_xy=(x_track, y_track),
        transform=(scale, tx, ty),
        driver_colors=driver_colors,
        fps=args.fps,
        width=screen_w,
        height=screen_h,
        title=f"F1 Replay {args.year} R{args.round:02d} {args.session}",
        race_info=info.event_name,
        session_info=info.session_name,
        total_laps=info.total_laps,
        driver_status=driver_status,
        fullscreen=args.fullscreen,
        pit_data=pit_data,
    )

    arcade.run()


if __name__ == "__main__":
    main()
