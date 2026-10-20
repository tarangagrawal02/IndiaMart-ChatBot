"""IndiaMART Smart Reply - Streamlit entry point.

Run locally with:  python -m streamlit run app.py
No API keys, secrets or accounts are required.
"""

import logging
import traceback

import streamlit as st

from smart_reply.content import DISCLOSURE
from ui import state
from ui.components import disclosure

st.set_page_config(
    page_title="IndiaMART Smart Reply",
    page_icon=":material/forum:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

state.init()

PAGES = [
    st.Page("app_pages/studio.py", title="Smart Reply Studio", icon=":material/edit_note:", default=True),
    st.Page("app_pages/prompt_lab.py", title="Prompt Lab", icon=":material/science:"),
    st.Page("app_pages/personas.py", title="Seller personas", icon=":material/groups:"),
    st.Page("app_pages/trust.py", title="Trust and adoption", icon=":material/verified_user:"),
    st.Page("app_pages/metrics.py", title="Metrics and pilot plan", icon=":material/monitoring:"),
    st.Page("app_pages/about.py", title="About and demo guide", icon=":material/menu_book:"),
]

page = st.navigation(PAGES, position="top")

with st.container(horizontal=True, vertical_alignment="center", gap="small"):
    st.markdown("### :material/forum: IndiaMART Smart Reply")
    st.caption("Professional replies. Better buyer conversations.")
disclosure(DISCLOSURE)

try:
    page.run()
except Exception:  # Streamlit's rerun/stop signals are BaseException, so they pass through.
    logging.getLogger("smart_reply").error("Page error\n%s", traceback.format_exc())
    st.error(
        "Something went wrong on this page. Your inputs in this session are safe; "
        "try again, or reset the session below.",
        icon=":material/error:",
    )
    if st.button("Reset session", icon=":material/restart_alt:"):
        st.session_state.clear()
        st.rerun()
