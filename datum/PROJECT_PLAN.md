# Datum — Floor Plan Dimension & Access Review
## Architecture plan

**Part 1** — extract real-world dimensions from CubiCasa5k SVG files, burn them onto the matching PNGs, across 100+ plans.
**Part 2** — a chat interface backed by the Claude API that reads those dimensions, cross-references *Technical Guidance Document M — Access and Use*, and returns an accessible / not accessible determination.

---

## 1. Stack

| Layer | Choice | Why |
|---|---|---|
| Processing | Python 3.11 — `lxml`, `Pillow`, `numpy`, `shapely` | SVG is XML; Pillow burns the annotation; shapely handles room polygons and clearance geometry |
| Backend | FastAPI + `uvicorn` | Async, trivial file endpoints, auto docs for the demo |
| Frontend | One static HTML/CSS/JS page | Full design control, no build step, no framework to debug the night before |
| LLM | Anthropic Python SDK, `claude-sonnet-5` | Fast enough for interactive chat, strong on structured JSON output |
| Reference doc | TGD M PDF → chunked text → keyword + embedding retrieval | Clause text goes into the prompt so answers cite real sections |
| Part 1 fallback | Colab notebook wrapping the same modules | Satisfies the "run in Colab" requirement without duplicating logic |

The pipeline modules are plain Python with no web dependencies. The notebook and the API both import them. Write the logic once.

---

## 2. Repository layout

```
datum/
├── requirements.txt
├── .env.example                  # ANTHROPIC_API_KEY=
├── run.py                        # uvicorn entrypoint
│
├── core/                         # ← no web imports, importable from Colab
│   ├── svg_inspect.py            # diagnostic: dump structure of one SVG
│   ├── svg_parse.py              # scale + geometry extraction
│   ├── geometry.py               # areas, door widths, clearances, turning circles
│   ├── annotate.py               # draw dimensions onto PNG
│   └── batch.py                  # walk dataset, run all plans, write manifest
│
├── review/
│   ├── tgdm_index.py             # PDF → clauses → searchable index
│   ├── rules.py                  # deterministic geometric checks
│   └── agent.py                  # Claude API calls, tool schema, verdict assembly
│
├── api/
│   └── main.py                   # FastAPI routes
│
├── web/
│   ├── index.html                # the UI (both tabs)
│   ├── app.js
│   └── style.css
│
├── notebooks/
│   └── 01_extract_dimensions.ipynb
│
└── data/
    ├── raw/                      # dataset as downloaded — read-only
    ├── out/                      # annotated PNGs
    ├── manifest.json             # every plan's extracted dimensions
    └── tgdm/TGD-M.pdf
```

---

## 3. Part 1 — dimension extraction

### 3.1 Establish the scale first, code second

Do not guess at the SVG structure. Run `svg_inspect.py` on one real file and read the output before writing the parser. It should print: root `width`/`height`/`viewBox`, every distinct tag, every distinct `class` value with counts, and any element whose class or id contains `scale`, `dim`, `ruler`, `calib`, or `measure`.

CubiCasa5k SVGs typically carry a calibration element — a two-point line or polyline representing a known real-world distance. That gives you **pixels per metre**. Everything downstream is that one number.

Build the resolver as an ordered chain, each strategy logged so you can see which fired:

1. Dedicated scale/calibration element → `px_per_m = length_in_px / known_length_m`
2. Root `width`/`height` carrying real units (`mm`, `cm`, `m`) compared against the `viewBox`
3. Any element with an explicit dimension text label, matched against its own drawn length
4. Fall back to a dataset-wide median `px_per_m` and flag the plan `estimated`

A plan that reaches step 4 is marked and excluded from Part 2 determinations. Never silently invent a scale.

### 3.2 What gets extracted per plan

```json
{
  "plan_id": "plan_0142",
  "px_per_m": 214.6,
  "scale_source": "calibration_element",
  "bbox_m": {"width": 9.40, "depth": 6.95},
  "floor_area_m2": 65.3,
  "rooms": [
    {"name": "Bathroom", "area_m2": 4.3, "bbox_m": [1.98, 2.15],
     "polygon_px": [[..]], "largest_inscribed_circle_m": 1.32}
  ],
  "doors": [{"id": "d3", "between": ["Hall","Bathroom"], "clear_width_mm": 720}],
  "corridors": [{"id": "c1", "min_clear_width_mm": 860}],
  "png_files": ["F1_original.png", "F1_scaled.png"],
  "status": "ok"
}
```

Every plan's record appends to `data/manifest.json`. **That manifest is the interface between Part 1 and Part 2** — Part 2 never re-parses SVGs.

### 3.3 Pixel alignment between SVG and PNG

The SVG viewBox and the PNG raster are often not 1:1. Before annotating, compute `png_width_px / viewbox_width` and apply it to every coordinate. Verify on one plan by drawing the room polygons over the PNG at 40% opacity — if they land on the walls, the transform is right. Do this check before batching 100 files.

### 3.4 Annotation

Two styles, both selectable in the UI:

- **Dimension lines** — extension lines and tick-terminated dimension lines outside the plan for overall width and depth, plus an area figure centred in each room. This is the drafting convention and the default.
- **Corner label** — a single title-block-style box, for when the plan is visually dense.

Rules: draw on a copy, never the original; use a font bundled in the repo (`DejaVuSans.ttf`) rather than a system font, or Colab will fall back to unreadable bitmap default; scale text size relative to image width so a 600px and a 3000px render both read; put a solid white pad behind every number so it survives on top of linework.

### 3.5 Batch

`batch.py` walks the dataset root, groups by plan folder, and for each plan handles its 1–3 PNGs. Wrap every plan in `try/except`, record the failure, keep going. A single malformed SVG must not kill a 104-plan run. Emit progress so the UI progress bar is real, not decorative.

---

## 4. Part 2 — accessibility review

### 4.1 The reference document

`tgdm_index.py` extracts text from the TGD M PDF, splits on clause numbering (`1.2.3` style headings), and stores `{clause_id, heading, text, page}` records. Retrieval is keyword match on the question plus the clause headings; add embeddings only if keyword retrieval proves weak. For a document this size, keyword retrieval is usually enough and it's far easier to debug.

**Do not hard-code clause values into the code.** Every threshold quoted to the user must come from retrieved clause text so the citation is real. This matters — the whole credibility of Part 2 rests on the numbers tracing back to the document.

### 4.2 Division of labour

This is the key architectural decision:

- **Python decides the numbers.** `rules.py` computes door clear widths, corridor minimums, room areas, and the largest inscribed circle per room. Deterministic, testable, reproducible.
- **Claude decides the meaning.** It receives the measured values plus the retrieved clause text, and judges compliance, explains the reasoning, and answers follow-up questions.

Never ask the model to measure. Never let Python decide compliance. Each side does what it's actually good at, and the demo doesn't collapse when the model hallucinates a millimetre.

### 4.3 Request shape

```python
system = (
  "You review residential floor plans against Technical Guidance Document M — "
  "Access and Use. You are given measured values extracted from the drawing and "
  "verbatim clause text. Judge only against the clause text supplied. Cite the "
  "clause id for every judgement. If a question cannot be answered from plan "
  "geometry alone, say so and name what drawing would answer it."
)

messages = [{"role": "user", "content": f"""
<plan_measurements>{json.dumps(plan_record, indent=2)}</plan_measurements>
<tgdm_clauses>{retrieved_clause_text}</tgdm_clauses>
<question>{user_question}</question>
"""}]
```

For the verdict card, make a second call requesting JSON only:

```json
{"determination":"not_accessible",
 "checks":[{"item":"Bathroom door clear width","measured_mm":720,
            "clause":"3.4","result":"fail","note":"..."}]}
```

Parse defensively — strip ``` fences, `try/except` the `json.loads`, and fall back to showing the prose answer if parsing fails.

### 4.4 Three outcomes, not two

`pass` / `fail` / **`undetermined`**. Level thresholds, handrails, and floor surfaces are not visible in a plan view. A tool that quietly returns "accessible" on something it never checked is worse than one that says it can't tell. The UI shows undetermined in amber and names the missing drawing.

---

## 5. API surface

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/scan` | Walk the dataset root, return plan count and PNG count |
| `POST` | `/api/annotate` | Run the batch; stream progress over SSE |
| `GET` | `/api/plans` | The manifest, for the results table |
| `GET` | `/api/plans/{id}/png` | Serve an annotated PNG |
| `GET` | `/api/plans/{id}/checks` | Deterministic rule results |
| `POST` | `/api/review` | `{plan_id, question}` → Claude answer + citations |
| `POST` | `/api/verdict` | `{plan_id}` → structured determination JSON |
| `GET` | `/api/export/{fmt}` | CSV of the manifest, or ZIP of annotated PNGs |

The API key lives in `.env`, read server-side only. It must never reach the browser.

---

## 6. Build order for tomorrow

Sequenced so you always have something demonstrable:

| # | Task | Est. |
|---|---|---|
| 1 | `svg_inspect.py` on one file — confirm where the scale lives | 30 min |
| 2 | `svg_parse.py` — scale + bbox + room polygons for that one file | 60 min |
| 3 | `annotate.py` — one annotated PNG you can look at | 45 min |
| 4 | Alignment check — polygons overlaid on the raster | 20 min |
| 5 | `batch.py` — 104 plans → `manifest.json` | 45 min |
| 6 | FastAPI + serve `web/index.html` — Tab 1 live | 60 min |
| 7 | `tgdm_index.py` — PDF chunked and searchable | 45 min |
| 8 | `rules.py` — doors, corridors, turning circles | 60 min |
| 9 | `agent.py` + `/api/review` — Tab 2 chat live | 60 min |
| 10 | `/api/verdict` — verdict card populated | 30 min |
| 11 | Export CSV/ZIP, error states, run on the full set | 45 min |

**Checkpoint after step 5.** If step 2 is fighting you, the whole schedule shifts — that is the step to start on and the one to ask for help with.

---

## 7. Risks

| Risk | Handling |
|---|---|
| No calibration element in the SVGs | The strategy chain in §3.1; if all fail, derive `px_per_m` from a known-size fixture (a standard door leaf) and label every output `estimated` |
| SVG and PNG coordinate spaces differ | The §3.3 overlay check, on one plan, before batching |
| Room polygons don't close cleanly | `shapely` `buffer(0)` to repair; skip and flag anything still invalid |
| Door width isn't directly encoded | Measure the gap in the wall polygon where a door element sits |
| Model quotes a threshold that isn't in TGD M | Clause text is supplied verbatim in the prompt and the system prompt forbids outside knowledge; spot-check three answers against the PDF |
| API rate limits during the demo | Cache verdicts in `manifest.json` after first computation; the demo replays from cache |
| Colab session drops mid-batch | `batch.py` skips plans already present in the manifest, so re-running resumes |

---

## 8. Interface

Two tabs, matching the two halves of the brief.

**01 Extract dimensions** — dataset intake, output settings, batch progress, a results table of every plan's extracted dimensions, and a live preview of the annotated PNG.

**02 Access review** — plan picker, chat thread against TGD M, and a verdict panel breaking the determination into individual checks, each carrying its measured value and its clause reference.

The design treats the app as a drawing sheet: drafting-mylar ground, ink linework, title-block type, section rules drawn as dimension lines with tick ends. One rule governs colour — **orange is measurement ink, used only on values describing a real-world distance or area**, on screen and in the exported PNGs. Everything structural stays ink black. It means a user scanning the interface finds every real measurement instantly, and it makes the UI and the output visually continuous.
