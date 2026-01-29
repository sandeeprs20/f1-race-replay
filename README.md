# F1 Race Replay

A Formula 1 race replay visualizer that downloads real telemetry data via [FastF1](https://github.com/theOehrly/Fast-F1) and renders interactive, animated replays of any F1 session -- races, qualifying, sprint, and practice. The UI is inspired by the official F1 TV broadcast graphics.

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

## Tech Stack

- **Python 3.x**
- **[Arcade](https://api.arcade.academy/)** -- 2D graphics engine for rendering
- **[FastF1](https://github.com/theOehrly/Fast-F1)** -- official F1 telemetry data library
- **NumPy** -- numerical operations and array manipulation
- **Pandas** -- data manipulation

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
```

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
│   └── tyres.py            # Tyre compound mapping
├── images/
│   ├── tyres/              # Tyre compound PNGs (soft, medium, hard, intermediate, wet)
│   ├── weather/            # Weather condition icons
│   └── pixel_car.png       # Pixelated F1 car for progress bar playhead
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
