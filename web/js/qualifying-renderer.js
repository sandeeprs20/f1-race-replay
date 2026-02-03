/**
 * Qualifying session renderer.
 * Orchestrates all qualifying UI components: header, mini track,
 * telemetry graphs, weather, driver focus, lap times panel.
 */

import { COLORS } from "./utils.js";
import { drawProgressBar } from "./panels/progress-bar.js";
import { drawControls } from "./panels/controls.js";
import { drawTrackStatus } from "./panels/track-status.js";
import { drawFastestLap } from "./panels/fastest-lap.js";

import { drawQualifyingHeader } from "./qualifying/header.js";
import { drawSpeedGraph, drawThrottleBrakeGraph } from "./qualifying/telemetry-graph.js";
import { drawMiniTrack } from "./qualifying/mini-track.js";
import { drawLapTimesPanel } from "./qualifying/lap-times-panel.js";
import { drawDriverFocus } from "./qualifying/driver-focus.js";
import { drawWeatherCompact } from "./qualifying/weather-compact.js";

export class QualifyingRenderer {
    constructor() {
        this.images = {};
        this.trackData = null;
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
                    resolve();
                };
                img.src = path;
            });
        });

        await Promise.all(promises);
    }

    /**
     * Store track data for the mini track component.
     */
    updateTrack(trackData, transform, screenH) {
        this.trackData = trackData;
    }

    /**
     * Main draw call for qualifying UI.
     */
    draw(ctx, frame, state, manifest, transform, W, H) {
        // Clear canvas
        ctx.fillStyle = COLORS.F1_BLACK;
        ctx.fillRect(0, 0, W, H);

        if (!frame) return;

        // Set default selected driver if not set
        if (!state.selectedDriver && frame.drivers) {
            const drivers = Object.keys(frame.drivers);
            if (drivers.length > 0) {
                state.selectedDriver = drivers[0];
            }
        }

        // Update lap telemetry in state
        state.updateLapTelemetry(frame);

        // Get lap length from manifest (or estimate from track data)
        const lapLength = manifest.lapLength || 5000;

        // --- Layout calculations ---
        // Left column: Mini track, Weather, Driver focus
        const leftColX = 20;
        const leftColW = 200;

        // Right column: Lap times panel
        const rightColW = 260;
        const rightColX = W - rightColW - 20;

        // Center area: Telemetry graphs
        const graphsX = leftColX + leftColW + 20;
        const graphsW = rightColX - graphsX - 20;
        const graphH = Math.min(180, (H - 200) / 2 - 20);

        // --- Draw components ---

        // 1. Header (GP name, session type, session time)
        drawQualifyingHeader(ctx, frame, state, manifest, W, H);

        // 2. Track status indicators (flags, safety car)
        if (state.showUI) {
            drawTrackStatus(ctx, frame, W, H);
            drawFastestLap(ctx, frame, W, H);
        }

        // 3. Mini track (top-left, below header)
        const miniTrackY = 70;
        const miniTrackH = 200;
        drawMiniTrack(ctx, leftColX, miniTrackY, leftColW, miniTrackH,
            frame, this.trackData, manifest.driverColors, state.selectedDriver);

        // 4. Weather panel (compact, below mini track)
        const weatherY = miniTrackY + miniTrackH + 10;
        const weatherH = 80;
        drawWeatherCompact(ctx, leftColX, weatherY, leftColW, weatherH, frame, this.images);

        // 5. Driver focus panel (below weather)
        const driverFocusY = weatherY + weatherH + 10;
        const driverFocusH = H - driverFocusY - 180; // Leave room for controls
        drawDriverFocus(ctx, leftColX, driverFocusY, leftColW, Math.max(driverFocusH, 280),
            frame, state, manifest, this.images);

        // 6. Telemetry graphs (center)
        const graphsY = 70;

        // Speed graph
        const selectedTelemetry = state.getTelemetry(state.selectedDriver);
        drawSpeedGraph(ctx, graphsX, graphsY, graphsW, graphH,
            selectedTelemetry, lapLength);

        // Throttle/Brake graph (below speed graph)
        drawThrottleBrakeGraph(ctx, graphsX, graphsY + graphH + 20, graphsW, graphH,
            selectedTelemetry, lapLength);

        // 7. Lap times panel (right side)
        const lapTimesY = 70;
        const lapTimesH = H - 120;
        drawLapTimesPanel(ctx, rightColX, lapTimesY, rightColW, lapTimesH,
            frame, state, manifest, this.images);

        // 8. Controls reference (bottom-left)
        if (state.showUI) {
            drawControls(ctx, W, H);
        }

        // 9. Progress bar (bottom center)
        if (state.showProgressBar) {
            drawProgressBar(ctx, state, this.images, W, H);
        }
    }
}
