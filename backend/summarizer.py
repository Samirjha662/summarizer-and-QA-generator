import os
import re
import math
import time
from collections import Counter
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.1-8b-instant"
CHUNK_WORDS  = 3500   # ~4600 tokens — stays under 6000 TPM free limit
OVERLAP      = 100
GROUP_SIZE   = 6
RETRY_LIMIT  = 3
RETRY_DELAY  = 5
RATE_DELAY   = 2

STOPWORDS = {
    "the","a","an","is","in","of","to","and","or","it","that","this",
    "was","for","are","be","as","at","by","we","he","she","they","with",
    "from","on","but","not","have","had","has","its","into","also","about",
    "which","their","been","were","more","one","can","all","will","when",
    "than","then","these","those","there","after","before","would","could",
    "should","may","might","just","each","such","very","any","how","what",
    "said","so","if","do","did","does","our","your","his","her","my","i"
}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CORE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def _get_client(api_key: str = None) -> Groq:
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("No Groq API key found. Provide one in the app or set GROQ_API_KEY in .env")
    return Groq(api_key=key)


def _call_groq(prompt: str, api_key: str = None, retries: int = RETRY_LIMIT) -> str:
    """Call Groq with retry + rate-limit handling."""
    client = _get_client(api_key)
    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(
                model      = GROQ_MODEL,
                messages   = [{"role": "user", "content": prompt[:20000]}],
                max_tokens = 1024,
            )
            time.sleep(RATE_DELAY)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err:
                m    = re.search(r'try again in ([\d.]+)s', err)
                wait = float(m.group(1)) + 2 if m else 30
                print(f"  [Rate limit] Waiting {wait:.0f}s...")
                time.sleep(wait)
            elif attempt < retries:
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(f"Groq failed after {retries} attempts: {e}")


def chunk_text(text: str, chunk_size: int = CHUNK_WORDS, overlap: int = OVERLAP) -> list[str]:
    words  = text.split()
    chunks = []
    step   = chunk_size - overlap
    i      = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + chunk_size]))
        i += step
    return chunks


def _extract_top_terms(text: str, top_n: int = 30) -> list[str]:
    words    = re.findall(r'\b[a-z]{4,}\b', text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    return [word for word, _ in Counter(filtered).most_common(top_n)]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SUMMARIZATION (3-LEVEL HIERARCHY)
# ═══════════════════════════════════════════════════════════════════════════════

def _summarize_chunk(chunk: str, chunk_index: int, total_chunks: int, api_key: str = None) -> str:
    prompt = f"""You are summarizing part {chunk_index + 1} of {total_chunks} of a document.
Extract ALL key ideas, facts, arguments, and important details as 8-12 bullet points.
Be thorough — do not skip important information. Only use facts from the text.

Text:
{chunk}
"""
    return _call_groq(prompt, api_key)


def _merge_group(summaries: list[str], group_index: int, total_groups: int, api_key: str = None) -> str:
    joined = "\n\n".join(f"Section {i+1}:\n{s}" for i, s in enumerate(summaries))
    prompt = f"""Merge these section summaries (group {group_index+1} of {total_groups}) into one.
Write 10-15 detailed bullet points. Keep all important facts. Remove only exact duplicates.
Only use facts from the summaries below.

{joined}
"""
    return _call_groq(prompt, api_key)


def _final_merge(group_summaries: list[str], summary_type: str, max_points: int, api_key: str = None) -> str:
    joined = "\n\n".join(f"--- Part {i+1} ---\n{s}" for i, s in enumerate(group_summaries))
    if summary_type == "concise":
        instruction = (
            f"Write a comprehensive summary with at least {max_points} bullet points. "
            "Cover all major topics. Each bullet should be a full, informative sentence."
        )
    else:
        instruction = (
            f"Write a detailed structured summary with clear headings and sub-bullets. "
            f"Include at least {max_points} key points spread across sections. "
            "Each point should be a full, informative sentence with context."
        )
    prompt = f"""You are writing the FINAL summary of an entire document.
{instruction}
Use clear language. Do NOT invent facts. Preserve all important details from the summaries.

Summaries:
{joined}
"""
    return _call_groq(prompt, api_key)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_summary(
    text        : str,
    summary_type: str  = "concise",
    max_points  : int  = 10,
    api_key     : str  = None,
) -> dict:
    if not text or not text.strip():
        return {"error": "No text provided."}
    if summary_type not in ("concise", "detailed"):
        return {"error": "Invalid summary_type. Use 'concise' or 'detailed'."}

    word_count = len(text.split())
    page_est   = word_count // 300

    try:
        if word_count <= CHUNK_WORDS:
            instruction = (
                f"Summarize in {max_points} bullet points or fewer. Be concise."
                if summary_type == "concise"
                else f"Write a structured summary with headings. Max {max_points} key points."
            )
            prompt = f"""You are an expert summarizer.
{instruction}
Only include facts from the text. Do NOT invent anything.

Text:
{text}
"""
            summary  = _call_groq(prompt, api_key)
            n_chunks = 1

        else:
            chunks       = chunk_text(text)
            total_chunks = len(chunks)
            total_groups = math.ceil(total_chunks / GROUP_SIZE)
            n_chunks     = total_chunks

            chunk_summaries = [
                _summarize_chunk(c, i, total_chunks, api_key)
                for i, c in enumerate(chunks)
            ]

            if total_groups == 1:
                group_summaries = chunk_summaries
            else:
                group_summaries = [
                    _merge_group(
                        chunk_summaries[g * GROUP_SIZE : (g + 1) * GROUP_SIZE],
                        g, total_groups, api_key
                    )
                    for g in range(total_groups)
                ]

            summary = _final_merge(group_summaries, summary_type, max_points, api_key)

        return {
            "summary"      : summary,
            "word_count"   : word_count,
            "page_estimate": page_est,
            "chunks"       : n_chunks,
        }

    except Exception as e:
        return {"error": f"Summarization failed: {str(e)}"}
