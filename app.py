import streamlit as st
import math
import time
import re
import os
from groq import Groq
from dotenv import load_dotenv
from backend.text_extractor import extract_text_from_pdf, clean_text
from backend.question_generator import generate_qa_pairs

load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

# ── Page Configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PDF Summarizer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Light base ── */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .stApp {
        background-color: #f4f6fb !important;
        color: #1e2235 !important;
    }
    [data-testid="stHeader"]  { background: transparent; }
    [data-testid="stSidebar"] { background: #ffffff !important; }

    /* Text */
    p, li, span, label, div { color: #2c3148; }
    h1, h2, h3, h4, h5, h6  { color: #1a1f36 !important; }

    /* Remove default padding */
    .block-container { padding-top: 1.4rem; padding-bottom: 1rem; }

    /* Inputs & text areas */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"]  textarea,
    .stTextArea textarea {
        background-color: #ffffff !important;
        color: #1e2235 !important;
        border: 1px solid #d0d7e8 !important;
        border-radius: 8px !important;
    }

    /* Password input */
    input[type="password"] {
        background-color: #ffffff !important;
        color: #1e2235 !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: #ffffff !important;
        border: 2px dashed #b0bcd8 !important;
        border-radius: 12px !important;
    }

    /* Tabs */
    [data-testid="stTabs"] [role="tab"] {
        background: #eef1f8 !important;
        color: #5a6282 !important;
        border-radius: 8px 8px 0 0;
        border: 1px solid #d8dded;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: #ffffff !important;
        color: #3451d1 !important;
        border-bottom: 2px solid #3451d1 !important;
        font-weight: 700;
    }

    /* Buttons */
    .stButton>button {
        width: 100%;
        background: #3451d1;
        color: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s;
    }
    .stButton>button:hover { background: #2a40b8; }

    /* Download button */
    [data-testid="stDownloadButton"] button {
        background: #eef1fb !important;
        color: #3451d1 !important;
        border: 1px solid #c0ccf0 !important;
        border-radius: 8px !important;
    }

    /* Divider */
    hr { border-color: #dde2ee !important; }

    /* Stat pills */
    .pill {
        display: inline-block;
        background: #e8edfb;
        color: #3451d1;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.82rem;
        font-weight: 700;
        margin-right: 6px;
        border: 1px solid #c8d2f0;
    }

    /* Expander */
    [data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #d8dded !important;
        border-radius: 10px !important;
    }

    /* Progress bar */
    [data-testid="stProgressBar"] > div > div {
        background: #3451d1 !important;
    }

    /* Hide branding */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

GROQ_MODEL  = "llama-3.1-8b-instant"
CHUNK_WORDS = 3500   # ~4600 tokens — stays under 6000 TPM free limit
OVERLAP     = 100
GROUP_SIZE  = 6
RATE_DELAY  = 2


def _chunk_text(text: str) -> list[str]:
    words  = text.split()
    chunks = []
    step   = CHUNK_WORDS - OVERLAP
    i      = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + CHUNK_WORDS]))
        i += step
    return chunks


def _call_groq_once(prompt: str, client: Groq) -> str:
    """Single non-streaming Groq call with rate-limit retry."""
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model      = GROQ_MODEL,
                messages   = [{"role": "user", "content": prompt[:20000]}],
                max_tokens = 1024,
            )
            time.sleep(RATE_DELAY)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e):
                m = re.search(r'try again in ([\d.]+)s', str(e))
                time.sleep(float(m.group(1)) + 2 if m else 30)
            elif attempt < 2:
                time.sleep(5)
            else:
                raise


def _stream_groq(prompt: str, client: Groq):
    """Generator: yields text chunks from Groq streaming API."""
    stream = client.chat.completions.create(
        model      = GROQ_MODEL,
        messages   = [{"role": "user", "content": prompt[:20000]}],
        max_tokens = 2048,
        stream     = True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


def run_streaming_summary(text: str, summary_type: str, max_points: int, client: Groq, status_placeholder):
    """
    Short docs  → stream directly.
    Large docs  → process chunks with progress bar, then stream final summary.
    """
    word_count   = len(text.split())
    is_large_doc = word_count > CHUNK_WORDS

    if not is_large_doc:
        if summary_type == "concise":
            instruction = (
                f"Write a comprehensive summary with at least {max_points} bullet points. "
                "Each bullet should be a full informative sentence covering a key idea."
            )
        else:
            instruction = (
                f"Write a detailed structured summary with headings and sub-bullets. "
                f"Include at least {max_points} key points. Each should be a full sentence with context."
            )
        prompt = f"""You are an expert summarizer.
{instruction}
Use only facts from the text. Do NOT invent anything. Be thorough.

Text:
{text[:20000]}
"""
        yield from _stream_groq(prompt, client)

    else:
        chunks       = _chunk_text(text)
        total_chunks = len(chunks)
        total_groups = math.ceil(total_chunks / GROUP_SIZE)

        progress = status_placeholder.progress(0, text=f"Processing chunk 1/{total_chunks}...")
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            progress.progress(
                int((i + 1) / total_chunks * 60),
                text=f"Processing chunk {i+1}/{total_chunks}..."
            )
            p = f"""Summarize part {i+1} of {total_chunks} of a document.
Extract ALL key ideas, facts, and details as 8-12 thorough bullet points.
Each bullet should be a full sentence. Only use facts from the text provided.

Text:
{chunk}
"""
            chunk_summaries.append(_call_groq_once(p, client))

        if total_groups > 1:
            group_summaries = []
            for g in range(total_groups):
                progress.progress(
                    60 + int((g + 1) / total_groups * 30),
                    text=f"Merging group {g+1}/{total_groups}..."
                )
                group  = chunk_summaries[g * GROUP_SIZE : (g + 1) * GROUP_SIZE]
                joined = "\n\n".join(f"Section {i+1}:\n{s}" for i, s in enumerate(group))
                p = f"""Merge these section summaries into one comprehensive list.
Write 10-15 detailed bullet points. Keep all important facts. Remove only exact duplicates.
Only use facts from the summaries below.

{joined}
"""
                group_summaries.append(_call_groq_once(p, client))
        else:
            group_summaries = chunk_summaries

        progress.progress(90, text="Generating final summary...")
        joined = "\n\n".join(f"--- Part {i+1} ---\n{s}" for i, s in enumerate(group_summaries))
        instruction = (
            f"Write a final concise summary in {max_points} bullet points or fewer."
            if summary_type == "concise"
            else f"Write a final structured summary with headings. Max {max_points} key points."
        )
        final_prompt = f"""You are writing the FINAL summary of an entire document.
{instruction}
Use clear, simple language. Do NOT invent facts. Remove repetition.

Summaries:
{joined}
"""
        progress.progress(100, text="Streaming summary...")
        status_placeholder.empty()
        yield from _stream_groq(final_prompt, client)


# ═══════════════════════════════════════════════════════════════════════════════
# APP LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📚 PDF Summarizer")
st.markdown("---")

left_col, right_col = st.columns([1, 1], gap="large")   # exact 50 / 50


# ══════════════════════════════════════════════════════════════════════════════
# LEFT — Upload & Settings
# ══════════════════════════════════════════════════════════════════════════════
with left_col:
    st.markdown("### 📂 Upload PDF")

    uploaded_file = st.file_uploader(
        "Drop your PDF here",
        type="pdf",
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### ⚙️ Settings")

    groq_api_key = os.getenv("GROQ_API_KEY", "")

    summary_type = st.radio(
        "Summary style",
        options=["concise", "detailed"],
        format_func=lambda x: "⚡ Concise (bullet points)" if x == "concise" else "📋 Detailed (with headings)",
        horizontal=True
    )

    max_points = st.slider("Max summary points", min_value=3, max_value=20, value=10)

    # ── Process uploaded file ──────────────────────────────────────────────────
    if uploaded_file is not None:
        current_file = uploaded_file.name

        # Clear cache when a new file is uploaded
        if st.session_state.get('last_file') != current_file:
            for k in ['cleaned_text', 'summary_text', 'qa_result', 'word_count', 'page_est']:
                st.session_state.pop(k, None)
            st.session_state['last_file'] = current_file

        # Extract text once
        if 'cleaned_text' not in st.session_state:
            with st.spinner("Extracting text from PDF..."):
                raw  = extract_text_from_pdf(uploaded_file)
                text = clean_text(raw)

            if not text:
                st.error("Could not extract text. Make sure it's a text-based PDF.")
                st.stop()

            st.session_state['cleaned_text'] = text
            st.session_state['word_count']   = len(text.split())
            st.session_state['page_est']     = len(text.split()) // 300

        wc = st.session_state['word_count']
        pg = st.session_state['page_est']

        st.success(f"✅ **{current_file}** loaded")
        st.markdown(
            f'<span class="pill">~{wc:,} words</span><span class="pill">~{pg} pages</span>',
            unsafe_allow_html=True
        )

        st.markdown("")

        col_a, col_b = st.columns(2)
        with col_a:
            regenerate = st.button("🔄 Re-summarize")
        with col_b:
            st.download_button(
                "⬇️ Download Text",
                data      = st.session_state['cleaned_text'],
                file_name = "extracted_text.txt",
                mime      = "text/plain"
            )

        if regenerate:
            st.session_state.pop('summary_text', None)
            st.session_state.pop('qa_result', None)
            st.rerun()

    else:
        st.info("📂 Upload a PDF above to get started.")
        st.markdown("**This app will:**")
        st.markdown("- Extract all text from your PDF")
        st.markdown("- Stream a live AI summary on the right")
        st.markdown("- Generate Q&A pairs from the content")


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT — Live Summary & Q&A
# ══════════════════════════════════════════════════════════════════════════════
with right_col:
    if uploaded_file is None or 'cleaned_text' not in st.session_state:
        st.markdown(
            """
            <div style="display:flex;flex-direction:column;align-items:center;
                        justify-content:center;height:65vh;color:#b0bec5;text-align:center;">
                <div style="font-size:5rem;">✨</div>
                <div style="font-size:1.3rem;margin-top:1rem;font-weight:600;">
                    Your summary will appear here
                </div>
                <div style="font-size:0.95rem;margin-top:0.5rem;">
                    Upload a PDF on the left to begin
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        cleaned_text = st.session_state['cleaned_text']
        tab_summary, tab_qa, tab_text = st.tabs(["📝 Summary", "❓ Q&A", "📄 Raw Text"])

        # ── Summary Tab ───────────────────────────────────────────────────────
        with tab_summary:
            settings_key = f"{summary_type}_{max_points}"

            # Auto-generate or re-generate when settings change
            if (
                'summary_text' not in st.session_state
                or st.session_state.get('summary_key') != settings_key
            ):
                if not groq_api_key:
                    st.warning("⚠️ GROQ_API_KEY not found in .env file.")
                else:
                    try:
                        client = Groq(api_key=groq_api_key)

                        wc          = st.session_state['word_count']
                        chunk_count = max(1, wc // CHUNK_WORDS)
                        est_min     = round((chunk_count * RATE_DELAY) / 60, 1)

                        if chunk_count > 1:
                            st.info(
                                f"📊 Large document — {chunk_count} chunks to process. "
                                f"Estimated time: ~{est_min} min. "
                                f"Progress bar will appear, then summary streams live."
                            )

                        status_ph = st.empty()

                        label = "⚡ Concise Summary" if summary_type == "concise" else "📋 Detailed Summary"
                        st.markdown(f"#### {label} *(streaming...)*")

                        full_text = st.write_stream(
                            run_streaming_summary(
                                cleaned_text, summary_type, max_points, client, status_ph
                            )
                        )

                        st.session_state['summary_text'] = full_text
                        st.session_state['summary_key']  = settings_key
                        st.rerun()   # re-render cleanly with download button visible

                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            else:
                # Show cached summary with download
                label = "⚡ Concise Summary" if summary_type == "concise" else "📋 Detailed Summary"
                st.markdown(f"#### {label}")
                st.markdown(st.session_state['summary_text'])
                st.markdown("---")
                st.download_button(
                    "⬇️ Download Summary",
                    data      = st.session_state['summary_text'],
                    file_name = f"{summary_type}_summary.txt",
                    mime      = "text/plain"
                )

        # ── Q&A Tab ───────────────────────────────────────────────────────────
        with tab_qa:
            if not groq_api_key:
                st.warning("⚠️ GROQ_API_KEY not found in .env file.")
            else:
                if 'qa_result' not in st.session_state:
                    with st.spinner("Generating Q&A pairs..."):
                        qa = generate_qa_pairs(cleaned_text, groq_api_key)
                        st.session_state['qa_result'] = qa

                if 'qa_result' in st.session_state:
                    st.markdown("#### Generated Questions & Answers")
                    st.markdown(st.session_state['qa_result'])
                    st.markdown("---")
                    st.download_button(
                        "⬇️ Download Q&A",
                        data      = st.session_state['qa_result'],
                        file_name = "qa_pairs.txt",
                        mime      = "text/plain"
                    )

        # ── Raw Text Tab ──────────────────────────────────────────────────────
        with tab_text:
            preview = cleaned_text[:5000] + ("..." if len(cleaned_text) > 5000 else "")
            st.text_area("Extracted Content", preview, height=450, label_visibility="collapsed")
