/**
 * Compact weather panel for qualifying UI.
 * Positioned within the left column layout.
 */

import { drawF1Panel, drawText, COLORS } from "../utils.js";

/**
 * Draw a compact weather panel at the specified position.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} panelX - Panel X position
 * @param {number} panelY - Panel Y position
 * @param {number} panelW - Panel width
 * @param {number} panelH - Panel height
 * @param {Object} frame - Current frame data
 * @param {Object} images - Preloaded weather icons
 */
export function drawWeatherCompact(ctx, panelX, panelY, panelW, panelH, frame, images) {
    drawF1Panel(ctx, panelX, panelY, panelW, panelH);

    // Title
    drawText(ctx, "WEATHER", panelX + 12, panelY + 8, {
        color: COLORS.F1_WHITE, size: 11, bold: true,
    });

    // Weather data
    const weather = frame.weather || {};
    const trackTemp = weather.TrackTemp || 0;
    const airTemp = weather.AirTemp || 0;
    const humidity = weather.Humidity || 0;
    const rainfall = weather.Rainfall || false;

    // Weather icon
    const iconKey = rainfall ? "weather_rain" : (humidity > 70 ? "weather_cloudy" : "weather_clear");
    const icon = images[iconKey];
    if (icon) {
        const iconX = panelX + panelW - 30;
        const iconY = panelY + 6;
        ctx.drawImage(icon, iconX, iconY, 20, 20);
    }

    // Compact info lines
    const lineH = 16;
    let y = panelY + 28;

    drawText(ctx, `Track: ${trackTemp > 0 ? trackTemp.toFixed(0) + "C" : "--"}`, panelX + 12, y, {
        color: COLORS.F1_LIGHT_GRAY, size: 10,
    });
    y += lineH;

    drawText(ctx, `Air: ${airTemp > 0 ? airTemp.toFixed(0) + "C" : "--"}`, panelX + 12, y, {
        color: COLORS.F1_LIGHT_GRAY, size: 10,
    });
    y += lineH;

    drawText(ctx, `${rainfall ? "WET" : "DRY"} | ${Math.round(humidity)}%`, panelX + 12, y, {
        color: rainfall ? COLORS.F1_RED : COLORS.F1_LIGHT_GRAY, size: 10,
    });
}
