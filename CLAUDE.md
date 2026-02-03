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
- **scikit-learn** - Machine learning for tyre degradation prediction
- **Matplotlib/Seaborn** - Chart rendering for analysis UI

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
│   ├── tyres.py               # Tyre compound mapping
│   ├── ml/                    # Machine learning modules
│   │   ├── feature_engineering.py  # Extract ML features from session data
│   │   └── tyre_degradation.py     # Tyre degradation prediction model
│   └── analysis/              # Analysis UI modules
│       ├── charts.py          # Matplotlib/Seaborn chart rendering
│       └── analysis_window.py # Arcade-based tyre analysis UI
├── images/                    # Asset directory
│   ├── tyres/                 # Tyre compound PNGs (soft, medium, hard, intermediate, wet)
│   ├── weather/               # Weather condition icons (clear, rain, cloudy)
│   └── pixel_car.png          # Pixelated F1 car for progress bar playhead
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
| `src/frames.py` | Position/progress calculation, overtake detection, fastest lap tracking, per-frame state building |
| `src/track.py` | Track geometry, coordinate transforms |
| `src/ml/feature_engineering.py` | Extract per-lap features for ML (tyre age, compound, weather, lap times) |
| `src/ml/tyre_degradation.py` | Gradient Boosting model for tyre degradation prediction |
| `src/analysis/charts.py` | Render Matplotlib/Seaborn charts to Arcade textures |
| `src/analysis/analysis_window.py` | Interactive tyre analysis UI with F1 styling |

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

# Open tyre degradation analysis UI
python main.py --year 2024 --round 1 --session R --analysis
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
| `--analysis` | Open tyre analysis UI instead of replay | False |

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
- **Brake Red** (`#E10600`) - Brake bar

### UI Panels
All panels feature rounded corners with red accent bars (F1 signature style):

1. **Top Center** - Grand Prix name (white) and session type (red)
2. **Top Center (dynamic)** - Track Status Indicator (shows YELLOW FLAG, RED FLAG, SAFETY CAR, VSC when active)
3. **Top Center (dynamic)** - Fastest Lap Banner (purple pop-up when new fastest lap is set, shows for 5 seconds with driver name and lap time)
4. **Top Left** - Lap counter (LAP X/Y format) and race time with speed multiplier
5. **Left Side** - Weather panel with track/air temp, humidity, wind, rain status, and weather icon
6. **Left Side (below weather)** - Selected driver telemetry box containing:
   - Driver name with team color accent bar
   - Speed (km/h) and gear indicator
   - DRS status (ON/OFF)
   - Gap to driver ahead and behind
   - **Sector Times Section** - S1/S2/S3 times with purple highlighting for overall best sectors
   - **Tyre Strategy Section** - Current compound, tyre age (laps), stint number, pit stop count
   - **Throttle/Brake Bars** - Vertical bars showing real-time throttle (green) and brake (red) input
7. **Right Side** - Leaderboard (collapsible with L key or click arrow)
   - Full view: position, driver, gap, tyre compound, DRS indicator
   - Collapsed view: position and driver only
   - Team color accent bars per row
   - Alternating row backgrounds for readability
   - Podium position highlighting (gold/silver/bronze)
   - Purple highlight for fastest lap holder
   - Selected driver highlighted with red tint
   - Hover highlight on mouse over
   - Click to select driver and view their telemetry
8. **Bottom Left** - Controls reference panel
9. **Bottom Left (above controls)** - Overtake Feed showing recent position changes (last 15 seconds)
10. **Bottom Center** - Race Director Messages (blue flags, penalties, track limits - auto-dismiss after 10 seconds)
11. **Bottom Center** - Progress bar with pixelated F1 car playhead (clickable to seek)
12. **Bottom Right** - Speed Trap panel showing top 3 speeds recorded during session

### Track Features
- **Track Rendering** - Multi-layer track with shadow, surface, racing line, and center line
- **Start/Finish Line** - White line with red accent marking the start/finish
- **Car Dots** - Team-colored circles with white highlight, larger for selected driver with ring outline

### Progress Bar Features
- F1 red fill indicating replay progress
- Pixelated F1 car image as animated playhead
- Click anywhere on the bar to seek to that position
- Dark gray background with subtle border

### Fullscreen Support
- Window is resizable - drag edges to resize
- Press `F` or `F11` to toggle fullscreen
- Use `--fullscreen` flag to start in fullscreen mode
- UI elements automatically reposition on resize
- Track coordinates recalculated to fit new window dimensions

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
extract_driver_telemetry() → per-driver telemetry arrays (x, y, speed, gear, drs, throttle, brake)
extract_race_control_messages() → track status (flags), blue flags, penalties, track limits
extract_sector_times() → sector times per driver per lap, overall best sectors
extract_pit_stops() → pit stop events, stint info, top speeds
    ↓
build_global_timeline() + resample_all_drivers() → synchronized timeline
    ↓
build_frames() → per-frame driver states including:
    - Position and progress
    - Sector times with personal/overall best tracking
    - Tyre strategy (stint, age, pit count)
    - Track status
    - Fastest lap detection and banner timing
    - Overtake detection
    ↓
F1ReplayWindow → renders frames with arcade (all UI panels + track features)
```

## Frame Data Structure

Each frame contains:
```python
{
    "t": float,                    # Time in seconds
    "drivers": {
        "VER": {
            "x": float, "y": float,    # Track position
            "speed": float,            # km/h
            "gear": int,               # 1-8
            "drs": int,                # DRS status (>=10 = active)
            "throttle": float,         # 0-100%
            "brake": float,            # 0-100%
            "lap": int,                # Current lap number
            "pos": int,                # Race position
            "progress": float,         # Total distance covered
            "compound": str,           # Tyre compound
            "sector_times": {          # Current lap sectors
                "s1": float, "s2": float, "s3": float
            },
            "stint": int,              # Current stint number
            "tyre_life": int,          # Laps on current tyres
            "pit_count": int,          # Number of pit stops
        },
        ...
    },
    "weather": {
        "AirTemp": float,
        "TrackTemp": float,
        "Humidity": float,
        "Rainfall": bool,
    },
    "track_status": str,           # GREEN/YELLOW/RED/SC/VSC
    "race_messages": [...],        # Active race director messages
    "fastest_lap": {
        "driver": str,
        "time": float,
        "is_new": bool,            # True if just set (for banner)
    },
    "position_changes": [...],     # Overtakes in this frame
    "overall_bests": {             # Session best sectors
        "s1": float, "s2": float, "s3": float
    },
}
```

## Testing

No formal test suite exists. Validation is done manually by running replays.

## Tyre Degradation Analysis

The `--analysis` flag opens a dedicated analysis UI for exploring tyre degradation patterns.

### Features
- **ML Prediction Model**: Gradient Boosting model trained on session lap data
- **Degradation Curves**: Visualize actual vs predicted lap time deltas by tyre age
- **Compound Comparison**: Compare degradation rates across SOFT, MEDIUM, HARD tyres
- **Stint Summary**: View stint lengths and degradation statistics per driver
- **Predictions**: Estimated cliff point, optimal stint length, degradation rate

### How It Works
1. Extracts per-lap features: tyre age, compound, weather, fuel load, lap times
2. Trains a Gradient Boosting model on valid (green flag, no pit) laps
3. Predicts lap time delta (degradation) based on conditions
4. Renders charts using Matplotlib/Seaborn embedded in Arcade UI

### Analysis UI Controls
| Key | Action |
|-----|--------|
| `←/→` | Previous/Next driver |
| `↑/↓` | Previous/Next stint |
| `ESC` | Close window |
| Mouse | Click driver/stint buttons to select |

## Planned Features

- **AI Racer** - Generate a "perfect lap" AI driver based on fastest lap telemetry, looped to race duration
- **Driver retirement (OUT) detection** - Show when drivers retire during replay
- **Overtake Probability** - Predict likelihood of overtakes based on pace delta and DRS
- **Driver Consistency Analysis** - Visualize lap time variance and consistency metrics

## Additional Documentation

For specialized topics, see:

- [Architectural Patterns](.claude/docs/architectural_patterns.md) - Data pipeline, state management, design decisions
