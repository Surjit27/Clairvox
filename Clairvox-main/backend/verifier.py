"""
Clairvox Evidence-First AI Research Assistant
Updated verifier module using the new Clairvox system
"""

import logging
from typing import List, Dict
from .clairvox_analyzer import ClairvoxAnalyzer
from .retriever import is_long_text
import nltk

# Initialize the Clairvox analyzer
clairvox_analyzer = ClairvoxAnalyzer()

# Ensure NLTK data is available
try:
    nltk.data.find('tokenizers/punkt')
except (nltk.downloader.DownloadError, AttributeError):
    nltk.download('punkt')

def analyze_claim(claim_text: str, original_query: str) -> Dict:
    """
    Analyze a single claim using the Clairvox evidence-first system.
    Returns the mandatory JSON format as specified.
    """
    # Create claim data structure
    claim_data = {
        'original_claim': claim_text,
        'normalized_claim': clairvox_analyzer._normalize_claim(claim_text)
    }
    
    # Analyze using Clairvox system
    result = clairvox_analyzer.analyze_claim(claim_data)
    
    # Convert to legacy format for backward compatibility
    legacy_result = {
        'claim': result['original_claim'],
        'confidence': result['confidence_score'],
        'explanation': result['explanation_plain'],
        'evidence': result['top_evidence'],
        'support_count': len(result['top_evidence']),
        'diversity_domains': list(set([e.get('venue', 'unknown') for e in result['top_evidence']])),
        'recency_score': 0.8,  # Placeholder - could be calculated from dates
        'contradiction_count': len(result['contradictions']),
        'source_quality_score': 0.7,  # Placeholder - could be calculated from source types
        # New Clairvox fields
        'clairvox_result': result
    }
    
    return legacy_result

def analyze_text_comprehensive(text: str) -> List[Dict]:
    """
    Analyze entire text using Clairvox system.
    Returns full Clairvox results for all claims.
    """
    return clairvox_analyzer.analyze_text(text)


