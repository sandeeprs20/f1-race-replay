/**
 * Speed trap panel (bottom right): top 3 speeds.
 * Collapsible downward (shows only title bar when collapsed).
 *
 * Arcade layout: panel at x=width-240, y=45 (from bottom).
 * Canvas: positioned at bottom-right, above progress bar.
 */

import { drawF1Panel, drawText, COLORS } from "../utils.js";

// Store click rect for collapse arrow (exported for app.js)
export let speedTrapArrowRect = null;

const COLLAPSED_H = 35;
const FULL_H = 135;
const PANEL_W = 220;

export function drawSpeedTrap(ctx, state, manifest, W, H) {
    const topSpeeds = manifest.topSpeeds;
    if (!topSpeeds || topSpeeds.length === 0) return;

    const collapsed = state.speedTrapCollapsed;
    const panelH = collapsed ? COLLAPSED_H : FULL_H;
    const panelX = W - PANEL_W - 20;
    // Bottom-right, 45px above bottom edge
    const panelY = H - panelH - 45;

    drawF1Panel(ctx, panelX, panelY, PANEL_W, panelH);

    drawText(ctx, "TOP SPEEDS", panelX + 12, panelY + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    // Collapse/expand arrow (points down when expanded, up when collapsed)
    const arrowX = panelX + PANEL_W - 20;
    const arrowY = panelY + 16;
    const arrowSize = 6;

    speedTrapArrowRect = { x: arrowX - 12, y: arrowY - 12, w: 24, h: 24 };

    ctx.beginPath();
    if (collapsed) {
        // Arrow pointing up (to expand)
        ctx.moveTo(arrowX - arrowSize, arrowY + arrowSize / 2);
        ctx.lineTo(arrowX, arrowY - arrowSize / 2);
        ctx.lineTo(arrowX + arrowSize, arrowY + arrowSize / 2);
    } else {
        // Arrow pointing down (to collapse)
        ctx.moveTo(arrowX - arrowSize, arrowY - arrowSize / 2);
        ctx.lineTo(arrowX, arrowY + arrowSize / 2);
        ctx.lineTo(arrowX + arrowSize, arrowY - arrowSize / 2);
    }
    ctx.fillStyle = COLORS.F1_LIGHT_GRAY;
    ctx.fill();

    // Draw speed entries only when expanded
    if (!collapsed) {
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
}
