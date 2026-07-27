"""
rules.py — deterministic geometry for Part 2.

Python decides the numbers. Nothing in this file knows what TGD M requires; it
only measures. Compliance is judged in agent.py, against retrieved clause text.

Three measurements, all from the SVG's own geometry:

1. Door clear widths.
   The plan encodes each opening as a <g class="Threshold"> rectangle inside a
   <g class="Door ..."> group. The build brief assumed the wall polygon is
   notched at the threshold and the clear width is that notch. It is not — in
   this dataset the wall layer runs unbroken straight through every doorway
   (verified: wall coverage 1.00 under all 13 thresholds of the sample plan).
   The threshold rectangle *is* the opening: its short side is the wall
   thickness, its long side is the span of the gap in the wall face. So we
   measure the threshold's long side, and cross-check that the short side
   matches the thickness of the wall it sits in. Every door carries the method
   used, so the number is never mistaken for something it isn't.

   This is a *structural* clear opening. TGD M Diagram 10 measures effective
   clear width from door stop to the open leaf, which is a little narrower once
   frame and leaf are allowed for. We do not apply a deduction — that would be
   inventing a number — we report what the drawing gives and label it.

2. Corridor minimum width.
   The narrowest cross-section of a circulation space's polygon, measured
   perpendicular to its long axis.

3. Wheelchair turning circle.
   The largest circle that fits inside a room without crossing any
   FixedFurniture. Solved by a coarse-to-fine search on the distance transform
   of the free area.
"""

import math
import re

import numpy as np
import shapely
from lxml import etree
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from core.svg_parse import parse_svg

SVG_NS = "{http://www.w3.org/2000/svg}"

# Space classes that are circulation rather than accommodation.
CIRCULATION_CLASSES = ("Entry", "Lobby", "Hall", "DraughtLobby", "Corridor", "Landing")
CIRCULATION_CODES = ("ET", "AULA", "HALLI", "KAYTAVA", "PORRAS")

# An "Undefined" space this elongated, and this narrow, is a passage in all but
# name. Flagged separately so a judgement never rests on the guess silently.
PROBABLE_CORRIDOR_ASPECT = 1.8
PROBABLE_CORRIDOR_MAX_WIDTH_M = 2.5

# Plausibility floor for the heuristic above — not a TGD M threshold. CubiCasa
# plans contain "Undefined" slivers that are wall recesses and service voids:
# plan 1007 has one 0.12 m x 3.58 m that the aspect test happily called a
# corridor with a 120 mm clear width. Nothing a person walks through is narrower
# than this or smaller than this, so anything below it is not a space at all.
CORRIDOR_MIN_PLAUSIBLE_WIDTH_M = 0.6
CORRIDOR_MIN_PLAUSIBLE_AREA_M2 = 1.0


# ---------------------------------------------------------------------------
# SVG geometry the dimension parser does not need
# ---------------------------------------------------------------------------

def _class_chain(el):
    parts, node = [], el
    while node is not None:
        parts.append(node.get("class") or "")
        node = node.getparent()
    return " ".join(parts)


def _points(poly_el):
    out = []
    for token in (poly_el.get("points") or "").split():
        if "," not in token:
            continue
        try:
            x, y = token.split(",")[:2]
            out.append((float(x), float(y)))
        except ValueError:
            continue
    return out


# --- SVG transforms --------------------------------------------------------
# Walls and rooms are drawn in global coordinates, but every FixedFurniture
# group is a reusable symbol: its BoundaryPolygon is in local units starting at
# the origin, positioned by a transform on the group. Ignore the transform and
# every fitting collapses onto (0,0), which is exactly what a first pass here
# did — furniture subtracted nothing. So compose the chain.

_TRANSFORM = re.compile(r"(matrix|translate|scale|rotate)\s*\(([^)]*)\)")

_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)      # (a, b, c, d, e, f)


def _mat_mul(m, n):
    """Compose two SVG matrices: apply n, then m."""
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _parse_transform(text):
    m = _IDENTITY
    if not text:
        return m
    for kind, args in _TRANSFORM.findall(text):
        vals = [float(v) for v in re.split(r"[\s,]+", args.strip()) if v]
        if kind == "matrix" and len(vals) == 6:
            t = tuple(vals)
        elif kind == "translate":
            tx = vals[0] if vals else 0.0
            ty = vals[1] if len(vals) > 1 else 0.0
            t = (1, 0, 0, 1, tx, ty)
        elif kind == "scale":
            sx = vals[0] if vals else 1.0
            sy = vals[1] if len(vals) > 1 else sx
            t = (sx, 0, 0, sy, 0, 0)
        elif kind == "rotate" and vals:
            ang = math.radians(vals[0])
            cos, sin = math.cos(ang), math.sin(ang)
            t = (cos, sin, -sin, cos, 0, 0)
            if len(vals) == 3:                      # rotate about a point
                cx, cy = vals[1], vals[2]
                t = _mat_mul(_mat_mul((1, 0, 0, 1, cx, cy), t), (1, 0, 0, 1, -cx, -cy))
        else:
            continue
        m = _mat_mul(m, t)
    return m


def _ctm(el):
    """Accumulated transform from the root down to this element."""
    chain, node = [], el
    while node is not None:
        chain.append(_parse_transform(node.get("transform")))
        node = node.getparent()
    m = _IDENTITY
    for t in reversed(chain):                       # root first
        m = _mat_mul(m, t)
    return m


def _apply(m, pts):
    a, b, c, d, e, f = m
    return [(a * x + c * y + e, b * x + d * y + f) for x, y in pts]


def _rect_points(el):
    """A <rect> as four corner points, in the rect's own coordinate space."""
    try:
        x = float(el.get("x", 0)); y = float(el.get("y", 0))
        w = float(el.get("width", 0)); h = float(el.get("height", 0))
    except ValueError:
        return []
    if w <= 0 or h <= 0:
        return []
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def _polygon(pts):
    if len(pts) < 3:
        return None
    g = Polygon(pts)
    if not g.is_valid:
        g = g.buffer(0)
    return g if (not g.is_empty and g.area > 0) else None


def _furniture_footprints(root):
    """One polygon per fixed fitting, in global coordinates.

    Each FixedFurniture group carries a BoundaryPolygon child that is the plan
    footprint of the fitting. Groups without one (a few are drawn as rects) fall
    back to their own geometry.
    """
    out = []
    for grp in root.iter():
        cls = grp.get("class") or ""
        if not cls.startswith("FixedFurniture") or cls == "FixedFurnitureSet":
            continue

        pts_local, host = [], None
        for child in grp.iter():
            if (child.get("class") or "") == "BoundaryPolygon":
                poly = child.find(SVG_NS + "polygon")
                if poly is not None:
                    pts_local, host = _points(poly), poly
                    break
        if not pts_local:
            for child in grp.iter():
                tag = child.tag.replace(SVG_NS, "")
                if tag == "polygon":
                    pts_local, host = _points(child), child
                elif tag == "rect":
                    pts_local, host = _rect_points(child), child
                if pts_local:
                    break
        if not pts_local or host is None:
            continue

        g = _polygon(_apply(_ctm(host), pts_local))
        if g is not None:
            out.append(g)
    return out


def _collect(svg_path):
    """Walls, door thresholds and fixed furniture, as shapely geometry in SVG units."""
    root = etree.parse(str(svg_path)).getroot()

    walls, thresholds = [], []

    for poly in root.iter(SVG_NS + "polygon"):
        chain = _class_chain(poly)
        if "Wall" not in chain:
            continue
        g = _polygon(_apply(_ctm(poly), _points(poly)))
        if g is not None:
            walls.append(g)

    furniture = _furniture_footprints(root)

    for grp in root.iter():
        if (grp.get("class") or "") != "Threshold":
            continue
        parent_chain = _class_chain(grp.getparent()) if grp.getparent() is not None else ""
        if "Door" not in parent_chain:
            continue                     # thresholds also appear under windows
        poly = grp.find(SVG_NS + "polygon")
        if poly is None:
            continue
        pts = _apply(_ctm(poly), _points(poly))
        if len(pts) >= 3:
            thresholds.append(pts)

    return {
        "walls": unary_union(walls) if walls else None,
        "wall_parts": walls,
        "furniture": unary_union(furniture) if furniture else None,
        "thresholds": thresholds,
    }


# ---------------------------------------------------------------------------
# 1. door clear widths
# ---------------------------------------------------------------------------

def _rect_axes(pts):
    """Long-axis span, short-axis span, centre and unit vectors of a threshold.

    Thresholds are drawn axis-aligned in this dataset, but the minimum rotated
    rectangle is used anyway so a rotated plan does not silently measure the
    diagonal.
    """
    g = Polygon(pts)
    rect = g.minimum_rotated_rectangle
    coords = list(rect.exterior.coords)[:4]
    edges = []
    for i in range(4):
        (x0, y0), (x1, y1) = coords[i], coords[(i + 1) % 4]
        edges.append((math.hypot(x1 - x0, y1 - y0), (x1 - x0, y1 - y0)))
    edges.sort(key=lambda e: e[0])
    short_len, short_vec = edges[0]
    long_len, long_vec = edges[-1]

    def unit(v):
        n = math.hypot(*v) or 1.0
        return (v[0] / n, v[1] / n)

    c = g.centroid
    return {
        "long": long_len, "short": short_len,
        "u_long": unit(long_vec), "u_short": unit(short_vec),
        "cx": c.x, "cy": c.y,
    }


def door_openings(plan, geo, px_per_m):
    """One record per door threshold: the clear span of the opening in mm."""
    walls = geo["walls"]
    rooms = [(r, Polygon(r.polygon_svg).buffer(0)) for r in plan.rooms
             if len(r.polygon_svg) >= 3]

    out = []
    for i, pts in enumerate(geo["thresholds"]):
        ax = _rect_axes(pts)
        cx, cy = ax["cx"], ax["cy"]
        ux, uy = ax["u_short"]                      # wall normal

        clear_mm = round(ax["long"] / px_per_m * 1000)
        thickness_mm = round(ax["short"] / px_per_m * 1000)

        # Which spaces sit either side of the opening?
        between, side_names = [], []
        for sign in (+1, -1):
            step = ax["short"] / 2 + max(6.0, ax["short"] * 0.6)
            probe = Point(cx + ux * step * sign, cy + uy * step * sign)
            hit = None
            for room, poly in rooms:
                if poly.contains(probe):
                    hit = room
                    break
            side_names.append(hit.name if hit else "Outside")
            between.append(hit.code if hit else "OUT")

        # Cross-check: the short side really is the wall the door sits in.
        in_wall = bool(walls is not None and walls.contains(Point(cx, cy)))

        # An external door has open air on one side.
        external = "OUT" in between

        out.append({
            "id": f"d{i + 1}",
            "between": side_names,
            "between_codes": between,
            "clear_width_mm": clear_mm,
            "wall_thickness_mm": thickness_mm,
            "external": external,
            "centre_svg": [round(cx, 2), round(cy, 2)],
            "method": "threshold_span" + ("" if in_wall else "_threshold_outside_wall"),
            "measures": "structural clear opening between wall faces, "
                        "not effective clear width past an open leaf",
        })
    return out


# ---------------------------------------------------------------------------
# 2. largest inscribed circle, clear of fixed furniture
# ---------------------------------------------------------------------------

def _largest_free_circle(free_geom, coarse=0.10, refine_steps=3):
    """Diameter (in the geometry's own units) of the biggest circle inside free_geom.

    Coarse grid, then three rounds of local refinement. Vectorised, so a whole
    plan costs milliseconds rather than seconds.
    """
    if free_geom is None or free_geom.is_empty:
        return 0.0, None

    parts = [free_geom] if free_geom.geom_type == "Polygon" else list(free_geom.geoms)
    parts = [p for p in parts if p.geom_type == "Polygon" and p.area > 0]
    if not parts:
        return 0.0, None
    poly = max(parts, key=lambda p: p.area)           # the circle must fit in one piece

    x0, y0, x1, y1 = poly.bounds
    step = max((x1 - x0), (y1 - y0)) * coarse
    if step <= 0:
        return 0.0, None

    boundary = poly.boundary
    best_r, best_pt = 0.0, None

    for _ in range(refine_steps + 1):
        xs = np.arange(x0, x1 + step, step)
        ys = np.arange(y0, y1 + step, step)
        gx, gy = np.meshgrid(xs, ys)
        gx, gy = gx.ravel(), gy.ravel()
        inside = shapely.contains_xy(poly, gx, gy)
        if not inside.any():
            break
        gx, gy = gx[inside], gy[inside]
        d = shapely.distance(shapely.points(np.column_stack([gx, gy])), boundary)
        k = int(np.argmax(d))
        if d[k] > best_r:
            best_r, best_pt = float(d[k]), (float(gx[k]), float(gy[k]))
        # tighten the window around the current best and halve the step
        if best_pt is None:
            break
        x0, x1 = best_pt[0] - step, best_pt[0] + step
        y0, y1 = best_pt[1] - step, best_pt[1] + step
        step /= 4.0

    return best_r * 2.0, best_pt


# ---------------------------------------------------------------------------
# 3. narrowest cross-section along the long axis
# ---------------------------------------------------------------------------

def _min_cross_section(poly, stations=120, trim=0.06):
    """Narrowest span of poly measured perpendicular to its long axis.

    trim skips the first and last few percent, where a room's own end wall makes
    the section meaningless.

    Only stations whose centreline point actually falls inside the polygon are
    counted, and the span measured is the run containing that point. Without
    that rule an L-shaped room returns the width of a corner sliver clipped by
    the section line — a sauna in the sample plan reported 2 mm.
    """
    if poly is None or poly.is_empty or poly.area <= 0:
        return None

    rect = poly.minimum_rotated_rectangle
    coords = list(rect.exterior.coords)[:4]
    edges = []
    for i in range(4):
        (ax, ay), (bx, by) = coords[i], coords[(i + 1) % 4]
        edges.append((math.hypot(bx - ax, by - ay), (ax, ay), (bx - ax, by - ay)))
    edges.sort(key=lambda e: e[0])
    long_len, (ox, oy), (lvx, lvy) = edges[-1]
    short_len = edges[0][0]
    if long_len <= 0:
        return None

    ux, uy = lvx / long_len, lvy / long_len          # along the long axis
    nx, ny = -uy, ux                                 # perpendicular
    reach = short_len * 1.5 + 1.0

    # start from the corner shared by the long and short edges
    sx, sy = ox, oy
    best = None
    for k in range(stations + 1):
        t = trim + (1 - 2 * trim) * (k / stations)
        px, py = sx + ux * long_len * t, sy + uy * long_len * t
        # the section line spans the full short side plus slack, centred on the
        # rectangle's centreline
        cx, cy = px + nx * short_len / 2, py + ny * short_len / 2
        centre = Point(cx, cy)
        if not poly.contains(centre):
            continue                      # centreline is outside an L-shaped room here
        line = LineString([(cx - nx * reach, cy - ny * reach),
                           (cx + nx * reach, cy + ny * reach)])
        seg = line.intersection(poly)
        if seg.is_empty:
            continue
        pieces = [seg] if seg.geom_type == "LineString" else [
            g for g in getattr(seg, "geoms", []) if g.geom_type == "LineString"]
        # the run the centreline sits on; a space beyond a partition is not part
        # of this cross-section
        pieces = [g for g in pieces if g.distance(centre) < 1e-6] or pieces
        if not pieces:
            continue
        width = max(g.length for g in pieces)
        if width <= 0:
            continue
        if best is None or width < best:
            best = width
    return best


# ---------------------------------------------------------------------------
# the public call
# ---------------------------------------------------------------------------

def _is_circulation(room):
    cat = room.category or ""
    if any(c in cat for c in CIRCULATION_CLASSES):
        return True, "class"
    if (room.code or "").upper().rstrip(".") in CIRCULATION_CODES:
        return True, "room_code"
    return False, None


def plan_geometry(svg_path, plan_id=None, plan=None):
    """Every deterministic measurement Part 2 needs, for one plan."""
    plan = plan or parse_svg(svg_path, plan_id)
    geo = _collect(svg_path)
    ppm = plan.px_per_m
    furniture = geo["furniture"]

    def to_mm(svg_units):
        return None if svg_units is None else round(svg_units / ppm * 1000)

    rooms_out, corridors_out = [], []
    for room in plan.rooms:
        if len(room.polygon_svg) < 3:
            continue
        poly = Polygon(room.polygon_svg)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area <= 0:
            continue

        free = poly.difference(furniture) if furniture is not None else poly
        circle_svg, centre = _largest_free_circle(free)
        bare_circle_svg, _ = _largest_free_circle(poly)
        min_x = _min_cross_section(poly)

        blocked = furniture is not None and poly.intersects(furniture)
        rec = {
            "code": room.code,
            "name": room.name,
            "category": room.category,
            "area_m2": room.area_m2,
            "width_m": room.width_m,
            "depth_m": room.depth_m,
            "outdoor": room.outdoor,
            "free_circle_mm": to_mm(circle_svg),
            "free_circle_ignoring_furniture_mm": to_mm(bare_circle_svg),
            "furniture_present": bool(blocked),
            "min_width_mm": to_mm(min_x),
            "circle_centre_svg": [round(centre[0], 2), round(centre[1], 2)] if centre else None,
        }
        rooms_out.append(rec)

        is_circ, why = _is_circulation(room)
        probable = False
        if not is_circ and "Undefined" in (room.category or ""):
            long_side = max(room.width_m, room.depth_m)
            short_side = min(room.width_m, room.depth_m)
            plausible = (short_side >= CORRIDOR_MIN_PLAUSIBLE_WIDTH_M
                         and room.area_m2 >= CORRIDOR_MIN_PLAUSIBLE_AREA_M2)
            if plausible and short_side > 0 \
               and long_side / short_side >= PROBABLE_CORRIDOR_ASPECT \
               and short_side <= PROBABLE_CORRIDOR_MAX_WIDTH_M:
                is_circ, why, probable = True, "shape_heuristic", True

        if is_circ and not room.outdoor:
            free_min = _min_cross_section(free.geoms[0] if free.geom_type == "MultiPolygon"
                                          and len(free.geoms) else free) \
                if free.geom_type in ("Polygon", "MultiPolygon") else None
            corridors_out.append({
                "id": f"c{len(corridors_out) + 1}",
                "code": room.code,
                "name": room.name,
                "identified_by": why,
                "probable_only": probable,
                "min_clear_width_mm": to_mm(min_x),
                "min_clear_width_less_furniture_mm": to_mm(free_min),
                "area_m2": room.area_m2,
            })

    doors_out = door_openings(plan, geo, ppm)

    return {
        "plan_id": plan.plan_id,
        "px_per_m": ppm,
        "scale_source": plan.scale_source,
        "eligible_for_determination": plan.scale_source != "convention_fallback_100",
        "overall_width_m": plan.overall_width_m,
        "overall_depth_m": plan.overall_depth_m,
        "internal_area_m2": plan.internal_area_m2,
        "doors": doors_out,
        "rooms": rooms_out,
        "corridors": corridors_out,
        "geometry_notes": [
            "Door clear widths are the span of the SVG Threshold rectangle parallel "
            "to the wall face. The wall layer in this dataset is unbroken through "
            "doorways, so the threshold rectangle is the encoded opening.",
            "Reported door widths are structural clear openings, not effective clear "
            "widths measured past an open leaf; the effective width is somewhat less.",
            "Turning circles are the largest circle fitting inside the room polygon "
            "with all FixedFurniture subtracted.",
            "Corridor width is the narrowest cross-section perpendicular to the "
            "space's long axis.",
        ],
        "warnings": plan.warnings,
    }


# ---------------------------------------------------------------------------
# CLI — print the measurements for one plan
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/sample_plan_0001/model.svg"
    g = plan_geometry(path, "sample")

    print(f"\n{g['plan_id']}   {g['overall_width_m']} x {g['overall_depth_m']} m   "
          f"{g['internal_area_m2']} m2   scale {g['px_per_m']} px/m ({g['scale_source']})")

    print(f"\nDOORS  ({len(g['doors'])})")
    print(f"  {'id':4} {'between':34} {'clear':>8} {'wall':>7}  method")
    for d in g["doors"]:
        print(f"  {d['id']:4} {' -> '.join(d['between'])[:34]:34} "
              f"{d['clear_width_mm']:>6} mm {d['wall_thickness_mm']:>5} mm  {d['method']}")

    print(f"\nROOMS  ({len(g['rooms'])})")
    print(f"  {'room':18} {'area':>8} {'circle':>9} {'no furn':>9} {'min width':>10}")
    for r in g["rooms"]:
        if r["outdoor"]:
            continue
        print(f"  {(r['code'] + ' ' + r['name'])[:18]:18} {r['area_m2']:>6} m2 "
              f"{r['free_circle_mm']:>6} mm {r['free_circle_ignoring_furniture_mm']:>6} mm "
              f"{r['min_width_mm']:>7} mm")

    print(f"\nCIRCULATION  ({len(g['corridors'])})")
    for c in g["corridors"]:
        tag = " (shape heuristic)" if c["probable_only"] else ""
        print(f"  {c['id']}  {c['code']} {c['name']:16} min {c['min_clear_width_mm']} mm  "
              f"less furniture {c['min_clear_width_less_furniture_mm']} mm{tag}")
    print()
