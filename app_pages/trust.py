import streamlit as st

from smart_reply.content import AI_VS_PM_RISKS, TRUST_PRIORITIES

st.subheader("Trust and adoption")
st.caption("The three requirements a future IndiaMART Smart Reply feature must get right for sellers to trust and use it.")

with st.container(border=True):
    st.markdown("**Evidence status**")
    st.markdown(
        ":orange-badge[Hypothesis] All three priorities are product hypotheses from desk research and prototype testing.  \n"
        ":gray-badge[Validated] No customer findings yet. No real sellers have been interviewed for this prototype; "
        "Week 5 of the pilot plan is reserved for that."
    )

for n, p in enumerate(TRUST_PRIORITIES, start=1):
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f"#### {p['icon']} Priority {n}: {p['title']}")
            st.badge("Hypothesis", color="orange")
        st.markdown(f"**Requirement.** {p['requirement']}")
        a, b = st.columns(2, gap="large")
        with a:
            st.markdown(f"**AI-identified risk**  \n{p['ai_risk']}")
            st.markdown(f"**PM's additional perspective**  \n{p['pm_view']}")
        with b:
            st.markdown(f"**Product decision**  \n{p['decision']}")
            st.markdown(f"**Success indicator**  \n{p['metric']}")
        st.caption(f":material/build: {p['built']}")

with st.container(border=True):
    st.markdown("**What AI brainstorming flagged vs what a PM adds**")
    st.table([{"Risk raised by AI": ai, "What the PM perspective adds": pm} for ai, pm in AI_VS_PM_RISKS])
    st.caption("The AI column reflects the kind of generic risks an LLM lists when asked; the PM column ties each to "
               "marketplace mechanics. Both are reasoning, not measured data.")
