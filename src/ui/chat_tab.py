import html

import streamlit as st

from ..brain_chat import ask_brain
from ..vector_store import load_vector_index


def render_sources(sources):
    if not sources:
        return
    with st.expander("Sources used"):
        for idx, source in enumerate(sources, start=1):
            st.markdown("**["+str(idx)+"] "+source.get("source", "Unknown")+"** — "+source.get("method", "text")+" · score "+str(round(source.get("score", 0), 3)))
            st.caption(source.get("text", "")[:700])


def render_message(role, content):
    safe_content = html.escape(content or "").replace("\n", "<br>")
    if role == "user":
        avatar = "U"
        label = "You"
        cls = "user"
    else:
        avatar = "S"
        label = "Second Brain"
        cls = "assistant"
    st.markdown(
        '<div class="sb-chat-row '+cls+'">'
        '<div class="sb-chat-avatar">'+avatar+'</div>'
        '<div class="sb-chat-stack">'
        '<div class="sb-chat-label">'+label+'</div>'
        '<div class="sb-chat-bubble">'+safe_content+'</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_chat_tab(router_cfg, router_model):
    st.markdown("""
<style>
.sb-chat-wrap { max-width: 980px; margin: 0 auto; }
.sb-chat-hero { max-width: 980px; margin: 0 auto 18px auto; padding: 20px 22px; border: 1px solid var(--sb-border, #e5e7eb); border-radius: 22px; background: var(--sb-panel, linear-gradient(135deg,#ffffff,#f7f7f8)); box-shadow: 0 10px 30px rgba(15,23,42,0.07); }
.sb-chat-title { font-size: 1.85rem; font-weight: 850; letter-spacing: -0.03em; color: var(--sb-text, #111827); }
.sb-chat-subtitle { color: var(--sb-muted, #6b7280); margin-top: 4px; }
.sb-chat-row { max-width: 980px; margin: 18px auto; display: flex; gap: 12px; align-items: flex-start; }
.sb-chat-row.user { flex-direction: row-reverse; }
.sb-chat-avatar { width: 34px; height: 34px; flex: 0 0 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 800; background: #10a37f; color: white; box-shadow: 0 3px 12px rgba(16,163,127,0.28); }
.sb-chat-row.user .sb-chat-avatar { background: #2563eb; box-shadow: 0 3px 12px rgba(37,99,235,0.28); }
.sb-chat-stack { max-width: min(760px, calc(100% - 52px)); }
.sb-chat-row.user .sb-chat-stack { display: flex; flex-direction: column; align-items: flex-end; }
.sb-chat-label { font-size: 0.78rem; font-weight: 700; color: var(--sb-muted, #6b7280); margin: 0 0 5px 2px; }
.sb-chat-bubble { padding: 14px 17px; border-radius: 20px; line-height: 1.58; font-size: 0.98rem; border: 1px solid var(--sb-border, #e5e7eb); background: var(--sb-assistant, #f7f7f8); color: var(--sb-text, #111827); box-shadow: 0 2px 10px rgba(15,23,42,0.04); overflow-wrap: anywhere; }
.sb-chat-row.user .sb-chat-bubble { background: #2563eb; color: #ffffff; border-color: #2563eb; border-bottom-right-radius: 6px; }
.sb-chat-row.assistant .sb-chat-bubble { border-bottom-left-radius: 6px; }
.sb-chat-input-card { max-width: 980px; margin: 22px auto 0 auto; padding: 12px; border: 1px solid var(--sb-border, #e5e7eb); border-radius: 22px; background: var(--sb-card, #ffffff); box-shadow: 0 12px 35px rgba(15,23,42,0.09); }
.sb-chat-empty { max-width: 720px; margin: 18px auto; text-align: center; color: var(--sb-muted, #6b7280); }
</style>
""", unsafe_allow_html=True)
    st.markdown('<div class="sb-chat-hero"><div class="sb-chat-title">Chat With My Brain</div><div class="sb-chat-subtitle">Ask across your extracted notes, memory chunks, and knowledge graph context.</div></div>', unsafe_allow_html=True)

    index = load_vector_index()
    chunk_count = len(index.get("chunks", []))
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.metric("Memory Chunks", chunk_count)
    with c2:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.brain_chat_messages = []
            st.success("Chat cleared.")
    with c3:
        top_k = st.slider("Context chunks", min_value=3, max_value=12, value=6, help="How much memory context to retrieve per question.")

    if "brain_chat_messages" not in st.session_state:
        st.session_state.brain_chat_messages = []

    if not chunk_count:
        st.info("No text memory chunks yet. Ingest a document first. Existing knowledge graph nodes are still searched as graph context.")

    if not st.session_state.brain_chat_messages:
        st.markdown('<div class="sb-chat-empty">Start with a question like “What are the main ideas in my notes?”</div>', unsafe_allow_html=True)

    for message in st.session_state.brain_chat_messages:
        render_message(message["role"], message["content"])
        if message.get("sources"):
            render_sources(message.get("sources", []))

    st.markdown('<div class="sb-chat-input-card">', unsafe_allow_html=True)
    if "brain_chat_input" not in st.session_state:
        st.session_state.brain_chat_input = ""
    c_input, c_send = st.columns([5, 1])
    with c_input:
        question = st.text_input("Ask your second brain...", key="brain_chat_input", label_visibility="collapsed", placeholder="Message your second brain...")
    with c_send:
        send = st.button("Send", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if not send or not question.strip():
        with st.expander("Try questions"):
            st.markdown("- What are the main topics in my brain?")
            st.markdown("- How are these ideas connected?")
            st.markdown("- What should I study next based on my notes?")
            st.markdown("- Summarize what I know about a topic.")
        return

    question = question.strip()
    st.session_state.brain_chat_messages.append({"role": "user", "content": question})
    render_message("user", question)

    with st.spinner("Searching memory and asking 9Router..."):
        response = ask_brain(router_cfg, question, st.session_state.brain_chat_messages[:-1], model_override=router_model, top_k=top_k)
    if response.get("success"):
        answer = response.get("answer", "")
        sources = response.get("results", [])
        render_message("assistant", answer)
        render_sources(sources)
        st.caption(str(response.get("elapsed", 0))+"s | Model: "+str(response.get("model", "")))
        st.session_state.brain_chat_messages.append({"role": "assistant", "content": answer, "sources": sources})
    else:
        error = "Brain chat failed: "+response.get("error", "Unknown error")
        st.error(error)
        st.session_state.brain_chat_messages.append({"role": "assistant", "content": error})
