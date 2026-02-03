/**
 * Controls reference panel (bottom left).
 */

import { drawText, COLORS } from "../utils.js";

const CONTROLS = [
    "CONTROLS",
    "[SPACE] Pause/Play",
    "[Arrows] Seek / Speed",
    "[R] Restart",
    "[H] Toggle UI",
    "[P] Progress Bar",
    "[L] Leaderboard",
    "[F] Fullscreen",
];

export function drawControls(ctx, W, H) {
    const x = 20;
    const y = H - 165;

    for (let i = 0; i < CONTROLS.length; i++) {
        drawText(ctx, CONTROLS[i], x, y + i * 16, {
            color: COLORS.F1_LIGHT_GRAY,
            size: 11,
            bold: i === 0,
        });
    }
}
