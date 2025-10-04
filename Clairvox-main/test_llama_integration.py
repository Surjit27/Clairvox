#!/usr/bin/env python3
"""
Test script to verify Llama model integration works correctly.
This script tests the claim extraction functionality with the new Meta Llama model.
"""

import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_llama_integration():
    """Test the Llama model integration for claim extraction."""
    try:
        # Import the claim extraction function
        from backend.synth import extract_claims_from_text
        
        # Test text for claim extraction
        test_text = """
        Intermittent fasting has gained popularity as a weight loss method. 
        Studies show that intermittent fasting can help reduce body weight by 3-8% over 3-24 weeks. 
        The practice involves alternating between periods of eating and fasting. 
        Research indicates that intermittent fasting may improve insulin sensitivity and reduce inflammation. 
        However, some studies suggest that intermittent fasting may not be suitable for everyone, particularly those with certain medical conditions.
        """
        
        logger.info("Testing Llama model integration...")
        logger.info(f"Model: meta-llama/Llama-3-8B-Instruct")
        
        # Test with LLM method
        os.environ["CLAIM_EXTRACTION_METHOD"] = "llm"
        claims = extract_claims_from_text(test_text, n=5)
        
        if claims:
            logger.info(f"✅ Successfully extracted {len(claims)} claims using Llama model:")
            for i, claim in enumerate(claims, 1):
                logger.info(f"  {i}. {claim.get('text', 'No text')}")
        else:
            logger.warning("⚠️ No claims extracted. This might be due to model loading issues or prompt formatting.")
            
        # Test with heuristic method as fallback
        logger.info("\nTesting heuristic fallback method...")
        os.environ["CLAIM_EXTRACTION_METHOD"] = "heuristic"
        heuristic_claims = extract_claims_from_text(test_text, n=5)
        
        if heuristic_claims:
            logger.info(f"✅ Heuristic method extracted {len(heuristic_claims)} claims:")
            for i, claim in enumerate(heuristic_claims, 1):
                logger.info(f"  {i}. {claim.get('text', 'No text')}")
        
        logger.info("\n🎉 Integration test completed!")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure you have installed the required dependencies:")
        logger.error("pip install transformers accelerate torch")
        
    except Exception as e:
        logger.error(f"❌ Error during testing: {e}")
        logger.error("This might be due to:")
        logger.error("1. Missing dependencies")
        logger.error("2. Insufficient GPU memory")
        logger.error("3. Model download issues")
        logger.error("4. Network connectivity problems")

if __name__ == "__main__":
    test_llama_integration()


