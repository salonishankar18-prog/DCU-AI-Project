# Datum — full-dataset results (CubiCasa5k sample, 101 plans)

Pre-computed output from a full run of both tabs over every plan in
`data/raw/` (100 CubiCasa5k plans + `sample_plan_0001`). Generated on
2026-07-27.

## Contents

- `manifest.json` — one record per plan: extracted dimensions, scale info,
  room list, and (where computed) the Tab 2 access-review verdict, embedded
  under each record's `verdict` key. This is the same file the running app
  reads from `data/out/manifest.json`.
- `dimensions.csv` — Tab 1 dimensions in flat/tabular form (plan id, scale,
  overall width/depth, floor area, room count, status).
- `tab2_verdicts.csv` — Tab 2 summary: plan id, determination
  (`compliant_with_flags` / `non_compliant` / `undetermined` / `excluded`),
  applicable TGD M section, the governing clause, model used, per-call cost,
  and whether the result was served from cache.
- `tgdm_clause_reference.json` — the TGD M 2022 clause index the Tab 2 model
  was shown for every judgement (clause id, heading, verbatim text, page,
  section scope). Rebuilt from the TGD M 2022 document text directly (see
  `build_tgdm_cache.py` in the project root) rather than from the literal
  PDF, since the PDF itself isn't redistributed in this repo.
- `plans/<plan_id>/` — per-plan output:
  - `dimensions.json` — full measurement record, including the room polygons
    the manifest drops to stay lightweight.
  - `F#_original_annotated.png` / `F#_scaled_annotated.png` — the dimensioned
    floor plan PNGs (Tab 1's visual output). The un-annotated source PNGs and
    `model.svg` are not duplicated here — they're already in `data/raw/<plan_id>/`.

## Determinations key

- `compliant_with_flags` — passes on the evidence available, with caveats noted.
- `non_compliant` — fails at least one measured requirement.
- `undetermined` — the plan view can't show what's needed (e.g. level thresholds,
  floor surfaces); the verdict names the drawing that would answer it.
- `excluded` — plan fell through to the scale fallback during Tab 1 extraction
  and was excluded from review rather than silently assessed on an estimated scale.

## Note on Tab 2 coverage

Tab 2's "run all" is capped at `VERDICT_ALL_BUDGET_USD = 2.00` (api/main.py)
so a full-dataset run can never exceed a small, fixed spend against the
configured API key. This run stopped at **20 of 101 plans** reviewed
(~$2.63 actual spend — a few workers finished concurrently right at the
threshold, slightly overshooting the $2 cap) before the remaining plans were
marked `skipped_budget` rather than run. This was a deliberate choice: full
101-plan coverage would need the endpoint called several more times (each
call resumes and covers roughly another ~20 plans under a fresh $2 cap),
for a total of roughly $10-13, and the decision was made to keep the
existing single-run safety cap rather than spend further. The remaining 81
plans have Tab 1 dimensions and annotated PNGs but no Tab 2 verdict; calling
`POST /api/verdict/all` again (with `refresh: false`, the default) will
resume and fill in more of them without re-billing what's already cached
here.
