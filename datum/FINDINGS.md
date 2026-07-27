# SVG inspection findings

Run against the uploaded plan: `model.svg`, `F1_original.png` (1624×656),
`F1_scaled.png` (3153×1273), plus the F2 pair.

---

## 1. The dimensions are already written in the file

Every room is a `<g class="Space ...">` containing a hidden label group:

```xml
<g class="TextLabel DimensionMeasureLabel" style="display: none;">
  <text>9'4" x 5'2"</text>
  <text>2.84 m x 1.58 m</text>
</g>
```

`display: none` is why they never appear in the PNG renders. Both imperial and metric
strings are present. Alongside it sits a visible `NameLabel` holding the room code
(`OH`, `MH`, `KPH`, …).

So the task is **read and verify**, not derive. The parser takes the label as the source of
truth and cross-checks it against the drawn polygon.

## 2. The scale is exactly 100 SVG units per metre

Derived independently for all 16 rooms by dividing each polygon's bounding box by its own
hidden label:

| Room | Label | Polygon (units) | Derived px/m |
|---|---|---|---|
| ULKOTILA | 2.84 × 1.58 m | 284.45 × 157.57 | 100.16 / 99.73 |
| RUOK | 1.89 × 4.47 m | 189.04 × 446.94 | 100.02 / 99.99 |
| K | 3.30 × 3.23 m | 330.47 × 323.28 | 100.14 / 100.09 |
| OH | 6.84 × 4.46 m | 684.06 × 445.62 | 100.01 / 99.91 |
| VAR | 7.36 × 7.80 m | 735.98 × 779.67 | 100.00 / 99.96 |

Median across every rectangular room: **100.026 px/m**, total spread 0.75%. One SVG unit is
one centimetre.

Two rooms disagree (Sauna 174, Den 116) because they are L-shaped — their bounding box
legitimately exceeds their labelled dimensions. The parser detects this by comparing
polygon area to bounding-box area and excludes non-rectangular rooms from the scale
calculation. It also reports true polygon area per room rather than width × depth, which
would overstate an L-shaped room.

## 3. The PNGs are padded, so the transform has to be fitted

| | Size | Scale vs SVG |
|---|---|---|
| viewBox | 2983.56 × 1149.58 | — |
| F1_scaled.png | 3153 × 1273 | 1.0018 |
| F1_original.png | 1624 × 656 | 0.5158 |

Neither PNG matches the viewBox aspect ratio, so a naïve `png_width / viewbox_width` gives
different horizontal and vertical factors and the annotations drift.

`core/align.py` solves it by matching the horizontal extent of the **wall** geometry to the
heavy black ink in the raster. Walls are used because outdoor spaces are not always
rendered — the top `PATIO` in this plan is in the SVG but not drawn — so anything that
includes them inflates the bounding box. The horizontal axis is used because it is the long
axis and is not disturbed by porches that protrude vertically.

Verified by overlaying every room polygon on the raster: they land on the walls exactly.

## 4. Extracted result for this plan

```
Scale        100.026 px/m   (room_label_crosscheck, 0.75% spread)
Overall      28.16 m × 8.27 m
Floor area   188.9 m²
Rooms        16
```

| Code | Room | Size | Area |
|---|---|---|---|
| OH | Living room | 6.84 × 4.46 m | 30.5 m² |
| K | Kitchen | 3.30 × 3.23 m | 10.5 m² |
| MH | Bedroom | 2.90 × 4.47 m | 13.0 m² |
| MH | Bedroom | 2.90 × 3.22 m | 9.3 m² |
| MH | Bedroom | 2.57 × 3.23 m | 7.6 m² (L-shaped) |
| KPH | Bathroom | 2.77 × 1.44 m | 4.0 m² |
| WC | Toilet | 1.24 × 1.02 m | 1.3 m² |
| ET | Entrance hall | 1.84 × 2.21 m | 4.0 m² |
| RUOK | Dining | 1.89 × 4.47 m | 8.3 m² |
| S | Sauna | 2.72 × 1.67 m | 3.3 m² |
| TK | Utility | 1.06 × 1.02 m | 1.1 m² |
| VAR | Storage | 7.36 × 7.80 m | 56.8 m² |
| TH | Workshop | 5.21 × 4.23 m | 22.4 m² |
| AUTOTALLI | Garage | 5.22 × 3.46 m | 16.9 m² |

Room codes are Finnish; `core/svg_parse.py` carries the mapping to English.

## 5. What this means for Part 2

The WC at 1.24 × 1.02 m and the utility room at 1.06 × 1.02 m are well under a 1500 mm
wheelchair turning circle, so this plan will fail several TGD M checks. That makes it a
useful demo case — the review tab has something real to report rather than a blanket pass.

Door clear widths are **not** yet extracted. The SVG has `Door Swing Beside` and `Threshold`
groups (13 of each) which encode the openings, so the geometry is available — it just needs
a pass in `rules.py` that measures the gap in the wall polygon at each threshold. That is
the main remaining piece of Part 2 input.
