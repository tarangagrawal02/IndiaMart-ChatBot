import streamlit as st

from smart_reply.content import MARKETPLACE_METRICS, PROTOTYPE_METRICS, SIX_WEEK_PLAN
from ui import state

state.init()
m = st.session_state.metrics

st.subheader("Metrics and pilot plan")

st.markdown("#### Prototype metrics")
st.caption("How this prototype measures itself. Live numbers are from your current browser session only and are not stored.")
with st.container(border=True):
    st.markdown("**Your session so far** :blue-badge[Live, this tab only]")
    with st.container(horizontal=True):
        st.metric("Replies generated", m["generations"])
        st.metric("Regenerations", m["regenerations"])
        st.metric("Edits", m["edits"])
        st.metric("Approved for copy", m["approvals"])
        st.metric("Missing details detected", m["missing_detected"])
        st.metric("Claims flagged", m["claims_detected"])
    total = m["generations"] + m["regenerations"]
    rate = f"{m['approvals'] / total:.0%}" if total else "n/a"
    last = f"{m['approve_seconds'][-1]} s" if m["approve_seconds"] else "n/a"
    st.caption(f"Approval (copy-unlock) rate: {rate} · Last time from generation to approval: {last} · "
               f"Last engine time: {m['last_ms']:.0f} ms")

st.table([{"Metric": a, "How it is measured": b, "Where": c} for a, b, c in PROTOTYPE_METRICS])

with st.container(border=True):
    st.markdown("**Illustrative pilot targets** :orange-badge[Simulated, not results]")
    st.table([
        {"Measure": "Median time to an approved reply", "Baseline (assumed)": "5-15 min", "Pilot target": "< 1 min"},
        {"Measure": "Drafts approved with ≤ 2 edits", "Baseline (assumed)": "n/a", "Pilot target": "≥ 50%"},
        {"Measure": "Unsupported claims in sent replies", "Baseline (assumed)": "unknown", "Pilot target": "0 per 1,000"},
        {"Measure": "Enquiries asked the right qualifying questions", "Baseline (assumed)": "unknown", "Pilot target": "≥ 90%"},
    ])
    st.caption("Baselines are assumptions to be replaced with measured data in the pilot.")

st.markdown("#### Future marketplace metrics")
st.table([{"Metric": a, "Definition": b, "Role": c} for a, b, c in MARKETPLACE_METRICS])

with st.container(border=True):
    st.markdown("**Measuring conversion impact properly**")
    st.markdown(
        "Conversion impact can't be assumed from the prototype. It needs a controlled experiment:\n"
        "- **Randomise at seller level** (not enquiry level), stratified by category and enquiry volume, "
        "into Smart Reply and control groups.\n"
        "- **Primary metrics:** time to first reply and reply rate. **Secondary:** buyer follow-up rate and "
        "qualified lead progression.\n"
        "- **Guardrails:** complaints about incorrect replies, unsupported-claim rate, seller rejection rate.\n"
        "- **Duration:** long enough to cover weekly cycles and fade novelty effects (4-6 weeks); fix the sample size "
        "and minimum detectable effect before starting.\n"
        "- **Decide in advance** what result would justify a wider rollout, a redesign, or stopping."
    )

st.markdown("#### Six-week plan")
STATUS = {
    "done": ":green-badge[:material/check: Completed in prototype]",
    "partial": ":orange-badge[:material/pending: Partly done]",
    "proposed": ":gray-badge[:material/schedule: Proposed]",
}
for week, title, status, detail in SIX_WEEK_PLAN:
    with st.container(border=True):
        st.markdown(f"**{week}: {title}** {STATUS[status]}")
        st.caption(detail)
