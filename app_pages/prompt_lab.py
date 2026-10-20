import streamlit as st

from smart_reply.engine import ReplyStyle, generate_reply
from smart_reply.prompts import SAMPLE_ENQUIRY, VERSIONS, seller_block
from smart_reply.seller import DEMO_BY_ID, SellerProfile
from smart_reply.validator import ERROR
from ui import state
from ui.components import md_escape, md_multiline, render_findings

state.init()
ss = st.session_state

st.subheader("Prompt Lab")
st.info(
    "**Simulated prompt-engineering demonstration.** The prompts below were not sent to an LLM. Each version "
    "selects a rule set in the API-free engine that reproduces the behaviour the prompt is designed to produce. "
    "All three use the same enquiry and the same seller context.",
    icon=":material/science:",
)

CONTEXTS = {
    "none": "No seller information",
    "demo": "Fictional demo profile (Shakti Tubes)",
    "studio": "My seller profile from the Studio",
}
ss.setdefault("lab_context", "none")
context = st.segmented_control("Seller context passed to every version", list(CONTEXTS), format_func=CONTEXTS.get,
                               key="lab_context", required=True)
if context == "demo":
    seller = SellerProfile.from_dict(DEMO_BY_ID["shakti"]["products"][0]["profile"])
elif context == "studio":
    seller = SellerProfile.from_dict(ss.seller)
    if seller.is_empty():
        st.caption("Your Studio seller profile is empty, so this is the same as no seller information.")
else:
    seller = SellerProfile()

with st.container(border=True):
    st.markdown("**Buyer enquiry (same for all versions)**")
    st.markdown(f"> {md_escape(SAMPLE_ENQUIRY)}")

results = {v: generate_reply(SAMPLE_ENQUIRY, seller, v, ReplyStyle()) for v in VERSIONS}


def yes_no(flag: bool) -> str:
    return ":green[:material/check: Yes]" if flag else ":red[:material/close: No]"


tab_compare, *version_tabs = st.tabs(["Compare all three"] + [VERSIONS[v]["short"] for v in VERSIONS])

with tab_compare:
    def claims(r):
        errors = sum(1 for f in r.findings if f.severity == ERROR)
        return f"{errors} errors, {len(r.findings) - errors} warnings"

    criteria = {
        "Acknowledges product, quantity, size, destination": lambda v, r: yes_no(True),
        "Asks for missing specifications": lambda v, r: yes_no(bool(r.questions)),
        "Unsupported claims found": lambda v, r: claims(r),
        "Uses verified seller details": lambda v, r: (yes_no(bool(r.facts_used)) if v == "v3"
                                                      else ":gray[Not given seller data]"),
        "Phone-friendly bullets": lambda v, r: yes_no("•" in r.text),
        "Clear, low-pressure next step": lambda v, r: yes_no(v != "v1"),
        "Length": lambda v, r: f"{len(r.text.split())} words",
    }
    st.table([{"Criterion": name, **{VERSIONS[v]["short"]: fn(v, r) for v, r in results.items()}}
              for name, fn in criteria.items()])
    st.markdown(
        "**How the versions progress**\n\n"
        "- **V1 → V2:** adding business rules removes the invented stock, delivery window and \"competitive rates\", "
        "and makes the reply ask for grade, thickness and length, which decide an MS pipe price.\n"
        "- **V2 → V3:** adding verified seller data and output rules turns a safe reply into a useful one: the "
        "seller's own rate, stock and terms appear only if entered, questions become short bullets for chat, and the "
        "reply explains why the details matter.\n"
        "- **Same input, different behaviour:** switch the seller context above and only V3 changes, because only V3 "
        "is given seller information."
    )
    cols = st.columns(3, gap="medium")
    for col, (v, r) in zip(cols, results.items()):
        with col:
            with st.container(border=True, height=520):
                st.markdown(f"**{VERSIONS[v]['short']}**")
                st.markdown(md_multiline(r.text))

for tab, (v, meta) in zip(version_tabs, VERSIONS.items()):
    r = results[v]
    with tab:
        st.markdown(f"#### {meta['name']}")
        prompt_col, reply_col = st.columns(2, gap="large")
        with prompt_col:
            st.markdown("**Full prompt** · use the copy icon to copy it")
            st.code(meta["prompt"], language=None, wrap_lines=True)
            if v == "v3":
                st.markdown("**Seller information supplied in this run**")
                st.code(seller_block(seller), language=None, wrap_lines=True)
            st.caption(f"Engine behaviour: {meta['engine']}")
        with reply_col:
            st.markdown("**Response**")
            with st.container(border=True):
                st.markdown(md_multiline(r.text))
            render_findings(r.findings)
            if v == "v1":
                st.caption("Shown for comparison only. This version isn't offered in the Studio because of these claims.")
        better, worse = st.columns(2, gap="large")
        with better:
            st.markdown("**Improvements**")
            for line in meta["improvements"]:
                st.markdown(f"- {line}")
        with worse:
            st.markdown("**Remaining limitations**")
            for line in meta["limitations"]:
                st.markdown(f"- {line}")
        with st.expander("Why the engine wrote this"):
            for line in r.rationale:
                st.markdown(f"- {md_escape(line)}")
