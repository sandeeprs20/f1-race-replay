/**
 * Header panel for qualifying sessions.
 * Shows GP name, session type, session time (instead of lap counter).
 */

import { drawText, COLORS } from "../utils.js";

export function drawQualifyingHeader(ctx, frame, state, manifest, W, H) {
    // GP name (top center, white)
    drawText(ctx, manifest.eventName, W / 2, 12, {
        color: COLORS.F1_WHITE, size: 18, bold: true, align: "center",
    });

    // Session type (red, below GP name)
    drawText(ctx, manifest.sessionName, W / 2, 36, {
        color: COLORS.F1_RED, size: 14, bold: true, align: "center",
    });

    // Session time (top left) - instead of lap counter
    const t = frame.t || 0;
    const minutes = Math.floor(t / 60);
    const seconds = Math.floor(t % 60);
    drawText(ctx, `Session Time: ${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`, 20, 12, {
        color: COLORS.F1_WHITE, size: 16, bold: true,
    });

    // Playback speed
    const speed = state.speed;
    drawText(ctx, `Playback: x${speed}`, 20, 34, {
        color: COLORS.F1_LIGHT_GRAY, size: 13,
    });
}
