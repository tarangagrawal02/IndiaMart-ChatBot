"""Reply composer: the common interface behind every prompt version.

``generate_reply`` takes the buyer enquiry, the seller profile, a prompt
version and a style, and returns the reply plus everything the UI needs to
explain it: a missing-information list with statuses, the reasoning, and the
validator findings.

Version behaviour (simulated prompt engineering - no LLM is called):
  v1  Basic prompt. Reproduces the typical failure mode of an unconstrained
      model: polite, but invents capability, delivery time and price claims.
      Used only in the Prompt Lab, where the validator flags it.
  v2  Specific and commercially aware. Acknowledges the requirement, asks for
      the missing specifications, invents nothing. Ignores seller data.
  v3  Seller-ready. Adds verified seller facts, plain-English bullets for
      mobile chat, domain hints, language/tone control and a clear next step.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from smart_reply import rules
from smart_reply.extractor import CONFIRMED, UNCONFIRMED, Extraction, detect_category, extract
from smart_reply.seller import (
    FIELD_LABELS,
    SellerProfile,
    coverage_includes,
    format_price,
    parse_amount,
    price_has_unit,
    specs_differ,
    units_compatible,
)
from smart_reply.validator import Finding, validate

VERSIONS = ("v1", "v2", "v3")

# Item statuses shown in the Missing information panel.
BUYER = "buyer"  # confirmed from buyer enquiry
SELLER = "seller"  # confirmed from seller input
CHECK = "check"  # needs seller confirmation
MISSING = "missing"  # missing information - asked in the reply
OPTIONAL = "optional"  # seller detail not entered (would strengthen the reply)

STATUS_LABELS = {
    BUYER: "From buyer enquiry",
    SELLER: "Confirmed from seller input",
    CHECK: "Needs seller confirmation",
    MISSING: "Missing information",
    OPTIONAL: "Seller detail not entered",
}


@dataclass(frozen=True)
class ReplyStyle:
    language: str = "english"  # "english" | "hinglish"
    tone: str = "simple"  # "simple" | "professional"
    length: str = "standard"  # "standard" | "short"
    extra_questions: bool = False

    @property
    def key(self) -> str:
        return "hinglish" if self.language == "hinglish" else self.tone


@dataclass
class Item:
    status: str
    label: str
    detail: str = ""


@dataclass
class ReplyResult:
    text: str
    version: str
    style: ReplyStyle
    extraction: Extraction
    items: list = field(default_factory=list)
    rationale: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    facts_used: list = field(default_factory=list)
    elapsed_ms: float = 0.0
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


# --------------------------------------------------------------------------
# Phrasebook. Keys: simple / professional / hinglish.
# --------------------------------------------------------------------------

P = {
    "greeting": {"simple": "Hello,", "professional": "Dear Sir/Madam,", "hinglish": "Namaste,"},
    "thanks": {
        "simple": "Thank you for your enquiry.",
        "professional": "Thank you for your enquiry and for considering us.",
        "hinglish": "Aapki enquiry ke liye dhanyavaad.",
    },
    "understand": {
        "simple": "We understand you need {summary}.",
        "professional": "We understand that you require {summary}.",
        "hinglish": "Aapko {summary} chahiye.",
    },
    "dest": {"simple": " for delivery in {dest}", "professional": " for delivery to {dest}",
             "hinglish": ", delivery {dest} mein"},
    "asked_price_delivery": {
        "simple": "You have asked for our rate and delivery time.",
        "professional": "We note that you have requested our rate and the delivery timeline.",
        "hinglish": "Aapne rate aur delivery time poocha hai.",
    },
    "asked_price": {
        "simple": "You have asked for our rate.",
        "professional": "We note that you have requested our rate.",
        "hinglish": "Aapne rate poocha hai.",
    },
    "asked_delivery": {
        "simple": "You have asked for the delivery time.",
        "professional": "We note that you have requested the delivery timeline.",
        "hinglish": "Aapne delivery time poocha hai.",
    },
    "facts_intro": {"simple": "From our side:", "professional": "Our details:", "hinglish": "Hamari taraf se:"},
    "fact_price": {
        "simple": "Current rate: {price} (final rate depends on the specification you confirm)",
        "professional": "Current rate: {price}, subject to the final specification",
        "hinglish": "Current rate: {price} (final rate specification par depend karega)",
    },
    "fact_stock": {"simple": "Current stock: {qty}", "professional": "Current stock: {qty}",
                   "hinglish": "Current stock: {qty}"},
    "fact_stock_short": {
        "simple": "Current stock: {qty}. For the balance quantity, we will confirm availability",
        "professional": "Current stock: {qty}. Availability of the balance quantity will be confirmed",
        "hinglish": "Current stock: {qty}. Baaki quantity ki availability hum confirm karenge",
    },
    "fact_moq": {"simple": "Minimum order: {moq}", "professional": "Minimum order quantity: {moq}",
                 "hinglish": "Minimum order: {moq}"},
    "fact_dispatch_from": {"simple": "Dispatch from: {loc}", "professional": "Dispatch location: {loc}",
                           "hinglish": "Dispatch: {loc} se"},
    "fact_dispatch_time": {"simple": "Usual dispatch time: {t}", "professional": "Usual dispatch time: {t}",
                           "hinglish": "Usual dispatch time: {t}"},
    "fact_coverage_yes": {"simple": "We deliver to {dest}", "professional": "We supply to {dest}",
                          "hinglish": "Hum {dest} mein delivery karte hain"},
    "fact_coverage_check": {
        "simple": "We will check transport options for {dest}",
        "professional": "We will check transport options to {dest}",
        "hinglish": "{dest} ke liye transport options hum check karenge",
    },
    "fact_gst": {"simple": "GST and freight: {v}", "professional": "GST and freight: {v}",
                 "hinglish": "GST aur freight: {v}"},
    "fact_gst_tbc": {
        "simple": "GST and freight will be confirmed in the quotation",
        "professional": "Applicable GST and freight will be confirmed in the quotation",
        "hinglish": "GST aur freight quotation mein confirm karenge",
    },
    "fact_payment": {"simple": "Payment terms: {v}", "professional": "Payment terms: {v}",
                     "hinglish": "Payment terms: {v}"},
    "fact_certs": {"simple": "Certifications: {v}", "professional": "Certifications: {v}",
                   "hinglish": "Certifications: {v}"},
    "no_guarantee": {
        "simple": "We cannot promise a fixed delivery date right now. We will confirm the delivery time with our quotation.",
        "professional": "We are not able to commit to a fixed delivery date at this stage; the delivery schedule will be confirmed with our quotation.",
        "hinglish": "Abhi hum koi fixed delivery date nahi bata sakte. Delivery time quotation ke saath confirm karenge.",
    },
    "ask_intro": {
        "simple": "To share an exact price and delivery time, please confirm:",
        "professional": "To prepare an accurate quotation, please confirm the following:",
        "hinglish": "Sahi rate aur delivery time batane ke liye, kripya yeh confirm karein:",
    },
    "offer": {
        "simple": "{label}: we offer {value}. Please confirm if this works, or share the one you need",
        "professional": "{label}: we offer {value}. Please confirm whether this meets your requirement",
        "hinglish": "{label}: hamare paas {value} hai. Kripya batayein ki yeh chalega ya aapko kaunsa chahiye",
    },
    "ask_quantity": {"simple": "Quantity you need", "professional": "Required quantity",
                     "hinglish": "Kitni quantity chahiye"},
    "ask_quantity_unit": {
        "simple": "Quantity and unit (for example pieces or tons)",
        "professional": "Required quantity and unit (e.g. pieces, tons)",
        "hinglish": "Quantity aur unit (jaise pieces ya tons)",
    },
    "ask_dest": {"simple": "Delivery location (city or pincode)", "professional": "Delivery location (city / pincode)",
                 "hinglish": "Delivery location (city ya pincode)"},
    "ask_dest_check": {
        "simple": "Delivery location (we read it as {dest}; please confirm)",
        "professional": "Delivery location (we have read this as {dest}; kindly confirm)",
        "hinglish": "Delivery location (humne {dest} samjha hai; kripya confirm karein)",
    },
    "next_with_q": {
        "simple": "Once you share these details, we will send our quotation with price and delivery time.",
        "professional": "On receipt of these details, we will share our quotation with the price and delivery schedule.",
        "hinglish": "Yeh details milte hi hum price aur delivery time ke saath quotation bhejenge.",
    },
    "next_no_q": {
        "simple": "We will prepare the quotation and share it with you. Please let us know if you have any questions.",
        "professional": "We will prepare our quotation and share it with you. Please let us know if you need any further information.",
        "hinglish": "Hum quotation bana kar aapko bhejenge. Koi sawal ho to zaroor batayein.",
    },
    "extra_intro": {"simple": "It will also help to know:", "professional": "In addition, it would help to know:",
                    "hinglish": "Yeh bhi bata dein to madad hogi:"},
    "closing": {"simple": "Thank you,", "professional": "Regards,", "hinglish": "Dhanyavaad,"},
    "closing_bare": {"simple": "Thank you.", "professional": "Regards.", "hinglish": "Dhanyavaad."},
    # short mode
    "short_open": {
        "simple": "Thank you for your enquiry for {summary}.",
        "professional": "Thank you for your enquiry for {summary}.",
        "hinglish": "{summary} ki enquiry ke liye dhanyavaad.",
    },
    "short_ask": {
        "simple": "Please confirm {items} so we can send an exact quote.",
        "professional": "Please confirm {items} so that we can share an accurate quotation.",
        "hinglish": "Kripya {items} confirm karein, phir hum sahi quote bhejenge.",
    },
    "short_next": {
        "simple": "We will then share the price and delivery time.",
        "professional": "We will then share the price and delivery schedule.",
        "hinglish": "Uske baad hum price aur delivery time batayenge.",
    },
}


def _p(name: str, style: ReplyStyle, **kw) -> str:
    return P[name][style.key].format(**kw)


def _join(items: list[str], lang: str = "english") -> str:
    conj = "aur" if lang == "hinglish" else "and"
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    oxford = "," if lang != "hinglish" else ""
    return ", ".join(items[:-1]) + f"{oxford} {conj} " + items[-1]


# --------------------------------------------------------------------------
# Summary of the buyer's requirement (built only from fixed nouns and
# pattern-matched values, never from free buyer text).
# --------------------------------------------------------------------------

def _quantity_phrase(ex: Extraction) -> str:
    q = ex.quantity
    if not q.found or q.status != CONFIRMED:
        return ""
    num = q.value.split()[0]
    if q.unit in (None, *rules.COUNT_UNITS):
        return num
    return f"{num} {q.unit} of"


def _spec_phrases(ex: Extraction, hyphen_size: bool = False) -> list[str]:
    out = []
    for rule, value in ex.found_specs():
        text = rule.display.format(value=value.value)
        if hyphen_size and rule.id == "size" and ex.category.id == "ms_pipe" and value.value.endswith("inch"):
            text = value.value.replace(" inch", "-inch") + " diameter"
        out.append(text)
    return out


def summary(ex: Extraction, style: ReplyStyle, with_dest: bool = True, v2: bool = False) -> str:
    product = ex.product if ex.category is not rules.GENERIC else "your requirement"
    if ex.category is rules.GENERIC and not ex.quantity.found:
        product = "the product you mentioned" if style.language != "hinglish" else "aapka product"
    qty = _quantity_phrase(ex)
    head = f"{qty} {product}".strip()
    specs = _spec_phrases(ex, hyphen_size=v2)
    if specs:
        if v2 and len(specs) == 1 and specs[0].endswith("diameter"):
            head += f" of {specs[0]}"
        else:
            head += " (" + ", ".join(specs) + ")"
    if with_dest and ex.destination.found and ex.destination.status == CONFIRMED:
        head += _p("dest", style, dest=ex.destination.value)
    return head


# --------------------------------------------------------------------------
# Seller fact checks
# --------------------------------------------------------------------------

@dataclass
class SellerAnalysis:
    facts: list = field(default_factory=list)  # (fact_key, kwargs, item label)
    items: list = field(default_factory=list)
    offers: dict = field(default_factory=dict)  # spec id -> seller value to offer
    product_mismatch: bool = False
    size_mismatch: bool = False


def analyse_seller(ex: Extraction, seller: SellerProfile, style: ReplyStyle) -> SellerAnalysis:
    a = SellerAnalysis()
    if seller.is_empty():
        return a

    # Does the seller's product match the enquiry?
    if seller.get("product_name") and ex.category is not rules.GENERIC:
        seller_cat, seller_status, _, _ = detect_category(seller.get("product_name"))
        if seller_cat is not rules.GENERIC and seller_cat.id != ex.category.id:
            a.product_mismatch = True
            a.items.append(Item(CHECK, "Seller product doesn't match the enquiry",
                                f"Your product is \"{seller.get('product_name')}\" but the buyer asked for "
                                f"{ex.product}. Product-specific facts (rate, stock, grade) were left out of the reply."))

    # Buyer size vs seller size.
    buyer_size = ex.specs.get("size")
    if buyer_size and buyer_size.found and seller.get("size") and specs_differ(buyer_size.value, seller.get("size")):
        a.size_mismatch = True
        a.items.append(Item(CHECK, "Size differs from your profile",
                            f"Buyer asked for {buyer_size.value}; your profile says {seller.get('size')}. "
                            "Rate and stock were left out because they may be for a different size."))

    product_facts_ok = not (a.product_mismatch or a.size_mismatch)

    # Offers: seller values for specs the buyer did not give.
    if product_facts_ok:
        for rule in ex.missing_specs():
            if rule.seller_field and seller.get(rule.seller_field):
                a.offers[rule.id] = seller.get(rule.seller_field)
                a.items.append(Item(SELLER, f"{rule.label} offered",
                                    f"{seller.get(rule.seller_field)} (buyer asked to confirm)"))

    # Price
    price = seller.get("unit_price")
    if price and product_facts_ok:
        if price_has_unit(price):
            a.facts.append(("fact_price", {"price": format_price(price)}, "Unit price"))
        else:
            a.items.append(Item(CHECK, "Price unit missing",
                                f"\"{price}\" has no unit (per kg, per piece...). Add the unit to include it in the reply."))
    elif not price:
        a.items.append(Item(OPTIONAL, "Unit price", "Not entered, so the reply asks for details instead of quoting."))

    # Stock
    avail_txt = seller.get("available_quantity")
    avail, avail_unit = parse_amount(avail_txt)
    req, req_unit = ex.quantity.number, ex.quantity.unit
    if avail_txt and product_facts_ok:
        if avail is not None and req and units_compatible(avail_unit, req_unit):
            if avail < req:
                a.facts.append(("fact_stock_short", {"qty": avail_txt}, "Available quantity"))
                a.items.append(Item(CHECK, "Stock below requested quantity",
                                    f"You have {avail_txt}; buyer needs {ex.quantity.value}. "
                                    "The reply does not promise the full quantity."))
            else:
                a.facts.append(("fact_stock", {"qty": avail_txt}, "Available quantity"))
        else:
            a.facts.append(("fact_stock", {"qty": avail_txt}, "Available quantity"))
            if req and avail is not None and not units_compatible(avail_unit, req_unit):
                a.items.append(Item(CHECK, "Stock and request use different units",
                                    f"Stock is \"{avail_txt}\", request is {ex.quantity.value}. Check before sending."))
    elif not avail_txt:
        a.items.append(Item(OPTIONAL, "Available quantity", "Not entered, so the reply makes no stock claim."))

    # MOQ
    moq_txt = seller.get("moq")
    if moq_txt:
        a.facts.append(("fact_moq", {"moq": moq_txt}, "Minimum order quantity"))
        moq, moq_unit = parse_amount(moq_txt)
        if moq is not None and req and units_compatible(moq_unit, req_unit) and moq > req:
            a.items.append(Item(CHECK, "Request is below your MOQ",
                                f"Buyer needs {ex.quantity.value}; your MOQ is {moq_txt}."))
        if moq is not None and avail is not None and units_compatible(moq_unit, avail_unit) and moq > avail:
            a.items.append(Item(CHECK, "Seller details conflict",
                                f"MOQ ({moq_txt}) is higher than available quantity ({avail_txt}). Please correct one of them."))

    # Dispatch and delivery
    if seller.get("dispatch_location"):
        a.facts.append(("fact_dispatch_from", {"loc": seller.get("dispatch_location")}, "Dispatch location"))
    if seller.get("dispatch_time"):
        a.facts.append(("fact_dispatch_time", {"t": seller.get("dispatch_time")}, "Estimated dispatch time"))
    else:
        a.items.append(Item(OPTIONAL, "Estimated dispatch time", "Not entered, so no delivery time is stated."))

    dest = ex.destination.value if ex.destination.status == CONFIRMED else None
    cov = coverage_includes(seller.get("delivery_coverage"), dest)
    if cov is True:
        a.facts.append(("fact_coverage_yes", {"dest": dest}, "Delivery coverage"))
    elif cov is False:
        a.facts.append(("fact_coverage_check", {"dest": dest}, "Delivery coverage"))
        a.items.append(Item(CHECK, "Destination outside listed coverage",
                            f"{dest} isn't in your delivery coverage (\"{seller.get('delivery_coverage')}\")."))
    elif dest and not seller.get("delivery_coverage"):
        a.items.append(Item(OPTIONAL, "Delivery coverage", f"Not entered, so the reply doesn't say whether you deliver to {dest}."))

    # Commercial terms
    if seller.get("gst_freight"):
        a.facts.append(("fact_gst", {"v": seller.get("gst_freight")}, "GST and freight"))
    elif any(f[0] == "fact_price" for f in a.facts):
        a.facts.append(("fact_gst_tbc", {}, None))
    if seller.get("payment_terms"):
        a.facts.append(("fact_payment", {"v": seller.get("payment_terms")}, "Payment terms"))
    if seller.get("certifications") and product_facts_ok:
        a.facts.append(("fact_certs", {"v": seller.get("certifications")}, "Certifications"))
    return a


SHORT_FACTS = {"fact_price", "fact_stock", "fact_stock_short", "fact_moq", "fact_gst_tbc"}


# --------------------------------------------------------------------------
# Version builders
# --------------------------------------------------------------------------

def _build_v1(ex: Extraction) -> tuple[str, list[str]]:
    """Unconstrained 'basic prompt' output: deliberately over-promises."""
    head = summary(ex, ReplyStyle(), with_dest=False)
    dest = f" with delivery to {ex.destination.value}" if ex.destination.found else ""
    text = (
        "Dear Buyer,\n\n"
        "Thank you for reaching out to us. "
        f"We are pleased to inform you that we can supply {head}{dest}.\n\n"
        "Our rates are highly competitive, and we can deliver within 7 to 10 business days.\n\n"
        "Please let us know if you would like to proceed with the order, and we will send you the final invoice.\n\n"
        "Best regards,\nSales Team"
    )
    rationale = [
        "Sounds polite and confident, which is what a basic prompt optimises for.",
        "Claims the seller can supply the full order, though nobody checked stock.",
        "Invents a 7-10 day delivery window and calls the rates \"highly competitive\".",
        "Asks for no grade, thickness or length, so any later quote risks a margin loss or a broken commitment.",
        "Pushes for the order and an invoice before a quotation exists.",
    ]
    return text, rationale


def _missing_shorts(ex: Extraction) -> list[str]:
    shorts = [r.short for r in ex.missing_specs()]
    if ex.category_status == UNCONFIRMED:
        shorts.insert(0, "exact product type")
    if not ex.quantity.found or ex.quantity.status != CONFIRMED:
        shorts.append("required quantity")
    if not ex.destination.found or ex.destination.status != CONFIRMED:
        shorts.append("delivery location")
    return shorts


def _build_v2(ex: Extraction) -> tuple[str, list[str], list[str]]:
    style = ReplyStyle()
    head = summary(ex, style, with_dest=False, v2=True)
    dest = f" for delivery in {ex.destination.value}" if ex.destination.found and ex.destination.status == CONFIRMED else ""
    shorts = _missing_shorts(ex)
    parts = ["Hello,", "Thank you for your enquiry.", f"We understand that you need {head}{dest}."]
    if shorts:
        parts.append(f"To share an accurate quotation and delivery timeline, please confirm the {_join(shorts)}.")
        parts.append("Once these details are available, we can check the applicable price and delivery options.")
        parts.append("Please share the required specifications so we can proceed with the quotation.")
    else:
        parts.append("We will check the applicable price and delivery options and share our quotation.")
    parts.append("Thank you.")
    rationale = [
        "Acknowledges the product, quantity, size and destination from the enquiry.",
        "Asks for the specifications needed to quote" + (f": {_join(shorts)}." if shorts else "."),
        "States no price, stock or delivery date.",
        "Ends with a clear next step: share the specifications, then receive the quotation.",
    ]
    return "\n\n".join(parts), rationale, shorts


def _build_v3(ex: Extraction, seller: SellerProfile, style: ReplyStyle, analysis: SellerAnalysis
              ) -> tuple[str, list[str], list[str], list[str]]:
    lang = style.language
    short = style.length == "short"
    questions: list[str] = []
    q_shorts: list[str] = []

    # Questions for the buyer (only what a quotation needs).
    if ex.category_status == UNCONFIRMED:
        questions.append(rules.PRODUCT_TYPE_QUESTION[style.key])
        q_shorts.append("the exact product type" if lang != "hinglish" else "exact product type")
    for rule in ex.missing_specs():
        if rule.id in analysis.offers:
            label = rule.label.split(" (")[0]
            questions.append(_p("offer", style, label=label, value=analysis.offers[rule.id]))
        else:
            questions.append(rule.question[style.key])
        q_shorts.append(rule.short)
    if not ex.quantity.found:
        questions.append(_p("ask_quantity", style))
        q_shorts.append("quantity")
    elif ex.quantity.status == UNCONFIRMED:
        questions.append(_p("ask_quantity_unit", style))
        q_shorts.append("quantity and unit")
    if not ex.destination.found:
        questions.append(_p("ask_dest", style))
        q_shorts.append("delivery location")
    elif ex.destination.status == UNCONFIRMED:
        questions.append(_p("ask_dest_check", style, dest=ex.destination.value))
        q_shorts.append("delivery location")
    extras = ex.category.extra_questions.get(style.key, []) if style.extra_questions else []

    facts = [(k, kw) for k, kw, _ in analysis.facts if not short or k in SHORT_FACTS]
    business = seller.get("business_name")
    sign = [_p("closing", style), business] if business else [_p("closing_bare", style)]

    if short:
        lines = [_p("greeting", style), _p("short_open", style, summary=summary(ex, style))]
        if facts:
            lines.append(". ".join(_p(k, style, **kw) for k, kw in facts) + ".")
        if "guarantee" in ex.intents:
            lines.append(_p("no_guarantee", style).split(". ")[0].rstrip(".") + ".")
        if q_shorts:
            lines.append(_p("short_ask", style, items=_join(q_shorts, lang)))
            lines.append(_p("short_next", style))
        else:
            lines.append(_p("next_no_q", style).split(". ")[0] + ".")
        text = "\n\n".join([lines[0], " ".join(lines[1:])] + ["\n".join(sign)])
    else:
        blocks = [_p("greeting", style), _p("thanks", style)]
        para = [_p("understand", style, summary=summary(ex, style))]
        if "price" in ex.intents and "delivery" in ex.intents:
            para.append(_p("asked_price_delivery", style))
        elif "price" in ex.intents:
            para.append(_p("asked_price", style))
        elif "delivery" in ex.intents:
            para.append(_p("asked_delivery", style))
        blocks.append(" ".join(para))
        if facts:
            blocks.append(_p("facts_intro", style) + "\n" + "\n".join("• " + _p(k, style, **kw) for k, kw in facts))
        if "guarantee" in ex.intents:
            blocks.append(_p("no_guarantee", style))
        if questions:
            blocks.append(_p("ask_intro", style) + "\n" + "\n".join("• " + q for q in questions))
            if ex.missing_specs() and "price" in ex.intents or ex.category.id == "ms_pipe" and ex.missing_specs():
                blocks.append(ex.category.price_note[style.key])
        if extras:
            blocks.append(_p("extra_intro", style) + "\n" + "\n".join("• " + q for q in extras))
        blocks.append(_p("next_with_q" if questions else "next_no_q", style))
        blocks.append("\n".join(sign))
        text = "\n\n".join(blocks)

    # Rationale
    r = []
    acknowledged = ["product"] if ex.category is not rules.GENERIC else []
    if ex.quantity.found and ex.quantity.status == CONFIRMED:
        acknowledged.append("quantity")
    if ex.found_specs():
        acknowledged.append("size/specification")
    if ex.destination.status == CONFIRMED:
        acknowledged.append("destination")
    if acknowledged:
        r.append(f"Repeats the buyer's {_join(acknowledged)} so they know the enquiry was read correctly.")
    if questions:
        r.append(f"Asks only {len(questions)} question{'s' if len(questions) != 1 else ''} needed for a quotation"
                 + (f", plus {len(extras)} optional ones you added." if extras else "."))
    else:
        r.append("No questions needed: every quotation detail is already known.")
    used = [label for _, _, label in analysis.facts if label]
    if used:
        lowered = [u.lower().replace("gst", "GST") for u in used]
        r.append(f"Uses only the seller details you entered: {_join(lowered)}.")
    if not seller.get("unit_price") or not any(k == "fact_price" for k, _ in facts):
        r.append("States no price, because no usable rate was entered.")
    if not seller.get("available_quantity"):
        r.append("Makes no stock or fulfilment claim, because no available quantity was entered.")
    if not seller.get("dispatch_time"):
        r.append("Gives no delivery date, because no dispatch time was entered.")
    if "guarantee" in ex.intents:
        r.append("The buyer asked for a guarantee; the reply politely declines to promise a fixed date.")
    if analysis.product_mismatch or analysis.size_mismatch:
        r.append("Leaves out your rate and stock because your profile may describe a different product or size.")
    if ex.injection:
        r.append("The enquiry contained instruction-like text. It was treated as buyer text and not followed.")
    if style.language == "hinglish":
        r.append("Written in Roman-script Hinglish, as commonly used in B2B WhatsApp chats.")
    elif style.tone == "simple":
        r.append("Short sentences and plain English, easy to check before sending.")
    else:
        r.append("Formal wording for corporate or first-time buyers.")
    if not short and questions:
        r.append("Bullet points read well on a phone screen and are easy for the buyer to answer.")
    r.append("Ends with a clear next step and keeps pricing decisions with the seller.")
    return text, r, questions + extras, used


# --------------------------------------------------------------------------
# Status items
# --------------------------------------------------------------------------

def _buyer_items(ex: Extraction) -> list[Item]:
    items = []
    if ex.category is rules.GENERIC:
        items.append(Item(MISSING, "Product", "Product not recognised from the enquiry; the reply asks for it."))
    elif ex.category_status == UNCONFIRMED:
        items.append(Item(CHECK, "Product type", f"Read as \"{ex.product}\" from a general word; exact type is asked."))
    else:
        items.append(Item(BUYER, "Product", ex.product))

    q = ex.quantity
    if not q.found:
        items.append(Item(MISSING, "Quantity", "Not stated; the reply asks for it."))
    elif q.status == UNCONFIRMED:
        items.append(Item(CHECK, "Quantity", f"{q.value}? {q.note}"))
    else:
        items.append(Item(BUYER, "Quantity", q.value + (f" ({q.note})" if q.note else "")))

    for rule in ex.category.specs:
        v = ex.specs[rule.id]
        if v.found:
            status = BUYER if v.status == CONFIRMED else CHECK
            items.append(Item(status, rule.label, v.value + (f" ({v.note})" if v.note else "")))
        elif ex.category is not rules.GENERIC or rule.id == "product":
            items.append(Item(MISSING, rule.label, "Not in the enquiry; asked in the reply."))
        else:
            items.append(Item(MISSING, rule.label, "Not in the enquiry; asked in the reply."))

    d = ex.destination
    if not d.found:
        items.append(Item(MISSING, "Delivery location", "Not stated; the reply asks for it."))
    elif d.status == UNCONFIRMED:
        items.append(Item(CHECK, "Delivery location", f"{d.value}? {d.note}"))
    else:
        items.append(Item(BUYER, "Delivery location", d.value))

    asks = [n for n, label in (("price", "price"), ("delivery", "delivery timeline"), ("stock", "stock availability"))
            if n in ex.intents]
    if asks:
        labels = {"price": "price", "delivery": "delivery timeline", "stock": "stock availability"}
        items.append(Item(BUYER, "Buyer asked for", _join([labels[a] for a in asks])))
    if "guarantee" in ex.intents:
        items.append(Item(CHECK, "Guarantee requested",
                          "The buyer wants a guaranteed delivery. The reply does not promise one; decide this yourself."))
    if ex.injection:
        items.append(Item(CHECK, "Instruction-like text ignored",
                          "Found: " + "; ".join(f"\"{s}\"" for s in ex.injection[:3])
                          + ". Buyer text cannot change the reply rules."))
    if ex.truncated:
        items.append(Item(CHECK, "Enquiry shortened", "Only the first 2,000 characters were read."))
    return items


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def generate_reply(enquiry: str, seller: SellerProfile | dict | None = None, version: str = "v3",
                   style: ReplyStyle | None = None) -> ReplyResult:
    start = time.perf_counter()
    style = style or ReplyStyle()
    if not isinstance(seller, SellerProfile):
        seller = SellerProfile.from_dict(seller)
    if version not in VERSIONS:
        version = "v3"

    ex = extract(enquiry)
    if ex.is_empty:
        return ReplyResult(text="", version=version, style=style, extraction=ex,
                           error="Please paste or type a buyer enquiry first.",
                           elapsed_ms=(time.perf_counter() - start) * 1000)

    questions, used = [], []
    if version == "v1":
        text, rationale = _build_v1(ex)
        items = _buyer_items(ex)
        seller_for_validation = SellerProfile()  # the basic prompt saw no seller data
    elif version == "v2":
        text, rationale, questions = _build_v2(ex)
        items = _buyer_items(ex)
        seller_for_validation = SellerProfile()
    else:
        analysis = analyse_seller(ex, seller, style)
        text, rationale, questions, used = _build_v3(ex, seller, style, analysis)
        items = _buyer_items(ex) + analysis.items
        seller_for_validation = seller

    findings = validate(text, seller_for_validation, ex.text, ex.quantity.number, ex.quantity.unit)
    return ReplyResult(
        text=text, version=version, style=style, extraction=ex, items=items, rationale=rationale,
        findings=findings, questions=questions, facts_used=used,
        elapsed_ms=(time.perf_counter() - start) * 1000,
    )


def validate_text(text: str, enquiry: str, seller: SellerProfile | dict | None) -> list[Finding]:
    """Validate an arbitrary (e.g. seller-edited) reply against the profile."""
    if not isinstance(seller, SellerProfile):
        seller = SellerProfile.from_dict(seller)
    ex = extract(enquiry)
    return validate(text, seller, ex.text, ex.quantity.number, ex.quantity.unit)


def sanitize_for_display(text: str) -> str:
    """Remove characters that could be interpreted as markup when echoing text."""
    return re.sub(r"[<>`*_\[\]#|]", "", text or "")


__all__ = ["ReplyResult", "ReplyStyle", "generate_reply", "validate_text", "STATUS_LABELS", "FIELD_LABELS"]
