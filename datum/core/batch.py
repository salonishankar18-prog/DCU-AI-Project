"""
batch.py — run the whole pipeline over a dataset folder.

Input layout (CubiCasa5k):
    dataset_root/
        <plan_id>/
            model.svg
            F1_original.png
            F1_scaled.png
            F2_original.png   (some plans have two floors)
            ...

Output layout — each plan keeps its original files alongside the annotated ones,
so the exported folder is self-contained:
    out_root/
        <plan_id>/
            model.svg                      (copied, unchanged)
            F1_original.png                (copied, unchanged)
            F1_original_annotated.png      (new)
            dimensions.json                (this plan's extracted measurements)
        manifest.json                      (every plan, for the review stage)
        dimensions.csv                     (one row per room, for spreadsheets)

The whole out_root then zips into a single download.
"""

import csv
import json
import os
import shutil
import traceback
import zipfile

from .svg_parse import parse_svg
from .annotate import annotate


def find_plans(dataset_root):
    """Every folder under dataset_root that contains a model.svg and at least one PNG."""
    found = []
    for dirpath, _dirnames, filenames in os.walk(dataset_root):
        if "model.svg" not in filenames:
            continue
        pngs = sorted(f for f in filenames if f.lower().endswith(".png"))
        if not pngs:
            continue
        found.append({
            "plan_id": os.path.relpath(dirpath, dataset_root).replace(os.sep, "_"),
            "dir": dirpath,
            "svg": os.path.join(dirpath, "model.svg"),
            "pngs": [os.path.join(dirpath, p) for p in pngs],
        })
    return sorted(found, key=lambda p: p["plan_id"])


def process_plan(plan_info, out_root, units="m", style="dimension_lines",
                 room_labels=True, copy_originals=True):
    """Handle one plan: parse, annotate every PNG, write its folder. Returns a record."""
    plan_id = plan_info["plan_id"]
    out_dir = os.path.join(out_root, plan_id)
    os.makedirs(out_dir, exist_ok=True)

    plan = parse_svg(plan_info["svg"], plan_id)

    if copy_originals:
        shutil.copy2(plan_info["svg"], os.path.join(out_dir, "model.svg"))

    outputs = []
    for png in plan_info["pngs"]:
        stem = os.path.splitext(os.path.basename(png))[0]
        if copy_originals:
            shutil.copy2(png, os.path.join(out_dir, os.path.basename(png)))
        result = annotate(
            plan, png, os.path.join(out_dir, f"{stem}_annotated.png"),
            units=units, style=style, room_labels=room_labels,
        )
        outputs.append(result)

    record = plan.to_dict()
    record["outputs"] = outputs
    record["status"] = "ok" if plan.scale_source != "convention_fallback_100" else "estimated"

    # Polygons are bulky and only needed by the geometry checks, so the per-plan
    # file keeps them and the shared manifest drops them.
    with open(os.path.join(out_dir, "dimensions.json"), "w") as fh:
        json.dump(record, fh, indent=2)

    return record


def run_batch(dataset_root, out_root, units="m", style="dimension_lines",
              room_labels=True, limit=None, resume=True, progress=None):
    """Process every plan under dataset_root.

    resume   — skip plans already present in the manifest, so an interrupted
               Colab session picks up where it stopped.
    progress — optional callback(done, total, plan_id, status) for the UI.
    """
    os.makedirs(out_root, exist_ok=True)
    manifest_path = os.path.join(out_root, "manifest.json")

    manifest = {}
    if resume and os.path.exists(manifest_path):
        with open(manifest_path) as fh:
            manifest = {r["plan_id"]: r for r in json.load(fh)}

    plans = find_plans(dataset_root)
    if limit:
        plans = plans[:limit]

    total = len(plans)
    for i, info in enumerate(plans, 1):
        pid = info["plan_id"]
        if resume and pid in manifest:
            if progress:
                progress(i, total, pid, "skipped")
            continue
        try:
            rec = process_plan(info, out_root, units, style, room_labels)
            status = rec["status"]
        except Exception as exc:                                   # noqa: BLE001
            rec = {
                "plan_id": pid, "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=3),
                "rooms": [], "warnings": [],
            }
            status = "failed"
        manifest[pid] = rec
        if progress:
            progress(i, total, pid, status)

        # Written every plan, not just at the end — a crash never loses work.
        _write_manifest(manifest_path, manifest)

    _write_manifest(manifest_path, manifest)
    _write_csv(os.path.join(out_root, "dimensions.csv"), manifest)

    counts = {}
    for rec in manifest.values():
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
    return {"out_root": out_root, "total": len(manifest), "counts": counts}


def _write_manifest(path, manifest):
    """Save the manifest without the heavy polygon arrays."""
    slim = []
    for rec in manifest.values():
        r = dict(rec)
        r["rooms"] = [
            {k: v for k, v in room.items() if k not in ("polygon_svg", "centroid_svg")}
            for room in rec.get("rooms", [])
        ]
        slim.append(r)
    with open(path, "w") as fh:
        json.dump(sorted(slim, key=lambda r: r["plan_id"]), fh, indent=2)


def _write_csv(path, manifest):
    """One row per room — the format most people actually want to look at."""
    cols = ["plan_id", "status", "px_per_m", "overall_width_m", "overall_depth_m",
            "internal_area_m2", "room_code", "room_name", "room_width_m",
            "room_depth_m", "room_area_m2", "is_rectangular", "outdoor"]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for rec in sorted(manifest.values(), key=lambda r: r["plan_id"]):
            base = [rec.get("plan_id"), rec.get("status"), rec.get("px_per_m"),
                    rec.get("overall_width_m"), rec.get("overall_depth_m"),
                    rec.get("internal_area_m2")]
            if not rec.get("rooms"):
                w.writerow(base + [""] * 7)
            for room in rec.get("rooms", []):
                w.writerow(base + [room.get("code"), room.get("name"),
                                   room.get("width_m"), room.get("depth_m"),
                                   room.get("area_m2"), room.get("is_rectangular"),
                                   room.get("outdoor")])


def zip_output(out_root, zip_path):
    """Package the whole output folder as one download."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _d, filenames in os.walk(out_root):
            for name in filenames:
                full = os.path.join(dirpath, name)
                z.write(full, os.path.relpath(full, out_root))
    return zip_path
