"""
Export replay data as chunked JSON for the web frontend.

Outputs:
  web/data/{year}_{round}_{session}/
      manifest.json   - session metadata, driver list, colors, etc.
      track.json      - track polyline in world coordinates
      chunk_000.json ... chunk_NNN.json  - 1000 frames per chunk

  web/data/sessions.json  - list of all exported sessions
"""

import json
import math
import os
import shutil
from pathlib import Path

import numpy as np


CHUNK_SIZE = 1000  # frames per chunk file


def _round_or_none(val, decimals):
    """Round a numeric value, returning None for NaN/None."""
    if val is None:
        return None
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, decimals)
    except (TypeError, ValueError):
        return None


def _compact_driver(drv_state):
    """Convert a per-driver state dict to compact field names with reduced precision."""
    return {
        "x": _round_or_none(drv_state.get("x"), 1),
        "y": _round_or_none(drv_state.get("y"), 1),
        "s": int(round(float(drv_state.get("speed", 0)))),
        "g": int(drv_state.get("gear", 0)),
        "d": int(drv_state.get("drs", 0)),
        "t": int(round(float(drv_state.get("throttle", 0)))),
        "b": int(round(float(drv_state.get("brake", 0)))),
        "l": int(drv_state.get("lap", 1)),
        "p": int(drv_state.get("pos", 0)),
        "pr": _round_or_none(drv_state.get("progress"), 1),
        "di": _round_or_none(drv_state.get("distance"), 1),
        # Tyre / strategy
        "cp": drv_state.get("compound"),
        "st": int(drv_state.get("stint", 1)),
        "tl": int(drv_state.get("tyre_life", 0)),
        "pc": int(drv_state.get("pit_count", 0)),
        # Sector times
        "s1": _round_or_none(drv_state.get("sector_times", {}).get("s1"), 3),
        "s2": _round_or_none(drv_state.get("sector_times", {}).get("s2"), 3),
        "s3": _round_or_none(drv_state.get("sector_times", {}).get("s3"), 3),
        "lt": _round_or_none(drv_state.get("lap_time"), 3),
    }


def _compact_weather(weather):
    """Compact weather dict."""
    if not weather:
        return None
    return {
        "at": _round_or_none(weather.get("AirTemp"), 1),
        "tt": _round_or_none(weather.get("TrackTemp"), 1),
        "hu": _round_or_none(weather.get("Humidity"), 0),
        "rf": bool(weather.get("Rainfall", False)),
        "ws": _round_or_none(weather.get("WindSpeed"), 1),
    }


def _compact_fastest_lap(fl):
    """Compact fastest lap info."""
    if not fl or not fl.get("driver"):
        return None
    return {
        "dr": fl["driver"],
        "tm": _round_or_none(fl.get("time"), 3),
        "ln": fl.get("lap_num"),
        "nw": bool(fl.get("is_new", False)),
    }


def _compact_position_changes(changes):
    """Compact position change list."""
    if not changes:
        return None
    return [
        {
            "dr": c.get("driver", ""),
            "fp": int(c.get("from_pos", 0)),
            "tp": int(c.get("to_pos", 0)),
            "pa": c.get("passed"),
            "t": _round_or_none(c.get("t"), 2),
        }
        for c in changes
    ]


def _compact_race_messages(msgs):
    """Compact race director messages."""
    if not msgs:
        return None
    return [
        {
            "ty": m.get("type", ""),
            "dr": m.get("driver", ""),
            "mg": m.get("message", ""),
            "ag": _round_or_none(m.get("age"), 1),
        }
        for m in msgs
    ]


def _compact_overall_bests(bests):
    """Compact overall bests dict."""
    if not bests:
        return None
    return {
        "s1": _round_or_none(bests.get("s1"), 3),
        "s2": _round_or_none(bests.get("s2"), 3),
        "s3": _round_or_none(bests.get("s3"), 3),
        "lp": _round_or_none(bests.get("lap"), 3),
        "fd": bests.get("fastest_driver"),
        "fn": bests.get("fastest_lap_num"),
    }


def _dicts_equal(a, b):
    """Compare two dicts for equality (handles None)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a == b


def _build_compact_frame(frame, prev_frame_compact=None):
    """
    Build a compact frame dict.
    Delta-encode: weather, track_status, fastest_lap, overall_bests
    (only include if changed from previous frame).
    """
    compact = {
        "t": round(float(frame["t"]), 2),
        "dr": {},
    }

    # Drivers (always included — positions change every frame)
    for drv_code, drv_state in frame.get("drivers", {}).items():
        compact["dr"][drv_code] = _compact_driver(drv_state)

    # Delta-encoded fields
    weather = _compact_weather(frame.get("weather"))
    prev_weather = prev_frame_compact.get("w") if prev_frame_compact else None
    if not _dicts_equal(weather, prev_weather):
        compact["w"] = weather

    track_status = frame.get("track_status", "GREEN")
    prev_status = prev_frame_compact.get("ts") if prev_frame_compact else None
    if track_status != prev_status:
        compact["ts"] = track_status

    fastest_lap = _compact_fastest_lap(frame.get("fastest_lap"))
    prev_fl = prev_frame_compact.get("fl") if prev_frame_compact else None
    if not _dicts_equal(fastest_lap, prev_fl):
        compact["fl"] = fastest_lap

    overall_bests = _compact_overall_bests(frame.get("overall_bests"))
    prev_ob = prev_frame_compact.get("ob") if prev_frame_compact else None
    if not _dicts_equal(overall_bests, prev_ob):
        compact["ob"] = overall_bests

    # Always include these if present (sparse by nature)
    pos_changes = _compact_position_changes(frame.get("position_changes"))
    if pos_changes:
        compact["pc"] = pos_changes

    race_msgs = _compact_race_messages(frame.get("race_messages"))
    if race_msgs:
        compact["rm"] = race_msgs

    return compact


def export_for_web(
    frames,
    track_x,
    track_y,
    driver_colors,
    session_info,
    fps,
    pit_data=None,
    output_dir="web/data",
):
    """
    Export replay data as chunked JSON for the web frontend.

    Args:
        frames: list of frame dicts (from build_frames or cache)
        track_x, track_y: numpy arrays of track polyline coordinates
        driver_colors: dict[driver_code] -> (R, G, B) tuple
        session_info: SessionInfo dataclass
        fps: frames per second
        pit_data: pit stop data dict (optional, for top speeds)
        output_dir: base output directory (default: web/data)
    """
    year = session_info.year
    round_num = session_info.round_number
    session_name = session_info.session_name

    # Determine session code from session_name
    session_code_map = {
        "Race": "R",
        "Qualifying": "Q",
        "Sprint": "S",
        "Sprint Qualifying": "SQ",
        "Practice 1": "FP1",
        "Practice 2": "FP2",
        "Practice 3": "FP3",
    }
    session_code = session_code_map.get(session_name, "R")

    # Session folder
    session_dir_name = f"{year}_R{round_num:02d}_{session_code}"
    session_path = Path(output_dir) / session_dir_name
    session_path.mkdir(parents=True, exist_ok=True)

    n_frames = len(frames)
    n_chunks = math.ceil(n_frames / CHUNK_SIZE)

    print(f"Exporting {n_frames} frames in {n_chunks} chunks to {session_path}")

    # ---- Track JSON ----
    pad = 50.0  # World-unit padding (matches desktop app)
    track_data = {
        "x": [round(float(v), 1) for v in track_x],
        "y": [round(float(v), 1) for v in track_y],
        "bounds": {
            "xmin": round(float(np.min(track_x)) - pad, 1),
            "xmax": round(float(np.max(track_x)) + pad, 1),
            "ymin": round(float(np.min(track_y)) - pad, 1),
            "ymax": round(float(np.max(track_y)) + pad, 1),
        },
    }
    _write_json(session_path / "track.json", track_data)
    print(f"  Wrote track.json ({len(track_x)} points)")

    # ---- Chunk frames ----
    # Build compact frames with delta encoding
    prev_compact = None
    # We need to track the "current state" for delta fields across chunks
    # so the first frame of each chunk carries full state.
    # Strategy: at chunk boundaries, reset prev_compact to None so first frame
    # in each chunk always includes all delta fields.

    for chunk_idx in range(n_chunks):
        start = chunk_idx * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, n_frames)
        chunk_frames = []

        # Reset delta tracking at each chunk boundary
        prev_compact = None

        for i in range(start, end):
            compact = _build_compact_frame(frames[i], prev_compact)
            chunk_frames.append(compact)
            # Track current state for delta encoding
            prev_compact = _build_delta_state(compact, prev_compact)

        chunk_fname = f"chunk_{chunk_idx:03d}.json"
        _write_json(session_path / chunk_fname, chunk_frames)
        if chunk_idx % 10 == 0 or chunk_idx == n_chunks - 1:
            print(f"  Wrote {chunk_fname} (frames {start}-{end - 1})")

    # ---- Manifest JSON ----
    # Collect driver list from first frame
    first_frame = frames[0]
    drivers = sorted(first_frame["drivers"].keys())

    # Convert driver colors to hex
    colors_hex = {}
    for drv, rgb in driver_colors.items():
        r, g, b = rgb[:3]
        colors_hex[drv] = f"#{r:02x}{g:02x}{b:02x}"

    # Top speeds from pit_data
    top_speeds = []
    if pit_data:
        for entry in pit_data.get("top_speeds", [])[:10]:
            top_speeds.append({
                "driver": entry.get("driver", ""),
                "speed": round(float(entry.get("speed", 0)), 1),
            })

    manifest = {
        "year": year,
        "round": round_num,
        "sessionCode": session_code,
        "sessionName": session_name,
        "eventName": session_info.event_name,
        "circuitName": session_info.circuit_name,
        "drivers": drivers,
        "driverColors": colors_hex,
        "totalLaps": session_info.total_laps,
        "fps": fps,
        "totalFrames": n_frames,
        "chunkSize": CHUNK_SIZE,
        "chunkCount": n_chunks,
        "topSpeeds": top_speeds,
        "duration": round(float(frames[-1]["t"]), 2),
    }
    _write_json(session_path / "manifest.json", manifest)
    print(f"  Wrote manifest.json")

    # ---- Update sessions.json ----
    _update_sessions_json(output_dir, manifest, session_dir_name)

    # ---- Copy assets ----
    _copy_assets()

    print(f"\nWeb export complete: {session_path}")
    print(f"Serve with: python -m http.server 8000 --directory web")
    return session_path


def _build_delta_state(compact, prev_state):
    """
    Build the "current state" dict that tracks delta-encoded fields.
    This merges newly emitted fields with previous state.
    """
    state = dict(prev_state) if prev_state else {}

    # Carry forward / update delta fields
    if "w" in compact:
        state["w"] = compact["w"]
    if "ts" in compact:
        state["ts"] = compact["ts"]
    if "fl" in compact:
        state["fl"] = compact["fl"]
    if "ob" in compact:
        state["ob"] = compact["ob"]

    return state


def _write_json(path, data):
    """Write JSON with compact formatting (no pretty-print for size)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)


def _update_sessions_json(output_dir, manifest, session_dir_name):
    """Update the sessions.json index file."""
    sessions_path = Path(output_dir) / "sessions.json"

    sessions = []
    if sessions_path.exists():
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                sessions = json.load(f)
        except (json.JSONDecodeError, IOError):
            sessions = []

    # Remove existing entry for this session (if re-exporting)
    sessions = [
        s for s in sessions
        if s.get("dir") != session_dir_name
    ]

    # Add new entry
    sessions.append({
        "dir": session_dir_name,
        "year": manifest["year"],
        "round": manifest["round"],
        "sessionCode": manifest["sessionCode"],
        "sessionName": manifest["sessionName"],
        "eventName": manifest["eventName"],
        "circuitName": manifest["circuitName"],
        "totalFrames": manifest["totalFrames"],
        "duration": manifest["duration"],
        "fps": manifest["fps"],
    })

    # Sort by year desc, round desc, session type
    session_order = {"R": 0, "S": 1, "SQ": 2, "Q": 3, "FP3": 4, "FP2": 5, "FP1": 6}
    sessions.sort(
        key=lambda s: (-s["year"], -s["round"], session_order.get(s["sessionCode"], 9))
    )

    _write_json(sessions_path, sessions)
    print(f"  Updated sessions.json ({len(sessions)} sessions)")


def _copy_assets():
    """Copy image assets from images/ to web/assets/."""
    base_dir = Path(__file__).resolve().parent.parent
    src_images = base_dir / "images"
    dst_assets = base_dir / "web" / "assets"

    if not src_images.exists():
        print("  Warning: images/ directory not found, skipping asset copy")
        return

    # Copy tyre images
    tyres_src = src_images / "tyres"
    tyres_dst = dst_assets / "tyres"
    tyres_dst.mkdir(parents=True, exist_ok=True)
    if tyres_src.exists():
        for img in tyres_src.glob("*.png"):
            shutil.copy2(img, tyres_dst / img.name)
        print(f"  Copied tyre images to web/assets/tyres/")

    # Copy weather images
    weather_src = src_images / "weather"
    weather_dst = dst_assets / "weather"
    weather_dst.mkdir(parents=True, exist_ok=True)
    if weather_src.exists():
        for img in weather_src.glob("*.png"):
            shutil.copy2(img, weather_dst / img.name)
        print(f"  Copied weather images to web/assets/weather/")

    # Copy pixel car
    pixel_car = src_images / "pixel_car.png"
    if pixel_car.exists():
        shutil.copy2(pixel_car, dst_assets / "pixel_car.png")
        print(f"  Copied pixel_car.png to web/assets/")
