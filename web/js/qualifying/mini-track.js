/**
 * Mini track component for qualifying UI.
 * Shows a compact track view with all drivers as colored dots.
 */

import { drawF1Panel, drawText, COLORS } from "../utils.js";

// Export click rects for app.js
export let miniTrackClickRects = [];

/**
 * Build a transform for the mini track area.
 */
function buildMiniTrackTransform(bounds, areaW, areaH, margin = 15) {
    const { xmin, xmax, ymin, ymax } = bounds;

    const availW = areaW - 2 * margin;
    const availH = areaH - 2 * margin;

    const worldW = xmax - xmin;
    const worldH = ymax - ymin;

    const scale = Math.min(availW / worldW, availH / worldH);

    const worldCx = (xmin + xmax) / 2;
    const worldCy = (ymin + ymax) / 2;

    const screenCx = areaW / 2;
    const screenCy = areaH / 2;

    const tx = screenCx - (worldCx * scale);
    const ty = screenCy - (worldCy * scale);

    return { scale, tx, ty };
}

/**
 * Transform world coordinates to mini track coordinates.
 * Note: Y is flipped for canvas (Y=0 at top).
 */
function worldToMiniTrack(worldX, worldY, transform, offsetX, offsetY, areaH) {
    const sx = worldX * transform.scale + transform.tx + offsetX;
    const sy_arcade = worldY * transform.scale + transform.ty;
    const sy = offsetY + areaH - sy_arcade;
    return [sx, sy];
}

/**
 * Draw the mini track panel with all driver positions.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} panelX - Panel X position
 * @param {number} panelY - Panel Y position
 * @param {number} panelW - Panel width
 * @param {number} panelH - Panel height
 * @param {Object} frame - Current frame data
 * @param {Object} trackData - Track data with x, y, bounds
 * @param {Object} driverColors - Map of driver -> color
 * @param {string} selectedDriver - Currently selected driver
 */
export function drawMiniTrack(ctx, panelX, panelY, panelW, panelH, frame, trackData, driverColors, selectedDriver) {
    // Reset click rects
    miniTrackClickRects = [];

    // Panel background
    drawF1Panel(ctx, panelX, panelY, panelW, panelH, { showRedAccent: true });

    // Title
    drawText(ctx, "TRACK", panelX + 12, panelY + 8, {
        color: COLORS.F1_WHITE, size: 13, bold: true,
    });

    if (!trackData || !trackData.bounds) return;

    // Track drawing area (below title)
    const trackAreaX = panelX + 10;
    const trackAreaY = panelY + 30;
    const trackAreaW = panelW - 20;
    const trackAreaH = panelH - 60;

    // Build transform for this small area
    const transform = buildMiniTrackTransform(trackData.bounds, trackAreaW, trackAreaH);

    // Draw track outline
    const trackX = trackData.x || [];
    const trackY = trackData.y || [];

    if (trackX.length > 1) {
        // Track surface
        ctx.beginPath();
        const [startX, startY] = worldToMiniTrack(trackX[0], trackY[0], transform, trackAreaX, trackAreaY, trackAreaH);
        ctx.moveTo(startX, startY);

        for (let i = 1; i < trackX.length; i++) {
            const [px, py] = worldToMiniTrack(trackX[i], trackY[i], transform, trackAreaX, trackAreaY, trackAreaH);
            ctx.lineTo(px, py);
        }

        ctx.strokeStyle = COLORS.TRACK_SURFACE;
        ctx.lineWidth = 4;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.stroke();

        // Center line
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        for (let i = 1; i < trackX.length; i++) {
            const [px, py] = worldToMiniTrack(trackX[i], trackY[i], transform, trackAreaX, trackAreaY, trackAreaH);
            ctx.lineTo(px, py);
        }
        ctx.strokeStyle = COLORS.TRACK_CENTER;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Start/finish indicator
        const [sfX, sfY] = worldToMiniTrack(trackX[0], trackY[0], transform, trackAreaX, trackAreaY, trackAreaH);
        ctx.beginPath();
        ctx.arc(sfX, sfY, 4, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.F1_RED;
        ctx.fill();
    }

    // Draw driver dots
    if (frame && frame.drivers) {
        for (const [drv, st] of Object.entries(frame.drivers)) {
            if (st.x == null || st.y == null) continue;

            const [sx, sy] = worldToMiniTrack(st.x, st.y, transform, trackAreaX, trackAreaY, trackAreaH);
            const color = driverColors[drv] || "#969696";
            const isSelected = drv === selectedDriver;
            const r = isSelected ? 5 : 3;

            // Selected driver highlight ring
            if (isSelected) {
                ctx.beginPath();
                ctx.arc(sx, sy, 8, 0, Math.PI * 2);
                ctx.strokeStyle = COLORS.F1_WHITE;
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Driver dot
            ctx.beginPath();
            ctx.arc(sx, sy, r, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();

            // Store click rect for this driver
            miniTrackClickRects.push({
                x: sx - 10,
                y: sy - 10,
                w: 20,
                h: 20,
                driver: drv,
            });
        }
    }

    // Selected driver label at bottom of panel
    if (selectedDriver) {
        const drvColor = driverColors[selectedDriver] || "#969696";
        drawText(ctx, `Selected: ${selectedDriver}`, panelX + 12, panelY + panelH - 18, {
            color: drvColor, size: 11, bold: true,
        });
    }
}
