import streamlit as st

from smart_reply.content import PAIN_STATEMENT, PERSONAS
from ui import state
from ui.components import md_escape

state.init()
ss = st.session_state

st.subheader("Seller personas")
st.warning(
    "**Hypotheses, not research findings.** These personas are built from desk research and the assignment brief. "
    "They need validation through interviews with real sellers before they guide product decisions. "
    "Names and businesses are fictional.",
    icon=":material/psychology_alt:",
)

primary = next(p for p in PERSONAS if p["primary"])
with st.container(border=True):
    st.markdown(f"**Primary persona: {primary['name']}**")
    st.markdown(f"> {PAIN_STATEMENT}")
    st.caption("Chosen because this seller has the product capability but loses enquiries at the first written reply, "
               "which is exactly the step Smart Reply improves.")

for persona in PERSONAS:
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f"#### {persona['icon']} {persona['name']}")
            if persona["primary"]:
                st.badge("Primary persona", icon=":material/star:", color="primary")
            st.badge("Hypothesis", icon=":material/science:", color="gray")
        st.caption(persona["example_name"])

        left, right = st.columns(2, gap="large")
        with left:
            st.markdown(f"**Business context**  \n{persona['context']}")
            st.markdown("**Goals**\n" + "\n".join(f"- {g}" for g in persona["goals"]))
            st.markdown("**Communication challenges**\n" + "\n".join(f"- {c}" for c in persona["challenges"]))
        with right:
            st.markdown(f"**Example buyer enquiry**\n\n> {md_escape(persona['enquiry'])}")
            st.markdown(f"**Current workaround**  \n{persona['workaround']}")
            st.markdown("**Adoption barriers**\n" + "\n".join(f"- {b}" for b in persona["barriers"]))
            st.markdown(f"**Expected Smart Reply benefit**  \n{persona['benefit']}")

        if st.button("Try this enquiry in the Studio", key=f"try_{persona['id']}", icon=":material/arrow_forward:"):
            ss.enquiry = persona["enquiry"]
            ss.pop("w_enquiry", None)
            ss["w_demo_seller"] = persona["demo_seller"]
            state.flash("info", "Persona enquiry loaded. Optionally click Load demo profile, then Generate smart reply.")
            st.switch_page("app_pages/studio.py")
