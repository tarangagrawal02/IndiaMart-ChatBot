"""Independent commercial-safety validator.

Runs on the final reply text (including the seller's own edits), separately
from the templates that produced it. It flags statements about price, stock,
delivery, guarantees, certifications, freight and specifications that are not
backed by the seller profile.

Limitation: this is pattern matching. It cannot catch every possible way of
phrasing an unsupported claim, and it can occasionally flag a harmless
sentence. Seller review is still required before any reply is used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from smart_reply.seller import SellerProfile, parse_amount, price_numbers, units_compatible

ERROR = "error"
WARNING = "warning"


@dataclass
class Finding:
    rule: str
    severity: str
    message: str
    excerpt: str


NEGATION = re.compile(r"\b(?:cannot|can't|can not|not|unable|won't|will not|no|nahi|nahin)\b", re.IGNORECASE)
QUESTION_START = re.compile(
    r"^\s*(?:[•\-*]\s*)?(?:please\s+(?:confirm|share|let us know|tell)|could you|can you|do you|will you|would you|"
    r"is this|are you|which|what|when|where|kripya|kya)\b",
    re.IGNORECASE,
)
EXAMPLE_MARKERS = re.compile(r"\b(?:for example|e\.g\.|such as|jaise|like)\b", re.IGNORECASE)

PRICE_FIGURE = re.compile(
    r"(?:₹|\brs\.?\s*|\binr\s*)\s*(\d[\d,]*(?:\.\d+)?)"
    r"|\b(\d[\d,]*(?:\.\d+)?)\s*(?:/-|rupees|/\s*(?:kg|piece|pc|ton|mt|unit|metre|meter|bag|nos?)\b|"
    r"per\s+(?:kg|piece|pc|ton|mt|unit|metre|meter|bag)\b)",
    re.IGNORECASE,
)
VAGUE_PRICE = re.compile(
    r"\b(?:highly\s+competitive|most\s+competitive|best\s+(?:price|rate)s?|lowest\s+(?:price|rate)s?|cheapest|"
    r"special\s+discount|discounted\s+(?:price|rate))\b",
    re.IGNORECASE,
)
STOCK_CLAIM = re.compile(
    r"\b(?:in\s+stock|ready\s+stock|stock\s+(?:is\s+)?available|available\s+(?:in|with)\s+(?:us|stock)|"
    r"we\s+have\s+(?:the\s+)?(?:stock|material|\d)|can\s+(?:supply|fulfil|fulfill|provide|arrange)|"
    r"we\s+can\s+deliver|yes,?\s+we\s+can|have\s+(?:enough|sufficient)\s+(?:stock|quantity)|"
    r"current\s+stock|stock\s+(?:mein|me)\s+hai|maal\s+(?:ready|available)|supply\s+kar\s+(?:denge|sakte))\b",
    re.IGNORECASE,
)
FULL_QTY = re.compile(r"\b(?:full|entire|complete|all|whole|poora|pura)\b", re.IGNORECASE)
DELIVERY_COMMIT = re.compile(
    r"\b(?:deliver(?:ed|y)?|dispatch(?:ed)?|reach|ship(?:ped)?|supply)\b[^.?!\n]{0,40}?"
    r"\b(?:within|in|by)\s+(?:\d+|one|two|three|four|five|seven|ten)\s*(?:(?:-|to)\s*\d+\s*)?"
    r"(?:working\s+|business\s+)?(?:days?|hours?|hrs|weeks?)\b"
    r"|\b(?:deliver(?:ed|y)?|dispatch(?:ed)?|reach)\b[^.?!\n]{0,30}?\bby\s+(?:tomorrow|today|tonight|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+)\b"
    r"|\b(?:same|next)[\s-]day\s+(?:delivery|dispatch)\b"
    r"|\b\d+\s*din\s+mein\b",
    re.IGNORECASE,
)
GUARANTEE = re.compile(
    r"\b(?:guarantee[ds]?|guaranteed|assured|we\s+assure|100%\s*(?:on[\s-]*time|sure)|promise[ds]?|"
    r"commit(?:ted)?\s+to\s+deliver|pakka)\b",
    re.IGNORECASE,
)
CERT_CLAIM = re.compile(
    r"\b(isi|bis|iso\s*\d{3,5}|ce|nsic|zed)\b[^.?!\n]{0,20}\b(?:certified|marked|approved|mark|certification)\b"
    r"|\b(?:we\s+are|our\s+(?:company|products?|pipes?|material|bolts?|bars?))\s+(?:is\s+|are\s+)?(?:\w+\s+){0,2}certified\b",
    re.IGNORECASE,
)
FREIGHT_CLAIM = re.compile(
    r"\b(?:free\s+(?:delivery|shipping|transport|freight)|freight\s+(?:is\s+)?(?:included|inclusive|free)|"
    r"including\s+freight|inclusive\s+of\s+(?:gst|freight|taxes)|gst\s+(?:is\s+)?included|no\s+gst|without\s+gst)\b",
    re.IGNORECASE,
)
PRESSURE = re.compile(
    r"\b(?:order\s+now|hurry|limited\s+(?:time|stock|offer)|last\s+chance|offer\s+ends|final\s+invoice|"
    r"proceed\s+with\s+the\s+order|book\s+(?:your|the)\s+order\s+(?:now|today)|confirm\s+the\s+order\s+now)\b",
    re.IGNORECASE,
)
SPEC_CLAIM = re.compile(r"\bclass\s+[abc]\b|\b\d+(?:\.\d+)?\s*mm\s*(?:thick|thickness|wall)\b|\bfe\s*\d{3}d?\b",
                        re.IGNORECASE)
PLACEHOLDER = re.compile(r"\[[^\]\n]{1,40}\]|<[^>\n]{1,40}>|\bX{3,}\b|\{[^}\n]*\}")


def _sentences(text: str) -> list[str]:
    parts = []
    for line in text.splitlines():
        parts += [p for p in re.split(r"(?<=[.!?])\s+", line) if p.strip()]
    return parts


def _is_question(sentence: str) -> bool:
    return sentence.rstrip().endswith("?") or bool(QUESTION_START.search(sentence))


def _negated_before(sentence: str, start: int) -> bool:
    return bool(NEGATION.search(sentence[:start]))


def _numbers(text: str) -> set[float]:
    return {float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")}


def validate(text: str, seller: SellerProfile | None = None, buyer_text: str = "",
             requested_qty: float | None = None, requested_unit: str | None = None) -> list[Finding]:
    seller = seller or SellerProfile()
    findings: list[Finding] = []
    if not (text or "").strip():
        return [Finding("empty", ERROR, "The reply is empty.", "")]

    seller_text = " ".join(seller.filled().values()).lower()
    allowed_prices = set(price_numbers(seller.get("unit_price")))
    dispatch_numbers = _numbers(seller.get("dispatch_time"))
    avail, avail_unit = parse_amount(seller.get("available_quantity"))

    def add(rule, severity, message, excerpt):
        excerpt = excerpt.strip()[:160]
        if not any(f.rule == rule and f.excerpt == excerpt for f in findings):
            findings.append(Finding(rule, severity, message, excerpt))

    for s in _sentences(text):
        question = _is_question(s)

        for m in PRICE_FIGURE.finditer(s):
            value = float((m.group(1) or m.group(2)).replace(",", ""))
            if value not in allowed_prices:
                add("price", ERROR, "States a price that is not in the seller profile.", s)

        if m := VAGUE_PRICE.search(s):
            if not question:
                add("vague_price", WARNING, "Makes a price claim that cannot be checked.", s)

        if (m := STOCK_CLAIM.search(s)) and not question and not _negated_before(s, m.start()):
            if not seller.get("available_quantity"):
                add("stock", ERROR, "Claims stock or ability to supply, but no available quantity is entered.", s)
            elif avail is not None and requested_qty and units_compatible(avail_unit, requested_unit) \
                    and avail < requested_qty and re.search(r"\bcan\s+(?:supply|fulfil|fulfill|provide|deliver)", s, re.I) \
                    and (FULL_QTY.search(s) or requested_qty in _numbers(s)):
                add("stock_short", ERROR, "Claims the full quantity, but available stock is lower than requested.", s)

        if (m := DELIVERY_COMMIT.search(s)) and not _negated_before(s, m.start()):
            claimed = _numbers(m.group(0))
            if not seller.get("dispatch_time") or not claimed <= dispatch_numbers:
                add("delivery", ERROR, "Commits to a delivery time that is not in the seller profile.", s)

        if (m := GUARANTEE.search(s)) and not question and not _negated_before(s, m.start()):
            add("guarantee", ERROR, "Makes a guarantee or promise. Replies should not guarantee outcomes.", s)

        if (m := CERT_CLAIM.search(s)) and not question:
            token = (m.group(1) or "").lower().replace(" ", "")
            certs = seller.get("certifications").lower().replace(" ", "")
            if not certs or (token and token not in certs):
                add("certification", ERROR, "Claims a certification that is not in the seller profile.", s)

        if (m := FREIGHT_CLAIM.search(s)) and not question and not _negated_before(s, m.start()):
            terms = seller.get("gst_freight").lower()
            if not terms:
                add("freight", ERROR, "Makes a GST or freight claim that is not in the seller profile.", s)
            elif re.search(r"\b(?:extra|actuals?|paid\s+by\s+(?:the\s+)?buyer|to\s+pay|excluded|exclusive)\b", terms):
                add("freight", ERROR, "Contradicts the GST and freight terms in the seller profile "
                                      f"(\"{seller.get('gst_freight')}\").", s)

        if PRESSURE.search(s):
            add("pressure", WARNING, "Pushes the buyer to commit before a quotation is agreed.", s)

        if not question and not EXAMPLE_MARKERS.search(s):
            for m in SPEC_CLAIM.finditer(s):
                spec = m.group(0).lower()
                norm = re.sub(r"\s+", "", spec)
                known = re.sub(r"\s+", "", (buyer_text or "").lower() + " " + seller_text)
                if norm not in known:
                    add("spec", WARNING, "Mentions a specification that neither the buyer nor the seller provided.", s)

        if PLACEHOLDER.search(s):
            add("placeholder", WARNING, "Contains placeholder text that should be replaced.", s)

    return findings


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity == ERROR for f in findings)
