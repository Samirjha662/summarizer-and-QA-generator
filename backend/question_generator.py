import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# default env key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")


def generate_qa_pairs(text, api_key=None):
    try:
        # if user provides key from sidebar, use it
        if api_key:
            genai.configure(api_key=api_key)

        if not text:
            return "No text available to generate questions."

        prompt = f"""
You are a helpful teacher.

Generate important questions and answers from the text.

Rules:
- Each question must be on a new line
- Each answer must be on a new line
- Leave one blank line between each Q&A
- Do NOT put question and answer on same line

Format EXACTLY like this:

Q1: What is AI?
A1: AI is artificial intelligence.

Q2: What is machine learning?
A2: Machine learning is a subset of AI.
       

Text:
{text[:120000]}
"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Error generating Q&A: {str(e)}"
