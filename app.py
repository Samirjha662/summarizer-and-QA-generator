from google import genai
from google.genai import types
import streamlit as st
import os
from backend.text_extractor import extract_text_from_pdf, clean_text
from backend.summarizer import generate_summary
from backend.question_generator import generate_qa_pairs
from utils import create_download_link

# ── Page Configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Intelligent PDF Summarizer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f5f5f5; }

    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 10px 24px;
        font-size: 16px;
        cursor: pointer;
    }
    .stButton>button:hover { background-color: #45a049; }

    .stTextArea>div>div>textarea { background-color: #ffffff; }

    .title-text {
        color: #2c3e50;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }

    /* Verification badge colors */
    .verdict-excellent { color: #27ae60; font-weight: bold; }
    .verdict-good      { color: #f39c12; font-weight: bold; }
    .verdict-review    { color: #e74c3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/000000/pdf.png", width=100)
    st.title("Settings")

    st.markdown("### 🔑 API Key")
    gemini_api_key = st.text_input(
        "Google Gemini API Key",
        type="password",
        help="Required for Q&A generation. Get one at https://aistudio.google.com/app/apikey"
    )
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)

    st.markdown("---")
    st.markdown("### ⚙️ Summary Settings")

    max_points = st.slider(
        "Max summary points",
        min_value=3,
        max_value=20,
        value=10,
        help="Controls how many bullet points appear in the final summary"
    )

    run_verification = st.toggle(
        "Run accuracy verification",
        value=False,
        help="Checks summary quality using 3 automated tests. Takes extra time."
    )

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.info(
        "Upload a PDF to get concise/detailed summaries and AI-generated Q&A pairs. "
        "Accuracy verification checks faithfulness, key term coverage, and spot checks."
    )

# ── Main Title ─────────────────────────────────────────────────────────────────
st.title("📚 Intelligent PDF Summarizer")
st.markdown("### Upload your PDF to get started")

# ── File Upload ────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:

    # ── Text Extraction ────────────────────────────────────────────────────────
    with st.spinner("Extracting text from PDF..."):
        raw_text     = extract_text_from_pdf(uploaded_file)
        cleaned_text = clean_text(raw_text)

    if not cleaned_text:
        st.error(
            "Could not extract text from the PDF. "
            "It might be empty or scanned (image-based). "
            "This app currently supports text-based PDFs only."
        )
        st.stop()

    # Show doc stats
    word_count = len(cleaned_text.split())
    page_est   = word_count // 300
    st.success(f"✅ PDF processed — ~{word_count:,} words (~{page_est} pages)")

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📄 Extracted Text", "📝 Summaries", "❓ Q&A Generator"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Extracted Text
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("Extracted Text Preview")
        preview = cleaned_text[:5000] + ("..." if len(cleaned_text) > 5000 else "")
        st.text_area("Content", preview, height=400)

        st.download_button(
            label     = "⬇️ Download Extracted Text",
            data      = cleaned_text,
            file_name = "extracted_text.txt",
            mime      = "text/plain"
        )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Summaries
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("Generate Summary")

        col1, col2 = st.columns(2)

        # ── Concise Summary ────────────────────────────────────────────────────
        with col1:
            if st.button("⚡ Generate Concise Summary"):
                word_count  = len(cleaned_text.split())
                chunk_count = max(1, word_count // 6000)
                est_minutes = round((chunk_count * 4) / 60, 1)  # 4 sec per call

                st.info(f"📊 ~{chunk_count} chunks to process — estimated time: {est_minutes} min")

                progress = st.progress(0, text="Starting...")
                    
                result = generate_summary(
                        cleaned_text,
                        summary_type = "concise",
                        max_points   = max_points,
                        verify       = run_verification
                    )

                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    # ✅ store only the string — fixes the dict crash
                    st.session_state['concise_summary']      = result['summary']
                    st.session_state['concise_verification'] = result.get('verification')
                    st.session_state['concise_pages']        = result.get('page_estimate', 0)
                    st.success("✅ Concise Summary Generated!")

        # ── Detailed Summary ───────────────────────────────────────────────────
        with col2:
            if st.button("📋 Generate Detailed Summary"):
                with st.spinner("Generating detailed summary... this may take a moment for large PDFs"):
                    result = generate_summary(
                        cleaned_text,
                        summary_type = "detailed",
                        max_points   = max_points,
                        verify       = run_verification
                    )

                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    # ✅ store only the string — fixes the dict crash
                    st.session_state['detailed_summary']      = result['summary']
                    st.session_state['detailed_verification'] = result.get('verification')
                    st.session_state['detailed_pages']        = result.get('page_estimate', 0)
                    st.success("✅ Detailed Summary Generated!")

        st.markdown("---")

        # ── Display Concise Summary ────────────────────────────────────────────
        if 'concise_summary' in st.session_state:
            st.markdown("#### 📌 Concise Summary")
            st.info(st.session_state['concise_summary'])

            st.download_button(
                label     = "⬇️ Download Concise Summary",
                data      = st.session_state['concise_summary'],   # ✅ always a string
                file_name = "concise_summary.txt",
                mime      = "text/plain"
            )

            # Verification report for concise
            if run_verification and st.session_state.get('concise_verification'):
                _show_verification(st.session_state['concise_verification'])

        # ── Display Detailed Summary ───────────────────────────────────────────
        if 'detailed_summary' in st.session_state:
            st.markdown("#### 📋 Detailed Summary")
            st.text_area(
                "Detailed Output",
                st.session_state['detailed_summary'],              # ✅ always a string
                height=300
            )

            st.download_button(
                label     = "⬇️ Download Detailed Summary",
                data      = st.session_state['detailed_summary'],  # ✅ always a string
                file_name = "detailed_summary.txt",
                mime      = "text/plain"
            )

            # Verification report for detailed
            if run_verification and st.session_state.get('detailed_verification'):
                _show_verification(st.session_state['detailed_verification'])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Q&A Generator
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("Generate Questions & Answers")

        if not gemini_api_key:
            st.warning("⚠️ Please enter your Google Gemini API Key in the sidebar to use this feature.")
        else:
            if st.button("🤖 Generate Q&A"):
                with st.spinner("Generating Q&A pairs..."):
                    qa_result = generate_qa_pairs(cleaned_text, gemini_api_key)
                    st.session_state['qa_result'] = qa_result

            if 'qa_result' in st.session_state:
                st.markdown("#### Generated Questions & Answers")
                st.markdown(st.session_state['qa_result'])

                st.download_button(
                    label     = "⬇️ Download Q&A",
                    data      = st.session_state['qa_result'],
                    file_name = "qa_pairs.txt",
                    mime      = "text/plain"
                )

else:
    # ── Landing state ──────────────────────────────────────────────────────────
    st.info("📂 Please upload a PDF file to begin.")

    st.markdown("---")
    st.markdown("#### What this app does")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**📄 Text Extraction**\nExtracts all text from your PDF instantly")
    with col_b:
        st.markdown("**📝 Smart Summaries**\nConcise bullets or detailed structured output")
    with col_c:
        st.markdown("**❓ Q&A Generation**\nGenerates questions and answers from the content")


# ── Verification Display Helper ────────────────────────────────────────────────
def _show_verification(v: dict):
    """Render the accuracy verification report inside an expander."""
    if not v:
        return

    verdict = v.get('verdict', 'N/A')
    passed  = v.get('checks_passed', '?/3')

    verdict_color = {
        "EXCELLENT"    : "🟢",
        "GOOD"         : "🟡",
        "NEEDS REVIEW" : "🔴",
    }.get(verdict, "⚪")

    with st.expander(f"🔍 Accuracy Report — {verdict_color} {verdict}  ({passed} checks passed)"):

        tc = v.get('term_coverage', {})
        st.markdown(f"**1. Key Term Coverage:** {tc.get('coverage_percent', 0)}%  `{tc.get('status','')}`")
        if tc.get('missing_terms'):
            st.caption(f"Missing terms: {', '.join(tc['missing_terms'][:10])}")

        fa = v.get('faithfulness', {})
        faithful_icon = "✅" if fa.get('faithful') else "❌"
        st.markdown(f"**2. Faithfulness Check:** {faithful_icon}  confidence: {fa.get('confidence','?')}%")
        if fa.get('issues'):
            for issue in fa['issues']:
                st.caption(f"⚠️ {issue}")

        sc = v.get('spot_check', {})
        st.markdown(f"**3. Spot Check:** {sc.get('coverage_percent',0)}%  `{sc.get('status','')}`  ({sc.get('spots_covered',0)}/{sc.get('spots_checked',0)} pages covered)")
