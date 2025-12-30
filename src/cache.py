from __future__ import annotations
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# A small container describing what we store in cache
@dataclass
class ReplayCache:
    meta: dict[str, Any]  # metadata(year/round/session/fps, event namem etc)
    timeline: Any  # numpy array (timeline)
    frames: Any  # list of per-frame dictionaries


def _cache_file_path(
    year: int,
    round_number: int,
    session_code: str,
    fps: int,
    cache_dir: str = "computed_data",
) -> Path:
    """
    Build a stable filename so that the same request always hits the same cache
    """

    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)

    fname = f"{year}_R{round_number:02d}_{session_code}_fps{fps}.pkl"
    return cache_root / fname


def load_replay_cache(
    year: int,
    round_number: int,
    session_code: str,
    fps: int,
    cache_dir: str = "computed_data",
) -> Optional[ReplayCache]:
    """
    Try to load cached replay data. Returns None if cache does not exist.
    """

    path = _cache_file_path(year, round_number, session_code, fps, cache_dir)

    if not path.exists():
        return None

    with path.open("rb") as f:
        obj = pickle.load(f)

    # Basic validation to ensure required keys exist
    if (
        not isinstance(obj, dict)
        or "meta" not in obj
        or "timeline" not in obj
        or "frames" not in obj
    ):
        return None

    return ReplayCache(meta=obj["meta"], timeline=obj["timeline"], frames=obj["frames"])


def save_replay_cache(
    year: int,
    round_number: int,
    session_code: str,
    fps: int,
    meta: dict[str, Any],
    timeline: Any,
    frames: Any,
    cache_dir: str = "computed_data",
) -> Path:
    """
    Save replay data to disk and return the file path

    """

    path = _cache_file_path(year, round_number, session_code, fps, cache_dir)

    payload = {"meta": meta, "timeline": timeline, "frames": frames}

    with path.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    return path
