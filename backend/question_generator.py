import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_MODEL = "llama-3.1-8b-instant"


def generate_qa_pairs(text: str, api_key: str = None) -> str:
    try:
        if not text:
            return "No text available to generate questions."

        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            return "Error: No Groq API key provided."

        client = Groq(api_key=key)

        prompt = f"""You are a helpful teacher.

Generate important questions and answers from the text below.

Rules:
- Write Q1, Q2, Q3... for questions
- Write A1, A2, A3... for answers
- Leave a blank line between each Q&A pair
- Do NOT put question and answer on the same line

Format:

Q1: What is AI?

A1: AI is artificial intelligence.

Q2: What is machine learning?

A2: Machine learning is a subset of AI.

Text:
{text[:12000]}
"""

        resp = client.chat.completions.create(
            model      = GROQ_MODEL,
            messages   = [{"role": "user", "content": prompt}],
            max_tokens = 2048,
        )
        return resp.choices[0].message.content

    except Exception as e:
        return f"Error generating Q&A: {str(e)}"
