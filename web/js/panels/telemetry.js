/**
 * Selected driver telemetry box (left side, below weather).
 * Shows speed, gear, DRS, gaps, sector times, tyre strategy, throttle/brake bars.
 *
 * Arcade layout: boxY = weather_y - box_h - 15 (below weather).
 * Canvas: boxY = WEATHER_BOTTOM + 15 = 225px from top.
 */

import { drawF1Panel, drawText, COLORS, drsIsActive } from "../utils.js";
import { getOrderedDrivers } from "./header.js";
import { WEATHER_BOTTOM } from "./weather.js";

const BOX_W = 260;
const BOX_H = 340;

export function drawTelemetry(ctx, frame, state, manifest, images, W, H) {
    if (!state.selectedDriver) {
        const ordered = getOrderedDrivers(frame);
        if (ordered.length > 0) state.selectedDriver = ordered[0][0];
        else return;
    }

    const drv = state.selectedDriver;
    const st = frame.drivers[drv];
    if (!st) return;

    const boxX = 20;
    const boxY = WEATHER_BOTTOM + 15;  // Below weather panel

    const driverColor = manifest.driverColors[drv] || "#969696";

    // Panel (no red accent — use team color)
    drawF1Panel(ctx, boxX, boxY, BOX_W, BOX_H, { showRedAccent: false });

    // Team color accent bar (top)
    ctx.fillStyle = driverColor;
    ctx.fillRect(boxX, boxY, BOX_W, 3);

    // Team color left accent bar
    ctx.fillStyle = driverColor;
    ctx.fillRect(boxX + 4, boxY + 10, 4, BOX_H - 20);

    // Driver info
    const speed = st.s || 0;
    const gear = st.g || 0;
    const drs = st.d || 0;

    const throttleVal = Math.min(Math.max(st.t || 0, 0), 100);
    let rawBrake = st.b || 0;
    const brakeVal = Math.min(Math.max(rawBrake <= 1 ? rawBrake * 100 : rawBrake, 0), 100);

    // Calculate gaps
    const ordered = getOrderedDrivers(frame);
    const driverIdx = ordered.findIndex(([d]) => d === drv);
    const progList = ordered.map(([, s]) => s.pr || 0);
    const spdList = ordered.map(([, s]) => s.s || 1);

    let gapAhead = "";
    let gapBehind = "";

    if (driverIdx > 0) {
        const gapM = Math.max(0, progList[driverIdx - 1] - progList[driverIdx]);
        const spdA = Math.max(spdList[driverIdx - 1] / 3.6, 1);
        const spdT = Math.max(spdList[driverIdx] / 3.6, 1);
        const avg = Math.max(0.5 * (spdA + spdT), 1);
        gapAhead = `+${(gapM / avg).toFixed(1)}s`;
    }
    if (driverIdx >= 0 && driverIdx < ordered.length - 1) {
        const gapM = Math.max(0, progList[driverIdx] - progList[driverIdx + 1]);
        const spdB = Math.max(spdList[driverIdx + 1] / 3.6, 1);
        const spdT = Math.max(spdList[driverIdx] / 3.6, 1);
        const avg = Math.max(0.5 * (spdB + spdT), 1);
        gapBehind = `-${(gapM / avg).toFixed(1)}s`;
    }

    // Title (driver code in team color)
    drawText(ctx, drv, boxX + 15, boxY + 10, {
        color: driverColor, size: 16, bold: true,
    });

    // Info lines
    const lines = [
        `Speed: ${speed} km/h`,
        `Gear: ${gear}   DRS: ${drsIsActive(drs) ? "ON" : "OFF"}`,
        gapAhead ? `Ahead: ${gapAhead}` : "Ahead: ---",
        gapBehind ? `Behind: ${gapBehind}` : "Behind: ---",
    ];

    for (let i = 0; i < lines.length; i++) {
        drawText(ctx, lines[i], boxX + 15, boxY + 35 + i * 22, {
            color: COLORS.F1_LIGHT_GRAY, size: 13,
        });
    }

    // Divider
    const dividerY = boxY + 130;
    ctx.beginPath();
    ctx.moveTo(boxX + 12, dividerY);
    ctx.lineTo(boxX + BOX_W - 12, dividerY);
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 1;
    ctx.stroke();

    // --- SECTOR TIMES ---
    const sectorY = dividerY + 8;
    drawText(ctx, "SECTORS", boxX + 15, sectorY, {
        color: COLORS.F1_WHITE, size: 11, bold: true,
    });

    const overallBests = frame.overallBests || {};
    const sectors = [
        { label: "S1:", val: st.s1, best: overallBests.s1 },
        { label: "S2:", val: st.s2, best: overallBests.s2 },
        { label: "S3:", val: st.s3, best: overallBests.s3 },
    ];

    for (let i = 0; i < sectors.length; i++) {
        const sy = sectorY + 22 + i * 20;
        drawText(ctx, sectors[i].label, boxX + 15, sy, {
            color: COLORS.F1_LIGHT_GRAY, size: 12,
        });

        let valText, valColor;
        if (sectors[i].val == null) {
            valText = "---";
            valColor = COLORS.F1_LIGHT_GRAY;
        } else {
            valText = sectors[i].val.toFixed(3);
            valColor = (sectors[i].best != null && Math.abs(sectors[i].val - sectors[i].best) < 0.001)
                ? COLORS.FASTEST_PURPLE : COLORS.F1_WHITE;
        }
        drawText(ctx, valText, boxX + 130, sy, {
            color: valColor, size: 12, bold: true, align: "right",
        });
    }

    // Divider 2
    const divider2Y = sectorY + 90;
    ctx.beginPath();
    ctx.moveTo(boxX + 12, divider2Y);
    ctx.lineTo(boxX + BOX_W - 12, divider2Y);
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 1;
    ctx.stroke();

    // --- TYRE STRATEGY ---
    const tyreY = divider2Y + 8;
    drawText(ctx, "TYRE", boxX + 15, tyreY, {
        color: COLORS.F1_WHITE, size: 11, bold: true,
    });

    const compound = st.cp || "Unknown";
    const stint = st.st || 1;
    const tyreLife = st.tl || 0;
    const pitCount = st.pc || 0;

    const tyreLines = [
        `Compound: ${(compound || "---").substring(0, 3).toUpperCase()}`,
        `Age: ${tyreLife} laps`,
        `Stint: ${stint}  Pits: ${pitCount}`,
    ];

    for (let i = 0; i < tyreLines.length; i++) {
        drawText(ctx, tyreLines[i], boxX + 15, tyreY + 22 + i * 20, {
            color: COLORS.F1_LIGHT_GRAY, size: 12,
        });
    }

    // --- THROTTLE / BRAKE BARS (right side of box) ---
    const barW = 30;
    const barH = 100;
    const barX = boxX + BOX_W - 90;
    const barY = boxY + BOX_H - barH - 40;

    // Throttle bar
    ctx.fillStyle = COLORS.F1_DARK_GRAY;
    ctx.fillRect(barX, barY, barW, barH);
    if (throttleVal > 0) {
        const fillH = (throttleVal / 100) * barH;
        ctx.fillStyle = COLORS.DRS_GREEN;
        ctx.fillRect(barX, barY + barH - fillH, barW, fillH);
    }
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 1;
    ctx.strokeRect(barX, barY, barW, barH);

    drawText(ctx, "THR", barX + barW / 2, barY - 10, {
        color: COLORS.DRS_GREEN, size: 9, bold: true, align: "center",
    });

    // Brake bar
    const brakeX = barX + barW + 10;
    ctx.fillStyle = COLORS.F1_DARK_GRAY;
    ctx.fillRect(brakeX, barY, barW, barH);
    if (brakeVal > 0) {
        const fillH = (brakeVal / 100) * barH;
        ctx.fillStyle = COLORS.F1_RED;
        ctx.fillRect(brakeX, barY + barH - fillH, barW, fillH);
    }
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 1;
    ctx.strokeRect(brakeX, barY, barW, barH);

    drawText(ctx, "BRK", brakeX + barW / 2, barY - 10, {
        color: COLORS.F1_RED, size: 9, bold: true, align: "center",
    });
}
