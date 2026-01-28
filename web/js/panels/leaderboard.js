/**
 * Leaderboard panel (right side): position, driver, gap, tyre, DRS.
 * Supports collapsed/expanded, click-to-select, hover highlight.
 *
 * Arcade layout: lb_y=50 (bottom), lb_h=height-120, top at height-70.
 * Canvas: panelY=70 (top), extends downward to H-50.
 */

import { drawF1Panel, drawText, COLORS, compoundKey, drsIsActive } from "../utils.js";
import { getOrderedDrivers } from "./header.js";

const ROW_H = 25;
const TITLE_H = 32;
const PADDING = 12;
const FULL_W = 300;
const COLLAPSED_W = 115;

// Store click rects for mouse interaction (exported for app.js)
export let leaderboardRects = [];
export let leaderboardArrowRect = null;

export function drawLeaderboard(ctx, frame, state, manifest, images, W, H) {
    const collapsed = state.leaderboardCollapsed;
    const panelW = collapsed ? COLLAPSED_W : FULL_W;
    const panelX = W - panelW - 20;

    const ordered = getOrderedDrivers(frame);
    const numDrivers = Math.min(ordered.length, 20);
    const panelH = TITLE_H + 8 + numDrivers * ROW_H + 15;

    // Top of panel at 70px from top (matches Arcade layout)
    const panelY = 70;

    // Panel background
    drawF1Panel(ctx, panelX, panelY, panelW, panelH);

    // Default selection
    if (!state.selectedDriver && ordered.length > 0) {
        state.selectedDriver = ordered[0][0];
    }

    // Title
    drawText(ctx, collapsed ? "LB" : "LEADERBOARD", panelX + 12, panelY + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    // Collapse/expand arrow
    const arrowX = panelX + panelW - 20;
    const arrowY = panelY + 16;
    const arrowSize = 6;

    leaderboardArrowRect = { x: arrowX - 12, y: arrowY - 12, w: 24, h: 24 };

    ctx.beginPath();
    if (collapsed) {
        // Arrow pointing left (to expand)
        ctx.moveTo(arrowX + arrowSize, arrowY - arrowSize);
        ctx.lineTo(arrowX - arrowSize, arrowY);
        ctx.lineTo(arrowX + arrowSize, arrowY + arrowSize);
    } else {
        // Arrow pointing right (to collapse)
        ctx.moveTo(arrowX - arrowSize, arrowY - arrowSize);
        ctx.lineTo(arrowX + arrowSize, arrowY);
        ctx.lineTo(arrowX - arrowSize, arrowY + arrowSize);
    }
    ctx.fillStyle = COLORS.F1_LIGHT_GRAY;
    ctx.fill();

    // Progress and speed lists for gap calculation
    const progList = ordered.map(([, st]) => st.pr || 0);
    const spdList = ordered.map(([, st]) => st.s || 0);

    // Reset click rects
    leaderboardRects = [];

    const topY = panelY + TITLE_H + 8;
    const xText = panelX + PADDING;
    const xGap = panelX + panelW - 90;
    const xTyre = panelX + panelW - 52;
    const xDrs = panelX + panelW - 20;

    for (let idx = 0; idx < numDrivers; idx++) {
        const [drv, st] = ordered[idx];
        const rowTop = topY + idx * ROW_H;
        const rowBottom = rowTop + ROW_H;
        const rowCy = (rowTop + rowBottom) / 2;

        // Save click rect
        leaderboardRects.push({
            x: panelX + 6,
            y: rowTop,
            w: panelW - 12,
            h: ROW_H,
            driver: drv,
        });

        const pos = st.p || (idx + 1);

        // Alternating row bg
        const rowBg = idx % 2 === 0 ? "rgba(35,35,45,0.78)" : "rgba(28,28,38,0.78)";
        ctx.fillStyle = rowBg;
        ctx.fillRect(panelX + 6, rowTop + 1, panelW - 12, ROW_H - 2);

        // Team color left accent bar
        const teamColor = manifest.driverColors[drv] || "#969696";
        ctx.fillStyle = teamColor;
        ctx.fillRect(panelX + 6, rowTop + 2, 4, ROW_H - 4);

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

        // Position color
        let posColor = COLORS.F1_WHITE;
        if (state.fastestLapDriver === drv) {
            posColor = COLORS.FASTEST_PURPLE;
        } else if (pos === 1) {
            posColor = COLORS.P1_GOLD;
        } else if (pos === 2) {
            posColor = COLORS.P2_SILVER;
        } else if (pos === 3) {
            posColor = COLORS.P3_BRONZE;
        }

        // Driver text
        drawText(ctx, `${String(pos).padStart(2, " ")}. ${drv}`, xText + 6, rowCy, {
            color: posColor, size: 14, baseline: "middle",
        });

        // Expanded columns
        if (!collapsed) {
            // Gap
            let gapStr, gapColor;
            if (idx === 0) {
                gapStr = "LEADER";
                gapColor = COLORS.F1_WHITE;
            } else {
                const gapM = Math.max(0, progList[idx - 1] - progList[idx]);
                const spdAhead = Math.max(spdList[idx - 1] / 3.6, 1);
                const spdThis = Math.max(spdList[idx] / 3.6, 1);
                const avgSpd = Math.max(0.5 * (spdAhead + spdThis), 1);
                const gapS = gapM / avgSpd;
                gapStr = `+${gapS.toFixed(1)}`;
                gapColor = COLORS.INTERVAL_YELLOW;
            }
            drawText(ctx, gapStr, xGap, rowCy, {
                color: gapColor, size: 12, align: "right", baseline: "middle",
            });

            // Tyre icon
            const tyreKey = compoundKey(st.cp);
            const tyreImg = images[tyreKey];
            if (tyreImg) {
                ctx.drawImage(tyreImg, xTyre - 8, rowCy - 8, 16, 16);
            }

            // DRS indicator
            const drsOn = drsIsActive(st.d);
            ctx.beginPath();
            ctx.arc(xDrs, rowCy, drsOn ? 5 : 4, 0, Math.PI * 2);
            ctx.fillStyle = drsOn ? COLORS.DRS_GREEN : COLORS.F1_GRAY;
            ctx.fill();
        }
    }
}
