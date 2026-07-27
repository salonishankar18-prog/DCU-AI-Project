"""
agent.py — Claude judges compliance; it never measures.

The division of labour is the load-bearing decision in this project:

    rules.py   computes every dimension from the drawing geometry
    tgdm_index retrieves the verbatim clause text those dimensions are judged against
    agent.py   hands both to Claude and asks only for a judgement

So there is no threshold anywhere in this file, or in any prompt it builds. If a
number appears in an answer it came out of `rules.py` or out of the clause text,
and the clause id sits next to it. A model that invents "1500 mm" from memory is
contradicted by the clause text it was given, and the system prompt forbids
outside knowledge.

Three outcomes, never two: pass / fail / undetermined. Level thresholds, floor
surfaces and handrails are not visible in a plan view, and a tool that quietly
returns "accessible" for something it never checked is worse than one that says
it cannot tell.
"""

import json
import os
import re

from .rules import plan_geometry
from .tgdm_index import get_index

# The project plan specifies claude-sonnet-4-6. Current guidance is to default to
# the latest Opus; both are one line apart, so the model is configuration.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

SYSTEM = (
    "You review residential floor plans against Technical Guidance Document M — "
    "Access and Use (Ireland, 2022).\n\n"
    "You are given measured values extracted from the drawing, and verbatim clause "
    "text retrieved from the document. Judge only against the clause text supplied.\n\n"
    "Rules you must follow:\n"
    "1. Never estimate, infer or recall a dimension. Every measurement you quote must "
    "appear in <plan_measurements>. If a measurement you need is not there, say so.\n"
    "2. Never quote a threshold, limit or minimum that does not appear verbatim in "
    "<tgdm_clauses>. Do not rely on memory of the document.\n"
    "3. Cite the clause id for every judgement, in the form 'TGD M 3.3.2.1'.\n"
    "4. If a question cannot be answered from plan geometry alone — level thresholds, "
    "floor surfaces, handrails, lighting, gradients — say so plainly and name the "
    "drawing that would answer it (a section, an elevation, a specification note).\n"
    "5. The plan is a dwelling. Section 3 of the document covers dwellings; Sections 1 "
    "and 2 cover buildings other than dwellings. Say which scope you are applying, and "
    "do not apply a Section 1 requirement to a dwelling without noting that it is "
    "guidance for a different building type.\n"
    "6. Door widths supplied are structural clear openings measured between wall faces. "
    "The document's 'effective clear width' is measured past the open leaf and is "
    "somewhat narrower. Where that distinction changes the answer, say so.\n\n"
    "Be direct and brief. No preamble.\n\n"
    "Your answer renders in a narrow chat bubble. Use short paragraphs and bullet "
    "lists only — no markdown tables, no headings. One line per door or room."
)

VERDICT_INSTRUCTION = (
    "Produce the determination for this plan as JSON only.\n\n"
    "'determination' is one of: accessible, not_accessible, undetermined.\n"
    "Each check has:\n"
    "  item            — what was checked, in plain words\n"
    "  measured_display— the measured value exactly as it appears in the measurements, "
    "with its unit (e.g. '537 mm', '1.32 m', '18.4 m2'). Empty string if the check "
    "cannot be measured from plan geometry.\n"
    "  clause          — the TGD M clause id the judgement rests on\n"
    "  result          — pass, fail, or undetermined\n"
    "  note            — one sentence. For 'undetermined', name the drawing that "
    "would answer it.\n\n"
    "Cover, at minimum: door clear widths (the worst case), circulation/corridor "
    "width, wheelchair turning space in the sanitary facility, the accessible WC "
    "provision, and the entrance. Include an undetermined check for anything the "
    "plan view cannot show. Do not invent measurements — every measured_display must "
    "come from the supplied measurements."
)

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "determination": {
            "type": "string",
            "enum": ["accessible", "not_accessible", "undetermined"],
        },
        "summary": {"type": "string"},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "measured_display": {"type": "string"},
                    "clause": {"type": "string"},
                    "result": {
                        "type": "string",
                        "enum": ["pass", "fail", "undetermined"],
                    },
                    "note": {"type": "string"},
                },
                "required": ["item", "measured_display", "clause", "result", "note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["determination", "summary", "checks"],
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
    }


def verdict(svg_path, plan_id, plan=None):
    """Structured determination for the verdict card."""
    geo = measurements_for(svg_path, plan_id, plan=plan)

    if _excluded(geo):
        return {
            "determination": "excluded",
            "summary": (
                "Excluded from determination: the scale fell through to the "
                "convention fallback with no room-label cross-check, so the "
                "measurements cannot be relied on."
            ),
            "checks": [{
                "item": "Drawing scale",
                "measured_display": f"{geo['px_per_m']:.1f} px/m",
                "clause": "",
                "result": "undetermined",
                "note": "No room dimension label was available to verify the scale "
                        "against. A drawing with a stated scale or a dimensioned "
                        "reference would resolve it.",
            }],
            "model": None,
            "eligible": False,
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

    # The schema guarantees valid JSON, but the plan calls for defensive parsing
    # and a demo should not die on a fenced code block.
    data = _parse_json(text)
    if data is None:
        return {
            "determination": "undetermined",
            "summary": "The determination could not be parsed. The prose answer is below.",
            "checks": [],
            "raw": text,
            "model": resp.model,
            "eligible": True,
        }

    # The UI renders the clause as "TGD M {clause}", and the model tends to include
    # that prefix itself. Strip it so the chip doesn't read "TGD M TGD M 3.3.2.1".
    for check in data.get("checks", []):
        check["clause"] = re.sub(r"^\s*TGD\s*M\s*", "", str(check.get("clause") or ""),
                                 flags=re.IGNORECASE).strip()

    data["model"] = resp.model
    data["eligible"] = True
    data["clauses_used"] = [c.clause_id for c in clauses]
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
