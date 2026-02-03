/**
 * F1 Race Replay — Web Frontend
 *
 * Main application: initializes canvas, loads session data,
 * runs the animation loop, and wires keyboard/mouse events.
 */

import { PlaybackState } from "./state.js";
import { DataLoader } from "./data-loader.js";
import { Renderer } from "./renderer.js";
import { buildWorldToScreenTransform } from "./transform.js";
import { leaderboardRects, leaderboardArrowRect } from "./panels/leaderboard.js";
import { progressBarRect } from "./panels/progress-bar.js";
import { speedTrapArrowRect } from "./panels/speed-trap.js";

// Qualifying UI imports (loaded dynamically)
import { miniTrackClickRects } from "./qualifying/mini-track.js";
import { lapTimesRects } from "./qualifying/lap-times-panel.js";

// Qualifying session types
const QUALIFYING_SESSIONS = ["Q", "Q1", "Q2", "Q3"];

class F1ReplayApp {
    constructor() {
        this.canvas = document.getElementById("replay-canvas");
        this.ctx = this.canvas.getContext("2d");

        this.state = new PlaybackState();
        this.loader = new DataLoader();
        this.renderer = new Renderer();

        this.transform = null;
        this.lastTimestamp = 0;
        this.isQualifying = false;

        this._setupCanvas();
        this._setupEvents();
        this._loadSessionList();
    }

    // ----- Canvas setup -----

    _setupCanvas() {
        this._resizeCanvas();
        window.addEventListener("resize", () => {
            this._resizeCanvas();
            this._recomputeTransform();
        });
    }

    _resizeCanvas() {
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = window.innerWidth * dpr;
        this.canvas.height = window.innerHeight * dpr;
        this.canvas.style.width = window.innerWidth + "px";
        this.canvas.style.height = window.innerHeight + "px";
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        // Logical size (CSS pixels) for drawing
        this.W = window.innerWidth;
        this.H = window.innerHeight;
    }

    _recomputeTransform() {
        if (!this.loader.track) return;
        const bounds = this.loader.track.bounds;
        this.transform = buildWorldToScreenTransform(bounds, this.W, this.H);
        this.renderer.updateTrack(this.loader.track, this.transform, this.H);
    }

    // ----- Session picker -----

    async _loadSessionList() {
        const select = document.getElementById("session-select");
        const loadBtn = document.getElementById("load-btn");

        try {
            const resp = await fetch("data/sessions.json");
            if (!resp.ok) throw new Error("No sessions found");
            const sessions = await resp.json();

            select.innerHTML = "";
            for (const s of sessions) {
                const opt = document.createElement("option");
                opt.value = s.dir;
                opt.textContent = `${s.year} R${String(s.round).padStart(2, "0")} ${s.sessionCode} — ${s.eventName}`;
                select.appendChild(opt);
            }
            loadBtn.disabled = false;

            loadBtn.addEventListener("click", () => {
                const dir = select.value;
                if (dir) this._loadSession(dir);
            });
        } catch (e) {
            select.innerHTML = '<option value="">No sessions exported yet</option>';
            console.error("Failed to load sessions.json:", e);
        }
    }

    async _loadSession(sessionDir) {
        const overlay = document.getElementById("loading-overlay");
        const picker = document.getElementById("session-picker-container");
        const progress = document.getElementById("load-progress");
        const status = document.getElementById("load-status");
        const bar = document.getElementById("load-bar");

        picker.classList.add("hidden");
        progress.classList.remove("hidden");

        try {
            // Load session data first to check session type
            status.textContent = "Loading manifest...";
            bar.style.width = "5%";
            const manifest = await this.loader.loadSession(sessionDir, (msg, pct) => {
                status.textContent = msg;
                bar.style.width = pct + "%";
            });

            // Check if this is a qualifying session
            this.isQualifying = QUALIFYING_SESSIONS.includes(manifest.sessionCode);

            // Create appropriate renderer and state based on session type
            if (this.isQualifying) {
                const { QualifyingRenderer } = await import("./qualifying-renderer.js");
                const { QualifyingState } = await import("./qualifying-state.js");
                this.renderer = new QualifyingRenderer();
                this.state = new QualifyingState();
            } else {
                this.renderer = new Renderer();
                this.state = new PlaybackState();
            }

            // Preload images
            status.textContent = "Loading assets...";
            bar.style.width = "70%";
            await this.renderer.preloadImages();

            // Set up state
            this.state.manifest = manifest;
            this.state.fps = manifest.fps;
            this.state.totalFrames = manifest.totalFrames;
            this.state.paused = true;
            this.state.frameIdx = 0;

            // Update fastest lap tracking from manifest
            this.state.fastestLapDriver = null;
            this.state.fastestLapTime = Infinity;

            // Compute transform
            this._recomputeTransform();

            // Hide overlay and start
            overlay.classList.add("hidden");
            this._startLoop();
        } catch (e) {
            status.textContent = `Error: ${e.message}`;
            console.error("Failed to load session:", e);
        }
    }

    // ----- Animation loop -----

    _startLoop() {
        this.lastTimestamp = performance.now();
        requestAnimationFrame((ts) => this._loop(ts));
    }

    _loop(timestamp) {
        const dt = (timestamp - this.lastTimestamp) / 1000; // seconds
        this.lastTimestamp = timestamp;

        // Advance playback
        const framesPerTick = this.state.speed * this.state.fps * dt;
        this.state.advance(framesPerTick);

        // Get current frame
        const frameIdx = Math.floor(this.state.frameIdx);
        const frame = this.loader.getFrame(frameIdx);

        // Track fastest lap from frame data
        if (frame && frame.fastestLap && frame.fastestLap.driver) {
            this.state.fastestLapDriver = frame.fastestLap.driver;
            this.state.fastestLapTime = frame.fastestLap.time;
        }

        // Ensure upcoming chunks are loaded
        this.loader.ensureChunk(Math.floor(frameIdx / this.loader.chunkSize));

        // Render
        this.renderer.draw(this.ctx, frame, this.state, this.state.manifest, this.transform, this.W, this.H);

        requestAnimationFrame((ts) => this._loop(ts));
    }

    // ----- Event handling -----

    _setupEvents() {
        // Keyboard
        window.addEventListener("keydown", (e) => this._onKeyDown(e));

        // Mouse
        this.canvas.addEventListener("click", (e) => this._onClick(e));
        this.canvas.addEventListener("mousemove", (e) => this._onMouseMove(e));
    }

    _onKeyDown(e) {
        switch (e.code) {
            case "Space":
                e.preventDefault();
                this.state.togglePause();
                break;
            case "ArrowRight":
                e.preventDefault();
                this.state.seekForward(5);
                break;
            case "ArrowLeft":
                e.preventDefault();
                this.state.seekBackward(5);
                break;
            case "ArrowUp":
                e.preventDefault();
                this.state.speedUp();
                break;
            case "ArrowDown":
                e.preventDefault();
                this.state.speedDown();
                break;
            case "KeyR":
                this.state.restart();
                break;
            case "KeyH":
                this.state.showUI = !this.state.showUI;
                break;
            case "KeyP":
                this.state.showProgressBar = !this.state.showProgressBar;
                break;
            case "KeyL":
                this.state.leaderboardCollapsed = !this.state.leaderboardCollapsed;
                break;
            case "KeyT":
                this.state.speedTrapCollapsed = !this.state.speedTrapCollapsed;
                break;
            case "KeyF":
            case "F11":
                e.preventDefault();
                this._toggleFullscreen();
                break;
        }
    }

    _onClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Progress bar click (common to both modes)
        if (this.state.showProgressBar && progressBarRect) {
            const pb = progressBarRect;
            if (x >= pb.x && x <= pb.x + pb.w && y >= pb.y && y <= pb.y + pb.h) {
                const progress = (x - pb.barX) / pb.barW;
                this.state.frameIdx = Math.max(0,
                    Math.min(progress * (this.state.totalFrames - 1), this.state.totalFrames - 1));
                // Clear telemetry on seek (if qualifying mode)
                if (this.isQualifying && this.state.clearTelemetry) {
                    this.state.clearTelemetry();
                }
                return;
            }
        }

        if (this.isQualifying) {
            // Qualifying UI click handling
            this._onQualifyingClick(x, y);
        } else {
            // Race UI click handling
            this._onRaceClick(x, y);
        }
    }

    _onRaceClick(x, y) {
        // Leaderboard arrow click
        if (leaderboardArrowRect) {
            const ar = leaderboardArrowRect;
            if (x >= ar.x && x <= ar.x + ar.w && y >= ar.y && y <= ar.y + ar.h) {
                this.state.leaderboardCollapsed = !this.state.leaderboardCollapsed;
                return;
            }
        }

        // Speed trap arrow click
        if (speedTrapArrowRect) {
            const ar = speedTrapArrowRect;
            if (x >= ar.x && x <= ar.x + ar.w && y >= ar.y && y <= ar.y + ar.h) {
                this.state.speedTrapCollapsed = !this.state.speedTrapCollapsed;
                return;
            }
        }

        // Leaderboard row click
        for (const r of leaderboardRects) {
            if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h) {
                this.state.selectedDriver = r.driver;
                return;
            }
        }
    }

    _onQualifyingClick(x, y) {
        // Mini track click (select driver by clicking on dot)
        for (const r of miniTrackClickRects) {
            if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h) {
                this.state.selectedDriver = r.driver;
                return;
            }
        }

        // Lap times panel row click
        for (const r of lapTimesRects) {
            if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h) {
                this.state.selectedDriver = r.driver;
                return;
            }
        }
    }

    _onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        this.state.hoverIndex = null;

        if (this.isQualifying) {
            // Qualifying UI hover handling (lap times panel)
            for (let i = 0; i < lapTimesRects.length; i++) {
                const r = lapTimesRects[i];
                if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h) {
                    this.state.hoverIndex = i;
                    break;
                }
            }
        } else {
            // Race UI hover handling (leaderboard)
            for (let i = 0; i < leaderboardRects.length; i++) {
                const r = leaderboardRects[i];
                if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h) {
                    this.state.hoverIndex = i;
                    break;
                }
            }
        }
    }

    _toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => {});
        } else {
            document.exitFullscreen().catch(() => {});
        }
    }
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    new F1ReplayApp();
});
