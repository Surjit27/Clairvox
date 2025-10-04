#!/usr/bin/env python3
"""
Test script to verify Ollama integration works correctly.
This script tests the claim extraction functionality with Ollama and Llama 3.2.
"""

import os
import sys
import logging
from backend.synth import extract_claims_from_text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ollama_integration():
    """Test the Ollama integration for claim extraction."""
    
    # Test text for claim extraction
    test_text = """
    Regular exercise has been shown to improve cardiovascular health and reduce the risk of heart disease. 
    Studies indicate that aerobic exercise can lower blood pressure and improve cholesterol levels. 
    Physical activity also helps with weight management and can reduce the risk of type 2 diabetes. 
    Exercise has positive effects on mental health, reducing symptoms of depression and anxiety. 
    Regular physical activity can improve sleep quality and cognitive function in older adults.
    """
    
    logger.info("Testing Ollama integration with Llama 3.2...")
    logger.info("Model: llama3.2 via Ollama")
    
    # Set environment variable to use Ollama
    os.environ["CLAIM_EXTRACTION_METHOD"] = "ollama"
    
    try:
        logger.info("Extracting claims using Ollama...")
        claims = extract_claims_from_text(test_text, n=5)
        
        if claims:
            logger.info(f"✅ Successfully extracted {len(claims)} claims using Ollama:")
            for i, claim in enumerate(claims, 1):
                logger.info(f"  {i}. {claim['text']}")
                logger.info(f"     Supporting span: {claim['supporting_span'][:100]}...")
        else:
            logger.warning("⚠️ No claims extracted. This might be due to:")
            logger.warning("1. Ollama not running on localhost:11434")
            logger.warning("2. Llama 3.2 model not installed")
            logger.warning("3. API connection issues")
            
    except Exception as e:
        logger.error(f"❌ Error during Ollama integration test: {e}")
        logger.error("Possible solutions:")
        logger.error("1. Make sure Ollama is running: ollama serve")
        logger.error("2. Install Llama 3.2: ollama pull llama3.2")
        logger.error("3. Check if Ollama is accessible at http://localhost:11434")

def test_fallback_heuristic():
    """Test the heuristic fallback method."""
    logger.info("\nTesting heuristic fallback method...")
    
    # Set environment variable to use heuristic
    os.environ["CLAIM_EXTRACTION_METHOD"] = "heuristic"
    
    test_text = "Exercise improves health. Diet affects weight. Sleep is important for recovery."
    
    try:
        claims = extract_claims_from_text(test_text, n=3)
        if claims:
            logger.info(f"✅ Heuristic method extracted {len(claims)} claims:")
            for i, claim in enumerate(claims, 1):
                logger.info(f"  {i}. {claim['text']}")
        else:
            logger.warning("⚠️ Heuristic method failed")
    except Exception as e:
        logger.error(f"❌ Error in heuristic test: {e}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Ollama Integration Test for Clairvox")
    logger.info("=" * 60)
    
    # Test Ollama integration
    test_ollama_integration()
    
    # Test heuristic fallback
    test_fallback_heuristic()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test completed!")
    logger.info("=" * 60)
