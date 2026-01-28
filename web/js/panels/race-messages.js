/**
 * Race director messages (blue flags, penalties, track limits).
 */

import { drawText, COLORS } from "../utils.js";

const MSG_COLORS = {
    blue_flag: "#0080FF",
    penalty: "#E10600",
    track_limit: "#FFD200",
};

export function drawRaceMessages(ctx, frame, W, H) {
    const messages = frame.raceMessages;
    if (!messages || messages.length === 0) return;

    const msgX = W / 2;
    const msgY = H - 55;

    const toShow = messages.slice(0, 2);
    for (let i = 0; i < toShow.length; i++) {
        const msg = toShow[i];
        let text = msg.message || "";
        if (text.length > 60) text = text.substring(0, 57) + "...";

        const color = MSG_COLORS[msg.type] || COLORS.INTERVAL_YELLOW;

        drawText(ctx, text, msgX, msgY - i * 18, {
            color, size: 10, align: "center",
        });
    }
}
