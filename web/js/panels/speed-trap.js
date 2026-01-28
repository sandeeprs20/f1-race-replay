/**
 * Speed trap panel (bottom right): top 3 speeds.
 *
 * Arcade layout: panel at x=width-240, y=45 (from bottom).
 * Canvas: positioned at bottom-right, above progress bar.
 */

import { drawF1Panel, drawText, COLORS } from "../utils.js";

export function drawSpeedTrap(ctx, manifest, W, H) {
    const topSpeeds = manifest.topSpeeds;
    if (!topSpeeds || topSpeeds.length === 0) return;

    const panelW = 220;
    const panelH = 135;
    const panelX = W - panelW - 20;
    // Bottom-right, 45px above bottom edge
    const panelY = H - panelH - 45;

    drawF1Panel(ctx, panelX, panelY, panelW, panelH);

    drawText(ctx, "TOP SPEEDS", panelX + 12, panelY + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    let yOffset = panelY + 40;
    for (let i = 0; i < Math.min(topSpeeds.length, 3); i++) {
        const entry = topSpeeds[i];
        const driverCol = manifest.driverColors[entry.driver] || COLORS.F1_WHITE;
        drawText(ctx, `${i + 1}. ${entry.driver} ${entry.speed.toFixed(1)} km/h`, panelX + 12, yOffset, {
            color: driverCol, size: 13,
        });
        yOffset += 30;
    }
}
