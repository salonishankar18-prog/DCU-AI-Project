"""
tgdm_index.py — turn the TGD M PDF into a searchable set of clauses.

The whole credibility of Part 2 rests on every number tracing back to this
document, so nothing here paraphrases. A clause is stored as the text that
actually sits between one numbered heading and the next, with its page, and
that text is what the model is shown.

Two practical notes about the PDF:

* The extractor sprinkles spaces inside words — "corr idor", "accou nt". Quoting
  is unaffected, but matching would be. So each clause also carries a squeezed
  copy (all whitespace removed, lowercased) and every keyword test runs against
  that. "corridor" then matches "corr idor" without any guessing.

* Clause numbering encodes scope, which matters more here than anywhere else:
      0.x  Part M generally
      1.x  buildings other than dwellings
      2.x  existing buildings other than dwellings
      3.x  dwellings
  A CubiCasa plan is a dwelling, so retrieval leans on 3.x and 0.x, but never
  suppresses the rest — the model is shown the scope of each clause and decides
  what applies.

Retrieval is keyword based, per the plan. It is easy to debug and, for a
document this size, sufficient; there are no embeddings and no vector store.
"""

import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = Path(os.getenv("TGDM_PDF", ROOT / "data" / "tgdm" / "TGD-M.pdf"))
CACHE = ROOT / "data" / "tgdm" / "tgdm_index.json"

# "1.3.3.3  Corridors and passageways", optionally behind a page number.
HEADING = re.compile(
    r"^\s*(?:\d{1,3}\s+)?"                 # page number bleeding into the line
    r"(\d\.\d+(?:\.\d+){0,2})\s+"          # clause id, at least one dot
    r"([A-Z][^\n]{2,80}?)\s*$"
)

SCOPE = {
    "0": "Part M — general application",
    "1": "Section 1 — buildings other than dwellings",
    "2": "Section 2 — existing buildings other than dwellings",
    "3": "Section 3 — dwellings",
}

STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "for", "to", "in", "on", "and", "or",
    "be", "can", "does", "do", "this", "that", "it", "with", "at", "any", "all",
    "what", "which", "how", "wide", "enough", "check", "every", "me", "my",
    "please", "tell", "about", "plan", "there", "from", "has", "have", "was",
    "if", "as", "by", "into", "not", "no", "than", "then", "so", "will",
}

# Domain vocabulary. A user asks about a "turning circle"; the document says
# "turning space". Expansion happens on the query only — the clause text is
# never rewritten.
SYNONYMS = {
    "door": ["door", "doorway", "effectiveclearwidth", "clearopening", "doorleaf"],
    "doors": ["door", "doorway", "effectiveclearwidth"],
    "width": ["width", "clearwidth", "effectiveclearwidth"],
    "turning": ["turning", "turningspace", "turningcircle", "manoeuvring"],
    "circle": ["turningspace", "turningcircle", "manoeuvring", "wheelchair"],
    "wheelchair": ["wheelchair", "turningspace", "manoeuvring"],
    "corridor": ["corridor", "passageway", "circulation"],
    "corridors": ["corridor", "passageway", "circulation"],
    "hall": ["corridor", "passageway", "circulation", "hall", "entrancehall"],
    "hallway": ["corridor", "passageway", "circulation"],
    "passage": ["corridor", "passageway", "circulation"],
    "pinch": ["corridor", "passageway", "clearwidth"],
    "bathroom": ["sanitary", "bathroom", "shower", "wc"],
    "bath": ["sanitary", "bathroom", "shower"],
    "toilet": ["wc", "sanitary", "toilet"],
    "wc": ["wc", "sanitary", "toilet"],
    "entrance": ["entrance", "accessibleentrance", "threshold"],
    "entry": ["entrance", "accessibleentrance", "entrylevel"],
    "threshold": ["threshold", "levelentry", "levelaccess"],
    "level": ["level", "levelentry", "threshold"],
    "ramp": ["ramp", "ramped", "gradient"],
    "stairs": ["stair", "stairway", "step", "going", "riser"],
    "step": ["step", "stairway", "going", "riser"],
    "socket": ["socket", "switch", "outlet"],
    "switch": ["switch", "socket", "outlet"],
    "room": ["room", "habitableroom"],
    "rooms": ["room", "habitableroom"],
    "circulation": ["circulation", "corridor", "passageway"],
    "accessible": ["accessible", "access"],
    "visitor": ["visitor", "visitable"],
    "parking": ["parking", "carparking"],
    "lift": ["lift", "passengerlift", "liftingplatform"],
    "fails": ["", ],
    "summarise": ["", ],
}

_SQUEEZE = re.compile(r"\s+")


def squeeze(s: str) -> str:
    """Lowercase with every space removed — matching survives the PDF's stray spaces."""
    return _SQUEEZE.sub("", (s or "").lower())


@dataclass
class Clause:
    clause_id: str
    heading: str
    text: str
    page: int
    scope: str

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# building the index
# ---------------------------------------------------------------------------

def _clean_line(line: str) -> str:
    s = line.rstrip()
    if not s.strip():
        return ""
    stripped = s.strip()
    if re.fullmatch(r"\d{1,3}", stripped):                  # bare page number
        return ""
    if re.fullmatch(r"[ivxlcdm]{1,6}", stripped.lower()):   # roman page number
        return ""
    if stripped.lower() in ("gov.ie/housing",):
        return ""
    return s


def build_index(pdf_path=DEFAULT_PDF, start_page=8):
    """Parse the PDF into clauses. start_page skips the cover and contents."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    clauses: list[Clause] = []
    current = None

    for pno, page in enumerate(reader.pages, start=1):
        if pno < start_page:
            continue
        raw = page.extract_text() or ""
        for line in raw.split("\n"):
            line = _clean_line(line)
            if not line:
                continue
            m = HEADING.match(line)
            if m:
                cid, heading = m.group(1), m.group(2).strip()
                # The contents pages list every heading with a dotted leader;
                # those are filtered out by start_page, but guard anyway.
                if "...." in heading:
                    continue
                current = Clause(clause_id=cid, heading=heading, text="",
                                 page=pno, scope=SCOPE.get(cid[0], "unknown"))
                clauses.append(current)
                continue
            if current is not None:
                current.text += line.strip() + " "

    for c in clauses:
        c.text = _SQUEEZE.sub(" ", c.text).strip()

    # A heading repeated in a running header can create an empty duplicate.
    seen, deduped = {}, []
    for c in clauses:
        key = c.clause_id
        if key in seen:
            prev = seen[key]
            if len(c.text) > len(prev.text):
                prev.text, prev.page = c.text, c.page
            continue
        seen[key] = c
        deduped.append(c)

    return [c for c in deduped if len(c.text) > 40]


def save_index(clauses, path=CACHE):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump([c.to_dict() for c in clauses], fh, indent=1)
    return path


def load_index(pdf_path=DEFAULT_PDF, path=CACHE, rebuild=False):
    """Cached index. Rebuilt automatically if the cache is missing or stale."""
    p = Path(path)
    if not rebuild and p.exists():
        try:
            if not Path(pdf_path).exists() or p.stat().st_mtime >= Path(pdf_path).stat().st_mtime:
                with open(p) as fh:
                    return [Clause(**d) for d in json.load(fh)]
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    if not Path(pdf_path).exists():
        return []
    clauses = build_index(pdf_path)
    save_index(clauses, p)
    return clauses


# ---------------------------------------------------------------------------
# retrieval
# ---------------------------------------------------------------------------

class TgdmIndex:
    """Keyword retrieval over the clause set."""

    def __init__(self, clauses):
        self.clauses = clauses
        self._sq_text = [squeeze(c.text) for c in clauses]
        self._sq_head = [squeeze(c.heading) for c in clauses]

    def __len__(self):
        return len(self.clauses)

    @staticmethod
    def terms(query: str) -> list[str]:
        """Query words, squeezed, with domain synonyms folded in."""
        words = re.findall(r"[a-zA-Z]+", (query or "").lower())
        out: list[str] = []
        for w in words:
            if w in STOPWORDS or len(w) < 3:
                continue
            out.append(w)
            out.extend(t for t in SYNONYMS.get(w, []) if t)
        # multi-word phrases the document actually uses
        q = squeeze(query)
        for phrase in ("effectiveclearwidth", "turningspace", "clearwidth",
                       "levelentry", "passingplace", "habitableroom",
                       "accessibleentrance", "wheelchair"):
            if phrase in q:
                out.append(phrase)
        seen, uniq = set(), []
        for t in out:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        return uniq

    def search(self, query, k=6, prefer_sections=("3", "0"), always_include=()):
        """Top-k clauses for a question.

        prefer_sections nudges dwellings guidance to the top for a dwelling plan.
        It is a ranking preference only — nothing is filtered out, and the scope
        of every returned clause is shown to the model.
        """
        terms = self.terms(query)
        scored = []
        for i, c in enumerate(self.clauses):
            head, text = self._sq_head[i], self._sq_text[i]
            score = 0.0
            for t in terms:
                if t in head:
                    score += 3.0
                hits = text.count(t)
                if hits:
                    score += min(hits, 4) * 1.0
            if score <= 0:
                continue
            if c.clause_id[0] in prefer_sections:
                score *= 1.6
            # a clause quoting a millimetre figure is usually the operative one
            if re.search(r"\d{3,4}\s*mm", c.text):
                score += 1.5
            scored.append((score, i))

        scored.sort(key=lambda s: (-s[0], self.clauses[s[1]].clause_id))
        picked = [self.clauses[i] for _, i in scored[:k]]

        for cid in always_include:
            if not any(c.clause_id == cid for c in picked):
                extra = self.get(cid)
                if extra:
                    picked.append(extra)
        return picked

    def get(self, clause_id):
        for c in self.clauses:
            if c.clause_id == clause_id:
                return c
        return None


def get_index(rebuild=False) -> TgdmIndex:
    return TgdmIndex(load_index(rebuild=rebuild))


# ---------------------------------------------------------------------------
# CLI — five sample retrievals
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    idx = get_index(rebuild="--rebuild" in sys.argv)
    print(f"\nTGD M indexed: {len(idx)} clauses from {DEFAULT_PDF.name}\n")

    by_section: dict[str, int] = {}
    for c in idx.clauses:
        by_section[c.scope] = by_section.get(c.scope, 0) + 1
    for k, v in sorted(by_section.items()):
        print(f"  {v:4d}  {k}")

    questions = [
        "What clear width does a door to a habitable room need?",
        "Can a 1500 mm wheelchair turning circle fit in the bathroom?",
        "Is the hall wide enough for a wheelchair to pass?",
        "Is the entrance threshold level and how wide must the entrance door be?",
        "Does this dwelling need an accessible WC at entry level?",
    ]
    for q in questions:
        print("\n" + "=" * 78)
        print("Q:", q)
        print("   terms:", ", ".join(idx.terms(q)[:12]))
        for c in idx.search(q, k=4):
            body = c.text[:230].replace("  ", " ")
            print(f"\n  [{c.clause_id}] {c.heading}   (p.{c.page} · {c.scope})")
            print(f"     {body}…")
    print()
