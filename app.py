import google.generativeai as genai
import streamlit as st
import os
from backend.text_extractor import extract_text_from_pdf, clean_text
from backend.summarizer import generate_summary
from backend.question_generator import generate_qa_pairs
from utils import create_download_link

# Page Configuration
st.set_page_config(
    page_title="Intelligent PDF Summarizer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 10px 24px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stTextArea>div>div>textarea {
        background-color: #ffffff;
    }
    .title-text {
        color: #2c3e50;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/000000/pdf.png", width=100)
    st.title("Settings")
    
    st.markdown("### 🔑 API Keys")
    gemini_api_key = st.text_input(
        "Google Gemini API Key (for Q&A)", 
        type="password", 
        help="Required for generating Key Questions & Answers. Get one at https://makersuite.google.com/app/apikey"
    )
    
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
    
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.info(
        "This tool extracts text from PDFs, generates concise and detailed summaries, "
        "and creates Q&A pairs to help you understand the content better."
    )

# Main Content
st.title("📚 Intelligent PDF/Book Summarizer")
st.markdown("### Upload your PDF to get started")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    with st.spinner("Extracting text from PDF..."):
        raw_text = extract_text_from_pdf(uploaded_file)
        cleaned_text = clean_text(raw_text)
    
    if cleaned_text:
        st.success("PDF processed successfully!")
        
        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📄 Extracted Text", "📝 Summaries", "❓ Q&A Generator"])
        
        with tab1:
            st.subheader("Extracted Text Preview")
            st.text_area("Content", cleaned_text[:5000] + ("..." if len(cleaned_text) > 5000 else ""), height=400)
            
            st.download_button(
                label="Download Extracted Text",
                data=create_download_link(cleaned_text, "extracted.txt"),
                file_name="extracted_text.txt",
                mime="text/plain"
            )

        with tab2:
            st.subheader("Generate Summary")
            col1, col2 = st.columns(2)
            
            summary_placeholder = st.empty()
            
            with col1:
                if st.button("Generate Concise Summary"):
                    with st.spinner("Generating concise summary..."):
                        summary = generate_summary(cleaned_text, summary_type="concise")
                        st.session_state['concise_summary'] = summary
                        st.success("Concise Summary Generated!")
            
            with col2:
                if st.button("Generate Detailed Summary"):
                    with st.spinner("Generating detailed summary... might take a moment"):
                        summary = generate_summary(cleaned_text, summary_type="detailed")
                        st.session_state['detailed_summary'] = summary
                        st.success("Detailed Summary Generated!")
            
            # Display logic
            if 'concise_summary' in st.session_state:
                st.markdown("#### Concise Summary")
                st.info(st.session_state['concise_summary'])
                st.download_button("Download Concise Summary", st.session_state['concise_summary'], "concise_summary.txt")
                
            if 'detailed_summary' in st.session_state:
                st.markdown("#### Detailed Summary")
                st.text_area("Detailed Output", st.session_state['detailed_summary'], height=300)
                st.download_button("Download Detailed Summary", st.session_state['detailed_summary'], "detailed_summary.txt")

        with tab3:
            st.subheader("Generate Questions & Answers")
            if not gemini_api_key:
                st.warning("Please enter your Google Gemini API Key in the sidebar to use this feature.")
            else:
                if st.button("Generate Q&A"):
                    with st.spinner("Consulting the AI Oracle..."):
                        qa_result = generate_qa_pairs(cleaned_text, gemini_api_key)
                        st.session_state['qa_result'] = qa_result
                
                if 'qa_result' in st.session_state:
                    st.markdown("#### Generated Questions & Answers")
                    st.markdown(st.session_state['qa_result'])
                    st.download_button("Download Q&A", st.session_state['qa_result'], "qa_pairs.txt")
                    
    else:
        st.error("Could not extract text from the PDF. It might be empty or scanned (image-based). Application currently supports text-based PDFs only.")

else:
    st.info("Please upload a PDF file to begin.")
