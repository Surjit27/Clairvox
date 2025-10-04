#!/usr/bin/env python3
"""
Demo script for enhanced Clairvox features
Shows the new 3-tier classification system and concept-based search
"""

from backend.clairvox_analyzer import ClairvoxAnalyzer
import json

def demo_enhanced_features():
    """Demo the enhanced Clairvox features"""
    print("Clairvox Enhanced Features Demo")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = ClairvoxAnalyzer()
    
    # Demo claim
    claim = "Regular exercise improves cardiovascular health"
    print(f"Demo Claim: {claim}")
    print("-" * 40)
    
    # Create claim data
    claim_data = {
        'original_claim': claim,
        'normalized_claim': analyzer._normalize_claim(claim)
    }
    
    print("Analyzing claim with enhanced features...")
    print("Features being demonstrated:")
    print("1. Concept-based queries with synonyms")
    print("2. 3-tier classification system")
    print("3. Enhanced confidence explanations")
    print("4. Top 3 sources with DOI and excerpts")
    print("5. Domain violation detection")
    print("6. Reproducible results panel")
    print()
    
    # Analyze claim
    result = analyzer.analyze_claim(claim_data)
    
    # Display results
    print("RESULTS:")
    print(f"Classification: {result['classification']}")
    print(f"Confidence Score: {result['confidence_score']}/100")
    print(f"Evidence Count: {len(result['top_evidence'])}")
    print(f"Contradictions: {len(result['contradictions'])}")
    
    # Show explanation
    print(f"\nExplanation: {result['explanation_plain']}")
    
    # Show drivers
    if result.get('drivers'):
        print(f"\nConfidence Drivers:")
        for driver in result['drivers']:
            print(f"  • {driver}")
    
    # Show search queries used
    if result.get('search_actions'):
        print(f"\nSearch Actions: {result['search_actions']}")
    
    print("\n" + "=" * 50)
    print("Demo completed! The enhanced features are working.")
    print("You can now run 'streamlit run app.py' to see the full UI.")

if __name__ == "__main__":
    demo_enhanced_features()
