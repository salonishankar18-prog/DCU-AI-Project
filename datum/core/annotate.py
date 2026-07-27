"""
annotate.py — burn the extracted dimensions onto a copy of the PNG.

Drafting conventions are followed deliberately: overall dimensions sit outside
the building on tick-terminated dimension lines with extension lines running back
to what they measure; room dimensions sit inside each room.

Colour rule, matching the web UI: orange marks a real-world measurement and
nothing else. The original drawing stays untouched underneath.
"""

import os
from PIL import Image, ImageDraw, ImageFont

from .align import fit_transform, to_px

DIM = (224, 83, 43)          # measurement ink
INK = (20, 32, 42)           # structural ink
WHITE = (255, 255, 255)

# Look here for fonts, in order. Bundle a copy in the repo so Colab, which has a
# different font set, does not silently fall back to an unreadable bitmap face.
FONT_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "assets", "DejaVuSans.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(size):
    """Load a scalable font, or fail loudly rather than degrade quietly."""
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise RuntimeError("no TrueType font found — bundle DejaVuSans.ttf in assets/")


def _text_with_backing(draw, xy, text, font, fill, anchor="mm", pad=3):
    """Draw text on a white pad so it stays readable over black linework."""
    x, y = xy
    l, t, r, b = draw.textbbox((x, y), text, font=font, anchor=anchor)
    draw.rectangle([l - pad, t - pad, r + pad, b + pad], fill=WHITE)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def _dim_line_h(draw, x0, x1, y, label, font, ext_to=None):
    """Horizontal dimension line: ticks at both ends, label centred, optional
    extension lines running back to the feature being measured."""
    draw.line([(x0, y), (x1, y)], fill=DIM, width=2)
    for x in (x0, x1):
        draw.line([(x, y - 7), (x, y + 7)], fill=DIM, width=2)      # end tick
        if ext_to is not None:
            draw.line([(x, y), (x, ext_to)], fill=DIM, width=1)     # extension
    _text_with_backing(draw, ((x0 + x1) / 2, y), label, font, DIM)


def _dim_line_v(draw, y0, y1, x, label, font, ext_to=None):
    """Vertical dimension line. Text is drawn upright rather than rotated so it
    stays legible at small render sizes."""
    draw.line([(x, y0), (x, y1)], fill=DIM, width=2)
    for y in (y0, y1):
        draw.line([(x - 7, y), (x + 7, y)], fill=DIM, width=2)
        if ext_to is not None:
            draw.line([(x, y), (ext_to, y)], fill=DIM, width=1)
    _text_with_backing(draw, (x, (y0 + y1) / 2), label, font, DIM)


def annotate(plan, png_path, out_path, units="m",
             room_labels=True, style="dimension_lines"):
    """Write an annotated copy of one PNG.

    plan        — a Plan from svg_parse.parse_svg
    units       — "m", "ft", or "both"
    room_labels — draw per-room size and area
    style       — "dimension_lines" (drafting convention) or "corner_label"

    Returns a small report dict for the manifest.
    """
    tf = fit_transform(plan, png_path)
    src = Image.open(png_path).convert("RGB")

    # Add white margin so dimension lines have somewhere to live. The renders are
    # tight to the drawing on at least one side, so we cannot draw outside without it.
    margin = max(70, int(src.width * 0.055))
    canvas = Image.new("RGB", (src.width + 2 * margin, src.height + 2 * margin), WHITE)
    canvas.paste(src, (margin, margin))
    draw = ImageDraw.Draw(canvas)

    # Everything shifts by the margin we just added.
    tf_m = dict(tf, off_x=tf["off_x"] + margin, off_y=tf["off_y"] + margin)

    # Type sizes scale with the image so a 1624px and a 3153px render both read.
    k = canvas.width / 1700.0
    f_big = _font(max(15, int(21 * k)))
    f_room = _font(max(11, int(15 * k)))
    f_small = _font(max(9, int(12 * k)))

    def fmt(w, d):
        """Format a width x depth pair in the requested units."""
        if units == "ft":
            return f"{w * 3.28084:.1f}' x {d * 3.28084:.1f}'"
        if units == "both":
            return f"{w:.2f} x {d:.2f} m  ({w * 3.28084:.1f}' x {d * 3.28084:.1f}')"
        return f"{w:.2f} x {d:.2f} m"

    wx0, wy0, wx1, wy1 = plan.wall_bbox_svg
    (bx0, by0) = to_px((wx0, wy0), tf_m)
    (bx1, by1) = to_px((wx1, wy1), tf_m)

    if style == "dimension_lines":
        # Overall width, above the building.
        _dim_line_h(draw, bx0, bx1, by0 - margin * 0.55,
                    f"{plan.overall_width_m:.2f} m", f_big, ext_to=by0)
        # Overall depth, to the left.
        _dim_line_v(draw, by0, by1, bx0 - margin * 0.55,
                    f"{plan.overall_depth_m:.2f} m", f_big, ext_to=bx0)
    else:
        lines = [
            f"{plan.plan_id}",
            f"Overall  {fmt(plan.overall_width_m, plan.overall_depth_m)}",
            f"Internal floor area  {plan.internal_area_m2:.1f} m2",
            f"Scale  {plan.px_per_m:.1f} px/m",
        ]
        y = margin * 0.4
        for i, line in enumerate(lines):
            _text_with_backing(draw, (margin * 0.4, y), line,
                               f_big if i == 0 else f_small, DIM, anchor="lt")
            y += (f_big if i == 0 else f_small).size * 1.5

    # Per-room dimensions, placed under the room code already printed on the plan.
    # Small rooms get progressively smaller type, then a single compact line, so a
    # 1.0 m toilet does not end up with text spilling across its neighbours.
    if room_labels:
        for room in plan.rooms:
            if room.outdoor:
                continue

            cx, cy = to_px(room.centroid_svg, tf_m)
            rx0, ry0, rx1, ry1 = room.polygon_svg[0][0], 0, 0, 0
            xs = [p[0] for p in room.polygon_svg]
            ys = [p[1] for p in room.polygon_svg]
            room_w_px = (max(xs) - min(xs)) * tf_m["scale"]

            size_txt = fmt(room.width_m, room.depth_m)
            area_txt = f"{room.area_m2:.1f} m2"

            # Step the font down until the size text fits inside the room.
            fitted = None
            for size in range(f_room.size, max(7, int(f_room.size * 0.55)) - 1, -1):
                cand = _font(size)
                if draw.textlength(size_txt, font=cand) <= room_w_px * 0.92:
                    fitted = cand
                    break

            if fitted is None:
                # Still too tight: one compact line, area only.
                tiny = _font(max(7, int(f_room.size * 0.55)))
                _text_with_backing(draw, (cx, cy + tiny.size * 1.4),
                                   area_txt, tiny, DIM, pad=2)
                continue

            small = _font(max(7, int(fitted.size * 0.82)))
            top = cy + fitted.size * 1.15
            _text_with_backing(draw, (cx, top), size_txt, fitted, DIM, pad=2)
            _text_with_backing(draw, (cx, top + small.size * 1.45),
                               area_txt, small, DIM, pad=2)

    # Footer stamp so an exported image is self-describing.
    _text_with_backing(
        draw, (margin * 0.4, canvas.height - margin * 0.4),
        f"{plan.plan_id} · {os.path.basename(png_path)} · scale {plan.px_per_m:.1f} px/m "
        f"· internal floor area {plan.internal_area_m2:.1f} m2 · dimensions read from model.svg",
        f_small, INK, anchor="lb")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path)

    return {
        "source_png": os.path.basename(png_path),
        "output_png": os.path.basename(out_path),
        "png_size": list(src.size),
        "fit_scale": round(tf["scale"], 5),
        "fit_trustworthy": tf["trustworthy"],
    }
