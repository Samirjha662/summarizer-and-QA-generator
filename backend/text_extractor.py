import PyPDF2
import re
import io

def extract_text_from_pdf(pdf_file):
    """
    Extracts text from a PDF file object.
    
    Args:
        pdf_file: A file-like object (e.g., streamlit UploadedFile).
        
    Returns:
        str: The extracted text.
    """
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def clean_text(text):
    """
    Cleans the extracted text by removing multiple spaces and special characters.
    """
    # Remove multiple newlines and spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove non-ascii characters (optional, depending on requirement)
    # text = re.sub(r'[^\x00-\x7F]+', ' ', text) 
    return text.strip()
