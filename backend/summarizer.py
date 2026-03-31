import google.generativeai as genai
import os
import re
import math
import json
import time
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

genai.configure(api_key=api_key)

# ✅ Fixed: use gemini-2.0-flash (1500 req/day free, no 404 error)
model = genai.GenerativeModel("gemini-2.0-flash")

# ── Constants ──────────────────────────────────────────────────────────────────
CHUNK_WORDS  = 6000    # ✅ increased from 3000 — fewer API calls
OVERLAP      = 200     # overlapping words between chunks (fixes boundary cuts)
GROUP_SIZE   = 10      # chunk-summaries merged per group
GEMINI_LIMIT = 200000  # max characters per Gemini request
RETRY_LIMIT  = 3       # retries on API failure
RETRY_DELAY  = 5       # seconds to wait between retries
RATE_DELAY   = 4       # ✅ added: seconds between every API call (max 15/min)

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

def _call_gemini(prompt: str, retries: int = RETRY_LIMIT) -> str:
    """
    Call Gemini with:
    - auto-retry on failure
    - smart wait on 429 rate limit (reads retry delay from error message)
    - fixed 4s delay after every successful call (stays under 15 req/min)
    """
    for attempt in range(1, retries + 1):
        try:
            response = model.generate_content(prompt[:GEMINI_LIMIT])
            time.sleep(RATE_DELAY)  # ✅ prevents hitting 15 req/min limit
            return response.text.strip()

        except Exception as e:
            error_str = str(e)

            # ✅ 429 rate limit — extract exact wait time from error message
            if "429" in error_str:
                match = re.search(r'seconds:\s*(\d+)', error_str)
                wait  = int(match.group(1)) + 2 if match else 60
                print(f"  [Rate limit 429] Waiting {wait}s before retry...")
                time.sleep(wait)

            # ✅ 404 wrong model name
            elif "404" in error_str:
                raise RuntimeError(
                    "Model not found (404). "
                    "Check your model name in summarizer.py. "
                    "Use 'gemini-2.0-flash' or run list_available_models() to see options."
                )

            # other errors — standard retry
            elif attempt < retries:
                print(f"  [Retry {attempt}/{retries}] Error: {e}. Waiting {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)

            else:
                raise RuntimeError(f"Gemini failed after {retries} attempts: {e}")


def chunk_text(text: str, chunk_size: int = CHUNK_WORDS, overlap: int = OVERLAP) -> list[str]:
    """
    Split text into overlapping word-based chunks.
    Overlap ensures context is never lost at chunk boundaries.
    """
    words  = text.split()
    chunks = []
    step   = chunk_size - overlap
    i      = 0
    while i < len(words):
        chunk = words[i : i + chunk_size]
        chunks.append(" ".join(chunk))
        i += step
    return chunks


def _extract_top_terms(text: str, top_n: int = 30) -> list[str]:
    """Extract the most frequent meaningful words from text."""
    words    = re.findall(r'\b[a-z]{4,}\b', text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    return [word for word, _ in Counter(filtered).most_common(top_n)]


def list_available_models():
    """Print all Gemini models available for your API key."""
    print("\nAvailable models for your API key:")
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(f"  → {m.name}")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SUMMARIZATION (3-LEVEL HIERARCHY)
# ═══════════════════════════════════════════════════════════════════════════════

def _summarize_chunk(chunk: str, chunk_index: int, total_chunks: int) -> str:
    """Level 1 — Summarize a single chunk."""
    prompt = f"""You are summarizing part {chunk_index + 1} of {total_chunks} of a large document.

Extract the key ideas, facts, arguments, or events from this section.
Write 4-6 clear bullet points. Be concise — avoid filler phrases.
Only include information explicitly stated in the text. Do NOT invent anything.

Text:
{chunk}
"""
    return _call_gemini(prompt)


def _merge_group(summaries: list[str], group_index: int, total_groups: int) -> str:
    """Level 2 — Merge a group of chunk summaries into one group summary."""
    joined = "\n\n".join(f"Section {i+1}:\n{s}" for i, s in enumerate(summaries))
    prompt = f"""You are merging section summaries from group {group_index + 1} of {total_groups} of a large document.

Combine into one coherent group summary. Write 5-8 bullet points.
Remove duplicates. Only keep facts explicitly present in the summaries below.
Do NOT add any new information.

Summaries:
{joined}
"""
    return _call_gemini(prompt)


def _final_merge(group_summaries: list[str], summary_type: str, max_points: int) -> str:
    """Level 3 — Produce the final summary from all group summaries."""
    joined = "\n\n".join(f"--- Group {i+1} ---\n{s}" for i, s in enumerate(group_summaries))

    if summary_type == "concise":
        instruction = (
            f"Write a final concise summary in {max_points} bullet points or fewer. "
            "Prioritize the most important ideas across the entire document."
        )
    else:
        instruction = (
            f"Write a final structured summary with clear headings and sub-points. "
            f"Cover all major themes. Max {max_points} key points total."
        )

    prompt = f"""You are writing the FINAL summary of an entire document.

{instruction}

Rules:
- Use clear simple language.
- Do NOT invent facts — only use what is in the group summaries below.
- Remove repetition.
- Make it useful for someone who has NOT read the document.

Group summaries:
{joined}
"""
    return _call_gemini(prompt)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — ACCURACY VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def check_key_terms(original_text: str, summary: str, top_n: int = 20) -> dict:
    """Check how many of the document's most important terms appear in the summary."""
    top_terms   = _extract_top_terms(original_text, top_n)
    summary_low = summary.lower()
    found       = [t for t in top_terms if t in summary_low]
    missing     = [t for t in top_terms if t not in summary_low]
    coverage    = round(len(found) / len(top_terms) * 100, 1) if top_terms else 0.0

    return {
        "coverage_percent" : coverage,
        "status"           : "PASS" if coverage >= 60 else "WARN",
        "top_terms_checked": top_terms,
        "found_terms"      : found,
        "missing_terms"    : missing,
    }


def verify_faithfulness(source_sample: str, summary: str) -> dict:
    """Ask Gemini to fact-check the summary against a sample of the source text."""
    prompt = f"""You are a strict fact-checker. Compare the summary against the source text.

Reply in valid JSON only — no markdown, no backticks:
{{
  "faithful": true or false,
  "confidence": <0-100>,
  "issues": ["list each claim in the summary NOT supported by the source, or [] if none"]
}}

Source text (sample):
{source_sample[:4000]}

Summary to check:
{summary}
"""
    raw = _call_gemini(prompt)
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        return {
            "faithful"  : None,
            "confidence": None,
            "issues"    : ["Could not parse faithfulness response."],
            "raw"       : raw
        }


def spot_check(original_text: str, summary: str, num_spots: int = 5) -> dict:
    """Pick random positions in the document and check if the summary covers them."""
    import random
    words       = original_text.split()
    total_words = len(words)
    results     = []

    sample_size = min(num_spots, max(1, total_words // 300))
    positions   = sorted(random.sample(range(0, max(1, total_words - 300)), sample_size))

    for pos in positions:
        snippet  = " ".join(words[pos : pos + 300])
        page_est = (pos // 300) + 1

        prompt = f"""Does the summary below reflect or acknowledge the key ideas in this snippet?

Answer in valid JSON only — no markdown, no backticks:
{{
  "covered": true or false,
  "key_idea": "one sentence — main idea of the snippet",
  "found_in_summary": "phrase from summary that covers it, or null"
}}

Snippet (from ~page {page_est}):
{snippet}

Summary:
{summary}
"""
        raw = _call_gemini(prompt)
        try:
            clean  = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean)
            result["page_estimate"] = page_est
            results.append(result)
        except json.JSONDecodeError:
            results.append({"page_estimate": page_est, "covered": None, "error": "Parse failed"})

    covered_count = sum(1 for r in results if r.get("covered") is True)
    coverage_pct  = round(covered_count / len(results) * 100) if results else 0

    return {
        "spots_checked"   : len(results),
        "spots_covered"   : covered_count,
        "coverage_percent": coverage_pct,
        "status"          : "PASS" if coverage_pct >= 70 else "WARN",
        "details"         : results,
    }


def run_full_verification(original_text: str, summary: str) -> dict:
    """Run all 3 verification checks and return a combined accuracy report."""
    print("\n[Verify] Running accuracy checks...")

    print("  → Check 1/3: Key term coverage...")
    term_result = check_key_terms(original_text, summary)

    print("  → Check 2/3: Faithfulness check...")
    faith_result = verify_faithfulness(original_text[:4000], summary)

    print("  → Check 3/3: Spot check...")
    spot_result = spot_check(original_text, summary, num_spots=5)

    passes  = sum([
        term_result["status"] == "PASS",
        faith_result.get("faithful") is True,
        spot_result["status"] == "PASS"
    ])
    verdict = "EXCELLENT" if passes == 3 else "GOOD" if passes == 2 else "NEEDS REVIEW"

    print(f"  ✓ Verification done — {verdict} ({passes}/3 checks passed)\n")

    return {
        "verdict"      : verdict,
        "checks_passed": f"{passes}/3",
        "term_coverage": term_result,
        "faithfulness" : faith_result,
        "spot_check"   : spot_result,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_summary(
    text        : str,
    summary_type: str  = "concise",
    max_points  : int  = 10,
    verify      : bool = False,
) -> dict:
    """
    Summarize any document using hierarchical summarization.

    Args:
        text:         Raw text extracted from a PDF or document.
        summary_type: "concise"  → tight bullet points
                      "detailed" → structured headings + explanations
        max_points:   Max bullet points in final summary (default 10).
        verify:       Run 3 accuracy checks after summarization (default False).

    Returns:
        {
            "summary"      : str,
            "word_count"   : int,
            "page_estimate": int,
            "chunks"       : int,
            "verification" : dict | None,
        }
        or { "error": str } on failure.
    """
    # ── Validate ───────────────────────────────────────────────────────────────
    if not text or not text.strip():
        return {"error": "No text provided. Please extract text from a document first."}

    if summary_type not in ("concise", "detailed"):
        return {"error": "Invalid summary_type. Use 'concise' or 'detailed'."}

    if not (1 <= max_points <= 30):
        return {"error": "max_points must be between 1 and 30."}

    word_count = len(text.split())
    page_est   = word_count // 300

    print(f"\n{'='*55}")
    print(f"  Document : ~{word_count:,} words  (~{page_est} pages)")
    print(f"  Mode     : {summary_type}  |  Max points: {max_points}")
    print(f"  Verify   : {verify}")
    print(f"{'='*55}")

    try:
        # ── Short doc: single call ─────────────────────────────────────────────
        if word_count <= CHUNK_WORDS:
            print("\n[Info] Short document — single summarization pass.")
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
            summary  = _call_gemini(prompt)
            n_chunks = 1

        else:
            # ── Large doc: 3-level hierarchical summarization ──────────────────
            chunks       = chunk_text(text)
            total_chunks = len(chunks)
            total_groups = math.ceil(total_chunks / GROUP_SIZE)
            n_chunks     = total_chunks

            print(f"\n[Level 1] Summarizing {total_chunks} chunks "
                  f"(~{total_chunks * RATE_DELAY // 60} min)...")
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                print(f"  → Chunk {i+1}/{total_chunks}", end="\r")
                chunk_summaries.append(_summarize_chunk(chunk, i, total_chunks))
            print(f"  ✓ {total_chunks} chunks done.              ")

            if total_groups == 1:
                group_summaries = chunk_summaries
            else:
                print(f"\n[Level 2] Merging into {total_groups} group(s)...")
                group_summaries = []
                for g in range(total_groups):
                    group = chunk_summaries[g * GROUP_SIZE : (g + 1) * GROUP_SIZE]
                    print(f"  → Group {g+1}/{total_groups}...", end="\r")
                    group_summaries.append(_merge_group(group, g, total_groups))
                print(f"  ✓ {total_groups} groups merged.              ")

            print(f"\n[Level 3] Generating final {summary_type} summary...")
            summary = _final_merge(group_summaries, summary_type, max_points)
            print(f"  ✓ Final summary ready.")

        # ── Verification ───────────────────────────────────────────────────────
        verification = run_full_verification(text, summary) if verify else None

        print(f"\n{'='*55}")
        print(f"  ✅ DONE")
        if verification:
            print(f"  Verdict : {verification['verdict']}")
            print(f"  Checks  : {verification['checks_passed']} passed")
        print(f"{'='*55}\n")

        return {
            "summary"      : summary,
            "word_count"   : word_count,
            "page_estimate": page_est,
            "chunks"       : n_chunks,
            "verification" : verification,
        }

    except Exception as e:
        return {"error": f"Summarization failed: {str(e)}"}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — QUICK TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Uncomment to check which models are available for your API key:
    # list_available_models()

    sample = """
    Artificial intelligence is transforming industries across the globe.
    Machine learning allows computers to learn from data without being explicitly programmed.
    Deep learning uses neural networks to recognize patterns in images, text, and audio.
    Natural language processing enables machines to understand and generate human language.
    Applications include medical diagnosis, autonomous vehicles, and fraud detection.
    Ethical concerns include bias, job displacement, privacy violations, and autonomous weapons.
    Researchers are working on explainable AI to make model decisions more transparent.
    """ * 30

    result = generate_summary(sample, summary_type="concise", max_points=8, verify=False)

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("\n── SUMMARY ──────────────────────────────────")
        print(result["summary"])
        print(f"\nPages: ~{result['page_estimate']} | Chunks: {result['chunks']}")
