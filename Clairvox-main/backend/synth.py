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
3. The output MUST be ONLY a valid JSON array of objects.
4. Each object in the array must have two keys: "text" (the full sentence of the claim) and "supporting_span" (the original text snippet it came from).

Text:
{context}

JSON Output:"""

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
        
        # Find JSON array in the response
        if not json_str.startswith('['):
            start_index = json_str.find('[')
            if start_index != -1:
                json_str = json_str[start_index:]
        
        if not json_str.endswith(']'):
            end_index = json_str.rfind(']')
            if end_index != -1:
                json_str = json_str[:end_index+1]

        claims = json.loads(json_str)
        
        if isinstance(claims, list) and all('text' in c and 'supporting_span' in c for c in claims):
            logging.info(f"Successfully extracted {len(claims)} claims using Ollama")
            return claims
        else:
            logging.warning(f"Ollama output was not in the expected format: {claims}")
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



