/**
 * Main draw orchestrator. Calls all panel renderers in order.
 */

import { TrackRenderer } from "./track-renderer.js";
import { drawHeader } from "./panels/header.js";
import { drawLeaderboard } from "./panels/leaderboard.js";
import { drawWeather } from "./panels/weather.js";
import { drawTelemetry } from "./panels/telemetry.js";
import { drawProgressBar } from "./panels/progress-bar.js";
import { drawTrackStatus } from "./panels/track-status.js";
import { drawFastestLap } from "./panels/fastest-lap.js";
import { drawRaceMessages } from "./panels/race-messages.js";
// Overtake feed removed - not useful
import { drawSpeedTrap } from "./panels/speed-trap.js";
import { drawControls } from "./panels/controls.js";
import { COLORS } from "./utils.js";

export class Renderer {
    constructor() {
        this.trackRenderer = new TrackRenderer();
        this.images = {};
    }

    /**
     * Preload all image assets.
     */
    async preloadImages() {
        const assetPaths = {
            "soft": "assets/tyres/soft.png",
            "medium": "assets/tyres/medium.png",
            "hard": "assets/tyres/hard.png",
            "intermediate": "assets/tyres/intermediate.png",
            "wet": "assets/tyres/wet.png",
            "unknown": "assets/tyres/unknown.png",
            "weather_clear": "assets/weather/clear.png",
            "weather_rain": "assets/weather/rain.png",
            "weather_cloudy": "assets/weather/cloudy.png",
            "pixel_car": "assets/pixel_car.png",
        };

        const promises = Object.entries(assetPaths).map(([key, path]) => {
            return new Promise((resolve) => {
                const img = new Image();
                img.onload = () => {
                    this.images[key] = img;
                    resolve();
                };
                img.onerror = () => {
                    // Missing asset is okay — just skip
                    resolve();
                };
                img.src = path;
            });
        });

        await Promise.all(promises);
    }

    /**
     * Recompute track screen points after resize.
     */
    updateTrack(trackData, transform, screenH) {
        this.trackRenderer.computeScreenPoints(trackData, transform, screenH);
    }

    /**
     * Main draw call — renders one frame.
     */
    draw(ctx, frame, state, manifest, transform, W, H) {

        // Clear
        ctx.fillStyle = COLORS.F1_BLACK;
        ctx.fillRect(0, 0, W, H);

        if (!frame) return;

        // Track
        this.trackRenderer.drawTrack(ctx);

        // Cars
        this.trackRenderer.drawCars(
            ctx, frame, manifest.driverColors, state.selectedDriver, transform, H
        );

        // Header (GP name, session, lap, time)
        drawHeader(ctx, frame, state, manifest, W, H);

        // UI panels
        if (state.showUI) {
            drawLeaderboard(ctx, frame, state, manifest, this.images, W, H);
            drawWeather(ctx, frame, this.images, W, H);
            drawTelemetry(ctx, frame, state, manifest, this.images, W, H);
            drawControls(ctx, W, H);
            drawTrackStatus(ctx, frame, W, H);
            drawFastestLap(ctx, frame, W, H);
            drawRaceMessages(ctx, frame, W, H);
            drawSpeedTrap(ctx, state, manifest, W, H);
        }

        // Progress bar (separate toggle)
        if (state.showProgressBar) {
            drawProgressBar(ctx, state, this.images, W, H);
        }
    }
}
