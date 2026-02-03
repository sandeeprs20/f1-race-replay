/**
 * Lap times panel for qualifying UI.
 * Shows sorted best lap times with driver codes, gaps, and team colors.
 */

import { drawF1Panel, drawText, COLORS, formatLapTime, compoundKey } from "../utils.js";

const ROW_H = 24;
const TITLE_H = 32;

// Export click rects for app.js
export let lapTimesRects = [];

/**
 * Get drivers sorted by best lap time for qualifying.
 * Returns array of [driver, driverState, bestTime]
 */
function getSortedQualifyingTimes(frame, state) {
    if (!frame || !frame.drivers) return [];

    const entries = [];
    for (const [drv, st] of Object.entries(frame.drivers)) {
        // Use bt (best time) from frame, or from state tracking
        let bestTime = st.bt || state.bestLapTimes[drv]?.time || null;
        entries.push([drv, st, bestTime]);
    }

    // Sort by best time (null times at the end)
    entries.sort((a, b) => {
        if (a[2] === null && b[2] === null) return 0;
        if (a[2] === null) return 1;
        if (b[2] === null) return -1;
        return a[2] - b[2];
    });

    return entries;
}

/**
 * Draw the lap times leaderboard panel for qualifying.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} panelX - Panel X position
 * @param {number} panelY - Panel Y position
 * @param {number} panelW - Panel width
 * @param {number} panelH - Max panel height
 * @param {Object} frame - Current frame data
 * @param {Object} state - QualifyingState instance
 * @param {Object} manifest - Session manifest with driverColors
 * @param {Object} images - Preloaded images (tyres)
 */
export function drawLapTimesPanel(ctx, panelX, panelY, panelW, panelH, frame, state, manifest, images) {
    // Reset click rects
    lapTimesRects = [];

    const sorted = getSortedQualifyingTimes(frame, state);
    const numDrivers = Math.min(sorted.length, 20);

    // Calculate actual panel height
    const actualH = Math.min(TITLE_H + 8 + numDrivers * ROW_H + 15, panelH);

    // Panel background
    drawF1Panel(ctx, panelX, panelY, panelW, actualH);

    // Title
    drawText(ctx, "LAP TIMES", panelX + 12, panelY + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    // Get fastest time for gap calculation
    const fastestTime = sorted.length > 0 && sorted[0][2] !== null ? sorted[0][2] : null;
    const fastestDriver = sorted.length > 0 ? sorted[0][0] : null;

    const topY = panelY + TITLE_H + 4;

    for (let idx = 0; idx < numDrivers; idx++) {
        const [drv, st, bestTime] = sorted[idx];
        const rowTop = topY + idx * ROW_H;
        const rowCy = rowTop + ROW_H / 2;
        const pos = idx + 1;

        // Save click rect
        lapTimesRects.push({
            x: panelX + 6,
            y: rowTop,
            w: panelW - 12,
            h: ROW_H,
            driver: drv,
        });

        // Alternating row background
        const rowBg = idx % 2 === 0 ? "rgba(35,35,45,0.78)" : "rgba(28,28,38,0.78)";
        ctx.fillStyle = rowBg;
        ctx.fillRect(panelX + 6, rowTop + 1, panelW - 12, ROW_H - 2);

        // Team color left accent bar
        const teamColor = manifest.driverColors[drv] || "#969696";
        ctx.fillStyle = teamColor;
        ctx.fillRect(panelX + 6, rowTop + 2, 3, ROW_H - 4);

        // Hover highlight
        if (state.hoverIndex === idx) {
            ctx.fillStyle = "rgba(255,255,255,0.10)";
            ctx.fillRect(panelX + 6, rowTop + 1, panelW - 12, ROW_H - 2);
        }

        // Selected highlight
        if (state.selectedDriver === drv) {
            ctx.fillStyle = "rgba(225,6,0,0.20)";
            ctx.fillRect(panelX + 6, rowTop + 1, panelW - 12, ROW_H - 2);
        }

        // Position color (P1=gold, P2=silver, P3=bronze, fastest=purple)
        let posColor = COLORS.F1_WHITE;
        if (drv === fastestDriver && bestTime !== null) {
            posColor = COLORS.FASTEST_PURPLE;
        } else if (pos === 1) {
            posColor = COLORS.P1_GOLD;
        } else if (pos === 2) {
            posColor = COLORS.P2_SILVER;
        } else if (pos === 3) {
            posColor = COLORS.P3_BRONZE;
        }

        // Position and driver code
        drawText(ctx, `${String(pos).padStart(2, " ")}. ${drv}`, panelX + 14, rowCy, {
            color: posColor, size: 13, baseline: "middle",
        });

        // Best lap time
        const timeX = panelX + 85;
        if (bestTime !== null) {
            const timeStr = formatLapTime(bestTime);
            const timeColor = (drv === fastestDriver) ? COLORS.FASTEST_PURPLE : COLORS.F1_WHITE;
            drawText(ctx, timeStr, timeX, rowCy, {
                color: timeColor, size: 12, bold: (drv === fastestDriver), baseline: "middle",
            });
        } else {
            drawText(ctx, "NO TIME", timeX, rowCy, {
                color: COLORS.F1_GRAY, size: 11, baseline: "middle",
            });
        }

        // Gap to P1
        const gapX = panelX + panelW - 55;
        if (idx === 0 && bestTime !== null) {
            // P1 shows nothing or "P1"
        } else if (bestTime !== null && fastestTime !== null) {
            const gap = bestTime - fastestTime;
            const gapStr = `+${gap.toFixed(3)}`;
            drawText(ctx, gapStr, gapX, rowCy, {
                color: COLORS.INTERVAL_YELLOW, size: 11, align: "right", baseline: "middle",
            });
        }

        // Tyre indicator (small dot)
        const tyreKey = compoundKey(st.cp);
        const tyreImg = images[tyreKey];
        if (tyreImg) {
            const tyreX = panelX + panelW - 22;
            ctx.drawImage(tyreImg, tyreX - 8, rowCy - 8, 16, 16);
        }
    }
}
