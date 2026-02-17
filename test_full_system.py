"""
Comprehensive test script for PDF Summarizer
Tests both summary generation and Q&A generation

Usage:
    python test_full_system.py --gemini-key YOUR_GEMINI_API_KEY
"""

import sys
import os
from unittest.mock import MagicMock
import argparse

# Mock streamlit completely
mock_st = MagicMock()
def mock_cache_resource(func):
    return func
mock_st.cache_resource = mock_cache_resource
sys.modules["streamlit"] = mock_st

print("✓ Successfully mocked streamlit.\n")

# Parse arguments
parser = argparse.ArgumentParser(description='Test PDF Summarizer')
parser.add_argument('--gemini-key', type=str, help='Google Gemini API Key', default=None)
args = parser.parse_args()

# Import modules
try:
    from backend.summarizer import generate_summary
    from backend.question_generator import generate_qa_pairs
    print("✓ Successfully imported backend modules.\n")
except ImportError as e:
    print(f"✗ Failed to import backend modules: {e}")
    sys.exit(1)

# Test data
sample_text = """
Artificial Intelligence (AI) is transforming the world in unprecedented ways. 
Machine learning, a subset of AI, enables computers to learn from data without being explicitly programmed. 
Deep learning, which uses neural networks with multiple layers, has achieved remarkable success in image recognition, 
natural language processing, and game playing. The applications of AI span across healthcare, finance, 
transportation, and entertainment. However, ethical considerations such as bias, privacy, and job displacement 
must be carefully addressed as AI continues to evolve.
"""

print("=" * 80)
print("TEST 1: SUMMARY GENERATION (CONCISE)")
print("=" * 80)
try:
    concise_summary = generate_summary(sample_text, summary_type="concise")
    print(f"\n✓ Concise Summary Generated:")
    print(f"   Length: {len(concise_summary)} characters")
    print(f"   Content: {concise_summary[:200]}..." if len(concise_summary) > 200 else f"   Content: {concise_summary}")
    
    if "Error" in concise_summary:
        print("\n⚠ WARNING: Error detected in summary output")
        concise_success = False
    else:
        concise_success = True
        print("\n✓ PASSED: Concise summary looks good")
except Exception as e:
    print(f"\n✗ FAILED: Error generating concise summary: {e}")
    concise_success = False

print("\n" + "=" * 80)
print("TEST 2: SUMMARY GENERATION (DETAILED)")
print("=" * 80)
try:
    detailed_summary = generate_summary(sample_text, summary_type="detailed")
    print(f"\n✓ Detailed Summary Generated:")
    print(f"   Length: {len(detailed_summary)} characters")
    print(f"   Content: {detailed_summary[:200]}..." if len(detailed_summary) > 200 else f"   Content: {detailed_summary}")
    
    if "Error" in detailed_summary:
        print("\n⚠ WARNING: Error detected in summary output")
        detailed_success = False
    else:
        detailed_success = True
        print("\n✓ PASSED: Detailed summary looks good")
except Exception as e:
    print(f"\n✗ FAILED: Error generating detailed summary: {e}")
    detailed_success = False

print("\n" + "=" * 80)
print("TEST 3: Q&A GENERATION (GEMINI)")
print("=" * 80)

if not args.gemini_key:
    print("\n⚠ SKIPPED: No Gemini API key provided. Use --gemini-key to test Q&A generation.")
    qa_success = None
else:
    try:
        qa_result = generate_qa_pairs(sample_text, args.gemini_key)
        print(f"\n✓ Q&A Generated:")
        print(f"   Length: {len(qa_result)} characters")
        print(f"   Preview:\n")
        # Print first 500 characters
        print(qa_result[:500] + "..." if len(qa_result) > 500 else qa_result)
        
        if "Error" in qa_result:
            print("\n✗ FAILED: Error detected in Q&A output")
            qa_success = False
        else:
            # Check if it has Q/A format
            if "Q1:" in qa_result or "Q:" in qa_result or "Question" in qa_result:
                qa_success = True
                print("\n✓ PASSED: Q&A format detected")
            else:
                qa_success = False
                print("\n⚠ WARNING: Q&A format not clearly detected")
    except Exception as e:
        print(f"\n✗ FAILED: Error generating Q&A: {e}")
        qa_success = False

# Summary report
print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)
print(f"Concise Summary:  {'✓ PASSED' if concise_success else '✗ FAILED'}")
print(f"Detailed Summary: {'✓ PASSED' if detailed_success else '✗ FAILED'}")
print(f"Q&A Generation:   {'✓ PASSED' if qa_success else '✗ FAILED' if qa_success is False else '⊘ SKIPPED'}")

# Calculate accuracy
tests_run = 2 if qa_success is None else 3
tests_passed = sum([concise_success, detailed_success, qa_success or 0])
accuracy = (tests_passed / tests_run) * 100 if tests_run > 0 else 0

print(f"\nAccuracy: {tests_passed}/{tests_run} tests passed ({accuracy:.1f}%)")

if accuracy == 100:
    print("\n🎉 All tests passed! System is working correctly.")
elif accuracy >= 66:
    print("\n⚠ Most tests passed, but some issues remain.")
else:
    print("\n❌ System has significant issues that need to be addressed.")

print("\n" + "=" * 80)
