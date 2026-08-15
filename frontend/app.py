"""
app.py — DocMind Streamlit frontend.

This file is UI + session state only. Every piece of RAG logic (retrieval,
generation, citations) lives in the FastAPI backend — see api_client.py for
the thin HTTP layer that connects the two.

Run standalone:
    streamlit run app.py
(with the backend already running — see README)
"""

import streamlit as st
import style
import api_client
from api_client import APIError

st.set_page_config(
    page_title="DocMind — Document Q&A",
    page_icon="◆",
    layout="centered",
    initial_sidebar_state="collapsed",
)
style.inject(st)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {question, answer, grounded, sources}
if "active_document" not in st.session_state:
    st.session_state.active_document = None
if "insights" not in st.session_state:
    st.session_state.insights = None
if "backend_status" not in st.session_state:
    st.session_state.backend_status = None


def refresh_active_document():
    try:
        result = api_client.get_active_document()
        st.session_state.active_document = result.get("document")
    except APIError:
        st.session_state.active_document = None


def refresh_backend_status():
    try:
        st.session_state.backend_status = api_client.check_health()
    except APIError as e:
        st.session_state.backend_status = {"error": str(e)}


if st.session_state.backend_status is None:
    refresh_backend_status()
if st.session_state.active_document is None:
    refresh_active_document()

backend_ok = st.session_state.backend_status and "error" not in st.session_state.backend_status
groq_configured = backend_ok and st.session_state.backend_status.get("groq_configured", False)

# ---------------------------------------------------------------------------
# Brand row
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="dm-brand fade-in">
      <div class="dm-brand-mark">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="white"/>
        </svg>
      </div>
      <span class="dm-brand-name">DocMind</span>
      <span class="dm-brand-tag">Document Q&amp;A</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="dm-hero fade-in">
      <div>
        <span class="eyebrow">RAG-Powered Document Intelligence</span>
        <h1>Ask your documents<br>anything.</h1>
        <p class="dm-sub">
          Upload a PDF and get grounded answers with page-level source citations —
          drawn only from what's actually in the document, never invented.
        </p>
        <div class="dm-note">
          Answers are generated from retrieved passages, not general knowledge.
          Every claim traces back to a specific page you can verify yourself.
        </div>
      </div>
      <div class="doc-panel-wrap">
        <div class="doc-panel">
          <div class="doc-citation-pin">Page 14</div>
          <div class="doc-icon-wrap">
            <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M16 6h24l12 12v40a2 2 0 0 1-2 2H16a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z" fill="url(#docGrad)" opacity="0.9"/>
              <path d="M40 6v10a2 2 0 0 0 2 2h10" stroke="rgba(255,255,255,0.5)" stroke-width="1.5"/>
              <circle cx="40" cy="42" r="13" fill="rgba(20,18,40,0.85)" stroke="var(--accent-2)" stroke-width="2"/>
              <path d="M35 42l3.5 3.5L46 38" stroke="var(--accent-2)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
              <defs>
                <linearGradient id="docGrad" x1="10" y1="6" x2="52" y2="60" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#8B7CFF"/><stop offset="1" stop-color="#4FD1E8"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="doc-footer-tag">Retrieval&nbsp;<b>Semantic</b>&nbsp;·&nbsp;Grounding&nbsp;<b>Page-cited</b></div>
        </div>
      </div>
    </div>
    <hr class="hairline">
    """,
    unsafe_allow_html=True,
)

if not backend_ok:
    error_msg = st.session_state.backend_status.get('error', 'Unknown error') if st.session_state.backend_status else 'Checking...'
    st.markdown(
        f"""
        <div class="dm-alert dm-alert-error fade-in">
          <div class="dm-alert-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <div class="dm-alert-body">
            <span class="eyebrow">Backend unavailable</span>
            <p>{error_msg} Start the FastAPI backend (see README) and reload this page.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
elif not groq_configured:
    st.markdown(
        """
        <div class="dm-alert dm-alert-warning fade-in">
          <div class="dm-alert-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 9v4"></path><path d="M12 17h.01"></path>
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"></path>
            </svg>
          </div>
          <div class="dm-alert-body">
            <span class="eyebrow">GROQ_API_KEY not configured</span>
            <p>The backend is running, but no Groq API key is set, so question-answering
            and document insights are disabled. Document upload still works. Add your
            key to <code>.env</code> (see <code>.env.example</code>) and restart the backend.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# How it works
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="section-head fade-in"><span class="eyebrow">Pipeline</span>'
    '<h3>How DocMind works</h3></div>',
    unsafe_allow_html=True,
)

steps = [
    ("01", "Upload", "Drop in a PDF — DocMind extracts text while preserving page numbers."),
    ("02", "Chunk & embed", "Text is split into meaningful passages and converted to vectors."),
    ("03", "Index", "Chunks and their page metadata are stored in a vector database."),
    ("04", "Ask", "Your question is embedded and matched against the indexed passages."),
    ("05", "Retrieve", "The most relevant chunks are pulled — not the whole document."),
    ("06", "Answer + cite", "An LLM answers using only that context, with page citations."),
]
step_html = '<div class="step-grid">'
for num, title, desc in steps:
    step_html += f"""<div class="step-card"><div class="step-num">{num}</div>
    <div class="step-title">{title}</div><p class="step-desc">{desc}</p></div>"""
step_html += "</div>"
st.markdown(step_html, unsafe_allow_html=True)

st.markdown('<hr class="hairline">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Document upload / management
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="section-head fade-in"><span class="eyebrow">Document</span>'
    '<h3>Upload a document</h3></div>',
    unsafe_allow_html=True,
)

active_doc = st.session_state.active_document

if active_doc:
    size_kb = active_doc["file_size_bytes"] / 1024
    st.markdown(
        f"""
        <div class="dm-card fade-in">
          <div class="doc-status-row">
            <div class="doc-status-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <path d="M14 2v6h6"></path><path d="m9 15 2 2 4-4"></path>
              </svg>
            </div>
            <div style="flex:1; min-width:0;">
              <span class="eyebrow" style="color:var(--green);">Active document</span>
              <div class="doc-status-name">{active_doc['filename']}</div>
            </div>
          </div>
          <div class="spec-grid">
            <div class="spec-item"><div class="spec-key">Pages</div><div class="spec-val">{active_doc['num_pages']}</div></div>
            <div class="spec-item"><div class="spec-key">Chunks indexed</div><div class="spec-val">{active_doc['num_chunks']}</div></div>
            <div class="spec-item"><div class="spec-key">File size</div><div class="spec-val">{size_kb:.0f} KB</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("↺  Clear document", use_container_width=True):
            try:
                api_client.clear_document()
                st.session_state.active_document = None
                st.session_state.chat_history = []
                st.session_state.insights = None
                st.rerun()
            except APIError as e:
                st.error(str(e))
    with col2:
        if st.button("✦  Document insights", use_container_width=True, disabled=not groq_configured):
            with st.spinner("Reading the document..."):
                try:
                    st.session_state.insights = api_client.get_insights()
                except APIError as e:
                    st.error(str(e))

    if st.session_state.insights:
        pages_used = ", ".join(str(p) for p in st.session_state.insights["sample_pages_used"])
        st.markdown(
            f"""
            <div class="dm-card dm-card-tight dm-card-accent fade-in" style="margin-top:1rem;">
              <span class="eyebrow">Document insights</span>
              <p style="margin:0.65rem 0 0.5rem 0; font-size:0.93rem; line-height:1.6; overflow-wrap:break-word;">{st.session_state.insights['overview']}</p>
              <span class="mono" style="font-size:0.72rem; color:var(--ink-muted);">Based on sampled pages: {pages_used}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)
    with st.expander("Upload a different document"):
        replace_file = st.file_uploader("Replace document", type=["pdf"], label_visibility="collapsed", key="replace_uploader")
        if replace_file is not None:
            with st.spinner("Processing document…"):
                try:
                    result = api_client.upload_document(replace_file.read(), replace_file.name)
                    st.session_state.active_document = result["document"]
                    st.session_state.chat_history = []
                    st.session_state.insights = None
                    st.success(result["message"])
                    st.rerun()
                except APIError as e:
                    st.error(str(e))

else:
    st.markdown(
        """
        <div class="upload-hint fade-in">
          <div class="upload-hint-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"></path>
              <path d="M12 12v9"></path><path d="m16 16-4-4-4 4"></path>
            </svg>
          </div>
          <div>
            <p class="upload-hint-title">Drag &amp; drop your PDF here</p>
            <p class="upload-hint-sub">or click below to browse — text-based PDF documents only</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "Drop your PDF here — supported: PDF documents",
        type=["pdf"],
        label_visibility="collapsed",
        disabled=not backend_ok,
    )
    if uploaded_file is not None:
        checklist_placeholder = st.empty()
        steps_display = [
            "Document uploaded", "Extracting text", "Creating document chunks",
            "Generating embeddings", "Building vector index", "Ready for questions",
        ]
        checklist_html = "<div class='dm-card'>"
        for s in steps_display:
            checklist_html += f"<div class='proc-item'><span class='proc-check'>·</span> {s}…</div>"
        checklist_html += "</div>"
        checklist_placeholder.markdown(checklist_html, unsafe_allow_html=True)

        try:
            result = api_client.upload_document(uploaded_file.read(), uploaded_file.name)
            done_html = "<div class='dm-card'>"
            for step in result["document"]["steps"]:
                detail = f"<span class='proc-detail'>{step['detail']}</span>" if step.get("detail") else ""
                done_html += f"<div class='proc-item'><span class='proc-check'>✓</span> {step['name']} {detail}</div>"
            done_html += "</div>"
            checklist_placeholder.markdown(done_html, unsafe_allow_html=True)

            st.session_state.active_document = result["document"]
            st.session_state.chat_history = []
            st.success(result["message"])
            st.rerun()
        except APIError as e:
            checklist_placeholder.empty()
            st.error(str(e))

st.markdown('<hr class="hairline">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Ask your document
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="section-head fade-in"><span class="eyebrow">Ask your document</span>'
    '<h3>Chat</h3></div>',
    unsafe_allow_html=True,
)

if not active_doc:
    st.markdown('<p class="dm-muted" style="font-size:0.92rem;">Upload a document above to start asking questions.</p>', unsafe_allow_html=True)
else:
    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            badge_class = "badge-grounded" if turn["grounded"] else "badge-ungrounded"
            badge_text = "Grounded in document" if turn["grounded"] else "No matching content found"
            st.markdown(
                f"""<div class="answer-card">
                  <span class="grounded-badge {badge_class}">{badge_text}</span>
                  <div class="answer-text">{turn['answer']}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if turn["sources"]:
                with st.expander(f"View {len(turn['sources'])} source{'s' if len(turn['sources']) != 1 else ''}"):
                    for i, src in enumerate(turn["sources"], start=1):
                        st.markdown(
                            f"""<div class="source-card">
                              <div class="source-head">
                                <span class="source-page">Source {i} · Page {src['page_number']}</span>
                                <span class="source-sim">retrieval similarity {src['retrieval_similarity']:.2f}</span>
                              </div>
                              <div class="source-excerpt">{src['excerpt']}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        '<p class="dm-muted" style="font-size:0.78rem; margin-top:0.4rem;">'
                        "Retrieval similarity reflects how closely a passage matched your question semantically — "
                        "it is not a measure of factual confidence.</p>",
                        unsafe_allow_html=True,
                    )

    question = st.chat_input(
        "Ask a question about the document…" if groq_configured else "Set GROQ_API_KEY on the backend to enable chat",
        disabled=not groq_configured,
    )
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving relevant passages and generating an answer…"):
                try:
                    result = api_client.ask_question(question)
                    st.session_state.chat_history.append({
                        "question": question,
                        "answer": result["answer"],
                        "grounded": result["grounded"],
                        "sources": result["sources"],
                    })
                    st.rerun()
                except APIError as e:
                    st.error(str(e))

st.markdown('<hr class="hairline">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Technical information
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="section-head fade-in"><span class="eyebrow">Under the hood</span>'
    '<h3>Technical information</h3></div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="dm-card dm-card-tight fade-in">
    <div class="spec-grid">
      <div class="spec-item"><div class="spec-key">Retrieval</div><div class="spec-val">Semantic (embeddings)</div></div>
      <div class="spec-item"><div class="spec-key">Embedding model</div><div class="spec-val">Sentence-Transformers</div></div>
      <div class="spec-item"><div class="spec-key">Vector store</div><div class="spec-val">ChromaDB</div></div>
      <div class="spec-item"><div class="spec-key">LLM</div><div class="spec-val">Groq · Llama</div></div>
      <div class="spec-item"><div class="spec-key">Backend</div><div class="spec-val">FastAPI</div></div>
      <div class="spec-item"><div class="spec-key">Frontend</div><div class="spec-val">Streamlit</div></div>
    </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<hr class="hairline">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# About / Limitations
# ---------------------------------------------------------------------------
st.markdown('<span class="eyebrow">About</span>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="limits-card fade-in" style="margin-top:0.9rem;">
      <div class="limits-head">
        <div class="limits-head-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 9v4"></path><path d="M12 17h.01"></path>
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"></path>
          </svg>
        </div>
        <h4>Limitations</h4>
      </div>
      <ul>
        <li>Answers are only as good as the retrieved passages — if relevant content
            wasn't indexed or wasn't retrieved for a given question, the answer will
            reflect that gap.</li>
        <li>Retrieval-augmented generation substantially <b>reduces</b> unsupported claims
            compared to an ungrounded LLM, but it does not <b>guarantee</b> perfect factual
            accuracy — always verify against the cited source pages for anything important.</li>
        <li>DocMind currently requires text-based PDFs; scanned/image-only PDFs without
            an existing text layer are not supported.</li>
        <li>One document is active at a time; uploading a new one replaces the current context.</li>
      </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="dm-footer">
      <div class="dm-footer-brand">
        <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"></path>
        </svg>
        DocMind — RAG-powered document intelligence, portfolio prototype
      </div>
      <div class="dm-footer-pills">
        <span class="dm-footer-pill">LangChain</span>
        <span class="dm-footer-pill">ChromaDB</span>
        <span class="dm-footer-pill">Sentence-Transformers</span>
        <span class="dm-footer-pill">Groq</span>
        <span class="dm-footer-pill">FastAPI</span>
        <span class="dm-footer-pill">Streamlit</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
