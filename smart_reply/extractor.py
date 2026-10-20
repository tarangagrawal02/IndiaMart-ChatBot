"""Deterministic requirement extraction from a buyer enquiry.

This is keyword and pattern matching, not natural-language understanding.
Each extracted value carries a status so the UI can show what was matched
reliably and what still needs confirmation. Anything not matched is reported
as missing rather than inferred.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from smart_reply import rules
from smart_reply.rules import Category, SpecRule

MAX_ENQUIRY_CHARS = 2000

CONFIRMED = "confirmed"  # matched by a specific pattern
UNCONFIRMED = "unconfirmed"  # something matched, but the reading may be wrong
MISSING = "missing"


@dataclass
class Value:
    value: str | None = None
    status: str = MISSING
    note: str = ""

    @property
    def found(self) -> bool:
        return self.value is not None


@dataclass
class Quantity(Value):
    number: float | None = None
    unit: str | None = None  # normalised unit, or None if not stated


@dataclass
class Extraction:
    raw: str
    text: str  # normalised, truncated text that rules ran on
    is_empty: bool
    truncated: bool
    category: Category
    category_status: str
    product: str  # fixed display noun from rules, never raw buyer text
    matched_keyword: str | None
    quantity: Quantity
    destination: Value
    specs: dict = field(default_factory=dict)  # spec id -> Value
    intents: set = field(default_factory=set)
    injection: list = field(default_factory=list)  # matched instruction-like snippets
    hinglish: bool = False

    def missing_specs(self) -> list[SpecRule]:
        return [s for s in self.category.specs if not self.specs[s.id].found]

    def found_specs(self) -> list[tuple[SpecRule, Value]]:
        return [(s, self.specs[s.id]) for s in self.category.specs if self.specs[s.id].found]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _clean(value: str) -> str:
    """Collapse whitespace and strip punctuation from a matched fragment."""
    value = re.sub(r"\s+", " ", value).strip(" .,;:-")
    return value


def _fmt_number(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:g}"


def normalise(text: str) -> tuple[str, bool]:
    text = (text or "").replace("\r", " ")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    truncated = len(text) > MAX_ENQUIRY_CHARS
    return text[:MAX_ENQUIRY_CHARS], truncated


def detect_category(text: str) -> tuple[Category, str, str, str | None]:
    """Return (category, status, display noun, matched keyword)."""
    best = None
    for order, cat in enumerate(rules.CATEGORIES):
        score, noun, kw, strong = 0, None, None, False
        for pattern, display in cat.strong_keywords.items():
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                score += 2
                if noun is None:
                    noun, kw, strong = display, m.group(0), True
        for pattern, display in cat.weak_keywords.items():
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                score += 1
                if noun is None:
                    noun, kw = display, m.group(0)
        if score and (best is None or score > best[0]):
            best = (score, -order, cat, noun, kw, strong)
    if best is None:
        return rules.GENERIC, MISSING, "the product", None
    _, _, cat, noun, kw, strong = best
    return cat, CONFIRMED if strong else UNCONFIRMED, noun, _clean(kw)


def _match_length(text: str) -> Value:
    """Length of each piece: accept lengths with context, or plausible piece lengths."""
    for m in rules.LENGTH_RE.finditer(text):
        number = float(m.group(1))
        unit = m.group(2).lower()
        unit = "m" if unit.startswith("m") else "ft"
        has_context = bool(m.group(3)) or "length" in m.group(0).lower()
        plausible = (unit == "m" and 1 <= number <= 15) or (unit == "ft" and 3 <= number <= 45)
        if has_context or plausible:
            return Value(f"{_fmt_number(number)} {unit}", CONFIRMED if has_context else UNCONFIRMED,
                         "" if has_context else "Read as length per piece; please check.")
    return Value()


def _match_pipe_size(text: str, rule: SpecRule) -> Value:
    for pattern in rule.patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            num = re.sub(r"\s+", "", m.group(1))
            tail = m.group(0)[len(m.group(1)):].lower()
            if "nb" in tail:
                return Value(f"{num} NB", CONFIRMED)
            if "mm" in tail:
                return Value(f"{num} mm", CONFIRMED)
            return Value(f"{num} inch", CONFIRMED)
    return Value()


def _match_spec(text: str, rule: SpecRule) -> Value:
    if rule.custom == "length":
        return _match_length(text)
    if rule.custom == "pipe_size":
        return _match_pipe_size(text, rule)
    for pattern in rule.patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = _display_case(_clean(m.group(0)))
            mm = re.search(r"(\d+(?:\.\d+)?)\s*mm", value, re.IGNORECASE)
            if rule.id == "thickness" and mm:
                value = f"{mm.group(1)} mm"
            return Value(value, CONFIRMED)
    return Value()


def _display_case(value: str) -> str:
    """Uppercase short codes (is, ss, ms, fe, hdg, mfi) for readability."""
    def fix(word: str) -> str:
        low = word.lower()
        if low in {"is", "ss", "ms", "hdg", "mfi", "nb", "gi", "dwg"}:
            return low.upper()
        if re.fullmatch(r"fe\d{3}d?", low):
            return "Fe " + low[2:].upper()
        if low == "fe":
            return "Fe"
        if re.fullmatch(r"m\d{1,2}", low):
            return low.upper()
        if low in {"class", "light", "medium", "heavy", "virgin", "recycled"}:
            return low.capitalize()
        return word
    return " ".join(fix(w) for w in value.split(" "))


def _spec_spans(text: str, category: Category) -> list[tuple[int, int]]:
    """Character spans used by size/length patterns, so they aren't read as quantity."""
    spans = []
    for rule in category.specs:
        for pattern in rule.patterns:
            spans += [m.span() for m in re.finditer(pattern, text, re.IGNORECASE)]
    spans += [m.span() for m in rules.LENGTH_RE.finditer(text)]
    spans += [m.span() for m in re.finditer(r"\b[1-9]\d{5}\b", text)]  # pincodes
    return spans


def extract_quantity(text: str, category: Category, product_kw: str | None) -> Quantity:
    spans = _spec_spans(text, category)

    def overlaps(span):
        return any(a < span[1] and span[0] < b for a, b in spans)

    unit_alt = "|".join(sorted(map(re.escape, rules.QUANTITY_UNITS), key=len, reverse=True))
    for m in re.finditer(rf"\b(\d[\d,]*(?:\.\d+)?)\s*({unit_alt})\b\.?", text, re.IGNORECASE):
        if overlaps(m.span(1)):
            continue
        number = float(m.group(1).replace(",", ""))
        unit = rules.QUANTITY_UNITS[m.group(2).lower()]
        if unit == "lengths" and number < 1:
            continue
        return Quantity(f"{_fmt_number(number)} {unit}", CONFIRMED, number=number, unit=unit)

    # "500 MS pipes", "200 nos of bolts": a number shortly before the product keyword.
    if product_kw:
        kw = re.escape(product_kw.split()[0])
        m = re.search(rf"\b(\d[\d,]*)\s+(?:[a-z]+\s+){{0,3}}?{kw}", text, re.IGNORECASE)
        if m and not overlaps(m.span(1)):
            number = float(m.group(1).replace(",", ""))
            return Quantity(_fmt_number(number), CONFIRMED, number=number, unit=None,
                            note="Unit not stated; read as number of pieces.")

    # A bare number we couldn't attach to anything is reported, not assumed.
    for m in re.finditer(r"\b(\d[\d,]*)\b", text):
        if not overlaps(m.span()) and float(m.group(1).replace(",", "")) >= 10:
            number = float(m.group(1).replace(",", ""))
            return Quantity(_fmt_number(number), UNCONFIRMED, number=number, unit=None,
                            note="A number was found but it is unclear whether it is the quantity.")
    return Quantity()


def _known_place(candidate: str) -> str | None:
    low = candidate.lower()
    for place in rules.INDIAN_CITIES + rules.STATES:
        if low == place.lower():
            return place
    return None


def extract_destination(text: str) -> Value:
    # 1. Explicit delivery phrase: "delivery in Pune", "deliver to Nashik".
    m = re.search(
        r"\b(?:deliver(?:y|ed)?|dispatch|ship(?:ping|ment)?|send|supply|site|location|destination)"
        r"\s*(?:is\s*)?(?:to|in|at|for|till|upto|up\s*to|:)\s*([A-Za-z][A-Za-z .]{1,40})",
        text,
        re.IGNORECASE,
    )
    if m:
        words = re.split(r"[\s.]+", m.group(1).strip())
        picked = []
        for w in words:
            if not w or w.lower() in rules.DESTINATION_STOPWORDS:
                break
            picked.append(w)
            if len(picked) == 3:
                break
        # Prefer the longest known place name at the start (e.g. "Navi Mumbai").
        for n in range(len(picked), 0, -1):
            place = _known_place(" ".join(picked[:n]))
            if place:
                return Value(place, CONFIRMED)
        if picked:
            guess = " ".join(picked[:2]).title()
            # fall through to the city scan first; it may find a known place elsewhere
            scan = _scan_places(text)
            if scan:
                return Value(scan, CONFIRMED)
            return Value(guess, UNCONFIRMED, "Not in the known-city list; please check the location.")

    # 2. A known city or state anywhere in the text.
    scan = _scan_places(text)
    if scan:
        return Value(scan, CONFIRMED)

    # 3. A six-digit Indian pincode.
    pin = re.search(r"\b([1-9]\d{5})\b", text)
    if pin:
        return Value(f"pincode {pin.group(1)}", CONFIRMED)
    return Value()


def _scan_places(text: str) -> str | None:
    for place in sorted(rules.INDIAN_CITIES + rules.STATES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(place)}\b", text, re.IGNORECASE):
            return place
    return None


def detect_intents(text: str) -> set:
    found = {name for name, pat in rules.INTENT_PATTERNS.items() if re.search(pat, text, re.IGNORECASE)}
    # "need ... delivery" without a timeline word still implies a timing question
    # only when combined with when/days; keep it strict otherwise.
    if "guarantee" in found and re.search(r"\b(?:quality|warranty)\b", text, re.IGNORECASE) \
            and not re.search(r"\bdeliver", text, re.IGNORECASE):
        found.discard("guarantee")
    return found


def detect_injection(text: str) -> list[str]:
    hits = []
    for pat in rules.INJECTION_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE | re.DOTALL):
            snippet = _clean(m.group(0))[:80]
            if snippet and snippet not in hits:
                hits.append(snippet)
    return hits


def detect_hinglish(text: str) -> bool:
    low = f" {text.lower()} "
    hits = sum(1 for w in rules.HINGLISH_MARKERS if re.search(rf"\b{re.escape(w)}\b", low))
    return hits >= 2


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def extract(raw: str) -> Extraction:
    text, truncated = normalise(raw)
    if not text.strip():
        return Extraction(
            raw=raw or "", text="", is_empty=True, truncated=False, category=rules.GENERIC,
            category_status=MISSING, product="the product", matched_keyword=None,
            quantity=Quantity(), destination=Value(),
            specs={s.id: Value() for s in rules.GENERIC.specs},
        )

    category, cat_status, product, kw = detect_category(text)
    specs = {rule.id: _match_spec(text, rule) for rule in category.specs}
    if category is rules.GENERIC:
        # Nothing reliable to anchor to; every generic spec stays missing.
        specs = {rule.id: Value() for rule in category.specs}

    return Extraction(
        raw=raw,
        text=text,
        is_empty=False,
        truncated=truncated,
        category=category,
        category_status=cat_status,
        product=product,
        matched_keyword=kw,
        quantity=extract_quantity(text, category, kw),
        destination=extract_destination(text),
        specs=specs,
        intents=detect_intents(text),
        injection=detect_injection(text),
        hinglish=detect_hinglish(text),
    )
