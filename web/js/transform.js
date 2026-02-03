/**
 * World-to-screen coordinate transforms.
 *
 * Key difference from Python/Arcade version:
 * Canvas Y=0 is at the TOP, while Arcade Y=0 is at the BOTTOM.
 * We flip Y in worldToScreen.
 */

export function buildWorldToScreenTransform(bounds, screenW, screenH, margin = 60) {
    const { xmin, xmax, ymin, ymax } = bounds;

    const availW = screenW - 2 * margin;
    const availH = screenH - 2 * margin;

    const worldW = xmax - xmin;
    const worldH = ymax - ymin;

    const scale = Math.min(availW / worldW, availH / worldH);

    const worldCx = (xmin + xmax) / 2;
    const worldCy = (ymin + ymax) / 2;

    const screenCx = screenW / 2;
    const screenCy = screenH / 2;

    const tx = screenCx - (worldCx * scale);
    const ty = screenCy - (worldCy * scale);

    return { scale, tx, ty };
}

/**
 * Transform a world coordinate to screen coordinate.
 * Flips Y axis for canvas (Y=0 at top).
 */
export function worldToScreen(x, y, transform, screenH) {
    const sx = x * transform.scale + transform.tx;
    // Arcade: sy = y * scale + ty (Y up)
    // Canvas: we need to flip Y. sy_canvas = screenH - sy_arcade
    const sy_arcade = y * transform.scale + transform.ty;
    const sy = screenH - sy_arcade;
    return [sx, sy];
}
