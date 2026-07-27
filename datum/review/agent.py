"""
agent.py — Claude judges compliance; it never measures, and it never does the
tolerance arithmetic either.

The division of labour is the load-bearing decision in this project:

    rules.py   computes every dimension from the drawing geometry
    tgdm_index retrieves the verbatim clause text those dimensions are judged against
    agent.py   hands both to Claude, asks for a judgement, then re-derives the
               pass/flag/fail call in Python against a fixed tolerance rule

So there is no TGD M threshold anywhere in this file, or in any prompt it builds.
If a number appears in an answer it came out of `rules.py` or out of the clause
text, and the clause id sits next to it. A model that invents "1500 mm" from
memory is contradicted by the clause text it was given, and the system prompt
forbids outside knowledge.

The compliance methodology below (tiering, categories, section applicability,
the ±25mm/±3% tolerance band) follows the TGD M compliance-checker specification:
Part M (M1-M5) is the legal requirement; TGD M's own figures are guidance, a
"deemed to satisfy" route. A dimension a little off the guidance figure is not
automatically "non-compliant" — the tolerance rule is generic drafting
tolerance, not a TGD M number, so it is safe to compute deterministically here
rather than leaving it to the model's arithmetic.

Three tiers of outcome for the plan itself: compliant / compliant with flagged
items / non-compliant — never a hard fail from anything but a Critical or
High-tier item outside tolerance. Per-check results add flag and informational
to pass/fail/undetermined, matching the same "never silently confident" rule
the old two-outcome-only design already had for level thresholds and floor
surfaces.
"""

import json
import os
import re

from .rules import plan_geometry
from .tgdm_index import get_index

# Sonnet 5 — near-Opus quality on this kind of structured judgement at Sonnet cost.
# Override with ANTHROPIC_MODEL; the model is configuration, not a code change.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

SYSTEM = (
    "You review residential floor plans against Technical Guidance Document M — "
    "Access and Use (Ireland, 2022), using the compliance-checking methodology "
    "below.\n\n"
    "You are given measured values extracted from the drawing, and verbatim clause "
    "text retrieved from the document. Judge only against the clause text supplied.\n\n"

    "CORE PRINCIPLE: Part M (M1-M5) is the actual legal requirement. TGD M's "
    "detailed dimensions are guidance — a 'deemed to satisfy' route to proving "
    "compliance, not the law itself. A dimension being slightly off the guidance "
    "figure does not automatically mean non-compliant — it may still satisfy the "
    "underlying requirement, or the discrepancy may be immaterial. Never conflate "
    "'doesn't match the guidance figure exactly' with 'fails Part M.'\n\n"

    "CLASSIFY EVERY CHECK along two axes:\n"
    "  category — 'verifiable' (a room/clearance dimension, door or corridor "
    "clear width, or presence/absence of a required room or route — the only "
    "category that can ever fail), 'not_verifiable' (door opening force, "
    "lighting levels, surface slip resistance, alarm presence, signage wording, "
    "visual contrast, gradients not shown as levels — never fails from a floor "
    "plan alone; flag as verify on site or in spec), or 'contextual' "
    "(practicability exceptions, existing-building status, transitional "
    "arrangements — informational only, never affects pass/fail).\n"
    "  tier — 'critical' (Part M itself, M1-M5, and the no-regression rule for "
    "extensions), 'high' (access-route gradient/width hierarchy, accessible "
    "entrances and doors, the wheelchair-accessible unisex WC, hazard "
    "protection on routes, vertical circulation, or — for dwellings — the "
    "visitability core package: level/ramped approach to an entrance, minimum "
    "entrance door clear width, level threshold, an accessible WC at entry "
    "level, corridor and door widths), 'medium' (entrance lobby sizing, "
    "signage/contrast/lighting levels, audible aids, parking, fitment details — "
    "never a standalone reason to fail a plan), or 'lower' (Section 2 existing-"
    "building relaxations, the practicability checklist, transitional dates, "
    "bibliography, worked examples — informational only, never affects pass/"
    "fail).\n\n"

    "For every 'verifiable' check, report measured_display (the measured value "
    "exactly as it appears in the measurements) AND required_display (the "
    "minimum or maximum figure quoted VERBATIM from the supplied clause text, "
    "with its unit) — both are needed so the pass/flag/fail arithmetic can be "
    "checked independently. Do not compute the tolerance comparison yourself; "
    "still set 'result' to your own best read as a fallback for cases where the "
    "numbers cannot be parsed.\n\n"

    "SECTION APPLICABILITY: state which TGD M section applies and why. Section "
    "1 is buildings other than dwellings (full new-build minimums); Section 2 "
    "is existing buildings other than dwellings, only when Section 1 is "
    "demonstrably impracticable; Section 3 is dwellings (a lighter visitability "
    "standard). Every plan in this dataset is a dwelling, so Section 3 applies "
    "unless the clause text you were given says otherwise — applying Section "
    "1's full minimums to a dwelling by default is a common cause of false "
    "failures.\n\n"

    "Rules you must follow:\n"
    "1. Never estimate, infer or recall a dimension. Every measurement you quote "
    "must appear in <plan_measurements>. If a measurement you need is not there, "
    "say so.\n"
    "2. Never quote a threshold, limit or minimum that does not appear verbatim "
    "in <tgdm_clauses>. Do not rely on memory of the document.\n"
    "3. Cite the clause id for every judgement, in the form 'TGD M 3.3.2.1'.\n"
    "4. If a question cannot be answered from plan geometry alone — level "
    "thresholds, floor surfaces, handrails, lighting, gradients not drawn as "
    "levels — classify it 'not_verifiable' and name the drawing that would "
    "answer it (a section, an elevation, a specification note). Don't assume "
    "something not shown on the drawing is missing from the building.\n"
    "5. Door widths supplied are structural clear openings measured between "
    "wall faces. The document's 'effective clear width' is measured past the "
    "open leaf and is somewhat narrower. Where that distinction changes the "
    "answer, say so.\n"
    "6. A plan should only ever be marked non-compliant because of a Critical "
    "or High-tier item genuinely unmet outside tolerance. Medium and Lower tier "
    "findings are always flagged alongside an otherwise-passing result, never "
    "grounds for outright rejection.\n\n"

    "Be direct and brief. No preamble.\n\n"
    "Your answer renders in a narrow chat bubble. Use short paragraphs and "
    "bullet lists only — no markdown tables, no headings. One line per door or "
    "room."
)

VERDICT_INSTRUCTION = (
    "Produce the determination for this plan as JSON only, following the "
    "classification rules in the system prompt.\n\n"
    "'applicable_section' is the TGD M section that applies (usually '3' for a "
    "dwelling) and 'section_reason' says why, in one sentence.\n\n"
    "'determination' is your own first-pass read — 'compliant', "
    "'compliant_with_flags', or 'non_compliant' — based on the checks you "
    "produce. The final determination is recomputed deterministically from "
    "your checks afterward, so treat this as a draft, not the final word.\n\n"
    "Each check has:\n"
    "  item             — what was checked, in plain words\n"
    "  category         — verifiable | not_verifiable | contextual\n"
    "  tier             — critical | high | medium | lower\n"
    "  measured_display — the measured value exactly as it appears in the "
    "measurements, with its unit (e.g. '537 mm', '1.32 m', '18.4 m2'). Empty "
    "string if the check cannot be measured from plan geometry.\n"
    "  required_display — the minimum/maximum figure quoted verbatim from the "
    "clause text, with its unit (e.g. '800 mm'). Empty string if the clause "
    "gives no single figure to compare against.\n"
    "  clause           — the TGD M clause id the judgement rests on\n"
    "  result           — pass, flag, fail, undetermined, or informational — "
    "your own best read; a fixed tolerance rule may override this for "
    "verifiable checks with parseable measured/required figures\n"
    "  note             — one sentence. For 'undetermined' or "
    "'not_verifiable', name the drawing that would answer it.\n\n"
    "Cover, at minimum: door clear widths (the worst case), circulation/"
    "corridor width, wheelchair turning space in the sanitary facility, the "
    "accessible WC provision, and the entrance. Include a check for anything "
    "the plan view cannot show, classified 'not_verifiable'. Do not invent "
    "measurements — every measured_display must come from the supplied "
    "measurements."
)

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "applicable_section": {"type": "string", "enum": ["1", "2", "3"]},
        "section_reason": {"type": "string"},
        "determination": {
            "type": "string",
            "enum": ["compliant", "compliant_with_flags", "non_compliant"],
        },
        "summary": {"type": "string"},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["verifiable", "not_verifiable", "contextual"],
                    },
                    "tier": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "lower"],
                    },
                    "measured_display": {"type": "string"},
                    "required_display": {"type": "string"},
                    "clause": {"type": "string"},
                    "result": {
                        "type": "string",
                        "enum": ["pass", "flag", "fail", "undetermined", "informational"],
                    },
                    "note": {"type": "string"},
                },
                "required": ["item", "category", "tier", "measured_display",
                             "required_display", "clause", "result", "note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["applicable_section", "section_reason", "determination", "summary", "checks"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# client
# ---------------------------------------------------------------------------

class NotConfigured(RuntimeError):
    """No API key. Tab 1 still works; Tab 2 says so instead of failing obscurely."""


def _client():
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key or key.startswith("sk-ant-your-key"):
        raise NotConfigured(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key, "
            "then restart the server. Tab 1 does not need it."
        )
    import anthropic
    return anthropic.Anthropic(api_key=key)


# ---------------------------------------------------------------------------
# cost — every Claude call is priced from its own usage block, not guessed
# ---------------------------------------------------------------------------

# USD per million tokens. Sonnet 5 has an introductory rate through 2026-08-31;
# priced here at the standard post-intro rate so the cost shown — and the
# spend cap below — is a conservative (slightly high) estimate rather than one
# that goes stale the day the intro pricing ends.
_PRICE_PER_MTOK = {
    "claude-sonnet-5": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30},
}
_DEFAULT_PRICE = {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30}


def _cost_usd(usage, model):
    """Turn one response's `usage` block into token counts and a USD estimate."""
    price = _PRICE_PER_MTOK.get(model, _DEFAULT_PRICE)
    input_tok = getattr(usage, "input_tokens", 0) or 0
    output_tok = getattr(usage, "output_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cost = (
        input_tok * price["input"]
        + output_tok * price["output"]
        + cache_write * price["cache_write"]
        + cache_read * price["cache_read"]
    ) / 1_000_000
    return {
        "model": model,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "cache_creation_input_tokens": cache_write,
        "cache_read_input_tokens": cache_read,
        "total_tokens": input_tok + output_tok + cache_write + cache_read,
        "cost_usd": round(cost, 6),
    }


# ---------------------------------------------------------------------------
# context assembly
# ---------------------------------------------------------------------------

def measurements_for(svg_path, plan_id, plan=None):
    """Everything Python measured, ready to go in the prompt."""
    return plan_geometry(svg_path, plan_id, plan=plan)


def _clause_block(clauses):
    parts = []
    for c in clauses:
        parts.append(
            f"<clause id=\"{c.clause_id}\" heading=\"{c.heading}\" "
            f"page=\"{c.page}\" scope=\"{c.scope}\">\n{c.text}\n</clause>"
        )
    return "\n\n".join(parts)


def _trim_measurements(geo):
    """Drop the bulky fields the model does not need to judge with."""
    slim = dict(geo)
    slim["rooms"] = [
        {k: v for k, v in r.items() if k not in ("circle_centre_svg",)}
        for r in geo.get("rooms", [])
    ]
    slim["doors"] = [
        {k: v for k, v in d.items() if k not in ("centre_svg",)}
        for d in geo.get("doors", [])
    ]
    return slim


def retrieve(question, k=6):
    idx = get_index()
    if not len(idx):
        return []
    # 3.3.2.1 carries Table 5 (door widths and corridor widths for dwellings) and
    # 3.4.2 the accessible WC. They are the operative dwelling clauses for almost
    # any geometric question, so they are always on the table.
    return idx.search(question, k=k, always_include=("3.3.2.1", "3.4.2"))


# ---------------------------------------------------------------------------
# rendering — the measurement-ink rule, enforced in code
# ---------------------------------------------------------------------------

# A real-world distance or area. Anything matching becomes orange; nothing else does.
_MEASURE = re.compile(
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(mm|cm|m²|m2|m\b|metres|meters)(?![\w])",
    re.IGNORECASE,
)
_CLAUSE_REF = re.compile(r"\bTGD\s*M\s*(\d(?:\.\d+){0,3})\b", re.IGNORECASE)


def to_html(text):
    """Render the model's answer for the chat bubble.

    Light markdown only, then the colour rule: every real-world distance or area
    is wrapped in measurement ink, and every clause id in a reference chip. The
    model is never asked to emit HTML, so it cannot paint something orange that
    is not a measurement.
    """
    def esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    lines = esc(text).split("\n")
    out, in_list = [], False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if stripped.startswith(("- ", "* ", "• ")):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{stripped[2:].strip()}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<p>{stripped}</p>")
    if in_list:
        out.append("</ul>")

    html = "".join(out)
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    html = _CLAUSE_REF.sub(lambda m: f'<span class="ref">TGD M {m.group(1)}</span>', html)
    html = _MEASURE.sub(
        lambda m: f'<span class="measure-sm">{m.group(1)} '
                  f'{"m²" if m.group(2).lower() in ("m2", "m²") else m.group(2)}</span>',
        html)
    return html


# ---------------------------------------------------------------------------
# tolerance — the compliance-checker's arithmetic, done in Python so it is
# verifiable rather than trusted from the model's own text
# ---------------------------------------------------------------------------

_MM_VALUE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(mm|cm|m)\b", re.IGNORECASE)
_MM_PER_UNIT = {"mm": 1.0, "cm": 10.0, "m": 1000.0}


def _to_mm(display):
    """Parse a measurement string like '537 mm', '1.2 m', '85 cm' into millimetres."""
    if not display:
        return None
    m = _MM_VALUE.search(display)
    if not m:
        return None
    return float(m.group(1).replace(",", "")) * _MM_PER_UNIT[m.group(2).lower()]


def _apply_tolerance(check):
    """Greater of ±25 mm or ±3% against the stated minimum, measured value
    rounded to the nearest 5 mm before comparing. Within tolerance is a pass;
    within 2x the tolerance band is a flag, never a fail; only Critical/High
    tier items outside both bands can fail. Assumes required_display is a
    stated minimum, which covers every check this dataset produces (door and
    corridor clear widths, turning circles, WC clearances) — this app has no
    maximum-type checks (e.g. a threshold height ceiling).
    """
    category = check.get("category") or "verifiable"
    tier = check.get("tier") or "high"

    if category == "contextual":
        check["result"] = "informational"
        return check

    if category == "not_verifiable":
        # Category B can flag "verify on site" but never hard-fail a plan.
        if check.get("result") == "fail":
            check["result"] = "flag"
        return check

    measured_mm = _to_mm(check.get("measured_display"))
    required_mm = _to_mm(check.get("required_display"))
    if measured_mm is None or required_mm is None:
        # Can't verify the arithmetic ourselves — trust the model's read, but
        # Medium/Lower tier items still may never fail outright.
        if check.get("result") == "fail" and tier not in ("critical", "high"):
            check["result"] = "flag"
        return check

    measured_mm = round(measured_mm / 5.0) * 5.0
    band = max(25.0, required_mm * 0.03)
    shortfall = required_mm - measured_mm
    if shortfall <= band:
        check["result"] = "pass"
    elif shortfall <= 2 * band:
        check["result"] = "flag"
    else:
        check["result"] = "fail" if tier in ("critical", "high") else "flag"
    check["tolerance_band_mm"] = round(band, 1)
    return check


def _overall_determination(checks):
    """Non-compliant only from a Critical/High-tier verifiable check that fails
    outside tolerance. Everything else that isn't a clean pass is a flag.
    """
    hard_fail = any(
        (c.get("category") or "verifiable") == "verifiable"
        and (c.get("tier") or "high") in ("critical", "high")
        and c.get("result") == "fail"
        for c in checks
    )
    if hard_fail:
        return "non_compliant"
    # A 'fail' that didn't qualify as a hard fail (wrong tier/category) still
    # deserves a flag rather than being silently dropped.
    flagged = any(c.get("result") in ("flag", "undetermined", "fail") for c in checks)
    return "compliant_with_flags" if flagged else "compliant"


# ---------------------------------------------------------------------------
# the two calls
# ---------------------------------------------------------------------------

def _excluded(geo):
    """A plan on the scale fallback is flagged, not silently reviewed."""
    return not geo.get("eligible_for_determination", True)


def answer_question(svg_path, plan_id, question, history=None, plan=None):
    """Free-text review answer with real clause citations."""
    client = _client()
    geo = measurements_for(svg_path, plan_id, plan=plan)
    clauses = retrieve(question)

    prefix = ""
    if _excluded(geo):
        prefix = (
            "NOTE: this plan's scale fell through to the convention fallback with no "
            "room-label cross-check. Its measurements are not reliable. Answer the "
            "question but state plainly at the start that no determination can be "
            "made for this plan.\n\n"
        )

    user = (
        f"{prefix}"
        f"<plan_measurements>\n{json.dumps(_trim_measurements(geo), indent=2)}\n</plan_measurements>\n\n"
        f"<tgdm_clauses>\n{_clause_block(clauses)}\n</tgdm_clauses>\n\n"
        f"<question>{question}</question>"
    )

    messages = []
    for turn in (history or [])[-6:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    if messages and messages[0]["role"] != "user":
        messages = messages[1:]
    messages.append({"role": "user", "content": user})

    resp = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=messages,
    )

    if resp.stop_reason == "refusal":
        raise RuntimeError("the model declined to answer this request")

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return {
        "answer": text,
        "html": to_html(text),
        "clauses_used": [c.clause_id for c in clauses],
        "model": resp.model,
        "eligible": not _excluded(geo),
        "usage": _cost_usd(resp.usage, resp.model),
    }


def verdict(svg_path, plan_id, plan=None):
    """Structured determination for the verdict card."""
    geo = measurements_for(svg_path, plan_id, plan=plan)

    if _excluded(geo):
        return {
            "determination": "excluded",
            "applicable_section": "",
            "section_reason": "",
            "summary": (
                "Excluded from determination: the scale fell through to the "
                "convention fallback with no room-label cross-check, so the "
                "measurements cannot be relied on."
            ),
            "checks": [{
                "item": "Drawing scale",
                "category": "verifiable",
                "tier": "critical",
                "measured_display": f"{geo['px_per_m']:.1f} px/m",
                "required_display": "",
                "clause": "",
                "result": "undetermined",
                "note": "No room dimension label was available to verify the scale "
                        "against. A drawing with a stated scale or a dimensioned "
                        "reference would resolve it.",
            }],
            "model": None,
            "eligible": False,
            "usage": None,
        }

    client = _client()

    # One retrieval per theme, so the model sees the clause behind every check it
    # is asked to make rather than whichever clauses one query happened to surface.
    seen, clauses = set(), []
    for q in (
        "minimum effective clear width of doors to habitable rooms in a dwelling",
        "minimum unobstructed corridor and passageway width in a dwelling",
        "wheelchair turning space and clear space beside the WC in a dwelling",
        "accessible WC at entry level in a dwelling",
        "accessible entrance, level threshold and entrance door clear width for a dwelling",
    ):
        for c in retrieve(q, k=4):
            if c.clause_id not in seen:
                seen.add(c.clause_id)
                clauses.append(c)

    user = (
        f"<plan_measurements>\n{json.dumps(_trim_measurements(geo), indent=2)}\n</plan_measurements>\n\n"
        f"<tgdm_clauses>\n{_clause_block(clauses)}\n</tgdm_clauses>\n\n"
        f"<task>{VERDICT_INSTRUCTION}</task>"
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": VERDICT_SCHEMA}},
    )

    if resp.stop_reason == "refusal":
        raise RuntimeError("the model declined to produce a determination")

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    usage = _cost_usd(resp.usage, resp.model)

    # The schema guarantees valid JSON, but the plan calls for defensive parsing
    # and a demo should not die on a fenced code block.
    data = _parse_json(text)
    if data is None:
        return {
            "determination": "undetermined",
            "applicable_section": "",
            "section_reason": "",
            "summary": "The determination could not be parsed. The prose answer is below.",
            "checks": [],
            "raw": text,
            "model": resp.model,
            "eligible": True,
            "usage": usage,
        }

    # The UI renders the clause as "TGD M {clause}", and the model tends to include
    # that prefix itself. Strip it so the chip doesn't read "TGD M TGD M 3.3.2.1".
    for check in data.get("checks", []):
        check["clause"] = re.sub(r"^\s*TGD\s*M\s*", "", str(check.get("clause") or ""),
                                 flags=re.IGNORECASE).strip()
        _apply_tolerance(check)

    # The model's own 'determination' is a first-pass read; recompute the final
    # call deterministically from the (now tolerance-checked) checks so the
    # pass/flag/fail arithmetic is verifiable, not just trusted from the prose.
    data["determination"] = _overall_determination(data.get("checks", []))

    data["model"] = resp.model
    data["eligible"] = True
    data["clauses_used"] = [c.clause_id for c in clauses]
    data["usage"] = usage
    return data


def _parse_json(text):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None
