#!/usr/bin/env python3
"""
Clairvox Demo Script
Demonstrates the three required test cases as specified in the requirements
"""

import sys
import os
import json
import time
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.verifier import analyze_claim, analyze_text_comprehensive
from backend.clairvox_analyzer import ClairvoxAnalyzer

def print_separator(title):
    """Print a formatted separator"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def print_result(result, test_name):
    """Print formatted result"""
    print(f"\n🧪 {test_name}")
    print("-" * 50)
    
    if isinstance(result, list):
        result = result[0] if result else {}
    
    # Extract Clairvox result if available
    clairvox_result = result.get('clairvox_result', {})
    
    print(f"📝 Original Claim: {clairvox_result.get('original_claim', result.get('claim', 'N/A'))}")
    print(f"🏷️  Classification: {clairvox_result.get('classification', 'N/A')}")
    print(f"📊 Confidence Score: {clairvox_result.get('confidence_score', result.get('confidence', 'N/A'))}/100")
    print(f"🎨 Confidence Color: {clairvox_result.get('confidence_color', 'N/A')}")
    
    if clairvox_result.get('drivers'):
        print(f"💡 Confidence Drivers:")
        for driver in clairvox_result['drivers']:
            print(f"   • {driver}")
    
    if clairvox_result.get('fabricated_terms'):
        print(f"🚨 Fabricated Terms Detected:")
        for term in clairvox_result['fabricated_terms']:
            print(f"   • {term}")
    
    print(f"🔄 Replication Status: {clairvox_result.get('replication_status', 'N/A')}")
    print(f"📖 Explanation: {clairvox_result.get('explanation_plain', result.get('explanation', 'N/A'))}")
    
    if clairvox_result.get('top_evidence'):
        print(f"📚 Top Evidence ({len(clairvox_result['top_evidence'])} sources):")
        for i, evidence in enumerate(clairvox_result['top_evidence'][:3], 1):
            print(f"   {i}. {evidence.get('title', 'No title')}")
            print(f"      Authors: {evidence.get('authors', 'Unknown')}")
            print(f"      Venue: {evidence.get('venue', 'Unknown')} ({evidence.get('date', 'Unknown date')})")
            if evidence.get('doi'):
                print(f"      DOI: {evidence['doi']}")
    
    if clairvox_result.get('contradictions'):
        print(f"⚠️  Contradictions Found ({len(clairvox_result['contradictions'])}):")
        for contradiction in clairvox_result['contradictions']:
            print(f"   • {contradiction.get('title', 'Unknown')}")
    
    if clairvox_result.get('suggested_corrections'):
        print(f"💡 Suggested Corrections: {clairvox_result['suggested_corrections']}")
    
    print(f"🔍 Search Actions: {clairvox_result.get('search_actions', 'N/A')}")

def test_fabricated_content():
    """Test Case 1: Fabricated Content Detection (Must Pass)"""
    print_separator("TEST CASE 1: FABRICATED CONTENT DETECTION")
    
    fabricated_text = """
    The neural photon resonance chamber uses gravito-electroencephalography 
    to achieve ultraviolet-pi band synchronization for memory transfer.
    This revolutionary device can transfer memories between human subjects 
    instantaneously across any distance using quantum entanglement principles.
    """
    
    print("📋 Test Input:")
    print(fabricated_text.strip())
    
    print("\n⏳ Analyzing...")
    start_time = time.time()
    
    try:
        results = analyze_text_comprehensive(fabricated_text)
        analysis_time = time.time() - start_time
        
        print(f"⏱️  Analysis completed in {analysis_time:.2f} seconds")
        
        if results:
            print_result(results[0], "Fabricated Content Analysis")
            
            # Check if test passes
            clairvox_result = results[0].get('clairvox_result', {})
            classification = clairvox_result.get('classification', '')
            confidence = clairvox_result.get('confidence_score', 0)
            fabricated_terms = clairvox_result.get('fabricated_terms', [])
            
            if classification in ['Fabricated', 'Physically Implausible'] and confidence <= 5 and fabricated_terms:
                print("\n✅ TEST PASSED: Fabricated content correctly detected!")
            else:
                print("\n❌ TEST FAILED: Fabricated content not properly detected")
        else:
            print("\n❌ TEST FAILED: No results returned")
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: Error during analysis - {e}")

def test_supported_claim():
    """Test Case 2: Supported Claim (Must Pass)"""
    print_separator("TEST CASE 2: SUPPORTED CLAIM")
    
    supported_text = """
    Optogenetic stimulation of engram cells in mice can induce recall of a memory.
    This technique uses light-sensitive proteins to activate specific neural circuits
    that store memories, allowing researchers to trigger memory retrieval.
    """
    
    print("📋 Test Input:")
    print(supported_text.strip())
    
    print("\n⏳ Analyzing...")
    start_time = time.time()
    
    try:
        results = analyze_text_comprehensive(supported_text)
        analysis_time = time.time() - start_time
        
        print(f"⏱️  Analysis completed in {analysis_time:.2f} seconds")
        
        if results:
            print_result(results[0], "Supported Claim Analysis")
            
            # Check if test passes
            clairvox_result = results[0].get('clairvox_result', {})
            classification = clairvox_result.get('classification', '')
            confidence = clairvox_result.get('confidence_score', 0)
            evidence = clairvox_result.get('top_evidence', [])
            
            if classification == 'Supported' and confidence >= 70 and evidence:
                print("\n✅ TEST PASSED: Supported claim correctly identified!")
            else:
                print("\n❌ TEST FAILED: Supported claim not properly identified")
        else:
            print("\n❌ TEST FAILED: No results returned")
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: Error during analysis - {e}")

def test_physically_implausible():
    """Test Case 3: Physically Implausible Claim (Must Pass)"""
    print_separator("TEST CASE 3: PHYSICALLY IMPLAUSIBLE CLAIM")
    
    implausible_text = """
    Instantaneous knowledge transfer across any distance is possible using 
    quantum entanglement. This technology allows for faster-than-light 
    communication and memory transfer between human subjects.
    """
    
    print("📋 Test Input:")
    print(implausible_text.strip())
    
    print("\n⏳ Analyzing...")
    start_time = time.time()
    
    try:
        results = analyze_text_comprehensive(implausible_text)
        analysis_time = time.time() - start_time
        
        print(f"⏱️  Analysis completed in {analysis_time:.2f} seconds")
        
        if results:
            print_result(results[0], "Physically Implausible Analysis")
            
            # Check if test passes
            clairvox_result = results[0].get('clairvox_result', {})
            classification = clairvox_result.get('classification', '')
            confidence = clairvox_result.get('confidence_score', 0)
            
            if classification == 'Physically Implausible' and confidence == 0:
                print("\n✅ TEST PASSED: Physically implausible claim correctly identified!")
            else:
                print("\n❌ TEST FAILED: Physically implausible claim not properly identified")
        else:
            print("\n❌ TEST FAILED: No results returned")
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: Error during analysis - {e}")

def test_ambiguous_clinical():
    """Test Case 4: Ambiguous Clinical Claim (Bonus Test)"""
    print_separator("TEST CASE 4: AMBIGUOUS CLINICAL CLAIM")
    
    ambiguous_text = """
    A new study suggests that intermittent fasting may help with weight loss,
    but the results are preliminary and more research is needed to confirm
    the long-term effects and safety of this approach.
    """
    
    print("📋 Test Input:")
    print(ambiguous_text.strip())
    
    print("\n⏳ Analyzing...")
    start_time = time.time()
    
    try:
        results = analyze_text_comprehensive(ambiguous_text)
        analysis_time = time.time() - start_time
        
        print(f"⏱️  Analysis completed in {analysis_time:.2f} seconds")
        
        if results:
            print_result(results[0], "Ambiguous Clinical Analysis")
            
            # Check if test passes
            clairvox_result = results[0].get('clairvox_result', {})
            classification = clairvox_result.get('classification', '')
            confidence = clairvox_result.get('confidence_score', 0)
            
            if classification in ['Weakly Supported', 'Unsupported'] and 0 < confidence < 70:
                print("\n✅ TEST PASSED: Ambiguous claim correctly handled!")
            else:
                print("\n⚠️  TEST PARTIAL: Ambiguous claim handled but may need refinement")
        else:
            print("\n❌ TEST FAILED: No results returned")
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: Error during analysis - {e}")

def main():
    """Run all demo tests"""
    print("🔎 CLAIRVOX DEMO - Evidence-First AI Research Assistant")
    print(f"📅 Demo run started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all test cases
    test_fabricated_content()
    test_supported_claim()
    test_physically_implausible()
    test_ambiguous_clinical()
    
    print_separator("DEMO COMPLETED")
    print("🎯 Summary:")
    print("   • Test Case 1: Fabricated Content Detection")
    print("   • Test Case 2: Supported Claim Analysis")
    print("   • Test Case 3: Physically Implausible Detection")
    print("   • Test Case 4: Ambiguous Clinical Claim Handling")
    print("\n📖 For more information, see README.md")
    print("🌐 Web interface: streamlit run app.py")

if __name__ == "__main__":
    main()


