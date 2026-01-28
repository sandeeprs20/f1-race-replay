/**
 * Track status indicator (YELLOW FLAG, RED FLAG, SAFETY CAR, VSC).
 */

import { drawRoundedRect, drawText, COLORS } from "../utils.js";

const STATUS_MAP = {
    GREEN: { color: "#00C800", text: "GREEN FLAG" },
    YELLOW: { color: "#FFD200", text: "YELLOW FLAG" },
    RED: { color: "#FF0000", text: "RED FLAG" },
    SC: { color: "#FFD200", text: "SAFETY CAR" },
    VSC: { color: "#FFD200", text: "VSC" },
};

export function drawTrackStatus(ctx, frame, W, H) {
    const status = frame.trackStatus || "GREEN";
    if (status === "GREEN") return;

    const info = STATUS_MAP[status] || STATUS_MAP.GREEN;

    const badgeW = 120;
    const badgeH = 28;
    const badgeX = W / 2 - badgeW / 2;
    const badgeY = 60;

    drawRoundedRect(ctx, badgeX, badgeY, badgeW, badgeH, 4, info.color);

    const textColor = status === "YELLOW" ? COLORS.F1_BLACK : COLORS.F1_WHITE;
    drawText(ctx, info.text, W / 2, badgeY + badgeH / 2, {
        color: textColor, size: 12, bold: true, align: "center", baseline: "middle",
    });
}
