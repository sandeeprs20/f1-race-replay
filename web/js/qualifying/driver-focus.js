/**
 * Driver focus panel for qualifying UI.
 * Shows detailed telemetry and lap times for the selected driver.
 */

import { drawF1Panel, drawText, COLORS, formatLapTime, drsIsActive, compoundKey } from "../utils.js";

/**
 * Draw the driver focus panel with detailed telemetry.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} panelX - Panel X position
 * @param {number} panelY - Panel Y position
 * @param {number} panelW - Panel width
 * @param {number} panelH - Panel height
 * @param {Object} frame - Current frame data
 * @param {Object} state - QualifyingState instance
 * @param {Object} manifest - Session manifest with driverColors
 * @param {Object} images - Preloaded images (tyres)
 */
export function drawDriverFocus(ctx, panelX, panelY, panelW, panelH, frame, state, manifest, images) {
    const drv = state.selectedDriver;
    if (!drv || !frame || !frame.drivers || !frame.drivers[drv]) {
        // Draw empty panel
        drawF1Panel(ctx, panelX, panelY, panelW, panelH, { showRedAccent: false });
        drawText(ctx, "SELECT A DRIVER", panelX + 12, panelY + panelH / 2, {
            color: COLORS.F1_GRAY, size: 12, baseline: "middle",
        });
        return;
    }

    const st = frame.drivers[drv];
    const driverColor = manifest.driverColors[drv] || "#969696";

    // Panel background with team color accent
    drawF1Panel(ctx, panelX, panelY, panelW, panelH, { showRedAccent: false });

    // Team color accent bar (top)
    ctx.fillStyle = driverColor;
    ctx.fillRect(panelX, panelY, panelW, 3);

    // Team color left accent bar
    ctx.fillStyle = driverColor;
    ctx.fillRect(panelX + 4, panelY + 10, 4, panelH - 20);

    // Driver code
    drawText(ctx, drv, panelX + 15, panelY + 10, {
        color: driverColor, size: 16, bold: true,
    });

    // Current telemetry
    const speed = st.s || 0;
    const gear = st.g || 0;
    const drs = st.d || 0;
    const lap = st.l || 1;

    let lineY = panelY + 38;
    const lineH = 20;

    // Speed and gear
    drawText(ctx, `Speed: ${speed} km/h`, panelX + 15, lineY, {
        color: COLORS.F1_LIGHT_GRAY, size: 12,
    });
    lineY += lineH;

    drawText(ctx, `Gear: ${gear}   DRS: ${drsIsActive(drs) ? "ON" : "OFF"}`, panelX + 15, lineY, {
        color: COLORS.F1_LIGHT_GRAY, size: 12,
    });
    lineY += lineH;

    drawText(ctx, `Lap: ${lap}`, panelX + 15, lineY, {
        color: COLORS.F1_LIGHT_GRAY, size: 12,
    });
    lineY += lineH + 5;

    // Divider
    ctx.beginPath();
    ctx.moveTo(panelX + 12, lineY);
    ctx.lineTo(panelX + panelW - 12, lineY);
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 1;
    ctx.stroke();
    lineY += 10;

    // Best lap time section
    drawText(ctx, "BEST LAP", panelX + 15, lineY, {
        color: COLORS.F1_WHITE, size: 11, bold: true,
    });
    lineY += lineH;

    const bestTime = st.bt || state.bestLapTimes[drv]?.time || null;
    if (bestTime !== null) {
        drawText(ctx, formatLapTime(bestTime), panelX + 15, lineY, {
            color: COLORS.FASTEST_PURPLE, size: 14, bold: true,
        });
    } else {
        drawText(ctx, "NO TIME", panelX + 15, lineY, {
            color: COLORS.F1_GRAY, size: 12,
        });
    }
    lineY += lineH + 5;

    // Divider
    ctx.beginPath();
    ctx.moveTo(panelX + 12, lineY);
    ctx.lineTo(panelX + panelW - 12, lineY);
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 1;
    ctx.stroke();
    lineY += 10;

    // Current lap sectors
    drawText(ctx, "CURRENT LAP", panelX + 15, lineY, {
        color: COLORS.F1_WHITE, size: 11, bold: true,
    });
    lineY += lineH;

    const overallBests = frame.overallBests || {};
    const sectors = [
        { label: "S1:", val: st.s1, best: overallBests.s1 },
        { label: "S2:", val: st.s2, best: overallBests.s2 },
        { label: "S3:", val: st.s3, best: overallBests.s3 },
    ];

    for (const sector of sectors) {
        drawText(ctx, sector.label, panelX + 15, lineY, {
            color: COLORS.F1_LIGHT_GRAY, size: 11,
        });

        let valText, valColor;
        if (sector.val == null) {
            valText = "---";
            valColor = COLORS.F1_LIGHT_GRAY;
        } else {
            valText = sector.val.toFixed(3);
            // Check if this is the overall best sector
            valColor = (sector.best != null && Math.abs(sector.val - sector.best) < 0.001)
                ? COLORS.FASTEST_PURPLE : COLORS.F1_WHITE;
        }

        drawText(ctx, valText, panelX + 100, lineY, {
            color: valColor, size: 11, bold: valColor === COLORS.FASTEST_PURPLE, align: "right",
        });
        lineY += lineH - 2;
    }
    lineY += 8;

    // Divider
    ctx.beginPath();
    ctx.moveTo(panelX + 12, lineY);
    ctx.lineTo(panelX + panelW - 12, lineY);
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 1;
    ctx.stroke();
    lineY += 10;

    // Tyre info
    drawText(ctx, "TYRE", panelX + 15, lineY, {
        color: COLORS.F1_WHITE, size: 11, bold: true,
    });

    // Tyre icon on the right
    const tyreKey = compoundKey(st.cp);
    const tyreImg = images[tyreKey];
    if (tyreImg) {
        ctx.drawImage(tyreImg, panelX + panelW - 35, lineY - 3, 20, 20);
    }
    lineY += lineH;

    const compound = st.cp || "Unknown";
    const tyreLife = st.tl || 0;

    drawText(ctx, `${(compound || "---").substring(0, 3).toUpperCase()} - ${tyreLife} laps`, panelX + 15, lineY, {
        color: COLORS.F1_LIGHT_GRAY, size: 11,
    });
}
