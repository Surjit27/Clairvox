import requests
import logging
import re
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from ddgs import DDGS
import wikipedia
from langdetect import detect
from .utils import cache_get, cache_set, get_cache_key, USER_AGENT

logging.basicConfig(level=logging.INFO)

# --- Helpers -----------------------------------------------------------------

def is_long_text(query: str, threshold: int = 300) -> bool:
    """Checks if the input text is long, like an article."""
    return len(query) > threshold

# --- MODIFIED: This function is rewritten to be 100% compatible ---
def is_predominantly_english(text: str, threshold: float = 0.9) -> bool:
    """
    Checks if a text is predominantly English without using unsupported regex.
    """
    if not text:
        return False

    total_letters = 0
    latin_letters = 0

    for char in text:
        if char.isalpha():  # Counts any letter from any language
            total_letters += 1
            if 'a' <= char.lower() <= 'z':  # Checks if it is a-z
                latin_letters += 1
    
    if total_letters == 0:
        return True  # A string with no letters can't be non-English

    ratio = latin_letters / total_letters
    return ratio >= threshold

def extract_topic_from_query(query: str) -> str:
    query_lower = query.lower()
    question_words = ['does', 'do', 'is', 'are', 'can', 'will', 'should',
                      'how', 'what', 'why', 'when', 'where']
    words = query_lower.split()
    while words and words[0] in question_words:
        words.pop(0)
    words = [w.rstrip('?.!') for w in words]
    topic = ' '.join(words)
    return topic.strip()

def is_duplicate(existing: List[str], snippet: str, threshold: float = 0.85) -> bool:
    for c in existing:
        if SequenceMatcher(None, c, snippet).ratio() > threshold:
            return True
    return False

def compute_confidence(snippet: str, topic_keywords: List[str], base: int = 50) -> int:
    count = sum(1 for kw in topic_keywords if kw.lower() in snippet.lower())
    return min(100, base + count * 10)

def extract_topic_keywords(query: str) -> List[str]:
    topic = extract_topic_from_query(query)
    words = topic.split()
    return list(set(words))

# --- Context & Evidence Fetching -------------------------------------------

def fetch_wikipedia_summary(query: str, num_web_results: int = 3) -> Optional[str]:
    cache_key = get_cache_key("rich_context_v4", query)
    cached = cache_get(cache_key)
    if cached:
        logging.info("Returning rich context from cache.")
        return cached

    context_parts = []
    
    if len(query) < 400:
        topic = extract_topic_from_query(query)
        try:
            wiki_results = wikipedia.search(topic)
            if wiki_results:
                page = wikipedia.page(wiki_results[0], auto_suggest=False, redirect=True)
                wiki_summary = page.summary
                if wiki_summary:
                    context_parts.append(wiki_summary)
        except Exception as e:
            logging.warning(f"Could not fetch Wikipedia summary: {e}")
    else:
        logging.info("Long text detected, skipping Wikipedia summary fetch.")

    logging.info("Performing web search for initial context...")
    try:
        search_query_for_context = query
        if len(query) > 500:
            first_sentence = query.split('.')[0]
            search_query_for_context = extract_topic_from_query(first_sentence)
        
        web_results = search_web_for_evidence_fast(search_query_for_context, max_results=num_web_results)
        if web_results:
            snippets = [r.get("snippet", "") for r in web_results if r.get("snippet")]
            context_parts.extend(snippets)
            logging.info(f"Added {len(snippets)} snippets from web search.")
    except Exception as e:
        logging.warning(f"Web search for initial context failed: {e}")

    if not context_parts:
        return None

    combined_context = "\n\n---\n\n".join(context_parts)
    cache_set(cache_key, combined_context)
    return combined_context

def search_web_for_evidence_fast(query: str, max_results: int = 5) -> List[Dict]:
    # We must now put the try...except block back to prevent future crashes
    results = []
    cache_key = get_cache_key("ddgs_search_en_strict", f"{query}_{max_results}")
    cached = cache_get(cache_key)
    if cached:
        return cached
    try:
        with DDGS(timeout=10) as ddgs:
            search_results = ddgs.text(query, max_results=max_results*2, region="us-en", safesearch="Moderate")
            
            for r in search_results:
                snippet = r.get("body", "") or ""
                
                if not snippet or not is_predominantly_english(snippet) or is_duplicate([res["snippet"] for res in results], snippet):
                    continue
                
                topic_keywords = extract_topic_keywords(query)
                results.append({
                    "url": r.get("href", ""),
                    "title": r.get("title", ""),
                    "snippet": snippet,
                    "confidence": compute_confidence(snippet, topic_keywords)
                })
                if len(results) >= max_results:
                    break
        cache_set(cache_key, results)
    except Exception as e:
        logging.warning(f"DDGS fallback failed: {e}")
    return results

# The functions below are not actively used by the app
def fetch_dbpedia_summary(query: str) -> Optional[str]: return None
def fetch_wikidata_summary(query: str) -> Optional[str]: return None
def extract_claims(query: str, max_claims: int = 5) -> List[Dict]: return []