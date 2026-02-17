import sys
from unittest.mock import MagicMock

# Mock streamlit completely
mock_st = MagicMock()
def mock_cache_resource(func):
    return func
mock_st.cache_resource = mock_cache_resource
sys.modules["streamlit"] = mock_st

print("Successfully mocked streamlit.")

try:
    from backend.summarizer import generate_summary
    print("Successfully imported generate_summary.")
except ImportError as e:
    print(f"Failed to import generate_summary: {e}")
    sys.exit(1)

# Test with short text
short_text = "This is a short text. It should be summarized easily."
print(f"\nTesting with short text ({len(short_text)} chars)...")
try:
    summary = generate_summary(short_text)
    print(f"Short summary: {summary}")
except Exception as e:
    print(f"Error summarizing short text: {e}")

# Test with long text (to trigger chunking)
# 1024 words is approx limit, so let's go way beyond
long_text = "This is a word. " * 2000 
print(f"\nTesting with long text ({len(long_text)} chars)...")
try:
    summary = generate_summary(long_text, summary_type="detailed")
    print(f"Long summary length: {len(summary)}")
except Exception as e:
    print(f"Error summarizing long text: {e}")
