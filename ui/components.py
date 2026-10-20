"""Reusable display components."""

from __future__ import annotations

import hashlib
import json
import re

import streamlit as st

from smart_reply.engine import BUYER, CHECK, MISSING, OPTIONAL, SELLER, STATUS_LABELS
from smart_reply.validator import ERROR

STATUS_STYLE = {
    BUYER: ("blue", ":material/description:"),
    SELLER: ("green", ":material/verified:"),
    CHECK: ("orange", ":material/help:"),
    MISSING: ("red", ":material/error:"),
    OPTIONAL: ("gray", ":material/remove:"),
}
STATUS_ORDER = [SELLER, BUYER, CHECK, MISSING, OPTIONAL]


def md_escape(text: str) -> str:
    """Escape Markdown so buyer or seller text renders literally."""
    text = re.sub(r"([\\`*_{}\[\]()#+\-.!|>~:$<])", r"\\\1", text or "")
    return text


def md_multiline(text: str) -> str:
    return "  \n".join(md_escape(line) for line in (text or "").splitlines())


def status_badge(status: str) -> str:
    color, icon = STATUS_STYLE[status]
    return f":{color}-badge[{icon} {STATUS_LABELS[status]}]"


def render_items(items: list) -> None:
    """Missing information panel grouped by status."""
    if not items:
        st.caption("Nothing to show yet.")
        return
    for status in STATUS_ORDER:
        group = [i for i in items if i.status == status]
        if not group:
            continue
        st.markdown(status_badge(status))
        for item in group:
            detail = f" — {md_escape(item.detail)}" if item.detail else ""
            st.markdown(f"- **{md_escape(item.label)}**{detail}")


def status_summary(items: list) -> None:
    counts = {s: sum(1 for i in items if i.status == s) for s in (SELLER, CHECK, MISSING)}
    with st.container(horizontal=True, gap="small"):
        st.badge(f"{counts[SELLER]} confirmed from seller input", icon=":material/verified:", color="green")
        st.badge(f"{counts[CHECK]} need seller confirmation", icon=":material/help:", color="orange")
        st.badge(f"{counts[MISSING]} missing — asked in reply", icon=":material/error:", color="red")


def render_findings(findings: list, empty_message: str = "No unsupported commercial claims found.") -> None:
    if not findings:
        st.success(empty_message, icon=":material/check_circle:")
        return
    errors = [f for f in findings if f.severity == ERROR]
    warnings = [f for f in findings if f.severity != ERROR]
    if errors:
        lines = "\n".join(f"- **{md_escape(f.message)}** “{md_escape(f.excerpt)}”" for f in errors)
        st.error(f"**{len(errors)} unsupported claim{'s' if len(errors) != 1 else ''}**\n\n{lines}",
                 icon=":material/gpp_bad:")
    if warnings:
        lines = "\n".join(f"- {md_escape(f.message)} “{md_escape(f.excerpt)}”" for f in warnings)
        st.warning(f"**{len(warnings)} thing{'s' if len(warnings) != 1 else ''} to check**\n\n{lines}",
                   icon=":material/warning:")


def copy_button(text: str, label: str = "Copy reply") -> None:
    """Clipboard button with in-place success/failure feedback.

    The text is JSON-encoded with '<', '>' and '&' escaped, so reply content
    (which can include buyer-derived values) can't break out of the script.
    """
    payload = json.dumps(text).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    uid = "cp" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    st.html(
        f"""
<div class="sr-copy">
  <button id="{uid}" type="button" aria-live="polite"
    style="font:inherit;font-weight:600;padding:0.45rem 1rem;border-radius:0.5rem;border:1px solid #0B5CAD;
           background:#0B5CAD;color:#fff;cursor:pointer;">{label}</button>
  <span id="{uid}-msg" role="status" style="margin-left:0.6rem;font-size:0.9rem;"></span>
</div>
<script>
(function() {{
  const btn = document.getElementById("{uid}");
  const msg = document.getElementById("{uid}-msg");
  if (!btn || btn.dataset.bound) return;
  btn.dataset.bound = "1";
  const text = {payload};
  function fallback() {{
    try {{
      const ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    }} catch (e) {{ return false; }}
  }}
  function done(ok) {{
    msg.textContent = ok ? "Copied. Paste it into your chat after a final check."
                         : "Copy was blocked by the browser. Use the copy icon on the box below, or select the text and press Ctrl+C.";
    msg.style.color = ok ? "#1a7f37" : "#cf222e";
  }}
  btn.addEventListener("click", function() {{
    if (navigator.clipboard && window.isSecureContext) {{
      navigator.clipboard.writeText(text).then(function() {{ done(true); }}, function() {{ done(fallback()); }});
    }} else {{
      done(fallback());
    }}
  }});
}})();
</script>
""",
        unsafe_allow_javascript=True,
    )


def disclosure(text: str) -> None:
    st.caption(f":material/info: {text}")


def section_header(title: str, caption: str | None = None) -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)
