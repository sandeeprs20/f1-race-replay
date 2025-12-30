# argparse is used to read command line arguments
import argparse

from src.telemetry import extract_driver_telemetry
from src.replay_clock import build_global_timeline, resample_all_drivers
from src.frames import build_frames
from src.cache import load_replay_cache, save_replay_cache

# Helper functions from f1_data.py
from src.f1_data import enable_cache, load_session, get_session_info

"""
Main function - execution starts here
"""


def main():
    # Creating a command line argument parser
    parser = argparse.ArgumentParser()

    # Argument for the season year (default = 2024)
    parser.add_argument("--year", type=int, default=2024)

    # Argument for the race round (default = 1)
    parser.add_argument("--round", type=int, default=1)

    # Argument for session type (default = R)
    parser.add_argument("--session", type=str, default="R")

    # Flag to force FastF1 to reload data instead of using cache
    parser.add_argument("--force", action="store_true")

    # Frames per second for the replay clock (default: 25)
    parser.add_argument("--fps", type=int, default=25)

    # Ignore our computed replay cache and recompute everything
    parser.add_argument("--refresh", action="store_true")

    # Parse the arguments provided by the user
    args = parser.parse_args()

    # enable fastf1 caching (creates folder if needed)
    cache_dir = enable_cache(".fastf1-cache")

    # Printing confirmation so we know cache is active
    print(f"FastF1 cache enabled: {cache_dir}")

    # Try to load our replay cache first unless referesh is required
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

    # Otherwise compute everything (slow path)
    else:
        print("\nCache miss (or --refresh). Computing replay...")

        # Step 2: Load session using FastF1
        session = load_session(
            args.year, args.round, args.session, force_reload=args.force
        )

        # Extract clean metadata
        info = get_session_info(session)

        print("\n=== SESSION LOADED ===")
        print(f"Event:   {info.event_name}")
        print(f"Session: {info.session_name}")
        print(f"Circuit: {info.circuit_name}")
        print(f"Drivers ({len(info.drivers)}): {', '.join(info.drivers)}")
        print(f"Laps loaded: {len(session.laps)}")

        # Step 3: Extract stitched telemetry per driver
        telemetry = extract_driver_telemetry(session)
        print(f"\nTelemetry extracted for {len(telemetry)} drivers")

        # Step 4: Build global replay timeline + resample all drivers onto it
        timeline, t0, t1 = build_global_timeline(telemetry, fps=args.fps)
        resampled = resample_all_drivers(telemetry, timeline, t0)

        print("\n=== REPLAY CLOCK BUILT ===")
        print(f"Timeline frames: {len(timeline)} at {args.fps} FPS")
        print(f"Replay duration: {timeline[-1]:.2f} seconds")

        # Step 5: Build per-frame state objects and compute positions
        frames = build_frames(resampled, timeline)

        print("\n=== FRAMES BUILT ===")
        print(f"Total frames: {len(frames)}")

        # Print a few snapshots of the top 5 drivers by position (debug)
        for idx in [0, len(frames) // 2, len(frames) - 1]:
            frame = frames[idx]
            t = frame["t"]
            ordered = sorted(frame["drivers"].items(), key=lambda kv: kv[1]["pos"])
            top5 = ordered[:5]
            top5_str = ", ".join([f"{drv}(P{st['pos']})" for drv, st in top5])
            print(f"t={t:.2f}s  Top5: {top5_str}")

        # Step 6: Save our computed replay cache to disk
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
            args.year,
            args.round,
            args.session,
            args.fps,
            meta,
            timeline,
            frames,
        )

        print(f"\nSaved replay cache to: {cache_path}")


if __name__ == "__main__":
    main()
