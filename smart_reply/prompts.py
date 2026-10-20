"""The three prompt versions shown in the Prompt Lab.

The prompt text is displayed for transparency. In this API-free prototype the
prompts are not sent to a model; each version selects a rule set in
``smart_reply.engine`` that reproduces the behaviour the prompt is designed
to produce.
"""

from __future__ import annotations

from smart_reply.seller import FIELD_LABELS, SellerProfile

SAMPLE_ENQUIRY = (
    "Hi, I need 500 units of MS pipes 2 inch diameter, delivery in Pune, need rate and delivery timeline."
)

PROMPT_V1 = f"""You are a helpful sales assistant. Reply professionally to this buyer enquiry:
{SAMPLE_ENQUIRY}
Write a polite business reply."""

PROMPT_V2 = f"""You are a B2B sales assistant for a small Indian industrial supplier.
Reply to this enquiry:
{SAMPLE_ENQUIRY}
Acknowledge the product, quantity, size, and destination. Identify missing specifications, including MS grade, pipe thickness, and length. Do not invent prices, stock availability, or delivery dates. Explain that an accurate quotation can be provided after the required details are confirmed. Keep the reply concise and end with a clear next step."""

PROMPT_V3 = f"""You are a sales communication assistant for a small Indian B2B supplier.

BUYER ENQUIRY:
{SAMPLE_ENQUIRY}

VERIFIED SELLER INFORMATION:
Use only the seller information supplied in the application.

RULES:
1. Acknowledge the buyer's product, quantity, size, destination, and request for price and delivery.
2. Ask only relevant questions needed for a quotation.
3. Never invent product specifications, prices, inventory, certifications, freight, or delivery commitments.
4. Use simple English, short sentences, and a professional tone.
5. Clearly distinguish known information from missing information.
6. Include an actionable next step.
7. Do not overpromise or pressure the buyer.
8. Preserve the seller's commercial control.
9. Make the response suitable for copying into a B2B chat.

OUTPUT:
Suggested reply, missing information, and a short explanation of the response strategy."""

VERSIONS = {
    "v1": {
        "name": "Version 1 - Basic prompt",
        "short": "V1 Basic",
        "prompt": PROMPT_V1,
        "engine": "Unconstrained template that reproduces a typical basic-prompt failure: confident, polite, "
                  "and inventing capability, price and delivery claims.",
        "improvements": [
            "Polite, well-formed business English.",
            "Fast to write: one line of instruction.",
        ],
        "limitations": [
            "No business rules, so the reply claims stock, a delivery window and competitive rates nobody checked.",
            "Ignores that MS pipe price depends on class, thickness and weight, and asks no qualifying questions.",
            "Pushes for an order and invoice before any quotation exists.",
            "Generic sign-off; no seller identity.",
        ],
    },
    "v2": {
        "name": "Version 2 - Specific and commercially aware",
        "short": "V2 Specific",
        "prompt": PROMPT_V2,
        "engine": "Acknowledgement and qualification rules: repeat the extracted requirement, ask for missing "
                  "specifications, forbid prices, stock and dates.",
        "improvements": [
            "Acknowledges the exact product, quantity, size and destination.",
            "Asks for MS grade, pipe thickness and length, the details that decide the price.",
            "Invents no price, stock or delivery date.",
            "Ends with a clear next step.",
        ],
        "limitations": [
            "Doesn't use anything the seller already knows (rate, stock, MOQ, dispatch time).",
            "A single long paragraph of questions is harder to answer on a phone.",
            "No explanation of why the details matter; no tone or language options.",
        ],
    },
    "v3": {
        "name": "Version 3 - Seller-ready prompt",
        "short": "V3 Seller-ready",
        "prompt": PROMPT_V3,
        "engine": "Full rule set: verified seller facts only, consistency checks, bullet questions, domain hint "
                  "(IS 1239 class), guarantee handling, language and tone control, then independent validation.",
        "improvements": [
            "Uses only verified seller details, and offers the seller's own grade/thickness/length for confirmation.",
            "Separates known facts from questions, in short bullets that work in WhatsApp-style chat.",
            "Explains simply why class and thickness change the price (IS 1239 Class A/B/C).",
            "Never promises the full quantity if stock is lower, and declines guaranteed delivery dates.",
            "Signs off with the seller's business name and a concrete next step.",
        ],
        "limitations": [
            "Only as good as the seller profile: wrong inputs produce a confidently wrong reply.",
            "Rule-based wording is less natural than a well-constrained LLM and covers five product categories.",
            "Still needs seller review before sending; the validator can miss creatively worded claims.",
        ],
    },
}


def seller_block(seller: SellerProfile) -> str:
    """The VERIFIED SELLER INFORMATION section as it would be filled at runtime."""
    filled = seller.filled()
    if not filled:
        return "(No seller information entered - the reply must not state any price, stock, or delivery commitment.)"
    return "\n".join(f"- {FIELD_LABELS[k]}: {v}" for k, v in filled.items())
