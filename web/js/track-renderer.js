/**
 * Track rendering: multi-layer polyline, start/finish line, car dots.
 */

import { worldToScreen } from "./transform.js";
import { COLORS } from "./utils.js";

export class TrackRenderer {
    constructor() {
        this.screenPoints = [];
    }

    /**
     * Recompute screen-space track points from world coords.
     */
    computeScreenPoints(trackData, transform, screenH) {
        this.screenPoints = [];
        const { x, y } = trackData;
        for (let i = 0; i < x.length; i++) {
            const [sx, sy] = worldToScreen(x[i], y[i], transform, screenH);
            this.screenPoints.push([sx, sy]);
        }
    }

    /**
     * Draw the multi-layer track.
     */
    drawTrack(ctx) {
        const pts = this.screenPoints;
        if (pts.length < 2) return;

        // Layer 1: Shadow (12px)
        this._drawPolyline(ctx, pts, COLORS.TRACK_SHADOW, 12);
        // Layer 2: Surface (8px)
        this._drawPolyline(ctx, pts, COLORS.TRACK_SURFACE, 8);
        // Layer 3: Racing line (3px)
        this._drawPolyline(ctx, pts, COLORS.TRACK_RACING, 3);
        // Layer 4: Center line (1px)
        this._drawPolyline(ctx, pts, COLORS.TRACK_CENTER, 1);

        // Start/finish line
        this._drawStartFinishLine(ctx, pts);
    }

    /**
     * Draw car dots on track.
     */
    drawCars(ctx, frame, driverColors, selectedDriver, transform, screenH) {
        const drivers = frame.drivers;
        if (!drivers) return;

        for (const [drv, st] of Object.entries(drivers)) {
            if (st.x == null || st.y == null) continue;

            const [sx, sy] = worldToScreen(st.x, st.y, transform, screenH);
            const color = driverColors[drv] || "#969696";
            const isSelected = drv === selectedDriver;
            const r = isSelected ? 8 : 6;

            // Selected driver highlight ring
            if (isSelected) {
                ctx.beginPath();
                ctx.arc(sx, sy, 12, 0, Math.PI * 2);
                ctx.strokeStyle = COLORS.F1_WHITE;
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Car dot
            ctx.beginPath();
            ctx.arc(sx, sy, r, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();

            // White highlight
            ctx.beginPath();
            ctx.arc(sx - 1, sy - 1, 2, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(255,255,255,0.47)";
            ctx.fill();
        }
    }

    _drawPolyline(ctx, pts, color, width) {
        ctx.beginPath();
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (let i = 1; i < pts.length; i++) {
            ctx.lineTo(pts[i][0], pts[i][1]);
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.stroke();
    }

    _drawStartFinishLine(ctx, pts) {
        if (pts.length < 2) return;

        const [x0, y0] = pts[0];
        const [x1, y1] = pts[1];

        const dx = x1 - x0;
        const dy = y1 - y0;
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len < 0.001) return;

        // Perpendicular
        const px = -dy / len;
        const py = dx / len;
        const halfLen = 15;

        // White line
        ctx.beginPath();
        ctx.moveTo(x0 - px * halfLen, y0 - py * halfLen);
        ctx.lineTo(x0 + px * halfLen, y0 + py * halfLen);
        ctx.strokeStyle = COLORS.F1_WHITE;
        ctx.lineWidth = 4;
        ctx.stroke();

        // Red accent
        ctx.beginPath();
        ctx.moveTo(x0 - px * halfLen * 0.5, y0 - py * halfLen * 0.5);
        ctx.lineTo(x0 + px * halfLen * 0.5, y0 + py * halfLen * 0.5);
        ctx.strokeStyle = COLORS.F1_RED;
        ctx.lineWidth = 2;
        ctx.stroke();
    }
}
