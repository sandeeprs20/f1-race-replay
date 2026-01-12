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

    # NEW: AI racer arguments
    parser.add_argument(
        "--ai", action="store_true", help="Enable AI racer (perfect lap)"
    )
    parser.add_argument(
        "--ai-driver",
        type=str,
        default=None,
        help="Base AI on specific driver's fastest lap (e.g., VER, HAM)",
    )
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

        telemetry = extract_driver_telemetry(session)
        print(f"\nTelemetry extracted for {len(telemetry)} drivers")

        # Generate AI racer if requested
        # if args.ai:
        #     from src.ai.simple_ai import (
        #         generate_ai_lap_from_fastest,
        #         generate_ai_lap_from_driver,
        #     )

        #     print("\n=== GENERATING AI RACER ===")

        #     if args.ai_driver:
        #         # AI based on specific driver
        #         ai_telemetry = generate_ai_lap_from_driver(session, args.ai_driver)
        #     else:
        #         # AI based on fastest lap overall
        #         ai_telemetry = generate_ai_lap_from_fastest(session)

        #     if ai_telemetry:
        #         telemetry["AI"] = ai_telemetry
        #         print("✓ AI racer added to replay")
        #     else:
        #         print("⚠ AI racer generation failed, continuing without AI")

        # If AI is requested, we need to add it to the cached frames
        if args.ai:
            print("⚠ Note: AI racer not in cache, generating fresh...")
            from src.ai.simple_ai import (
                generate_ai_lap_from_fastest,
                generate_ai_lap_from_driver,
            )

            if args.ai_driver:
                ai_telemetry = generate_ai_lap_from_driver(session, args.ai_driver)
            else:
                ai_telemetry = generate_ai_lap_from_fastest(session)

            if ai_telemetry:
                # The AI telemetry is only one lap - we need to loop it to match race duration
                from src.replay_clock import resample_all_drivers

                # Get lap length and lap time from AI telemetry
                lap_length = float(ai_telemetry["distance"][-1])
                lap_time = float(ai_telemetry["time"][-1] - ai_telemetry["time"][0])

                # Determine how many laps we need to cover the timeline
                race_duration = timeline[-1]
                num_laps = int(np.ceil(race_duration / lap_time)) + 1

                print(
                    f"Looping AI lap {num_laps} times to cover {race_duration:.1f}s race"
                )

                # Tile/repeat the AI lap data to cover the full race
                tiled_telemetry = {
                    "time": [],
                    "x": [],
                    "y": [],
                    "distance": [],
                    "speed": [],
                    "gear": [],
                    "drs": [],
                    "lap": [],
                    "throttle": [],
                    "brake": [],
                }

                for lap_num in range(1, num_laps + 1):
                    time_offset = (lap_num - 1) * lap_time
                    tiled_telemetry["time"].append(ai_telemetry["time"] + time_offset)
                    tiled_telemetry["x"].append(ai_telemetry["x"])
                    tiled_telemetry["y"].append(ai_telemetry["y"])
                    tiled_telemetry["distance"].append(
                        ai_telemetry["distance"] + (lap_num - 1) * lap_length
                    )
                    tiled_telemetry["speed"].append(ai_telemetry["speed"])
                    tiled_telemetry["gear"].append(ai_telemetry["gear"])
                    tiled_telemetry["drs"].append(ai_telemetry["drs"])
                    tiled_telemetry["lap"].append(
                        np.full_like(ai_telemetry["lap"], lap_num)
                    )
                    tiled_telemetry["throttle"].append(ai_telemetry["throttle"])
                    tiled_telemetry["brake"].append(ai_telemetry["brake"])

                # Concatenate all laps
                for key in tiled_telemetry:
                    tiled_telemetry[key] = np.concatenate(tiled_telemetry[key])

                # Create a dict with AI telemetry
                ai_dict = {"AI": tiled_telemetry}

                # Resample using existing function
                ai_resampled = resample_all_drivers(ai_dict, timeline, timeline[0])

                # Get lap length from session
                lap_length_session = 5000.0  # Default estimate
                try:
                    example_lap = session.laps.pick_fastest()
                    tel_example = example_lap.get_telemetry(add_driver_ahead=False)
                    lap_length_session = float(tel_example["Distance"].max())
                except:
                    lap_length_session = lap_length

                # Add AI to each frame with proper position calculation
                for i, frame in enumerate(frames):
                    ai_lap = int(ai_resampled["AI"]["lap"][i])
                    ai_dist = float(ai_resampled["AI"]["distance"][i])

                    # Calculate AI progress (same formula as in frames.py)
                    ai_progress = float(
                        (ai_lap - 1) * lap_length_session
                        + (ai_dist % lap_length_session)
                    )

                    frame["drivers"]["AI"] = {
                        "x": float(ai_resampled["AI"]["x"][i]),
                        "y": float(ai_resampled["AI"]["y"][i]),
                        "speed": float(ai_resampled["AI"]["speed"][i]),
                        "distance": float(ai_resampled["AI"]["distance"][i]),
                        "gear": int(ai_resampled["AI"]["gear"][i]),
                        "drs": int(ai_resampled["AI"]["drs"][i]),
                        "lap": ai_lap,
                        "throttle": float(ai_resampled["AI"]["throttle"][i]),
                        "brake": float(ai_resampled["AI"]["brake"][i]),
                        "compound": "SOFT",  # Default tyre for AI
                        "progress": ai_progress,
                        "pos": 0,  # Placeholder, will be recalculated below
                    }

                    # Recalculate all positions including AI
                    all_drivers = list(frame["drivers"].items())
                    all_drivers.sort(key=lambda x: x[1]["progress"], reverse=True)

                    # Update positions
                    for pos, (drv, _) in enumerate(all_drivers, start=1):
                        frame["drivers"][drv]["pos"] = pos

                print("✓ AI racer added to cached replay")

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

        # If AI is requested, we need to add it to the cached frames
        if args.ai:
            print("⚠ Note: AI racer not in cache, generating fresh...")
            from src.ai.simple_ai import (
                generate_ai_lap_from_fastest,
                generate_ai_lap_from_driver,
            )

            if args.ai_driver:
                ai_telemetry = generate_ai_lap_from_driver(session, args.ai_driver)
            else:
                ai_telemetry = generate_ai_lap_from_fastest(session)

            if ai_telemetry:
                # Resample AI to match the cached timeline
                from src.replay_clock import resample_all_drivers

                # Create a dict with just AI telemetry
                ai_dict = {"AI": ai_telemetry}

                # Resample using existing function
                ai_resampled = resample_all_drivers(ai_dict, timeline, timeline[0])

                # Add AI to each frame with proper position calculation
                for i, frame in enumerate(frames):
                    ai_lap = int(ai_resampled["AI"]["lap"][i])
                    ai_dist = float(ai_resampled["AI"]["distance"][i])

                    # Get lap_length from first real driver
                    first_driver_key = next(iter(frame["drivers"].keys()))
                    # Estimate lap length from existing drivers
                    lap_length = 5000.0  # Default estimate
                    try:
                        # Try to get lap length from session if available
                        if session:
                            example_lap = session.laps.pick_fastest()
                            tel_example = example_lap.get_telemetry(
                                add_driver_ahead=False
                            )
                            lap_length = float(tel_example["Distance"].max())
                    except:
                        pass

                    # Calculate AI progress (same formula as in frames.py)
                    ai_progress = float(
                        (ai_lap - 1) * lap_length + (ai_dist % lap_length)
                    )

                    frame["drivers"]["AI"] = {
                        "x": float(ai_resampled["AI"]["x"][i]),
                        "y": float(ai_resampled["AI"]["y"][i]),
                        "speed": float(ai_resampled["AI"]["speed"][i]),
                        "distance": float(ai_resampled["AI"]["distance"][i]),
                        "gear": int(ai_resampled["AI"]["gear"][i]),
                        "drs": int(ai_resampled["AI"]["drs"][i]),
                        "lap": ai_lap,
                        "throttle": float(ai_resampled["AI"]["throttle"][i]),
                        "brake": float(ai_resampled["AI"]["brake"][i]),
                        "compound": "SOFT",  # Default tyre for AI
                        "progress": ai_progress,
                        "pos": 0,  # Placeholder, will be recalculated below
                    }

                    # Recalculate all positions including AI
                    all_drivers = list(frame["drivers"].items())
                    all_drivers.sort(key=lambda x: x[1]["progress"], reverse=True)

                    # Update positions
                    for pos, (drv, _) in enumerate(all_drivers, start=1):
                        frame["drivers"][drv]["pos"] = pos

                print("AI racer added to cached replay")

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

        frames = build_frames(
            resampled,
            timeline,
            lap_length,
            tyre_map=tyre_map,
            weather_data=weather_data,
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

    # CHANGE 4: CUSTOM COLOR FOR AI
    # Give AI a distinctive bright green color
    if args.ai and "AI" in frames[0]["drivers"]:
        driver_colors["AI"] = (0, 255, 100)  # Bright green

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
    )

    arcade.run()


if __name__ == "__main__":
    main()
