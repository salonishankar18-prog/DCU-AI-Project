# Claude Code build prompt — Datum

This repo already contains a tested pipeline in `core/` — do not rewrite it, only import
and wire it up. Read these three files first, in this order, before writing anything:

1. `FINDINGS.md` — what is actually inside a CubiCasa5k SVG, confirmed by inspecting a real
   file. This tells you where the dimensions live and why the alignment step exists.
2. `PROJECT_PLAN.md` — the full architecture, repo layout, API surface, and build order.
3. `core/*.py` — read the module docstrings. `svg_parse.py` extracts dimensions,
   `align.py` fits the SVG→PNG transform, `annotate.py` draws on the PNG, `batch.py` runs
   a whole dataset folder. Each is complete and has been run successfully against a real
   plan — `EXAMPLE_annotated.png` is its actual output.

`ui-prototype.html` is the approved visual design. Port its tokens, typography, layout, and
the measurement-ink colour rule into `web/`. Don't redesign it — wire the mock data in it to
the real API.

## Build order — stop for confirmation at each ⏸

**⏸ 1. Wire up Tab 1 end to end, on the sample data already in the repo.**
`api/main.py` — `POST /api/scan` (call `core.batch.find_plans`), `POST /api/annotate`
(call `core.batch.run_batch`, stream progress over SSE), `GET /api/plans` (read
`manifest.json`), `GET /api/plans/{id}/png`, `GET /api/export/csv`, `GET /api/export/zip`
(call `core.batch.zip_output`). Serve `web/index.html`. Confirm the batch runs against a
real dataset folder and the results table, progress bar, and PNG preview all populate from
real output before moving on.

**⏸ 2. Door and corridor geometry.**
Write `review/rules.py`. The SVG carries `Door Swing Beside` and `Threshold` groups (13 of
each in the sample plan) — the clear width of each opening is the gap in the wall polygon
at that threshold. Corridor minimum width is the narrowest cross-section of a circulation
space's polygon along its long axis. Also compute, per room, the largest circle that fits
inside the polygon without crossing fixed furniture (`FixedFurniture*` groups) — this is
the wheelchair turning-circle check. Print the results for the sample plan's rooms and
doors and show me before continuing; door/corridor geometry is easy to get subtly wrong and
this is the number every Part 2 check depends on.

**⏸ 3. TGD M index.**
`review/tgdm_index.py` — extract text from the PDF at `data/tgdm/TGD-M.pdf`, split on
clause numbering, store `{clause_id, heading, text, page}`. Keyword retrieval on the
question plus clause headings; do not add embeddings unless keyword retrieval proves
insufficient for the plan questions in step 4. Show me five sample retrievals (a door-width
question, a turning-circle question, a corridor question) before continuing.

**⏸ 4. Review agent and Tab 2.**
`review/agent.py` per §4 of `PROJECT_PLAN.md`: Python computes every measurement via
`rules.py`, Claude receives those values plus verbatim retrieved clause text and judges
compliance — it never estimates a dimension itself. Three outcomes only: `pass` / `fail` /
`undetermined`, the last for anything not readable from plan geometry (level thresholds,
floor surfaces), naming what drawing would answer it. Wire `POST /api/review` and
`POST /api/verdict`. Confirm the chat and verdict card work against the sample plan with
real clause citations before considering this done.

Then finish the remaining items in §6 of `PROJECT_PLAN.md` (export, error states, full
dataset run) without stopping for further confirmation.

## Non-negotiables

- Don't touch `core/`'s parsing or alignment logic. If a bug turns up, fix it in place and
  tell me what and why — don't route around it.
- Never modify anything under `data/raw/`. All output goes to `data/out/`.
- A plan that falls through to the scale-estimation fallback (`scale_source ==
  "convention_fallback_100"` with no room-label cross-check) is excluded from Part 2
  determinations — flag it, don't silently review it.
- `.env` holds the Anthropic API key, read server-side only, never sent to the browser.
- Python measures, Claude judges — this is the load-bearing design decision in the whole
  project. No exceptions in either direction.
- No TGD M threshold is ever hard-coded in Python or in a prompt. Every number quoted to
  the user traces back to retrieved clause text, with the clause id shown next to it.
- The measurement-ink colour rule from `ui-prototype.html` holds throughout: orange marks
  a value describing a real-world distance or area, and nothing else, on screen and in the
  annotated PNGs.
- `batch.py` already wraps each plan in try/except and resumes from `manifest.json` — keep
  that behaviour when you extend it, don't reintroduce a run that dies on one bad file.

## Definition of done

`python run.py` serves the UI at `localhost:8000`. Tab 1 scans a real dataset folder,
annotates every plan with a live progress bar, shows results and a PNG preview, exports CSV
and a ZIP containing originals + annotated copies + per-plan `dimensions.json`. Tab 2 loads
a plan, answers questions with clause citations, and renders a verdict card with individual
pass/fail/undetermined checks, each showing its measured value and TGD M clause reference.
