/**
 * Overtake feed (left side, above controls).
 *
 * Arcade layout: panel at x=20, y=200 (from bottom).
 * Canvas: positioned above controls area near the bottom-left.
 */

import { drawF1Panel, drawText, COLORS } from "../utils.js";

export function drawOvertakeFeed(ctx, frame, state, manifest, W, H) {
    const currentTime = frame.t || 0;
    const changes = frame.positionChanges || [];

    // Add new overtakes
    for (const change of changes) {
        state.recentOvertakes.push({
            driver: change.driver || "",
            passed: change.passed || "",
            newPos: change.toPos || 0,
            time: currentTime,
        });
    }

    // Remove old overtakes (>15s)
    state.recentOvertakes = state.recentOvertakes.filter(
        o => currentTime - o.time <= 15
    );

    // Keep only last 2
    const recent = state.recentOvertakes.slice(-2);

    if (recent.length === 0) return;

    const panelW = 260;
    const panelH = 45 + recent.length * 26;
    const panelX = 20;
    // Position above the controls area (controls start at H - 165)
    const panelY = H - 165 - panelH - 10;

    drawF1Panel(ctx, panelX, panelY, panelW, panelH);

    drawText(ctx, "OVERTAKES", panelX + 12, panelY + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    let yOffset = panelY + 38;
    for (let i = recent.length - 1; i >= 0; i--) {
        const o = recent[i];
        const text = o.passed
            ? `${o.driver} passes ${o.passed} for P${o.newPos}`
            : `${o.driver} gains P${o.newPos}`;

        const driverCol = manifest.driverColors[o.driver] || COLORS.F1_WHITE;

        drawText(ctx, text, panelX + 12, yOffset, {
            color: driverCol, size: 12,
        });
        yOffset += 26;
    }
}
