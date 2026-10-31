"""Streamlit chat UI for Parkha, on the offline rules backend (no AWS account needed).

streamlit run app.py
"""

from datetime import date

import streamlit as st

import brand
from parkha import assistant

brand.page("parkha")

EXAMPLES = [
    "I sprayed chlorantraniliprole on my brinjal yesterday. When can I harvest?",
    "hijo cauli ma neem chhareko, kahile tipna milchha?",
    "गोलभेडामा टुटा लाग्यो, के गर्ने?",
    "cabbage diamondback moth what to spray",
    "Is Furadan banned?",
]

with st.sidebar:
    st.header("Try a question")
    picked = None
    for q in EXAMPLES:
        if st.button(q, width="stretch"):
            picked = q
    st.divider()
    today = st.date_input("Today is", value=date.today())
    st.caption(
        "Runs on the offline rules backend: the same tools, label book and safety gate as the Bedrock path. "
        "Harvest dates come from the label waiting period, never from a model."
    )


st.session_state.setdefault("history", [])
for role, text in st.session_state.history:
    with st.chat_message(role, avatar=brand.avatar(role, "parkha")):
        st.markdown(text)

question = st.chat_input("Ask about a pest, a product or when it is safe to harvest") or picked
if question:
    st.chat_message("user", avatar=brand.avatar("user", "parkha")).markdown(question)
    reply = assistant.ask(question, backend="rules", today=today)
    body = reply.answer
    if reply.sources:
        body += "\n\n**Sources**\n" + "\n".join(
            f"- [{s.get('title', s.get('id'))}]({s.get('url', '')})" for s in reply.sources
        )
    with st.chat_message("assistant", avatar=brand.avatar("assistant", "parkha")):
        st.markdown(body)
    st.session_state.history += [("user", question), ("assistant", body)]

brand.footer()
