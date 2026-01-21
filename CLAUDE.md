# F1 Race Replay

## Project Overview

A Formula 1 race replay visualization system that downloads real telemetry data via FastF1 and renders interactive, animated replays of races, qualifying, and practice sessions. Features include real-time leaderboard, driver telemetry, tyre tracking, weather display, and an F1 TV broadcast-inspired UI style.

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
| `src/arcade_replay.py` | F1ReplayWindow class, UI rendering, F1 TV broadcast styling |
| `src/telemetry.py` | Telemetry extraction and lap stitching |
| `src/f1_data.py` | FastF1 session loading, SessionInfo dataclass, driver status, race control messages, sector times, pit stops extraction |
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
| `L` | Toggle leaderboard collapsed/expanded view |
| `F` or `F11` | Toggle fullscreen mode |

## UI Features

### F1 TV Broadcast Style
The UI mimics the official F1 TV broadcast graphics with a clean, professional look:

**Color Palette:**
- **F1 Red** (`#E10600`) - Official F1 red, accent bars, session text
- **F1 Black** (`#15151E`) - Near-black background
- **F1 Dark Gray** (`#26263E`) - Panel backgrounds
- **F1 White** (`#FFFFFF`) - Primary text
- **F1 Light Gray** (`#B4B4B9`) - Secondary text

**Position Colors:**
- **Gold** (`#FFD700`) - P1 / Leader
- **Silver** (`#C0C0C8`) - P2
- **Bronze** (`#CD7F32`) - P3
- **Purple** (`#AA00FF`) - Fastest lap holder

**Status Colors:**
- **DRS Green** (`#00D250`) - DRS active indicator, throttle bar
- **Interval Yellow** (`#FFD200`) - Gap times

### UI Panels
All panels feature rounded corners with red accent bars (F1 signature style):

1. **Top Center** - Grand Prix name (white) and session type (red)
2. **Top Center (dynamic)** - Track Status Indicator (shows YELLOW FLAG, RED FLAG, SAFETY CAR, VSC when active)
3. **Top Center (dynamic)** - Fastest Lap Banner (purple pop-up when new fastest lap is set, shows for 5 seconds)
4. **Top Left** - Lap counter (LAP X/Y format) and race time with speed multiplier
5. **Left Side** - Weather panel with track/air temp, humidity, wind, rain status, and weather icon
6. **Left Side (below weather)** - Selected driver telemetry with team color accent bar, speed, gear, DRS, gaps to drivers ahead/behind, vertical throttle/brake bars
7. **Left Side (below telemetry)** - Sector Times Panel showing S1/S2/S3 times with color coding (purple = overall best)
8. **Left Side (below sectors)** - Tyre Strategy Box showing current stint, tyre age, pit stop count
9. **Right Side** - Leaderboard with team color accent bars per row, alternating row backgrounds, podium position highlighting, tyre compound icons, DRS indicators
10. **Bottom Left** - Controls reference
11. **Bottom Left (above controls)** - Overtake Feed showing recent position changes
12. **Bottom Center** - Race Director Messages (blue flags, penalties, track limits)
13. **Bottom Center** - Clean progress bar (F1 red fill, clickable to seek)
14. **Bottom Right** - Speed Trap showing top 3 speeds recorded during session

### Track Features
- **Start/Finish Line** - White line with red accent marking the start/finish

### Leaderboard Features
- Team color accent bar on the left of each row
- Alternating row backgrounds for readability
- Selected driver highlighted with red tint
- Hover highlight on mouse over
- Click to select driver and view their telemetry
- Tyre compound icons and DRS status indicators per driver

### Fullscreen Support
- Window is resizable - drag edges to resize
- Press `F` or `F11` to toggle fullscreen
- Use `--fullscreen` flag to start in fullscreen mode
- UI elements automatically reposition on resize

## Caching Strategy

Two-layer caching for performance:
1. **FastF1 Cache** (`.fastf1-cache/`) - Downloaded session data from FIA API
2. **Replay Cache** (`computed_data/`) - Pickled replay frames, format: `{year}_R{round:02d}_{session}_fps{fps}.pkl`

**Note:** After updates that change the frame structure (e.g., adding new UI data), use `--refresh` to regenerate the replay cache and see new features.

## Data Flow

```
FastF1 API
    ↓
load_session() → session object
    ↓
extract_driver_telemetry() → per-driver telemetry arrays
extract_race_control_messages() → track status, blue flags, penalties
extract_sector_times() → sector times per driver per lap
extract_pit_stops() → pit stop events, stint info, top speeds
    ↓
build_global_timeline() + resample_all_drivers() → synchronized timeline
    ↓
build_frames() → per-frame driver states with positions, sector times, tyre strategy, track status
    ↓
F1ReplayWindow → renders frames with arcade (all UI panels + track features)
```

## Testing

No formal test suite exists. Validation is done manually by running replays.

## Planned Features

- **AI Racer** - Generate a "perfect lap" AI driver based on fastest lap telemetry, looped to race duration
- **Driver retirement (OUT) detection** - Show when drivers retire during replay

## Additional Documentation

For specialized topics, see:

- [Architectural Patterns](.claude/docs/architectural_patterns.md) - Data pipeline, state management, design decisions
