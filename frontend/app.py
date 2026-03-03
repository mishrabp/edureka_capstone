"""
Clinical RAG — Streamlit Frontend

Layout:
  Sidebar (LEFT)  → RAG management only: upload, index, document list, reset
  Main area       → RAG gate → starter prompts → chat (with clear chat button)

Chat is blocked until at least one document is indexed.
"""
from __future__ import annotations

import sys
import os
import glob

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import api_client as client

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Clinical RAG Assistant | Secure Medical Q&A",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="auto", # Visible on desktop, collapsed on mobile
)

# ── Prompt library loader ─────────────────────────────────────────────────────

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def load_prompt_library() -> list[dict]:
    library = []
    for path in sorted(glob.glob(os.path.join(PROMPTS_DIR, "*.txt"))):
        meta = {"title": "", "category": "", "icon": "💬", "description": "", "prompts": []}
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        first_heading = True
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            if line.startswith("# Category:"):
                meta["category"] = line.split(":", 1)[1].strip()
            elif line.startswith("# Icon:"):
                meta["icon"] = line.split(":", 1)[1].strip()
            elif line.startswith("# Description:"):
                meta["description"] = line.split(":", 1)[1].strip()
            elif line.startswith("#"):
                if first_heading:
                    meta["title"] = line.lstrip("#").strip()
                    first_heading = False
            else:
                meta["prompts"].append(line.strip())
        if meta["prompts"]:
            library.append(meta)
    return library


# ── Custom CSS (Mobile-First, ADA, SEO) ────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ChatGPT-Style Palette & Base */
:root {
    --bg-main: #f9f9f9;    /* Light Gray Background */
    --bg-sidebar: #f1f1f1; /* Slightly darker sidebar */
    --bg-user-bubble: #ffffff;
    --text-main: #1a1a1b;  /* Strict Charcoal (WCAG AAA) */
    --text-muted: #404040; /* High Contrast Muted */
    --accent: #005fb8;     /* Accessible High-Contrast Blue */
    --border: #d1d1d1;     /* Clearer visible borders */
}

html, body, [class*="css"] { 
    font-family: 'Inter', sans-serif; 
    background-color: var(--bg-main);
    color: var(--text-main);
    line-height: 1.6;
    letter-spacing: 0.01rem;
}

.stApp { background-color: var(--bg-main); font-size: 1rem; }

/* Main layout / Mobile-First Responsive */
.block-container {
    max-width: 850px !important;
    padding-top: 2rem !important;
    padding-bottom: 2rem !important; /* Reduced to allow auto-scroll anchoring */
    margin: 0 auto;
}

/* Tablet & Mobile Overrides */
@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    .stChatInputContainer {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
}

/* Sidebar styling for ADA/Accessibility */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border);
}

/* Hide Streamlit components for a cleaner look */
#MainMenu, footer, header { visibility: hidden; }

/* SEO hidden but readable h1 */
.seo-h1 {
    position: absolute; width: 1px; height: 1px;
    padding: 0; margin: -1px; overflow: hidden;
    clip: rect(0, 0, 0, 0); border: 0;
}

/* RAG gate empty-state center card */
.rag-gate {
    background: #ffffff;
    border: 2px solid var(--border);
    border-radius: 20px; padding: 2rem;
    text-align: center; margin: 3rem auto;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
}
.rag-gate h2 { color: #000000; font-size: 1.6rem; font-weight: 700; margin-bottom: 1.2rem; }
.rag-gate p  { color: var(--text-muted); font-size: 1rem; line-height: 1.6; }
.rag-gate .step {
    background: #f8f9fa; border: 1px solid var(--border); border-radius: 12px;
    padding: 1rem 1.4rem; margin: 0.8rem 0; text-align: left;
    color: var(--text-main); font-size: 1rem;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}
.rag-gate .step span { color: var(--accent); font-weight: 700; margin-right: 1rem; font-size: 1.2rem; }

/* Status Badges */
.status-badge {
    display: inline-block; padding: 6px 14px;
    border-radius: 8px; font-size: 0.85rem; font-weight: 700;
}
.status-ok  { background: #e6fffa; color: #0694a2; border: 1px solid #b2f5ea; }
.status-err { background: #fff5f5; color: #e53e3e; border: 1px solid #feb2b2; }

/* Source Cards (ADA compliant labels) */
.source-card {
    background: #ffffff; border: 2px solid var(--border);
    border-radius: 12px; padding: 1.2rem; margin-top: 1rem;
    font-size: 1rem; color: var(--text-muted);
    line-height: 1.6;
}
.source-card strong { color: #000000; font-weight: 800; }

/* Step Trace (Monospaced) */
.step-trace {
    background: #f1f3f5; border: 1px solid var(--border);
    border-radius: 8px; padding: 1rem;
    font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; 
    color: #495057; line-height: 1.6;
}

/* Doc List Items */
.doc-item {
    background: transparent; border: 1px solid transparent;
    border-radius: 10px; padding: 0.8rem 1rem;
    margin-bottom: 0.6rem; font-size: 0.95rem;
    transition: background 0.2s, border-color 0.2s;
}
.doc-item:hover { background: #2a2a2a; border-color: var(--border); }

/* Starter Prompt Cards (Responsive Grid) */
.prompt-category-header {
    background: transparent; border: 1px solid var(--border);
    border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem;
    min-height: 100px; display: flex; flex-direction: column; justify-content: center;
}
.prompt-category-header .cat-title { color: #000000; font-weight: 800; font-size: 1.3rem; }
.prompt-category-header .cat-desc  { color: var(--text-muted); font-size: 1rem; margin-top: 8px; }

/* Chat Bubble UI */
.stChatMessage { 
    background-color: transparent !important; 
    border: none !important; 
    padding: 1.5rem 0 !important; 
}

/* User Message Bubble */
[data-testid="stChatMessage"]:has(div[aria-label="user message"]) > div {
    background-color: var(--bg-user-bubble) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    padding: 1.2rem 1.6rem !important;
    display: inline-block !important;
    max-width: 90% !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

/* Chat Input Bar - Fixed Bottom */
.stChatInputContainer {
    padding-bottom: 2rem !important;
}
.stChatInputContainer > div {
    border: 2px solid var(--border) !important;
    border-radius: 18px !important;
    background-color: #ffffff !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06) !important;
}

/* Scale for Smaller Screens */
@media (max-width: 480px) {
    .rag-gate h2 { font-size: 1.2rem; }
    .rag-gate .step { font-size: 0.8rem; }
}
</style>
""", unsafe_allow_html=True)

# ── SEO Elements ─────────────────────────────────────────────────────────────

st.markdown('<h1 class="seo-h1">Clinical Knowledge Assistant - AI-Powered Medical Document Q&A</h1>', unsafe_allow_html=True)
st.markdown("""
<head>
    <meta name="description" content="Secure, HIPAA-inspired clinical RAG assistant. Ask questions grounded in your clinical guidelines, patient records, and lab results.">
    <meta name="keywords" content="Medical AI, Clinical RAG, Healthcare Documentation, Patient Records Search, Medical Assistant">
</head>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())
if "docs" not in st.session_state:
    st.session_state.docs = []
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "rag_ready" not in st.session_state:
    st.session_state.rag_ready = False


def refresh_docs():
    try:
        st.session_state.docs = client.list_documents()
        st.session_state.rag_ready = len(st.session_state.docs) > 0
    except Exception:
        st.session_state.docs = []
        st.session_state.rag_ready = False


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — RAG management only
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🏥 Clinical RAG")
    st.caption("Knowledge base management")

    # Backend health badge
    try:
        h = client.health()
        docs_n = h.get("docs_indexed", 0)
        badge_cls = "status-ok"
        badge_txt = f"● Connected · {docs_n} doc(s) indexed"
    except Exception:
        badge_cls = "status-err"
        badge_txt = "✕ Backend offline — run: bash run.sh"
    st.markdown(
        f'<span class="status-badge {badge_cls}">{badge_txt}</span>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("### 📂 Upload Documents")

    uploaded_files = st.file_uploader(
        "Select files",
        type=["pdf", "txt", "csv", "xlsx", "xls"],
        accept_multiple_files=True,
        help="Supported: PDF, TXT, CSV, XLSX/XLS",
    )

    if st.button("⬆️  Index documents", use_container_width=True, type="primary"):
        if not uploaded_files:
            st.warning("Select at least one file first.")
        else:
            for uf in uploaded_files:
                with st.spinner(f"Indexing {uf.name}…"):
                    try:
                        res = client.upload_document(uf.read(), uf.name)
                        st.success(f"✓ **{uf.name}** — {res['chunks_indexed']} chunks")
                    except Exception as e:
                        st.error(f"✗ {uf.name}: {e}")
            refresh_docs()
            st.rerun()

    st.divider()
    st.markdown("### 📚 Indexed Documents")
    refresh_docs()

    if not st.session_state.docs:
        st.caption("No documents indexed yet.")
    else:
        for doc in st.session_state.docs:
            col1, col2 = st.columns([4, 1])
            with col1:
                ext_emoji = {"pdf": "📄", "txt": "📝", "csv": "📊", "xlsx": "📊", "xls": "📊"}
                emoji = ext_emoji.get(doc.get("file_type", ""), "📎")
                st.markdown(
                    f'<div class="doc-item">{emoji} <strong>{doc["filename"]}</strong><br>'
                    f'<span style="color:#7d8590">{doc["chunks"]} chunks</span></div>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("🗑️", key=f"del_{doc['doc_id']}", help="Remove"):
                    try:
                        client.delete_document(doc["doc_id"])
                        refresh_docs()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    st.divider()
    st.markdown("### ⚙️ Actions")
    if st.session_state.messages:
        if st.button("🗑️ Clear chat history", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    confirm = st.checkbox("Confirm: delete ALL docs", key="confirm_reset")
    reset_btn = st.button(
        "🔄 Truncate & Rebuild RAG DB",
        use_container_width=True,
        disabled=not confirm,
        type="primary",
        key="reset_db_btn",
    )
    if reset_btn and confirm:
        with st.spinner("Wiping vector store…"):
            try:
                result = client.reset_store()
                removed = result.get("removed_documents", 0)
                st.success(f"✓ Reset — {removed} doc(s) removed. Re-upload to rebuild.")
                st.session_state.messages = []
                st.session_state.rag_ready = False
                refresh_docs()
                st.session_state["confirm_reset"] = False
                st.rerun()
            except Exception as e:
                st.error(f"Reset failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ═══════════════════════════════════════════════════════════════════════════════

# ── Redesigned Header ─────────────────────────────────────────────────────────

# ChatGPT doesn't have a giant header. We'll use a centered workspace title 
# when the chat is empty, otherwise we just show the messages.

if not st.session_state.messages:
    st.markdown('<h2 style="text-align:center; margin-top:3rem; font-weight:700">How can I help you today?</h2>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#888; margin-bottom:3rem">Grounded Clinical Assistant · Clinical Guidelines & Records</p>', unsafe_allow_html=True)


# ── RAG Gate ──────────────────────────────────────────────────────────────────
# Block everything until the knowledge base has at least one document.

if not st.session_state.rag_ready:
    st.markdown("""
    <div class="rag-gate">
        <h2>📭 Knowledge Base is Empty</h2>
        <p>The assistant can only answer from documents you upload.<br>
        Please build your RAG database first:</p>
        <div class="step"><span>①</span> Use the sidebar to <strong>upload</strong> your clinical documents (PDF, TXT, CSV, XLSX)</div>
        <div class="step"><span>②</span> Click <strong>⬆️ Index documents</strong> to process and embed them</div>
        <div class="step"><span>③</span> Return here once indexing is complete — the chat will unlock automatically</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Past chat messages ────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(f"📎 {len(msg['sources'])} source(s)", expanded=False):
                for src in msg["sources"]:
                    page_info = f" · page {src['page']}" if src.get("page") is not None else ""
                    st.markdown(
                        f'<div class="source-card">'
                        f'<strong>{src["filename"]}</strong>{page_info}<br>'
                        f'{src["excerpt"][:300]}…</div>',
                        unsafe_allow_html=True,
                    )

        if msg["role"] == "assistant" and msg.get("agent_steps"):
            with st.expander("🔍 Agent reasoning trace", expanded=False):
                st.markdown(
                    '<div class="step-trace">' + "<br>".join(msg["agent_steps"]) + '</div>',
                    unsafe_allow_html=True,
                )


# ── Starter prompts (only when chat is empty) ─────────────────────────────────

if not st.session_state.messages:
    prompt_library = load_prompt_library()
    if prompt_library:
        st.markdown(
            '<p style="text-align:center;color:#a8b2d8;font-size:1rem;margin-bottom:1rem">'
            '👇 Choose a topic to get started, or type your own question below'
            '</p>',
            unsafe_allow_html=True,
        )
        cols = st.columns(3)
        for idx, cat in enumerate(prompt_library):
            with cols[idx % 3]:
                st.markdown(
                    f'<div class="prompt-category-header">'
                    f'<span style="font-size:1.3rem">{cat["icon"]}</span>&nbsp;&nbsp;'
                    f'<span class="cat-title">{cat["title"]}</span><br>'
                    f'<span class="cat-desc">{cat["description"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                for p in cat["prompts"][:3]:
                    short = p if len(p) <= 65 else p[:62] + "…"
                    if st.button(short, key=f"card_{cat['title']}_{p[:30]}", use_container_width=True):
                        st.session_state.pending_prompt = p

        st.markdown("---")


# (Chat controls relocated to sidebar)


# ── Auto-Scroll Helper ───────────────────────────────────────────────────────

def auto_scroll():
    # Subtle JS tool to force scroll-to-bottom
    st.components.v1.html("""
        <script>
            window.parent.document.querySelectorAll('[data-testid="stMain"]').forEach(el => {
                el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
            });
        </script>
    """, height=0)

# ── Send a prompt (from button click or typed input) ──────────────────────────

def _send_prompt(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            try:
                result = client.ask(prompt, session_id=st.session_state.session_id)
                answer = result.get("answer", "I could not generate a response.")
                sources = result.get("sources", [])
                agent_steps = result.get("agent_steps", [])

                st.markdown(answer)

                if sources:
                    with st.expander(f"📎 {len(sources)} source(s)", expanded=False):
                        for src in sources:
                            page_info = f" · page {src['page']}" if src.get("page") is not None else ""
                            st.markdown(
                                f'<div class="source-card" role="note" aria-label="Reference Source">'
                                f'<strong>{src["filename"]}</strong>{page_info}<br>'
                                f'{src["excerpt"][:300]}…</div>',
                                unsafe_allow_html=True,
                            )

                if agent_steps:
                    with st.expander("🔍 Agent reasoning trace", expanded=False):
                        st.markdown(
                            '<div class="step-trace" role="status" aria-label="Agent Reasoning Trace">' + "<br>".join(agent_steps) + '</div>',
                            unsafe_allow_html=True,
                        )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "agent_steps": agent_steps,
                })
                auto_scroll()

            except Exception as e:
                err_str = str(e)
                if "rag_empty" in err_str or "503" in err_str:
                    err_msg = "⚠️ The knowledge base is empty. Please upload and index documents first."
                else:
                    err_msg = f"⚠️ Error: {err_str}"
                st.error(err_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": err_msg,
                    "sources": [],
                    "agent_steps": [],
                })
                auto_scroll()


# Fire pending prompt or typed input
if typed_prompt := st.chat_input("Ask a clinical question about your documents…"):
    _send_prompt(typed_prompt)

elif st.session_state.pending_prompt:
    queued = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    _send_prompt(queued)
    st.rerun()
