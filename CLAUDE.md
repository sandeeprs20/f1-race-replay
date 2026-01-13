# F1 Race Replay

## Project Overview

A Formula 1 race replay visualization system that downloads real telemetry data via FastF1 and renders interactive, animated replays of races, qualifying, and practice sessions. Features include real-time leaderboard, driver telemetry, tyre tracking, and weather display.

## Tech Stack

- **Python 3.x** - Core language
- **Arcade** - 2D graphics/game engine for visualization
- **FastF1** - Official F1 telemetry data library
- **NumPy** - Numerical operations and array manipulation
- **Pandas** - Data manipulation (tyre maps, weather)
- **Pillow** - Weather icon generation

## Project Structure

```
f1-race-replay/
├── main.py                    # Entry point, CLI parser, orchestration
├── requirements.txt           # Python dependencies
├── src/
│   ├── arcade_replay.py       # Main visualization window (F1ReplayWindow class)
│   ├── telemetry.py           # Per-driver telemetry extraction
│   ├── f1_data.py             # FastF1 session loading, SessionInfo dataclass
│   ├── replay_clock.py        # Timeline generation, interpolation/resampling
│   ├── frames.py              # Per-frame driver state construction
│   ├── track.py               # Track geometry, coordinate transforms
│   ├── cache.py               # Pickle-based replay persistence
│   ├── team_colors.py         # Driver → team → RGB color mapping
│   ├── colors.py              # MD5-based fallback color generation
│   └── tyres.py               # Tyre compound mapping
├── images/                    # Asset directory
│   ├── tyres/                 # Tyre compound PNGs
│   └── weather/               # Weather condition icons
├── computed_data/             # Cached replay pickle files
└── .fastf1-cache/             # FastF1 downloaded data cache
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py:1-372` | CLI args, pipeline orchestration, caching logic |
| `src/arcade_replay.py:36-266` | F1ReplayWindow class, state management, rendering |
| `src/telemetry.py:25-110` | Telemetry extraction and lap stitching |
| `src/replay_clock.py:147-240` | Interpolation (continuous) vs stepwise (discrete) resampling |
| `src/frames.py:23-71` | Position/progress calculation across lap boundaries |

## Adding New Features or Fixing Bugs

**IMPORTANT**: When you work on a new feature or bug, create a git branch first. Then work on 
changes in that branch for the reminder of the session.

## Build & Run Commands

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Basic run (2024 Season Round 1 Qualifying at 25fps)
python main.py

# Custom session
python main.py --year 2024 --round 5 --session R --fps 30

# Force re-download (ignore FastF1 cache)
python main.py --year 2024 --round 1 --force

# Regenerate replay (ignore computed cache)
python main.py --year 2024 --round 1 --refresh
```

## CLI Arguments

| Flag | Description | Default |
|------|-------------|---------|
| `--year` | Season year | 2024 |
| `--round` | Race round number | 1 |
| `--session` | Session type: R, Q, S, FP1/2/3 | Q |
| `--fps` | Replay frame rate | 25 |
| `--force` | Force re-download despite cache | False |
| `--refresh` | Ignore computed cache, recompute | False |

## Keyboard Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause/Resume playback |
| `←/→` | Seek backward/forward 1 frame (when paused) |
| `↑/↓` | Increase/decrease playback speed |
| `R` | Restart (jump to frame 0) |
| `H` | Toggle HUD visibility |
| `P` | Toggle progress bar |

## Caching Strategy

Two-layer caching for performance:
1. **FastF1 Cache** (`.fastf1-cache/`) - Downloaded session data from FIA API
2. **Replay Cache** (`computed_data/`) - Pickled replay frames, format: `{year}_R{round:02d}_{session}_fps{fps}.pkl`

## Testing

No formal test suite exists. Validation is done manually by running replays.

## Planned Features

- **AI Racer** - Generate a "perfect lap" AI driver based on fastest lap telemetry, looped to race duration

## Additional Documentation

For specialized topics, see:

- [Architectural Patterns](.claude/docs/architectural_patterns.md) - Data pipeline, state management, design decisions
