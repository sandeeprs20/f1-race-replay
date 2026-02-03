/**
 * Telemetry graph components for qualifying UI.
 * Draws speed and throttle/brake graphs against lap distance.
 */

import { drawF1Panel, drawText, COLORS } from "../utils.js";

const GRID_LINES = 5;

/**
 * Draw a speed vs distance graph.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} x - Panel X position
 * @param {number} y - Panel Y position
 * @param {number} w - Panel width
 * @param {number} h - Panel height
 * @param {Object} telemetry - { distance: [], speed: [] }
 * @param {number} lapLength - Total lap length in meters
 */
export function drawSpeedGraph(ctx, x, y, w, h, telemetry, lapLength) {
    // Panel background
    drawF1Panel(ctx, x, y, w, h, { showRedAccent: true });

    // Title
    drawText(ctx, "SPEED", x + 12, y + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    // Graph area (with margins for labels)
    const graphX = x + 50;
    const graphY = y + 35;
    const graphW = w - 70;
    const graphH = h - 60;

    // Draw graph background
    ctx.fillStyle = "rgba(20, 20, 30, 0.8)";
    ctx.fillRect(graphX, graphY, graphW, graphH);

    // Draw grid lines
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 0.5;

    // Horizontal grid lines (speed)
    const maxSpeed = 350;
    const minSpeed = 0;
    for (let i = 0; i <= GRID_LINES; i++) {
        const lineY = graphY + (i / GRID_LINES) * graphH;
        ctx.beginPath();
        ctx.moveTo(graphX, lineY);
        ctx.lineTo(graphX + graphW, lineY);
        ctx.stroke();

        // Y-axis labels
        const speedVal = maxSpeed - (i / GRID_LINES) * (maxSpeed - minSpeed);
        drawText(ctx, Math.round(speedVal).toString(), graphX - 5, lineY, {
            color: COLORS.F1_LIGHT_GRAY, size: 9, align: "right", baseline: "middle",
        });
    }

    // Vertical grid lines (distance)
    const effectiveLapLength = lapLength || 5000;
    for (let i = 0; i <= 4; i++) {
        const lineX = graphX + (i / 4) * graphW;
        ctx.beginPath();
        ctx.moveTo(lineX, graphY);
        ctx.lineTo(lineX, graphY + graphH);
        ctx.stroke();

        // X-axis labels
        const distVal = (i / 4) * effectiveLapLength;
        let label = distVal >= 1000 ? `${(distVal / 1000).toFixed(1)}km` : `${Math.round(distVal)}m`;
        if (i === 0) label = "0";
        drawText(ctx, label, lineX, graphY + graphH + 5, {
            color: COLORS.F1_LIGHT_GRAY, size: 9, align: "center",
        });
    }

    // Draw speed line
    const distances = telemetry.distance || [];
    const speeds = telemetry.speed || [];

    if (distances.length > 1) {
        ctx.beginPath();
        ctx.strokeStyle = COLORS.F1_RED;
        ctx.lineWidth = 2;

        let firstPoint = true;
        for (let i = 0; i < distances.length; i++) {
            const distPct = distances[i] / effectiveLapLength;
            const speedPct = (speeds[i] - minSpeed) / (maxSpeed - minSpeed);

            const px = graphX + distPct * graphW;
            const py = graphY + (1 - speedPct) * graphH;

            if (px < graphX || px > graphX + graphW) continue;

            if (firstPoint) {
                ctx.moveTo(px, py);
                firstPoint = false;
            } else {
                ctx.lineTo(px, py);
            }
        }
        ctx.stroke();
    }

    // Y-axis label
    ctx.save();
    ctx.translate(x + 12, graphY + graphH / 2);
    ctx.rotate(-Math.PI / 2);
    drawText(ctx, "km/h", 0, 0, {
        color: COLORS.F1_LIGHT_GRAY, size: 10, align: "center", baseline: "middle",
    });
    ctx.restore();

    // X-axis label
    drawText(ctx, "Distance", graphX + graphW / 2, graphY + graphH + 20, {
        color: COLORS.F1_LIGHT_GRAY, size: 10, align: "center",
    });
}

/**
 * Draw a combined throttle/brake vs distance graph.
 * Throttle is green, brake is red, overlaid.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} x - Panel X position
 * @param {number} y - Panel Y position
 * @param {number} w - Panel width
 * @param {number} h - Panel height
 * @param {Object} telemetry - { distance: [], throttle: [], brake: [] }
 * @param {number} lapLength - Total lap length in meters
 */
export function drawThrottleBrakeGraph(ctx, x, y, w, h, telemetry, lapLength) {
    // Panel background
    drawF1Panel(ctx, x, y, w, h, { showRedAccent: false, bgColor: COLORS.PANEL_BG });

    // Title with legend
    drawText(ctx, "INPUTS", x + 12, y + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    // Legend
    ctx.fillStyle = COLORS.DRS_GREEN;
    ctx.fillRect(x + 70, y + 10, 10, 10);
    drawText(ctx, "THR", x + 85, y + 8, {
        color: COLORS.F1_LIGHT_GRAY, size: 10,
    });

    ctx.fillStyle = COLORS.F1_RED;
    ctx.fillRect(x + 120, y + 10, 10, 10);
    drawText(ctx, "BRK", x + 135, y + 8, {
        color: COLORS.F1_LIGHT_GRAY, size: 10,
    });

    // Graph area
    const graphX = x + 50;
    const graphY = y + 35;
    const graphW = w - 70;
    const graphH = h - 60;

    // Draw graph background
    ctx.fillStyle = "rgba(20, 20, 30, 0.8)";
    ctx.fillRect(graphX, graphY, graphW, graphH);

    // Draw grid lines
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 0.5;

    // Horizontal grid lines (0-100%)
    for (let i = 0; i <= GRID_LINES; i++) {
        const lineY = graphY + (i / GRID_LINES) * graphH;
        ctx.beginPath();
        ctx.moveTo(graphX, lineY);
        ctx.lineTo(graphX + graphW, lineY);
        ctx.stroke();

        // Y-axis labels
        const pctVal = 100 - (i / GRID_LINES) * 100;
        drawText(ctx, `${Math.round(pctVal)}%`, graphX - 5, lineY, {
            color: COLORS.F1_LIGHT_GRAY, size: 9, align: "right", baseline: "middle",
        });
    }

    // Vertical grid lines (distance)
    const effectiveLapLength = lapLength || 5000;
    for (let i = 0; i <= 4; i++) {
        const lineX = graphX + (i / 4) * graphW;
        ctx.beginPath();
        ctx.moveTo(lineX, graphY);
        ctx.lineTo(lineX, graphY + graphH);
        ctx.stroke();

        // X-axis labels
        const distVal = (i / 4) * effectiveLapLength;
        let label = distVal >= 1000 ? `${(distVal / 1000).toFixed(1)}km` : `${Math.round(distVal)}m`;
        if (i === 0) label = "0";
        drawText(ctx, label, lineX, graphY + graphH + 5, {
            color: COLORS.F1_LIGHT_GRAY, size: 9, align: "center",
        });
    }

    const distances = telemetry.distance || [];
    const throttles = telemetry.throttle || [];
    const brakes = telemetry.brake || [];

    // Draw throttle line (green)
    if (distances.length > 1) {
        ctx.beginPath();
        ctx.strokeStyle = COLORS.DRS_GREEN;
        ctx.lineWidth = 1.5;

        let firstPoint = true;
        for (let i = 0; i < distances.length; i++) {
            const distPct = distances[i] / effectiveLapLength;
            const throttlePct = Math.min(Math.max(throttles[i] || 0, 0), 100) / 100;

            const px = graphX + distPct * graphW;
            const py = graphY + (1 - throttlePct) * graphH;

            if (px < graphX || px > graphX + graphW) continue;

            if (firstPoint) {
                ctx.moveTo(px, py);
                firstPoint = false;
            } else {
                ctx.lineTo(px, py);
            }
        }
        ctx.stroke();
    }

    // Draw brake line (red)
    if (distances.length > 1) {
        ctx.beginPath();
        ctx.strokeStyle = COLORS.F1_RED;
        ctx.lineWidth = 1.5;

        let firstPoint = true;
        for (let i = 0; i < distances.length; i++) {
            const distPct = distances[i] / effectiveLapLength;
            const brakePct = Math.min(Math.max(brakes[i] || 0, 0), 100) / 100;

            const px = graphX + distPct * graphW;
            const py = graphY + (1 - brakePct) * graphH;

            if (px < graphX || px > graphX + graphW) continue;

            if (firstPoint) {
                ctx.moveTo(px, py);
                firstPoint = false;
            } else {
                ctx.lineTo(px, py);
            }
        }
        ctx.stroke();
    }

    // X-axis label
    drawText(ctx, "Distance", graphX + graphW / 2, graphY + graphH + 20, {
        color: COLORS.F1_LIGHT_GRAY, size: 10, align: "center",
    });
}
