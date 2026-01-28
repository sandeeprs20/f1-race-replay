/**
 * Drawing utilities: rounded rects, F1 panels, color helpers, text helpers.
 */

// F1 TV Broadcast color palette
export const COLORS = {
    F1_RED: "#E10600",
    F1_BLACK: "#15151E",
    F1_DARK_GRAY: "#26263E",
    F1_GRAY: "#44444E",
    F1_WHITE: "#FFFFFF",
    F1_LIGHT_GRAY: "#B4B4B9",

    P1_GOLD: "#FFD700",
    P2_SILVER: "#C0C0C8",
    P3_BRONZE: "#CD7F32",

    DRS_GREEN: "#00D250",
    FASTEST_PURPLE: "#AA00FF",
    INTERVAL_YELLOW: "#FFD200",

    PANEL_BG: "rgba(28,28,38,0.94)",
    PANEL_BG_ALT: "rgba(38,38,50,0.94)",

    // Track layers
    TRACK_SHADOW: "#1E1E23",
    TRACK_SURFACE: "#37373C",
    TRACK_RACING: "#646469",
    TRACK_CENTER: "#8C8C91",
};

/**
 * Draw a filled rounded rectangle.
 */
export function drawRoundedRect(ctx, x, y, w, h, radius, fillStyle) {
    radius = Math.min(radius, w / 2, h / 2);
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.fillStyle = fillStyle;
    ctx.fill();
}

/**
 * Draw a rounded rectangle outline.
 */
export function drawRoundedRectOutline(ctx, x, y, w, h, radius, strokeStyle, lineWidth = 1) {
    radius = Math.min(radius, w / 2, h / 2);
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
}

/**
 * Draw an F1 broadcast-style panel with semi-transparent background and red accent.
 */
export function drawF1Panel(ctx, x, y, w, h, opts = {}) {
    const { radius = 4, showRedAccent = true, bgColor = COLORS.PANEL_BG } = opts;

    drawRoundedRect(ctx, x, y, w, h, radius, bgColor);

    if (showRedAccent) {
        // Red accent line at the top
        ctx.fillStyle = COLORS.F1_RED;
        ctx.fillRect(x, y, w, 3);
    }
}

/**
 * Convert hex color to rgba string with given alpha.
 */
export function hexToRgba(hex, alpha = 1) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

/**
 * Draw text with common options.
 */
export function drawText(ctx, text, x, y, opts = {}) {
    const {
        color = COLORS.F1_WHITE,
        size = 13,
        bold = false,
        align = "left",
        baseline = "top",
        font = '"Segoe UI", Arial, sans-serif',
    } = opts;

    ctx.fillStyle = color;
    ctx.font = `${bold ? "bold " : ""}${size}px ${font}`;
    ctx.textAlign = align;
    ctx.textBaseline = baseline;
    ctx.fillText(text, x, y);
}

/**
 * Format seconds as M:SS.mmm
 */
export function formatLapTime(seconds) {
    if (seconds == null || !isFinite(seconds)) return "---";
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toFixed(3).padStart(6, "0")}`;
}

/**
 * Normalize compound name to tyre image key.
 */
export function compoundKey(compound) {
    if (!compound) return "unknown";
    const c = compound.trim().toUpperCase();
    if (c.startsWith("SOFT")) return "soft";
    if (c.startsWith("MED")) return "medium";
    if (c.startsWith("HARD")) return "hard";
    if (c.startsWith("INTER")) return "intermediate";
    if (c.startsWith("WET")) return "wet";
    return "unknown";
}

/**
 * Check if DRS is active.
 */
export function drsIsActive(drsVal) {
    return (drsVal | 0) >= 10;
}
