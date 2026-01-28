/**
 * Progress bar with pixel car playhead (bottom center).
 */

import { COLORS } from "../utils.js";

const BAR_W_RATIO = 0.5;  // 50% of screen width
const BAR_H = 8;
const CAR_SIZE = 40;

// Export for click detection
export let progressBarRect = null;

export function drawProgressBar(ctx, state, images, W, H) {
    const barW = Math.max(400, W * BAR_W_RATIO);
    const barX = (W - barW) / 2;
    const barY = H - 35;

    // Background
    ctx.fillStyle = COLORS.F1_DARK_GRAY;
    ctx.fillRect(barX, barY, barW, BAR_H);

    // Progress
    const progress = state.frameIdx / Math.max(state.totalFrames - 1, 1);
    const fillW = progress * barW;

    if (fillW > 0) {
        ctx.fillStyle = COLORS.F1_RED;
        ctx.fillRect(barX, barY, fillW, BAR_H);
    }

    // Border
    ctx.strokeStyle = COLORS.F1_GRAY;
    ctx.lineWidth = 1;
    ctx.strokeRect(barX, barY, barW, BAR_H);

    // Pixel car playhead
    const carImg = images["pixel_car"];
    if (carImg) {
        const aspect = carImg.width / carImg.height;
        const carH = CAR_SIZE;
        const carW = carH * aspect;
        const carX = barX + fillW - carW / 2;
        const carY = barY - carH - 2;
        ctx.drawImage(carImg, carX, carY, carW, carH);
    }

    // Store rect for click detection (include car area)
    progressBarRect = {
        x: barX,
        y: barY - CAR_SIZE - 10,
        w: barW,
        h: BAR_H + CAR_SIZE + 20,
        barX, barW,
    };
}
