# Datum — Floor Plan Dimension & Access Review

Two-part project on the CubiCasa5k dataset:

1. **Extract dimensions** from each plan's `model.svg` and burn them onto the matching
   PNGs, across the whole dataset.
2. **Access review** — a chat interface, backed by the Claude API, that reads those
   dimensions, cross-references *Technical Guidance Document M — Access and Use*, and
   returns an accessible / not-accessible determination per plan.

## What's built

Both parts are complete and have been run against a real 100-plan dataset.

`core/` — the tested pipeline, unchanged (see `FINDINGS.md`):

| File | Does |
|---|---|
| `core/svg_parse.py` | Reads the hidden `DimensionMeasureLabel` text in each room, cross-checks it against the drawn polygon, resolves scale (confirmed at 100 px/m), reports true polygon area (not width×depth, which overstates L-shaped rooms) |
| `core/align.py` | Fits the SVG→PNG pixel transform by matching wall linework, since the renders are padded and not 1:1 with the viewBox |
| `core/annotate.py` | Draws dimension lines (drafting convention) or a corner label onto a copy of the PNG; adaptive font sizing so small rooms don't overflow |
| `core/batch.py` | Walks a dataset folder, processes every plan, writes `manifest.json` + `dimensions.csv`, resumable, packages a zip |

`review/`, `api/`, `web/` — built on top:

| File | Does |
|---|---|
| `review/rules.py` | Door clear widths, corridor minimum cross-sections, and the largest furniture-free circle per room. Python's numbers — no TGD M thresholds anywhere in it |
| `review/tgdm_index.py` | Splits the TGD M PDF into 140 numbered clauses with page and scope, keyword retrieval with domain synonyms |
| `review/agent.py` | The two Claude calls. Receives measured values plus verbatim clause text and judges only against that text |
| `api/main.py` | FastAPI routes, SSE progress stream, CSV/ZIP export |
| `web/` | The approved design from `ui-prototype.html`, wired to live data |

Two things worth knowing, both found during the build and documented in place:

- **The wall layer is not notched at doorways.** The build brief assumed the door clear
  width was a gap in the wall polygon. It isn't — walls run unbroken through every
  doorway (wall coverage 1.00 under all 13 thresholds of the sample plan). The
  `Threshold` rectangle *is* the encoded opening, so `rules.py` measures its span
  parallel to the wall face and labels the method on every door.
- **Fixed furniture is drawn as a positioned symbol.** Each `FixedFurniture` group holds a
  `BoundaryPolygon` in local coordinates with a `transform` matrix on the group. Ignore the
  transform and every fitting collapses onto the origin and subtracts nothing —
  `rules.py` composes the transform chain.

## Design decisions that are load-bearing

- **Python measures, Claude judges.** `rules.py` computes every dimension; `agent.py`
  contains no threshold and never asks the model for a measurement.
- **No hard-coded TGD M numbers.** Every limit quoted to the user comes from retrieved
  clause text, with the clause id shown beside it.
- **Three outcomes.** `pass` / `fail` / `undetermined` — the last for anything a plan view
  cannot show (level thresholds, floor surfaces), naming the drawing that would answer it.
- **Plans on the scale fallback are excluded**, not silently reviewed. 6 of the 100 plans
  in the test set fell through; they carry an `est` chip and a banner.
- **Orange is measurement ink.** Applied by regex in `agent.py:to_html`, so the model
  cannot paint something orange that isn't a real-world distance or area.
## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your ANTHROPIC_API_KEY
```

Put a CubiCasa5k folder (plan subfolders, each with `model.svg` + PNGs) at `data/raw/`,
and the TGD M PDF at `data/tgdm/TGD-M.pdf`.

```bash
python run.py                # serves the UI at localhost:8000
```

Tab 1 needs no API key. Tab 2 reports that it is unconfigured until one is set.

The review model defaults to `claude-sonnet-5`; override with `ANTHROPIC_MODEL` in `.env`.

## Repo contents

```
├── requirements.txt
├── .env.example
├── PROJECT_PLAN.md            full architecture
├── CLAUDE_CODE_PROMPT.md      the build instructions this was built from
├── run.py                     uvicorn entrypoint
├── FINDINGS.md                what's actually in a CubiCasa5k SVG, confirmed by inspection
├── ui-prototype.html          approved visual design — open directly in a browser
├── EXAMPLE_annotated.png      real output from core/, for reference
├── assets/
│   └── DejaVuSans.ttf         bundled font so Colab renders text consistently
├── core/                      tested — parsing, alignment, annotation, batching
│   ├── svg_parse.py
│   ├── align.py
│   ├── annotate.py
│   └── batch.py
├── review/                    geometry checks, TGD M index, the Claude calls
│   ├── rules.py
│   ├── tgdm_index.py
│   └── agent.py
├── api/
│   └── main.py                FastAPI routes
├── web/                       index.html · app.js · style.css
└── notebooks/
    └── 01_extract_dimensions.ipynb   Colab-ready, imports core/ directly
```
