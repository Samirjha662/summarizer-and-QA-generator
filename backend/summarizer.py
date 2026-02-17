import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")



# # split into chunks
# def chunk_text(text, chunk_size=3000):
#     words = text.split()
#     chunks = []

#     for i in range(0, len(words), chunk_size):
#         chunk = words[i:i+chunk_size]
#         chunks.append(" ".join(chunk))

#     return chunks


# def summarize_chunk(chunk):
#     prompt = f"""
#     Summarize this text clearly in important points:
#     {chunk}
#     """

#     response = model.generate_content(prompt)
#     return response.text



def generate_summary(text, summary_type="concise"):

    try:
        if not text:
            return "no text found to summarize." 
        
        if summary_type=="concise":
            instruction = "Summarize in short bullet points(maximum 8-10 points)"
        else:
            instruction="provide a detailed structured summary with headings and explanations"
    

        prompt = f"""
        You are an expert academic summarizer.
        {instruction}

        Focus only on important concepts.
        Avoid unnecessary details.
        Use clear  simple language.

        Text:
        {text[:200000]}
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Error generating summary: {str(e)}"