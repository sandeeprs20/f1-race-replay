/**
 * Fastest lap purple banner (shown for 5 seconds when new fastest lap is set).
 */

import { drawRoundedRect, drawText, COLORS, formatLapTime } from "../utils.js";

export function drawFastestLap(ctx, frame, W, H) {
    const fl = frame.fastestLap;
    if (!fl || !fl.isNew) return;
    if (!fl.driver || !fl.time) return;

    const timeStr = formatLapTime(fl.time);

    const bannerW = 320;
    const bannerH = 40;
    const bannerX = W / 2 - bannerW / 2;
    const bannerY = 95;

    drawRoundedRect(ctx, bannerX, bannerY, bannerW, bannerH, 4, COLORS.FASTEST_PURPLE);

    drawText(ctx, `FASTEST LAP - ${fl.driver} - ${timeStr}`, W / 2, bannerY + bannerH / 2, {
        color: COLORS.F1_WHITE, size: 13, bold: true, align: "center", baseline: "middle",
    });
}
