"""
svg_parse.py — read a CubiCasa5k model.svg and pull out the real-world dimensions.

Two facts about these files, confirmed by inspection:

1. Every room (<g class="Space ...">) contains a hidden label:
       <g class="TextLabel DimensionMeasureLabel" style="display: none;">
           <text>9'4" x 5'2"</text>
           <text>2.84 m x 1.58 m</text>
       </g>
   The dimensions are already written in the file. We read them, we don't guess them.

2. The drawing scale is exactly 100 SVG units per metre (1 unit = 1 cm).
   We still re-derive it per file from the room polygons vs their labels, so a file
   that breaks the convention gets caught instead of silently producing wrong numbers.
"""

import re
from dataclasses import dataclass, field, asdict
from statistics import median

from lxml import etree

SVG_NS = "{http://www.w3.org/2000/svg}"

# "2.84 m x 1.58 m"  ->  (2.84, 1.58)
_METRIC = re.compile(r"([\d.]+)\s*m\s*[xX×]\s*([\d.]+)\s*m")

# Finnish room codes used throughout CubiCasa5k, mapped to English.
ROOM_NAMES = {
    "OH": "Living room",   "MH": "Bedroom",      "K": "Kitchen",
    "KPH": "Bathroom",     "WC": "Toilet",       "ET": "Entrance hall",
    "RUOK": "Dining",      "S": "Sauna",         "TK": "Utility",
    "VAR": "Storage",      "TH": "Workshop",     "AUTOTALLI": "Garage",
    "ULKOTILA": "Outdoor", "PATIO": "Patio",     "PARVEKE": "Balcony",
    "KH": "Utility room",  "PSH": "Shower room", "VH": "Walk-in closet",
}


@dataclass
class Room:
    """One space in the plan, with the dimensions read out of the SVG."""
    code: str                       # label as drawn, e.g. "MH"
    name: str                       # English name, e.g. "Bedroom"
    category: str                   # SVG class, e.g. "Space Bedroom"
    width_m: float                  # from the hidden label
    depth_m: float                  # from the hidden label
    area_m2: float                  # true polygon area, not width x depth
    polygon_svg: list               # [(x, y), ...] in SVG units
    centroid_svg: tuple             # (x, y) in SVG units
    is_rectangular: bool            # False for L-shaped rooms
    outdoor: bool                   # patios, balconies — excluded from floor area


@dataclass
class Plan:
    """Everything extracted from one model.svg."""
    plan_id: str
    px_per_m: float
    scale_source: str
    scale_confidence: float         # spread across room cross-checks; lower is better
    viewbox: tuple                  # (w, h) in SVG units
    wall_bbox_svg: tuple            # (x0, y0, x1, y1) — the building footprint
    overall_width_m: float
    overall_depth_m: float
    internal_area_m2: float         # sum of indoor room areas
    rooms: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["rooms"] = [asdict(r) if not isinstance(r, dict) else r for r in self.rooms]
        return d


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def _class_chain(el):
    """Every class attribute from this element up to the root, space-joined.

    Lets us ask 'is this polygon anywhere inside a Wall group?' without caring
    how deeply it's nested.
    """
    parts, node = [], el
    while node is not None:
        parts.append(node.get("class") or "")
        node = node.getparent()
    return " ".join(parts)


def _points(polygon_el):
    """Parse an SVG points="x,y x,y ..." attribute into [(x, y), ...]."""
    raw = polygon_el.get("points")
    if not raw:
        return []
    out = []
    for token in raw.strip().split():
        if "," not in token:
            continue
        try:
            x, y = token.split(",")[:2]
            out.append((float(x), float(y)))
        except ValueError:
            continue
    return out


def _shoelace_area(pts):
    """Polygon area via the shoelace formula. Correct for L-shapes and concave rooms,
    which a width x depth multiplication is not."""
    if len(pts) < 3:
        return 0.0
    total = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def _centroid(pts):
    """Area-weighted centroid — where a room label should sit."""
    if len(pts) < 3:
        return (0.0, 0.0)
    cx = cy = a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if a == 0:
        xs, ys = zip(*pts)
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))


def _bbox(pts):
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs), max(ys)


# ----------------------------------------------------------------------------
# main entry point
# ----------------------------------------------------------------------------

def parse_svg(svg_path, plan_id=None):
    """Read one model.svg and return a populated Plan."""
    tree = etree.parse(str(svg_path))
    root = tree.getroot()
    warnings = []

    vb_w = float(root.get("width", 0))
    vb_h = float(root.get("height", 0))

    # --- collect every Space, with its hidden dimension label -----------------
    rooms, scale_samples = [], []

    for space in root.iter():
        cls = space.get("class") or ""
        # Match the class token exactly. Guards against "SpaceDimensionsLabel",
        # which starts with "Space" but is a text label, not a room.
        if cls.split()[:1] != ["Space"]:
            continue

        # the room outline: first polygon that is not a dimension arrow marker
        pts = []
        for poly in space.iter(SVG_NS + "polygon"):
            if "DimensionMark" in _class_chain(poly):
                continue
            pts = _points(poly)
            if pts:
                break
        if not pts:
            warnings.append(f"space '{cls}' has no polygon — skipped")
            continue

        # the drawn room code, e.g. "MH"
        code = ""
        for g in space.iter():
            if (g.get("class") or "") == "TextLabel NameLabel":
                t = g.find(SVG_NS + "text")
                if t is not None and t.text:
                    code = t.text.strip()

        # the HIDDEN metric dimension label — this is the dataset's own answer
        label_w = label_d = None
        for g in space.iter():
            if (g.get("class") or "") != "TextLabel DimensionMeasureLabel":
                continue
            for t in g.findall(SVG_NS + "text"):
                m = _METRIC.search(t.text or "")
                if m:
                    label_w, label_d = float(m.group(1)), float(m.group(2))

        x0, y0, x1, y1 = _bbox(pts)
        box_w, box_h = x1 - x0, y1 - y0
        area_svg = _shoelace_area(pts)

        # A rectangle's polygon area equals its bounding-box area. If it doesn't,
        # the room is L-shaped and width x depth would overstate its floor area.
        rectangular = box_w * box_h > 0 and abs(area_svg - box_w * box_h) / (box_w * box_h) < 0.02

        # Cross-check the drawing against its own label to derive px-per-metre.
        # Only rectangular rooms are valid samples.
        if label_w and label_d and rectangular:
            scale_samples += [box_w / label_w, box_h / label_d]

        rooms.append({
            "code": code,
            "name": ROOM_NAMES.get(code.upper().rstrip("."), code or "Unnamed"),
            "category": cls,
            "label_w_m": label_w,
            "label_d_m": label_d,
            "polygon_svg": pts,
            "centroid_svg": _centroid(pts),
            "bbox_svg": (x0, y0, x1, y1),
            "_area_svg": area_svg,
            "is_rectangular": rectangular,
            "outdoor": ("Outdoor" in cls or "Patio" in cls or "Balcony" in cls),
        })

    # --- resolve the scale ----------------------------------------------------
    if scale_samples:
        px_per_m = median(scale_samples)
        spread = (max(scale_samples) - min(scale_samples)) / px_per_m
        source = "room_label_crosscheck"
        if spread > 0.05:
            warnings.append(f"scale samples disagree by {spread:.1%}")
    else:
        px_per_m, spread, source = 100.0, 1.0, "convention_fallback_100"
        warnings.append("no usable room labels — assumed 100 px/m; treat as estimated")

    # --- finalise room measurements in metres --------------------------------
    final_rooms, internal_area = [], 0.0
    for r in rooms:
        x0, y0, x1, y1 = r["bbox_svg"]
        w = r["label_w_m"] if r["label_w_m"] else (x1 - x0) / px_per_m
        d = r["label_d_m"] if r["label_d_m"] else (y1 - y0) / px_per_m
        area = r["_area_svg"] / (px_per_m ** 2)
        if not r["outdoor"]:
            internal_area += area
        final_rooms.append(Room(
            code=r["code"], name=r["name"], category=r["category"],
            width_m=round(w, 2), depth_m=round(d, 2), area_m2=round(area, 2),
            polygon_svg=r["polygon_svg"], centroid_svg=r["centroid_svg"],
            is_rectangular=r["is_rectangular"], outdoor=r["outdoor"],
        ))

    # --- building footprint, from wall geometry only --------------------------
    # Walls are always drawn in the PNG. Outdoor spaces sometimes are not, so
    # they must not define the footprint.
    wxs, wys = [], []
    for poly in root.iter(SVG_NS + "polygon"):
        if "Wall" not in _class_chain(poly):
            continue
        for x, y in _points(poly):
            wxs.append(x)
            wys.append(y)
    if wxs:
        wall_bbox = (min(wxs), min(wys), max(wxs), max(wys))
    else:
        wall_bbox = (0, 0, vb_w, vb_h)
        warnings.append("no wall polygons found — footprint fell back to viewBox")

    return Plan(
        plan_id=plan_id or "plan",
        px_per_m=round(px_per_m, 3),
        scale_source=source,
        scale_confidence=round(spread, 4),
        viewbox=(vb_w, vb_h),
        wall_bbox_svg=wall_bbox,
        overall_width_m=round((wall_bbox[2] - wall_bbox[0]) / px_per_m, 2),
        overall_depth_m=round((wall_bbox[3] - wall_bbox[1]) / px_per_m, 2),
        internal_area_m2=round(internal_area, 2),
        rooms=final_rooms,
        warnings=warnings,
    )
