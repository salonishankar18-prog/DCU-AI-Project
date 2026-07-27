"""
align.py — work out how SVG coordinates map onto a given PNG.

The PNGs in a plan folder are renders of the same SVG at different sizes
(F1_original.png is 1624x656, F1_scaled.png is 3153x1273). Neither matches the
viewBox exactly, because each render is padded. So we can't assume a scale
factor — we fit one.

Method: the external walls are solid black and always drawn, so their extent is
a reliable landmark in both the vector and the raster. We match the horizontal
extent of the wall geometry to the horizontal extent of the heavy black ink in
the image, and solve for a single uniform scale factor.

Horizontal is used because it is the long axis here and is not disturbed by
porches or balconies that protrude vertically and are sometimes not rendered.
"""

import numpy as np
from PIL import Image

# A pixel is "ink" below this grey level. Walls are near 0; the cyan guide lines
# in these renders are much lighter and are correctly excluded.
INK_LEVEL = 100

# A row or column must contain at least this many ink pixels to count as
# structural. Filters out thin furniture strokes and stray annotation marks.
MIN_INK_RUN = 20


def png_ink_bbox(png_path, ink_level=INK_LEVEL, min_run=MIN_INK_RUN):
    """Bounding box of the heavy black linework in the image.

    Returns (x0, y0, x1, y1) in pixels.
    """
    grey = np.array(Image.open(png_path).convert("L"))
    ink = grey < ink_level
    cols = np.where(ink.sum(axis=0) >= min_run)[0]
    rows = np.where(ink.sum(axis=1) >= min_run)[0]
    if len(cols) == 0 or len(rows) == 0:
        raise ValueError(f"no structural ink found in {png_path}")
    return int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1])


def fit_transform(plan, png_path):
    """Solve for the scale and offset that map SVG units onto PNG pixels.

    Returns a dict with:
        scale     — multiply an SVG coordinate by this to get pixels
        off_x/off_y — then add these
        residual_y — how far off the vertical prediction is, as a fraction.
                     A small value means the fit is trustworthy.
    """
    px0, py0, px1, py1 = png_ink_bbox(png_path)
    wx0, wy0, wx1, wy1 = plan.wall_bbox_svg

    svg_w = wx1 - wx0
    png_w = px1 - px0
    if svg_w <= 0 or png_w <= 0:
        raise ValueError("degenerate bounding box")

    # One uniform scale, solved on the horizontal axis.
    scale = png_w / svg_w

    # Offsets place the SVG wall bbox onto the measured ink bbox.
    off_x = px0 - wx0 * scale
    off_y = py0 - wy0 * scale

    # Sanity check: does the same scale predict the vertical extent?
    # It won't match exactly, because protruding porches add ink below the walls,
    # so we only require the prediction to not *exceed* what's in the image.
    predicted_h = (wy1 - wy0) * scale
    actual_h = py1 - py0
    residual_y = (predicted_h - actual_h) / max(actual_h, 1)

    return {
        "scale": scale,
        "off_x": off_x,
        "off_y": off_y,
        "png_ink_bbox": (px0, py0, px1, py1),
        "residual_y": round(residual_y, 4),
        "trustworthy": residual_y < 0.02,   # walls must not extend past the ink
    }


def to_px(xy, tf):
    """Convert one (x, y) SVG point to pixel coordinates."""
    return (xy[0] * tf["scale"] + tf["off_x"], xy[1] * tf["scale"] + tf["off_y"])
