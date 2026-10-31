"""Streamlit chat UI for Parkha, on the offline rules backend (no AWS account needed).

streamlit run app.py
"""

from datetime import date

import streamlit as st

from parkha import assistant

st.set_page_config(page_title="Parkha", page_icon="🌱", layout="centered")

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
    show_trace = st.toggle("Show tool calls and the safety gate", value=False)
    st.caption(
        "Runs on the offline rules backend: the same tools, label book and safety gate as the Bedrock path. "
        "Harvest dates come from the label waiting period, never from a model."
    )

st.title("Parkha (पर्ख)")
st.caption(
    "Pest advice for Nepali vegetable farmers that never skips the waiting period. English, Nepali or romanised Nepali."
)

st.session_state.setdefault("history", [])
for role, text, extra in st.session_state.history:
    with st.chat_message(role):
        st.markdown(text)
        if extra and show_trace:
            with st.expander("How it decided"):
                st.json(extra)

question = st.chat_input("Ask about a pest, a product or when it is safe to harvest") or picked
if question:
    st.chat_message("user").markdown(question)
    reply = assistant.ask(question, backend="rules", today=today)
    body = reply.answer
    if reply.sources:
        body += "\n\n**Sources**\n" + "\n".join(
            f"- [{s.get('title', s.get('id'))}]({s.get('url', '')})" for s in reply.sources
        )
    trace = {
        k: v
        for k, v in reply.public(debug=True).items()
        if k in ("tool_calls", "tool_results", "gate_problems", "refusal")
    }
    with st.chat_message("assistant"):
        st.markdown(body)
        if show_trace:
            with st.expander("How it decided", expanded=True):
                st.json(trace)
    st.session_state.history += [("user", question, None), ("assistant", body, trace)]
