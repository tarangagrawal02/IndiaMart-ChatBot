import streamlit as st

from smart_reply.content import PAIN_STATEMENT, SAMPLE_ENQUIRIES
from smart_reply.seller import FIELD_HELP, FIELD_LABELS
from smart_reply.validator import has_errors
from ui import state
from ui.components import copy_button, md_escape, md_multiline, render_findings, render_items, status_summary

state.init()
state.seed_studio_widgets()
ss = st.session_state

VERSION_LABELS = {"v2": "V2 · Specific", "v3": "V3 · Seller-ready"}
LANGUAGE_LABELS = {"english": "English", "hinglish": "Hinglish"}
TONE_LABELS = {"simple": "Simple", "professional": "Professional"}
LENGTH_LABELS = {"standard": "Standard", "short": "Short"}

FIELD_GROUPS = {
    "Product": ["business_name", "product_name", "material_grade", "size", "wall_thickness", "length"],
    "Price and stock": ["unit_price", "available_quantity", "moq"],
    "Delivery": ["dispatch_location", "delivery_coverage", "dispatch_time"],
    "Terms": ["gst_freight", "payment_terms", "certifications"],
}

# --------------------------------------------------------------------------
# Start here
# --------------------------------------------------------------------------

with st.expander("Start here: 2-minute demo", expanded=ss.reply is None, icon=":material/play_circle:"):
    guide, overview = st.columns([3, 2], gap="large")
    with guide:
        st.markdown(
            "1. Click **Load sample enquiry** (the MS pipes enquiry is already loaded), then **Generate smart reply**. "
            "With no seller details, the reply asks for grade, thickness and length and states no price.\n"
            "2. Open **Prompt Lab** (top menu) and compare the three prompt versions on the same enquiry.\n"
            "3. Back here, open **Seller profile**, enter a fictional price (e.g. `₹68 per kg`) and available quantity, "
            "or click **Load demo profile**. Click **Regenerate**.\n"
            "4. Clear the price or click **Reset demo profile**, regenerate, and check that nothing is invented.\n"
            "5. Turn on **Edit reply**, type a claim like *guaranteed delivery in 2 days*, and watch the safety check flag it. "
            "Then tick the review box and use **Copy reply**.\n"
            "6. Explore **Seller personas** and **Trust and adoption**."
        )
    with overview:
        st.markdown(
            f"**The problem.** {PAIN_STATEMENT}\n\n"
            "**The solution.** Paste a buyer enquiry and get a clear reply that repeats the requirement, asks only "
            "the questions a quotation needs, and uses only facts the seller entered.\n\n"
            "**Safeguards.** No invented prices, stock or dates; an independent claim check; seller review before copying; "
            "nothing sent or stored."
        )

st.subheader("Smart Reply Studio")

inputs, output = st.columns([5, 6], gap="large")

# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

with inputs:
    with st.container(border=True):
        st.markdown("**1. Buyer enquiry**")
        st.text_area(
            "Buyer enquiry",
            key="w_enquiry",
            on_change=state.sync_enquiry,
            height=140,
            max_chars=2000,
            placeholder="Paste the buyer's message here, e.g. Need 200 MS pipes 1 inch, delivery Nagpur, send rate.",
            label_visibility="collapsed",
            help="Buyer text is treated as data. Instructions inside it are never followed.",
        )
        with st.container(horizontal=True, gap="small"):
            st.button("Load sample enquiry", icon=":material/description:", on_click=state.load_sample)
            with st.popover("More samples", icon=":material/library_books:"):
                st.caption("Each sample tests a different behaviour.")
                for i, (label, text) in enumerate(SAMPLE_ENQUIRIES.items()):
                    st.button(label, key=f"sample_{i}", on_click=state.load_sample, args=(text,), width="stretch")
            st.button("Clear form", icon=":material/backspace:", on_click=state.clear_form)

    with st.container(border=True):
        st.markdown("**2. Seller profile** · optional")
        st.caption("Leave anything you don't know blank. The reply only states facts entered here; blanks stay unknown.")
        options = state.demo_seller_options()
        with st.container(horizontal=True, gap="small", vertical_alignment="bottom"):
            st.selectbox("Fictional demo seller", list(options), format_func=options.get, key="w_demo_seller",
                         width=320)
            st.button("Load demo profile", icon=":material/person_add:", on_click=state.load_demo_profile)
            st.button("Reset demo profile", icon=":material/person_remove:", on_click=state.reset_demo_profile)
        if ss.demo_loaded:
            why = "; ".join(ss.demo_loaded["reasons"]) or "first listed product"
            st.caption(f":material/info: Fictional data loaded from the demo catalogue. "
                       f"Product picked by keyword retrieval ({md_escape(why)}).")

        filled = sum(1 for v in ss.seller.values() if v)
        with st.expander(f"Seller details · {filled} of {len(FIELD_LABELS)} filled", icon=":material/storefront:"):
            for tab, names in zip(st.tabs(list(FIELD_GROUPS)), FIELD_GROUPS.values()):
                with tab:
                    for name in names:
                        st.text_input(FIELD_LABELS[name], key=f"w_seller_{name}", on_change=state.sync_seller,
                                      args=(name,), max_chars=120, help=FIELD_HELP.get(name),
                                      placeholder="Unknown")

    with st.container(border=True):
        st.markdown("**3. Reply settings**")
        st.segmented_control("Prompt version", list(VERSION_LABELS), format_func=VERSION_LABELS.get,
                             key="w_set_version", on_change=state.sync_setting, args=("version",), required=True,
                             help="V1 (basic prompt) is shown only in Prompt Lab because it makes unsupported claims.")
        disabled = ss.settings["version"] != "v3"
        with st.container(horizontal=True, gap="medium"):
            st.segmented_control("Language", list(LANGUAGE_LABELS), format_func=LANGUAGE_LABELS.get,
                                 key="w_set_language", on_change=state.sync_setting, args=("language",),
                                 required=True, disabled=disabled)
            st.segmented_control("Tone", list(TONE_LABELS), format_func=TONE_LABELS.get, key="w_set_tone",
                                 on_change=state.sync_setting, args=("tone",), required=True, disabled=disabled)
            st.segmented_control("Length", list(LENGTH_LABELS), format_func=LENGTH_LABELS.get, key="w_set_length",
                                 on_change=state.sync_setting, args=("length",), required=True, disabled=disabled)
        st.toggle("Add optional clarifying questions", key="w_set_extra", on_change=state.sync_setting,
                  args=("extra",), disabled=disabled)
        if disabled:
            st.caption("V2 uses only the enquiry: no seller details, language or tone options. Switch to V3 for those.")
        st.button("Generate smart reply", type="primary", icon=":material/auto_awesome:", on_click=state.generate,
                  width="stretch")

# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

with output:
    if ss.flash:
        kind, message = ss.flash
        ss.flash = None
        {"success": st.success, "info": st.info, "error": st.error}[kind](message)
        if kind == "success":
            st.toast(message, icon=":material/check_circle:")

    if not ss.reply:
        with st.container(border=True):
            st.markdown("**Suggested reply**")
            st.info("Your reply will appear here. Add or load an enquiry, then click **Generate smart reply**.",
                    icon=":material/arrow_back:")
    else:
        reply = ss.reply
        result = reply["result"]

        if state.is_stale():
            with st.container(horizontal=True, vertical_alignment="center"):
                st.warning("The enquiry, seller profile or settings changed after this reply was made.",
                           icon=":material/update:")
                st.button("Regenerate", key="stale_regen", icon=":material/refresh:", on_click=state.generate)

        if ss.pending:
            with st.container(border=True):
                st.warning("You have edited this reply. Applying this change will replace your edits with a new draft.",
                           icon=":material/edit_off:")
                with st.container(horizontal=True, gap="small"):
                    st.button("Replace my edits", type="primary", on_click=state.apply_style, args=(ss.pending,))
                    st.button("Keep my edits", on_click=state.cancel_pending)

        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown(f"**Suggested reply** · {VERSION_LABELS.get(result.version, result.version)}")
                if reply["edited"]:
                    st.badge("Edited by you", icon=":material/edit:", color="violet")
            status_summary(result.items)

            editing = st.toggle("Edit reply", key="w_edit_mode", help="Your edits are kept until you regenerate or reset.")
            if editing:
                st.text_area("Edit the reply", key="w_reply", on_change=state.sync_reply_edit, height=380,
                             label_visibility="collapsed")
            else:
                with st.container(border=True):
                    st.markdown(md_multiline(reply["current"]))

            with st.container(horizontal=True, gap="small"):
                st.button("Regenerate", icon=":material/refresh:", on_click=state.generate,
                          help="Builds a fresh draft from the current inputs. Replaces edits.")
                st.button("Make shorter", icon=":material/short_text:", on_click=state.request_style, args=("shorter",))
                st.button("Use simpler English", icon=":material/translate:", on_click=state.request_style,
                          args=("simpler",))
                st.button("More professional", icon=":material/business_center:", on_click=state.request_style,
                          args=("professional",))
                st.button("Add clarifying questions", icon=":material/live_help:", on_click=state.request_style,
                          args=("questions",))
                st.button("Reset reply", icon=":material/undo:", on_click=state.reset_reply,
                          disabled=not reply["edited"], help="Discard your edits and return to the last generated draft.")

        findings = state.current_findings()
        with st.container(border=True):
            st.markdown("**Safety check** · runs on the text above, including your edits")
            render_findings(findings)

        with st.container(border=True):
            st.markdown("**Review and copy**")
            st.checkbox("I have reviewed this reply and it is correct to send", key="w_reviewed",
                        on_change=state.approve)
            blocked = has_errors(findings)
            if blocked:
                st.checkbox("I confirm the flagged statements are true and I am authorised to make them",
                            key="w_ack_claims")
            if ss.w_reviewed and (not blocked or ss.w_ack_claims):
                copy_button(reply["current"])
                st.caption("If the button can't reach your clipboard, use the copy icon on the box below, "
                           "or select the text and press Ctrl+C (long-press on mobile).")
                st.code(reply["current"], language=None, wrap_lines=True)
            else:
                st.caption(":material/lock: Copying unlocks after review" +
                           (" and confirmation of the flagged claims." if blocked else "."))
            st.caption("Smart Reply never sends messages. You paste the reply into your chat yourself.")

if ss.reply:
    result = ss.reply["result"]
    missing_col, why_col = st.columns(2, gap="large")
    with missing_col:
        with st.container(border=True):
            st.markdown("**Missing information**")
            st.caption("What was read from the enquiry, what came from your profile, and what still needs an answer.")
            render_items(result.items)
    with why_col:
        with st.container(border=True):
            st.markdown("**Why this reply works**")
            for line in result.rationale:
                st.markdown(f"- {md_escape(line)}")
            st.caption("Generated by rule-based simulation. No AI model or API was called.")

    m = ss.metrics
    with st.expander("Session metrics (this browser tab only, not stored)", icon=":material/monitoring:"):
        with st.container(horizontal=True):
            st.metric("Engine time", f"{m['last_ms']:.0f} ms")
            st.metric("Generated", m["generations"])
            st.metric("Regenerated", m["regenerations"])
            st.metric("Edits", m["edits"])
            st.metric("Approved for copy", m["approvals"])
            st.metric("Claims flagged", m["claims_detected"])
        if m["approve_seconds"]:
            st.caption(f"Time from generation to approval: last {m['approve_seconds'][-1]} s.")
