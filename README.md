# F1 Race Replay

A Formula 1 race replay visualizer that downloads real telemetry data via [FastF1](https://github.com/theOehrly/Fast-F1) and renders interactive, animated replays of any F1 session -- races, qualifying, sprint, and practice. Available as both a Python desktop app (Arcade) and a web frontend. The UI is inspired by the official F1 TV broadcast graphics.

<img width="1915" height="1028" alt="image" src="https://github.com/user-attachments/assets/2cc53768-6c46-4ed5-a44c-c32d8fc5ba03" />


## Features

- **Real telemetry data** -- pulls position, speed, gear, throttle, brake, and DRS data for every driver on track via the FIA API
- **Track visualization** -- renders the actual circuit layout with team-colored car dots moving in real time, start/finish line marking, and multi-layer track rendering
- **F1 TV broadcast-style UI** -- clean, professional panels with rounded corners, red accent bars, and the official F1 color palette
- **Live leaderboard** -- interactive leaderboard with team colors, podium highlighting (gold/silver/bronze), tyre compound icons, DRS indicators, and click-to-select driver telemetry
- **Driver telemetry panel** -- real-time speed, gear, DRS status, gaps to cars ahead/behind, throttle/brake input bars, sector times with purple highlighting for session bests, and tyre strategy info
- **Weather panel** -- track/air temperature, humidity, wind speed, rainfall status with weather icons
- **Track status indicators** -- yellow flag, red flag, safety car, and VSC banners displayed dynamically
- **Fastest lap banner** -- purple pop-up notification when a new fastest lap is set
- **Overtake detection** -- real-time feed showing position changes as they happen
- **Race director messages** -- blue flags, penalties, and track limit warnings
- **Speed trap** -- top 3 speeds recorded during the session
- **Progress bar** -- clickable F1 red progress bar with a pixelated F1 car as the playhead
- **Playback controls** -- pause, seek, speed up/slow down (0.5x to 64x), restart
- **Fullscreen support** -- resizable window with automatic UI repositioning
- **Two-layer caching** -- FastF1 API cache + computed replay cache for instant loading after first run
- **Web frontend** -- browser-based replay viewer with the same features as the desktop app
- **Qualifying-specific UI** -- dedicated layout for qualifying sessions with live telemetry graphs, mini track view, and lap times leaderboard

## Tech Stack

**Desktop App (Python):**
- **Python 3.x**
- **[Arcade](https://api.arcade.academy/)** -- 2D graphics engine for rendering
- **[FastF1](https://github.com/theOehrly/Fast-F1)** -- official F1 telemetry data library
- **NumPy** -- numerical operations and array manipulation
- **Pandas** -- data manipulation
- **scikit-learn** -- machine learning for tyre degradation analysis
- **Matplotlib / Seaborn** -- chart rendering for analysis UI

**Web Frontend:**
- **JavaScript (ES6+)** -- vanilla JS with ES modules, no frameworks
- **HTML5 Canvas** -- 2D rendering
- **CSS3** -- styling

## Getting Started

### Prerequisites

- Python 3.x

### Installation

```bash
git clone https://github.com/sandeeprs20/f1-race-replay.git
cd f1-race-replay

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### Usage

```bash
# Default: 2024 Season Round 1 Qualifying at 25fps
python main.py

# Custom session (e.g. 2024 Round 5 Race at 30fps)
python main.py --year 2024 --round 5 --session R --fps 30

# Start in fullscreen
python main.py --year 2024 --round 1 --session R --fullscreen

# Force re-download telemetry data
python main.py --year 2024 --round 1 --force

# Regenerate replay from cached telemetry
python main.py --year 2024 --round 1 --refresh

# Export session for web frontend
python main.py --year 2024 --round 1 --session Q --export-web
```

### Web Frontend

The web frontend provides the same replay experience in your browser.

```bash
# 1. Export session data for web
python main.py --year 2024 --round 1 --session Q --export-web

# 2. Start a local web server
cd web
python -m http.server 8000

# 3. Open http://localhost:8000 in your browser
```

Select a session from the dropdown and click **Load** to start the replay.

### CLI Arguments

| Flag | Description | Default |
|------|-------------|---------|
| `--year` | Season year | 2024 |
| `--round` | Race round number | 1 |
| `--session` | Session type: `R`, `Q`, `S`, `FP1`, `FP2`, `FP3` | `Q` |
| `--fps` | Replay frame rate | 25 |
| `--force` | Force re-download from FIA API | `False` |
| `--refresh` | Regenerate replay frames from cached data | `False` |
| `--fullscreen` | Start in fullscreen mode | `False` |
| `--export-web` | Export session data as JSON for web frontend | `False` |
| `--analysis` | Open tyre degradation analysis UI | `False` |

### Keyboard Controls

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume |
| `Left` / `Right` | Seek backward / forward 5 seconds |
| `Up` / `Down` | Increase / decrease playback speed |
| `R` | Restart from beginning |
| `H` | Toggle HUD panels |
| `P` | Toggle progress bar |
| `L` | Toggle leaderboard (expanded / collapsed) |
| `F` / `F11` | Toggle fullscreen |

## Qualifying Session UI

When loading a qualifying session (`Q`, `Q1`, `Q2`, `Q3`), the web frontend automatically switches to a dedicated qualifying layout optimized for hot lap analysis:

**Layout:**
- **Mini Track View** (top-left) -- compact circuit map showing all drivers as team-colored dots, click to select a driver
- **Weather Panel** (left) -- track/air temperature, humidity, rainfall status
- **Driver Focus Panel** (left) -- selected driver's speed, gear, DRS, best lap time, current lap sector times with purple highlighting for session bests, tyre compound
- **Live Telemetry Graphs** (center) -- two real-time graphs plotting data against lap distance:
  - **Speed Graph** -- speed trace (km/h) throughout the lap
  - **Throttle/Brake Graph** -- overlaid throttle (green) and brake (red) inputs
- **Lap Times Leaderboard** (right) -- drivers sorted by best lap time, showing gap to P1, purple highlight for fastest, click to select driver

**Features:**
- Telemetry graphs update in real-time as the selected driver drives
- Graphs reset automatically when the driver starts a new lap
- Click on mini track dots or leaderboard rows to switch between drivers
- Session time displayed instead of lap counter

## How It Works

```
FastF1 API
    |
    v
Session Loading --> Telemetry Extraction --> Timeline Resampling --> Frame Construction --> Visualization
    |                    |                        |                       |                      |
    |  FastF1 session    |  Per-driver lap-by-    |  Fixed FPS timeline   |  Per-frame driver    |  Arcade game
    |  fetch + cache     |  lap telemetry         |  with interpolation   |  state dicts with    |  loop rendering
    |                    |  concatenation         |  (continuous) and     |  positions, sectors, |  all UI panels
    |                    |                        |  stepwise (discrete)  |  tyres, weather      |
    v                    v                        v                       v                      v
  SessionInfo       Raw telemetry arrays     Synchronized timeline    Frame list             Window
```

The pipeline resamples continuous values (position, speed, throttle) via linear interpolation for smooth motion, while discrete values (gear, DRS, lap number) use stepwise/last-known resampling to avoid unphysical states.

## Project Structure

```
f1-race-replay/
├── main.py                 # Entry point, CLI args, pipeline orchestration
├── requirements.txt        # Python dependencies
├── src/
│   ├── arcade_replay.py    # F1ReplayWindow -- main visualization and UI rendering
│   ├── f1_data.py          # FastF1 session loading, SessionInfo dataclass
│   ├── telemetry.py        # Per-driver telemetry extraction and lap stitching
│   ├── replay_clock.py     # Timeline generation, interpolation/resampling
│   ├── frames.py           # Per-frame driver state construction, overtake detection
│   ├── track.py            # Track geometry, coordinate transforms
│   ├── cache.py            # Pickle-based replay persistence
│   ├── team_colors.py      # Driver/team color mapping
│   ├── colors.py           # MD5-based fallback color generation
│   ├── tyres.py            # Tyre compound mapping
│   ├── web_export.py       # Export session data as JSON for web frontend
│   ├── ml/                 # Machine learning modules
│   │   ├── feature_engineering.py
│   │   └── tyre_degradation.py
│   └── analysis/           # Analysis UI modules
│       ├── charts.py
│       └── analysis_window.py
├── web/                    # Web frontend
│   ├── index.html          # Main HTML page
│   ├── css/style.css       # Styles
│   ├── js/
│   │   ├── app.js          # Main application, event handling
│   │   ├── renderer.js     # Race UI renderer
│   │   ├── qualifying-renderer.js  # Qualifying UI renderer
│   │   ├── qualifying-state.js     # Qualifying state with telemetry tracking
│   │   ├── data-loader.js  # Chunk-based data loading
│   │   ├── track-renderer.js
│   │   ├── state.js        # Playback state management
│   │   ├── panels/         # UI panel components
│   │   └── qualifying/     # Qualifying-specific components
│   │       ├── telemetry-graph.js  # Speed and throttle/brake graphs
│   │       ├── mini-track.js       # Compact track view
│   │       ├── lap-times-panel.js  # Best lap times leaderboard
│   │       └── driver-focus.js     # Selected driver details
│   └── assets/             # Images (tyres, weather icons, pixel car)
├── images/                 # Desktop app assets
├── computed_data/          # Cached replay pickle files
└── .fastf1-cache/          # FastF1 API data cache
```

## Caching

Two-layer caching keeps things fast:

1. **FastF1 Cache** (`.fastf1-cache/`) -- raw session data from the FIA API. Bypass with `--force`.
2. **Replay Cache** (`computed_data/`) -- pre-computed replay frames as pickle files. Bypass with `--refresh`.

After code changes that affect frame data (e.g. adding new UI fields), use `--refresh` to regenerate the replay cache.

## License

This project is for personal/educational use. F1 telemetry data is provided by the FIA via FastF1.
