/**
 * Weather panel (upper left, below lap counter).
 *
 * Arcade layout: bottom-left Y = height - 210, so panel spans
 *   70px..210px from screen top. Canvas: panelY = 70.
 */

import { drawF1Panel, drawText, COLORS } from "../utils.js";

const PANEL_W = 180;
const PANEL_H = 140;

export function drawWeather(ctx, frame, images, W, H) {
    const panelX = 20;
    const panelY = 70;   // 70px from top (matches Arcade layout)

    drawF1Panel(ctx, panelX, panelY, PANEL_W, PANEL_H);

    // Title
    drawText(ctx, "WEATHER", panelX + 12, panelY + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    // Weather data
    const weather = frame.weather || {};
    const trackTemp = weather.TrackTemp || 0;
    const airTemp = weather.AirTemp || 0;
    const humidity = weather.Humidity || 0;
    const rainfall = weather.Rainfall || false;
    const windSpeed = weather.WindSpeed || 0;

    // Weather icon
    const iconKey = rainfall ? "weather_rain" : (humidity > 70 ? "weather_cloudy" : "weather_clear");
    const icon = images[iconKey];
    if (icon) {
        const iconX = panelX + PANEL_W - 34;
        const iconY = panelY + 6;
        ctx.drawImage(icon, iconX, iconY, 24, 24);
    }

    // Info lines
    const lines = [
        trackTemp > 0 ? `Track: ${trackTemp.toFixed(1)}C` : "Track: --",
        airTemp > 0 ? `Air: ${airTemp.toFixed(1)}C` : "Air: --",
        humidity > 0 ? `Humidity: ${Math.round(humidity)}%` : "Humidity: --",
        windSpeed > 0 ? `Wind: ${windSpeed.toFixed(1)} km/h` : "Wind: --",
        `Rain: ${rainfall ? "WET" : "DRY"}`,
    ];

    const startY = panelY + 32;
    for (let i = 0; i < lines.length; i++) {
        drawText(ctx, lines[i], panelX + 12, startY + i * 20, {
            color: COLORS.F1_LIGHT_GRAY, size: 10,
        });
    }
}

// Export layout constants for other panels to reference
export const WEATHER_BOTTOM = 70 + PANEL_H;  // 210px from top
