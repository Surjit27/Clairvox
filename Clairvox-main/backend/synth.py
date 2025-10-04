from typing import List, Dict
import os
import logging
import requests
import json
from .extractor import split_into_sentences, clean_text
from .utils import cache_get, cache_set, get_cache_key

# --- LLM Configuration ---
CLAIM_EXTRACTION_METHOD = os.environ.get("CLAIM_EXTRACTION_METHOD", "ollama").lower()
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"  # Using Llama 3.2 via Ollama

# --- PROMPT FOR OLLAMA LLAMA 3.2 ---
# Updated prompt format for Ollama with Llama 3.2
CLAIM_EXTRACTION_PROMPT = """You are an expert at analyzing text and extracting key claims. Your task is to identify the most important and distinct claims from the given text.

Analyze the text below and extract 5 to 7 of the most important and distinct claims.

**CRITICAL INSTRUCTIONS:**
1. Each claim MUST be a single, complete, and grammatically correct sentence.
2. DO NOT start claims with "..." or use fragmented sentences. Do not include markdown like '---'.
3. The output MUST be ONLY a valid JSON array starting with [ and ending with ].
4. Each object in the array must have two keys: "text" (the full sentence of the claim) and "supporting_span" (the original text snippet it came from).
5. Return ONLY the JSON array, no other text.

Text:
{context}

Return only this JSON format:
[
  {
    "text": "First claim here",
    "supporting_span": "Original text snippet"
  },
  {
    "text": "Second claim here", 
    "supporting_span": "Original text snippet"
  }
]"""

def extract_claims_with_ollama(context: str) -> List[Dict]:
    """Uses Ollama with Llama 3.2 to extract claims from text."""
    prompt = CLAIM_EXTRACTION_PROMPT.format(context=context[:2048])
    
    try:
        # Prepare the request payload for Ollama API
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 1024
            }
        }
        
        # Make request to Ollama API
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        raw_output = result.get('response', '').strip()
        
        if not raw_output:
            logging.warning("Empty response from Ollama")
            return []
        
        # Clean the output to be valid JSON
        json_str = raw_output.strip()
        
        # Remove any leading text before the first [
        if '[' in json_str:
            json_str = json_str[json_str.find('['):]
        
        # Remove any trailing text after the last ]
        if ']' in json_str:
            json_str = json_str[:json_str.rfind(']') + 1]
        
        # Fix malformed JSON by ensuring proper array structure
        if not json_str.startswith('['):
            json_str = '[' + json_str
        if not json_str.endswith(']'):
            json_str = json_str + ']'
        
        # Clean up common JSON formatting issues
        json_str = json_str.replace('\n', '')  # Remove newlines
        json_str = json_str.replace('\r', '')  # Remove carriage returns
        json_str = json_str.replace('\t', '')  # Remove tabs
        json_str = json_str.replace('  ', ' ')  # Replace double spaces with single
        json_str = json_str.strip()
        
        # Try to fix malformed JSON structure
        # If it looks like multiple JSON objects without proper array structure
        if json_str.count('{') > 1 and not json_str.startswith('['):
            # Split by } and { to find individual objects
            parts = json_str.split('}')
            fixed_parts = []
            for part in parts:
                if part.strip() and '{' in part:
                    if not part.strip().startswith('{'):
                        part = '{' + part.split('{', 1)[1] if '{' in part else part
                    fixed_parts.append(part + '}')
            
            if fixed_parts:
                json_str = '[' + ','.join(fixed_parts) + ']'
        
        try:
            claims = json.loads(json_str)
            
            if isinstance(claims, list) and all('text' in c and 'supporting_span' in c for c in claims):
                logging.info(f"Successfully extracted {len(claims)} claims using Ollama")
                return claims
            else:
                logging.warning(f"Ollama output was not in the expected format: {claims}")
                return []
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            logging.error(f"Attempted to parse: {json_str[:200]}...")
            
            # Try to extract claims from malformed JSON using regex
            import re
            try:
                # Look for text and supporting_span patterns
                text_pattern = r'"text":\s*"([^"]+)"'
                span_pattern = r'"supporting_span":\s*"([^"]+)"'
                
                text_matches = re.findall(text_pattern, json_str)
                span_matches = re.findall(span_pattern, json_str)
                
                if text_matches and span_matches and len(text_matches) == len(span_matches):
                    claims = []
                    for i in range(len(text_matches)):
                        claims.append({
                            'text': text_matches[i],
                            'supporting_span': span_matches[i]
                        })
                    logging.info(f"Extracted {len(claims)} claims using regex fallback")
                    return claims
            except Exception as regex_error:
                logging.error(f"Regex fallback also failed: {regex_error}")
            
            return []

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to connect to Ollama API: {e}")
        return []
    except (json.JSONDecodeError, IndexError, TypeError) as e:
        logging.error(f"Failed to parse Ollama output for claim extraction: {e}")
        logging.error(f"Raw Ollama output was: {raw_output}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in Ollama claim extraction: {e}")
        return []

def extract_claims_with_heuristic(context: str, n: int = 8) -> List[Dict]:
    """Fallback heuristic: split text into sentences and return the first N."""
    sentences = split_into_sentences(context)
    claims = []
    for sentence in sentences:
        cleaned = clean_text(sentence)
        if len(cleaned.split()) > 5 and not cleaned.endswith('?'):
            claims.append({
                "text": cleaned,
                "supporting_span": sentence
            })
        if len(claims) == n:
            break
    return claims


def extract_claims_from_text(context: str, n: int = 8) -> List[Dict]:
    """
    Main function to extract claims. Uses Ollama or heuristic based on environment variable.
    """
    cache_key = get_cache_key("claims_v2", f"method={CLAIM_EXTRACTION_METHOD}|n={n}|{context}")
    cached = cache_get(cache_key)
    if cached:
        logging.info("Cache hit for claim extraction.")
        return cached

    claims = []
    if CLAIM_EXTRACTION_METHOD == "ollama":
        try:
            claims = extract_claims_with_ollama(context)
        except Exception as e:
            logging.warning(f"Ollama claim extraction failed ({e}), falling back to heuristic.")
            claims = []
    
    if not claims:
        logging.info("Using heuristic method for claim extraction.")
        claims = extract_claims_with_heuristic(context, n)
    
    if claims:
        cache_set(cache_key, claims)

    return claims



