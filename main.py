# argparse is used to read command line arguments
import argparse

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

    # Parse the arguments provided by the user
    args = parser.parse_args()

    # enable fastf1 caching (creates folder if needed)
    cache_dir = enable_cache(".fastf1-cache")

    # Printing confirmation so we know cache is active
    print(f"FastF1 cache enabled: {cache_dir}")

    # Load the requested F1 session data using fastf1
    session = load_session(args.year, args.round, args.session, force_reload=args.force)

    # Extract clean metadata from loaded session
    info = get_session_info(session)

    print("\n=== SESSION LOADED ===")

    # Printing all info for the loaded session
    print(f"Event: {info.event_name}")
    print(f"Session: {info.session_name}")
    print(f"Circuit: {info.circuit_name}")
    print(f"Drivers ({len(info.drivers)}): {', '.join(info.drivers)}")
    print(f"Laps loaded: {len(session.laps)}")


if __name__ == "__main__":
    main()
