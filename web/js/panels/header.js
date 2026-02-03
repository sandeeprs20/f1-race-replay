/**
 * Header panel: GP name, session type, lap counter, race time.
 */

import { drawText, COLORS } from "../utils.js";

export function drawHeader(ctx, frame, state, manifest, W, H) {
    // GP name (top center, white)
    drawText(ctx, manifest.eventName, W / 2, 12, {
        color: COLORS.F1_WHITE, size: 18, bold: true, align: "center",
    });

    // Session type (red, below GP name)
    drawText(ctx, manifest.sessionName, W / 2, 36, {
        color: COLORS.F1_RED, size: 14, bold: true, align: "center",
    });

    // Lap counter (top left)
    const ordered = getOrderedDrivers(frame);
    const leaderLap = ordered.length > 0 ? (ordered[0][1].l || 1) : 1;
    const totalLaps = manifest.totalLaps || Math.max(...Object.values(frame.drivers).map(d => d.l || 1));
    drawText(ctx, `LAP ${leaderLap}/${totalLaps}`, 20, 12, {
        color: COLORS.F1_WHITE, size: 16, bold: true,
    });

    // Race time + speed
    const t = frame.t || 0;
    const minutes = Math.floor(t / 60);
    const seconds = Math.floor(t % 60);
    const speed = state.speed;
    drawText(ctx, `Race Time: ${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")} (x${speed})`, 20, 34, {
        color: COLORS.F1_LIGHT_GRAY, size: 13,
    });
}

export function getOrderedDrivers(frame) {
    if (!frame.drivers) return [];
    return Object.entries(frame.drivers).sort((a, b) => (a[1].p || 99) - (b[1].p || 99));
}
