# This import allows us to use forward references in type hints, i.e,
# referencing classes that are defined later in the file.
from __future__ import annotations

import os

# dataclass automatically generates __init__, __repr__, etc.
# It helps us store structured data cleanly
from dataclasses import dataclass

# List is used for type hints (List[str], etc.)
# Optional allows a value to be None
from typing import List, Optional

# FastF1 is the library that provides Formula 1 timing and telemetry data
import fastf1

import inspect

"""
This is a dataclass which is a simple container for session metadata.
Just stores information nicely
"""


@dataclass
class SessionInfo:
    # Year of the race
    year: int

    # Round number in the season (eg. 1 for Bahrain)
    round_number: int

    # Name of session (Race, Quali, Sprint)
    session_name: str

    # Name of the event (Bahrain Grand Prix)
    event_name: str

    # Name of locatiojn of the circuit
    circuit_name: str

    # List of driver abbreviations (VER, HAM)
    drivers: List[str]


"""
This function enables fastf1 caching. 
Required the cache directory to exist before enabling it
"""


def enable_cache(cache_dir: str = ".fastf1-cache") -> str:
    # Create the cache diectory if it does not exist
    os.makedirs(cache_dir, exist_ok=True)

    # Tell fastf1 to use this directory for caching downloaded data
    fastf1.Cache.enable_cache(cache_dir)

    # Return the cache directory path (useful for loggin and debugging)
    return cache_dir


def load_session(
    year: int,
    round_number: int,
    session_type: str = "R",  # (Race)
    *,
    telemetry: bool = True,  # Whether to load telemetry data
    weather: bool = True,  # Whether to load weather data
    messages: bool = True,  # Whether to load race control messages
    force_reload: bool = False,  # Force re-download even if cached
):
    """
    session_type examples:
        R = Race
        S = Sprint
        Q = Qualifying
        FP1, FP2, FP3
    """

    # Get the session object (no download yet)
    session = fastf1.get_session(year, round_number, session_type)

    # Build kwargs we want to pass into session.load()
    load_kwargs = {
        "telemetry": telemetry,
        "weather": weather,
        "messages": messages,
    }

    # Find which parameters session.load() actually supports in YOUR installed version
    supported_params = set(inspect.signature(session.load).parameters.keys())

    # Only pass keys that exist in this version of FastF1
    safe_kwargs = {k: v for k, v in load_kwargs.items() if k in supported_params}

    # NOTE: force reload varies by version, so we DON'T pass force=...
    # We'll just load normally; later we can add a cache-clear option if needed.
    session.load(**safe_kwargs)

    return session


"""
This function extracts readable metadata from a loaded session
"""


def get_session_info(session) -> SessionInfo:
    # Try to get event name safely, some seasons store it differently,
    # so we guard with getattr
    event_name = getattr(session.event, "EventName", None) or getattr(
        session.event, "EventName", "Unknown Event"
    )

    # Try to get circuit name or location
    circuit_name = getattr(session.event, "Location", None) or getattr(
        session.event, "CircuitName", "Unknown Circuit"
    )

    # sessions.drivers gives driver NUMBERS as strings (eg. "1", "44")
    drivers = list(session.drivers)

    # This list will store the driver abbreviations (VER, HAM)
    codes: List[str] = []

    # Loop over each driver number
    for d in drivers:
        try:
            # Convert driver number to driver info dict
            # Then extract abbreviation
            codes.append(session.get_driver(d)["Abbreviation"])
        except Exception:
            # Fall back in case something goes wrong
            codes.append(str(d))

    # Create and return a SessionInfo object
    return SessionInfo(
        # Extract year from the event date
        year=int(session.event["EventDate"].year)
        if "EventDate" in session.event
        else -1,
        # Extract round number
        round_number=int(session.event["RoundNumber"])
        if "RoundNumber" in session.event
        else -1,
        # Name of the session (Race, Qualifying)
        session_name=str(session.name),
        # Event name string
        event_name=str(event_name),
        # Circuit name string
        circuit_name=str(circuit_name),
        # Sorted unique list of driver abbreviations
        drivers=sorted(set(codes)),
    )
