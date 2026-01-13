# Architectural Patterns

## Data Pipeline Architecture

The system follows a linear pipeline with clear transformation stages:

```
FastF1 API → Session Loading → Telemetry Extraction → Timeline Resampling → Frame Construction → Visualization
```

### Pipeline Stages

1. **Session Loading** (`src/f1_data.py:46-110`)
   - FastF1 session fetch with local caching
   - Returns `SessionInfo` dataclass with metadata

2. **Telemetry Extraction** (`src/telemetry.py:25-80`)
   - Per-driver lap-by-lap telemetry concatenation
   - Handles missing data gracefully with try/except blocks

3. **Timeline Resampling** (`src/replay_clock.py:147-240`)
   - Fixed FPS timeline generation
   - Two resampling strategies based on value type (see below)

4. **Frame Construction** (`src/frames.py:23-121`)
   - Per-frame driver state dictionaries
   - Position calculation via progress metric
   - Weather data injection

5. **Visualization** (`src/arcade_replay.py:36-925`)
   - Arcade game loop with delta-time updates
   - Event-driven input handling

## Resampling Strategy

Critical design decision at `src/replay_clock.py:147-240`:

### Continuous Values (Linear Interpolation)
- X, Y position, Speed, Distance, Throttle, Brake
- Uses `np.interp()` for smooth motion
- Prevents visual jitter

### Discrete Values (Stepwise/Last-Known)
- Gear (integer), DRS state (boolean), Lap number
- Uses `searchsorted()` to find last known value
- Prevents unphysical states like "gear = 6.7"

## State Management

### F1ReplayWindow State (`src/arcade_replay.py:36-95`)

Core state variables:
- `frame_idx: float` - Current playback frame (allows fractional for smooth seeking)
- `paused: bool` - Playback state toggle
- `speed_choices: List[float]` - [0.5, 1, 2, 4, 8, 16, 32, 64]
- `speed_i: int` - Index into speed_choices
- `selected_driver: str | None` - Driver for telemetry box focus
- `retired_drivers: Set[str]` - Drivers marked as OUT
- `last_progress: dict` - Previous frame progress for retirement detection

### Frame Data Structure

Each frame (`src/frames.py:100-121`) contains:
```python
{
    "t": float,              # Elapsed time in seconds
    "drivers": {
        "VER": {
            "x", "y": float,     # Track coordinates
            "speed": float,      # km/h
            "distance": float,   # Meters traveled
            "lap": int,
            "gear": int,
            "drs": int,          # 0 or 1
            "progress": float,   # Position metric
            "pos": int,          # Leaderboard position
            "compound": str,     # "SOFT", "MEDIUM", etc.
            "throttle": float,   # 0-100
            "brake": float,      # 0-100
        }
    },
    "weather": {...}
}
```

## Position Calculation

The "progress" metric (`src/frames.py:23-71`) uniquely orders drivers:

```
progress = (lap_number - 1) * lap_length + (distance % lap_length)
```

This handles lap boundary transitions correctly and allows simple sorting for positions.

## Coordinate System

### World Space
- FastF1 provides X, Y in meters relative to track origin
- Track stored in `src/track.py`

### Screen Space Transformation (`src/track.py:45-80`)
- Pre-computed affine transform for performance
- Centers track in window with padding
- Aspect ratio preservation

## Caching Pattern

Two-layer caching for different concerns:

### FastF1 Cache (External Data)
- Location: `.fastf1-cache/`
- Purpose: Avoid repeated API calls
- Control: `--force` flag bypasses

### Replay Cache (Computed Data)
- Location: `computed_data/`
- Format: Pickle files (`{year}_R{round:02d}_{session}_fps{fps}.pkl`)
- Contains: timeline, frames, metadata
- Control: `--refresh` flag bypasses
- Implementation: `src/cache.py:30-88`

## AI Racer Design

Simple, deterministic approach (`src/ai/simple_ai.py:9-56`):

1. Extract fastest lap telemetry from session
2. Create single-lap AI telemetry dict
3. Loop/tile the lap to match race duration:
   - Calculate lap time from telemetry
   - Repeat N times with time/distance offsets
   - Concatenate arrays

This avoids complex path planning while providing realistic "perfect" performance.

## Color Assignment

### Team Colors (`src/team_colors.py:10-45`)
- Hard-coded driver → team → RGB mapping
- Updated manually per season

### Fallback Colors (`src/colors.py:5-25`)
- MD5 hash of driver code → deterministic HSV
- Ensures unique colors for unknown drivers

## Event Handling Pattern

Arcade's event system (`src/arcade_replay.py:200-350`):

- `on_key_press()` - Keyboard input dispatch
- `on_mouse_press()` - Click handling (leaderboard selection, progress bar seeking)
- `on_mouse_motion()` - Hover state tracking
- `on_update(delta_time)` - Frame advance logic

## Error Handling Conventions

- Telemetry extraction uses try/except with logging (`src/telemetry.py:40-80`)
- Missing drivers silently skipped rather than crashing
- Default values provided for missing weather data

## Dataclass Usage

Two primary dataclasses:

1. **SessionInfo** (`src/f1_data.py:26-44`)
   - Immutable metadata container
   - Year, round, event name, circuit, driver list

2. **ReplayCache** (`src/cache.py:9-13`)
   - Serialization container
   - Meta dict, timeline array, frames list
