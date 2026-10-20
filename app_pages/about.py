import streamlit as st

from smart_reply.content import DISCLOSURE, PAIN_STATEMENT, RESEARCH

st.subheader("About and demo guide")

with st.container(border=True):
    st.markdown("#### Product overview")
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown(f"**The seller problem**  \n{PAIN_STATEMENT}")
        st.markdown("**Selected persona**  \nThe small industrial manufacturer: deep product knowledge, limited "
                    "confidence writing professional English, and enquiries that rarely include every specification.")
        st.markdown("**The solution**  \nSmart Reply reads the enquiry, finds the missing details, and drafts a short, "
                    "plain-English reply that repeats the requirement, asks only what a quotation needs, and uses only "
                    "facts the seller has entered.")
    with b:
        st.markdown("**Trust safeguards**\n"
                    "- No invented prices, stock, dates, freight or certifications\n"
                    "- Independent claim check on the final text, including edits\n"
                    "- Review required before copying; nothing is ever sent automatically\n"
                    "- Buyer text can't change the rules\n"
                    "- Nothing stored; fictional data only")
        st.markdown("**Future product opportunity**  \nDraft the reply inside the lead manager before the seller opens "
                    "the lead, so replying becomes review-and-send within minutes, with the seller's catalogue as "
                    "verified context.")

with st.container(border=True):
    st.markdown("#### 2-minute demo guide")
    st.markdown(
        "1. **Smart Reply Studio:** load the MS pipes enquiry and click **Generate smart reply**.\n"
        "2. **Prompt Lab:** compare all three prompt versions on the same enquiry.\n"
        "3. **Studio:** enter a fictional price and available quantity (or load the demo profile) and regenerate.\n"
        "4. Remove or change those details and regenerate; confirm nothing is invented.\n"
        "5. Edit the reply, then review it and use **Copy reply**.\n"
        "6. Explore **Seller personas** and **Trust and adoption**."
    )
    st.caption("No login, installation or API key needed.")

with st.container(border=True):
    st.markdown("#### How the prototype works")
    st.markdown(
        """
```mermaid
flowchart LR
    A[Buyer enquiry<br/>untrusted text] --> B[Rule-based extraction<br/>product, quantity, size,<br/>destination, intents]
    S[Seller profile<br/>optional, seller-entered] --> C
    B --> C[Reply composer<br/>prompt version V1, V2 or V3<br/>language and tone]
    C --> D[Independent validator<br/>price, stock, delivery,<br/>guarantee, freight checks]
    D --> E[Seller reviews,<br/>edits and copies]
```
"""
    )
    st.markdown(
        "- **Extraction:** configurable keyword and unit patterns for MS pipes, fasteners, steel sections, HDPE granules "
        "and fabrication. Anything it can't read reliably is marked unconfirmed or missing.\n"
        "- **Composition:** templates plus verified seller facts. The selected prompt version changes how the reply is built.\n"
        "- **Validation:** runs separately on the final text and flags unsupported claims.\n"
        "- **Honest scope:** this is rule-based simulation, not an AI model, and not a claim of natural-language understanding."
    )

with st.container(border=True):
    st.markdown("#### Future architecture (not built)")
    st.markdown(
        "A production version would replace the rules with a constrained LLM grounded in the seller's own data:\n"
        "1. **Seller catalogue store:** structured, validated product records (schema checks for grades, sizes, "
        "price ranges), split into one chunk per product with seller and verification metadata.\n"
        "2. **Retrieval:** hybrid search (keyword + semantic) filtered by product category and delivery region, "
        "then re-ranking to pick the best catalogue entries for the enquiry.\n"
        "3. **Generation:** the seller-ready prompt (V3) with only retrieved, verified facts in context.\n"
        "4. **Validation and review:** the same claim checks plus seller approval before sending.\n\n"
        "The **fictional demo catalogue** in this prototype is a small stand-in: it picks the best-matching product "
        "by keyword overlap, with no embeddings or external services."
    )

with st.container(border=True):
    st.markdown("#### Secondary research used")
    st.caption("Figures from third-party sources, collected during assignment research. Not independently verified for "
               "this prototype, and never used inside generated replies.")
    for r in RESEARCH:
        st.markdown(f"- {r['claim']} *Used for: {r['use']}* — [{r['source']}]({r['url']})")

with st.container(border=True):
    st.markdown("#### Limitations")
    st.markdown(
        "- Rule-based extraction covers five categories and common phrasings; unusual wording may not be understood.\n"
        "- The validator detects common claim patterns but can't guarantee it catches every unsupported statement.\n"
        "- Hinglish templates haven't been reviewed with native-speaking sellers.\n"
        "- Personas, priorities and targets are hypotheses; no real seller research has been done yet.\n"
        "- No persistence: everything resets when the browser tab closes."
    )
    st.caption(DISCLOSURE)
