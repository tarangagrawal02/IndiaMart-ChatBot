"""Session state: one place that initialises state and defines every action.

Canonical values live in plain session-state keys (``enquiry``, ``seller``,
``settings``, ``reply``...). Widgets use ``w_``-prefixed keys that are
re-seeded from the canonical values whenever a page renders them, so values
survive page switches. Nothing is written to disk or sent anywhere.
"""

from __future__ import annotations

import time

import streamlit as st

from smart_reply.engine import ReplyStyle, generate_reply, validate_text
from smart_reply.extractor import extract
from smart_reply.prompts import SAMPLE_ENQUIRY
from smart_reply.seller import DEMO_BY_ID, FIELD_LABELS, SellerProfile, retrieve_demo_product
from smart_reply.validator import ERROR, WARNING

SELLER_FIELDS = list(FIELD_LABELS)

DEFAULT_SETTINGS = {
    "version": "v3",
    "language": "english",
    "tone": "simple",
    "length": "standard",
    "extra": False,
}

SETTING_OPTIONS = {
    "version": ["v2", "v3"],
    "language": ["english", "hinglish"],
    "tone": ["simple", "professional"],
    "length": ["standard", "short"],
}


def init() -> None:
    ss = st.session_state
    ss.setdefault("enquiry", SAMPLE_ENQUIRY)
    ss.setdefault("seller", SellerProfile().to_dict())
    ss.setdefault("demo_loaded", None)
    ss.setdefault("settings", dict(DEFAULT_SETTINGS))
    ss.setdefault("reply", None)  # dict, see _store_reply
    ss.setdefault("pending", None)  # style change waiting for "replace my edits" confirmation
    ss.setdefault("flash", None)  # (kind, message) shown once
    ss.setdefault("metrics", {
        "generations": 0, "regenerations": 0, "edits": 0, "approvals": 0,
        "missing_detected": 0, "claims_detected": 0, "last_ms": 0.0, "approve_seconds": [],
    })


# --------------------------------------------------------------------------
# Widget <-> canonical sync
# --------------------------------------------------------------------------

def seed(widget_key: str, value) -> None:
    """Give a widget its canonical value if Streamlit dropped its key."""
    if widget_key not in st.session_state:
        st.session_state[widget_key] = value


def seed_studio_widgets() -> None:
    ss = st.session_state
    seed("w_enquiry", ss.enquiry)
    for f in SELLER_FIELDS:
        seed(f"w_seller_{f}", ss.seller.get(f, ""))
    for name, value in ss.settings.items():
        seed(f"w_set_{name}", value)
    if ss.reply:
        seed("w_reply", ss.reply["current"])
    seed("w_reviewed", False)
    seed("w_ack_claims", False)


def sync_enquiry() -> None:
    st.session_state.enquiry = st.session_state.w_enquiry or ""


def sync_seller(field: str) -> None:
    st.session_state.seller[field] = st.session_state.get(f"w_seller_{field}", "") or ""


def sync_setting(name: str) -> None:
    ss = st.session_state
    value = ss.get(f"w_set_{name}")
    if name in SETTING_OPTIONS and value not in SETTING_OPTIONS[name]:
        # segmented controls can be deselected; keep the previous value
        ss[f"w_set_{name}"] = ss.settings[name]
        return
    ss.settings[name] = bool(value) if name == "extra" else value
    # Style changes apply straight away unless they would overwrite edits.
    if ss.reply and not ss.reply["edited"]:
        _generate(regenerate=True)


def sync_reply_edit() -> None:
    ss = st.session_state
    if not ss.reply:
        return
    new = ss.get("w_reply", "")
    if new != ss.reply["current"]:
        ss.reply["current"] = new
        ss.reply["edited"] = new != ss.reply["generated"]
        ss.metrics["edits"] += 1
        ss.w_reviewed = False  # changed text needs a fresh review
        ss.w_ack_claims = False


def set_widget(key: str, value) -> None:
    st.session_state[key] = value


# --------------------------------------------------------------------------
# Derived values
# --------------------------------------------------------------------------

def style() -> ReplyStyle:
    s = st.session_state.settings
    return ReplyStyle(language=s["language"], tone=s["tone"], length=s["length"], extra_questions=s["extra"])


def fingerprint() -> tuple:
    ss = st.session_state
    return (ss.enquiry.strip(), tuple(sorted(ss.seller.items())), tuple(sorted(ss.settings.items())))


def is_stale() -> bool:
    ss = st.session_state
    return bool(ss.reply) and ss.reply["fingerprint"] != fingerprint()


def current_findings():
    ss = st.session_state
    if not ss.reply:
        return []
    return validate_text(ss.reply["current"], ss.reply["enquiry"], ss.seller)


def flash(kind: str, message: str) -> None:
    st.session_state.flash = (kind, message)


# --------------------------------------------------------------------------
# Actions (used as widget callbacks)
# --------------------------------------------------------------------------

def _generate(regenerate: bool = False) -> bool:
    ss = st.session_state
    result = generate_reply(ss.enquiry, ss.seller, ss.settings["version"], style())
    ss.metrics["last_ms"] = result.elapsed_ms
    if not result.ok:
        flash("error", result.error)
        return False
    ss.reply = {
        "generated": result.text,
        "current": result.text,
        "edited": False,
        "result": result,
        "enquiry": ss.enquiry,
        "fingerprint": fingerprint(),
        "created": time.time(),
    }
    ss.w_reply = result.text
    ss.w_reviewed = False
    ss.w_ack_claims = False
    ss.pending = None
    m = ss.metrics
    m["regenerations" if regenerate else "generations"] += 1
    m["missing_detected"] += sum(1 for i in result.items if i.status == "missing")
    m["claims_detected"] += sum(1 for f in result.findings if f.severity in (ERROR, WARNING))
    return True


def generate() -> None:
    had_reply = bool(st.session_state.reply)
    if _generate(regenerate=had_reply):
        flash("success", "Reply regenerated." if had_reply else "Reply generated. Review it before copying.")


def load_sample(text: str = SAMPLE_ENQUIRY) -> None:
    st.session_state.enquiry = text
    st.session_state.w_enquiry = text
    flash("info", "Sample enquiry loaded. Click Generate smart reply.")


def clear_form() -> None:
    ss = st.session_state
    ss.enquiry = ""
    ss.w_enquiry = ""
    ss.reply = None
    ss.pending = None
    for k in ("w_reply",):
        ss.pop(k, None)
    flash("info", "Enquiry and reply cleared. Your seller profile was kept.")


def load_demo_profile(seller_id: str | None = None) -> None:
    ss = st.session_state
    seller_id = seller_id or ss.get("w_demo_seller") or "shakti"
    ex = extract(ss.enquiry)
    product, reasons = retrieve_demo_product(seller_id, ex.category.id, ss.enquiry)
    profile = SellerProfile.from_dict(product["profile"]).to_dict()
    ss.seller = profile
    for f in SELLER_FIELDS:
        ss[f"w_seller_{f}"] = profile.get(f, "")
    ss.demo_loaded = {"id": seller_id, "reasons": reasons, "product": profile.get("product_name", "")}
    flash("info", f"Fictional demo profile loaded: {profile.get('business_name')}. Regenerate to use it.")


def reset_demo_profile() -> None:
    ss = st.session_state
    ss.seller = SellerProfile().to_dict()
    for f in SELLER_FIELDS:
        ss[f"w_seller_{f}"] = ""
    ss.demo_loaded = None
    flash("info", "Seller profile cleared. All seller details are now unknown.")


def reset_reply() -> None:
    ss = st.session_state
    if not ss.reply:
        return
    ss.reply["current"] = ss.reply["generated"]
    ss.reply["edited"] = False
    ss.w_reply = ss.reply["generated"]
    ss.w_reviewed = False
    ss.w_ack_claims = False
    ss.pending = None
    ss.metrics["regenerations"] += 1
    flash("info", "Reply reset to the last generated version.")


STYLE_ACTIONS = {
    "shorter": ({"length": "short"}, "Reply shortened."),
    "simpler": ({"language": "english", "tone": "simple"}, "Switched to simpler English."),
    "professional": ({"tone": "professional", "length": "standard"}, "Made more professional."),
    "questions": ({"extra": True}, "Added clarifying questions."),
}


def request_style(action: str) -> None:
    """Apply a one-click style change, asking first if it would overwrite edits."""
    ss = st.session_state
    if ss.reply and ss.reply["edited"]:
        ss.pending = action
        return
    apply_style(action)


def apply_style(action: str) -> None:
    ss = st.session_state
    changes, message = STYLE_ACTIONS[action]
    ss.settings.update(changes)
    if ss.settings["version"] != "v3":
        ss.settings["version"] = "v3"  # style controls are a seller-ready feature
    for name, value in ss.settings.items():
        ss[f"w_set_{name}"] = value
    ss.pending = None
    if _generate(regenerate=True):
        flash("success", message)


def cancel_pending() -> None:
    st.session_state.pending = None
    flash("info", "Kept your edits. No changes were applied.")


def approve() -> None:
    """Review checkbox callback: count approvals and time-to-approve."""
    ss = st.session_state
    if ss.get("w_reviewed") and ss.reply:
        ss.metrics["approvals"] += 1
        ss.metrics["approve_seconds"].append(round(time.time() - ss.reply["created"], 1))


def demo_seller_options() -> dict:
    return {sid: DEMO_BY_ID[sid]["summary"] for sid in DEMO_BY_ID}
