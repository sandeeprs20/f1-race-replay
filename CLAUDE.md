# F1 Race Replay

## Project Overview

A Formula 1 race replay visualization system that downloads real telemetry data via FastF1 and renders interactive, animated replays of races, qualifying, and practice sessions. Features include real-time leaderboard, driver telemetry, tyre tracking, weather display, and a retro neon UI style.

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
| `main.py` | CLI args, pipeline orchestration, caching logic |
| `src/arcade_replay.py` | F1ReplayWindow class, UI rendering, neon styling |
| `src/telemetry.py` | Telemetry extraction and lap stitching |
| `src/f1_data.py` | FastF1 session loading, SessionInfo dataclass, driver status |
| `src/replay_clock.py` | Interpolation (continuous) vs stepwise (discrete) resampling |
| `src/frames.py` | Position/progress calculation across lap boundaries |
| `src/track.py` | Track geometry, coordinate transforms |

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

# Start in fullscreen mode
python main.py --year 2024 --round 1 --session R --fullscreen
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
| `--fullscreen` | Start in fullscreen mode | False |

## Keyboard Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause/Resume playback |
| `←/→` | Seek backward/forward 5 seconds |
| `↑/↓` | Increase/decrease playback speed |
| `R` | Restart (jump to frame 0) |
| `H` | Toggle HUD/UI panels visibility |
| `P` | Toggle progress bar |
| `F` or `F11` | Toggle fullscreen mode |

## UI Features

### Retro Neon Style
The UI uses a synthwave/retro neon color palette:
- **Neon Cyan** (`#00FFFF`) - Primary text, borders
- **Neon Pink** (`#FF0080`) - Highlights, titles, accents
- **Neon Yellow** (`#FFFF00`) - Gap times
- **Neon Green** (`#00FF64`) - DRS indicator, throttle bar
- **Dark Purple** (`#140523`) - Panel backgrounds

### UI Panels
All panels feature rounded corners and neon glow effects:

1. **Top Center** - Grand Prix name and session type (Race/Qualifying/etc.)
2. **Top Left** - Lap counter (LAP X/Y format) and race time with speed multiplier
3. **Left Side** - Weather box showing track/air temp, humidity, wind, rain status
4. **Left Side (below weather)** - Driver telemetry box with speed, gear, DRS, gaps, throttle/brake bars
5. **Right Side** - Leaderboard with position colors (P1 yellow, P2 cyan, P3 orange)
6. **Bottom Left** - Controls reference
7. **Bottom Center** - Segmented progress bar (clickable to seek)

### Fullscreen Support
- Window is resizable - drag edges to resize
- Press `F` or `F11` to toggle fullscreen
- Use `--fullscreen` flag to start in fullscreen mode
- UI elements automatically reposition on resize

## Caching Strategy

Two-layer caching for performance:
1. **FastF1 Cache** (`.fastf1-cache/`) - Downloaded session data from FIA API
2. **Replay Cache** (`computed_data/`) - Pickled replay frames, format: `{year}_R{round:02d}_{session}_fps{fps}.pkl`

## Data Flow

```
FastF1 API
    ↓
load_session() → session object
    ↓
extract_driver_telemetry() → per-driver telemetry arrays
    ↓
build_global_timeline() + resample_all_drivers() → synchronized timeline
    ↓
build_frames() → per-frame driver states with positions
    ↓
F1ReplayWindow → renders frames with arcade
```

## Testing

No formal test suite exists. Validation is done manually by running replays.

## Planned Features

- **AI Racer** - Generate a "perfect lap" AI driver based on fastest lap telemetry, looped to race duration
- **Driver retirement (OUT) detection** - Show when drivers retire during replay

## Additional Documentation

For specialized topics, see:

- [Architectural Patterns](.claude/docs/architectural_patterns.md) - Data pipeline, state management, design decisions
