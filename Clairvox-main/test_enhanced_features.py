#!/usr/bin/env python3
"""
Test script for enhanced Clairvox features
Demonstrates the new 3-tier classification system and concept-based search
"""

from backend.clairvox_analyzer import ClairvoxAnalyzer
import json

def test_enhanced_features():
    """Test the enhanced Clairvox features"""
    print("Testing Enhanced Clairvox Features")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = ClairvoxAnalyzer()
    
    # Test claims with different expected classifications
    test_claims = [
        "Intermittent fasting reduces inflammation markers in humans",
        "Quantum entanglement allows faster-than-light communication",
        "Regular exercise improves cardiovascular health",
        "Memory transfer between human brains is possible using optogenetics"
    ]
    
    for i, claim in enumerate(test_claims, 1):
        print(f"\nTest Claim {i}: {claim}")
        print("-" * 40)
        
        # Create claim data
        claim_data = {
            'original_claim': claim,
            'normalized_claim': analyzer._normalize_claim(claim)
        }
        
        # Analyze claim
        result = analyzer.analyze_claim(claim_data)
        
        # Display results
        print(f"Classification: {result['classification']}")
        print(f"Confidence Score: {result['confidence_score']}/100")
        print(f"Evidence Count: {len(result['top_evidence'])}")
        print(f"Contradictions: {len(result['contradictions'])}")
        
        # Show top 3 sources
        if result['top_evidence']:
            print("\nTop Sources:")
            for j, evidence in enumerate(result['top_evidence'][:3], 1):
                print(f"  {j}. {evidence.get('title', 'No title')}")
                print(f"     DOI: {evidence.get('doi', 'N/A')}")
                print(f"     Type: {evidence.get('type', 'unknown')}")
                print(f"     Venue: {evidence.get('venue', 'Unknown')}")
        
        # Show explanation
        print(f"\nExplanation: {result['explanation_plain']}")
        
        # Show drivers
        if result.get('drivers'):
            print(f"\nConfidence Drivers:")
            for driver in result['drivers']:
                print(f"  • {driver}")
        
        print("\n" + "=" * 50)

if __name__ == "__main__":
    test_enhanced_features()
