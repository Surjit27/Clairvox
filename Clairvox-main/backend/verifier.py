"""
Clairvox Evidence-First AI Research Assistant
Enhanced verifier module with comprehensive output formatting
"""

import logging
import requests
import json
import os
from typing import List, Dict, Optional
from .retriever import search_web_for_evidence_fast, extract_topic_keywords
from .utils import cache_get, cache_set, get_cache_key

logging.basicConfig(level=logging.INFO)

# --- LLM Configuration for Enhanced Analysis ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# Enhanced analysis prompt for comprehensive explanations
ENHANCED_ANALYSIS_PROMPT = """You are an expert research analyst. Analyze the following claim and provide a comprehensive, point-wise explanation.

**CLAIM TO ANALYZE:** {claim_text}

**CONTEXT:** {context}

**EVIDENCE FOUND:** {evidence_summary}

**TASK:** Provide a detailed analysis with the following structure:

1. **Claim Classification:** (Supported/Partially Supported/Unsupported/Contradicted)
2. **Confidence Level:** (High/Medium/Low with percentage)
3. **Key Evidence Points:** (List 3-5 main supporting or contradicting points)
4. **Source Quality Assessment:** (Evaluate the reliability of sources)
5. **Potential Limitations:** (What gaps exist in the evidence)
6. **Recommendations:** (What additional research would strengthen this claim)

**CRITICAL INSTRUCTIONS:**
- Return ONLY plain text explanations, NO HTML tags, NO markdown formatting
- Use simple bullet points with dashes (-) not HTML lists
- Provide comprehensive, detailed explanations that thoroughly analyze the claim
- Include specific evidence points that directly support or contradict the claim
- Explain the strength and quality of the evidence found
- Identify any gaps or limitations in the evidence
- Provide actionable recommendations for further research
- Keep explanations factual, objective, and well-structured
- Do not include any HTML syntax like <div>, <span>, <strong>, etc.

**OUTPUT FORMAT:** Return a JSON object with these exact keys:
{{
    "classification": "Supported/Partially Supported/Unsupported/Contradicted",
    "confidence_score": 85,
    "explanation_plain": "Detailed point-wise explanation here in plain text only",
    "key_evidence_points": ["Point 1", "Point 2", "Point 3"],
    "source_quality": "High/Medium/Low",
    "limitations": ["Limitation 1", "Limitation 2"],
    "recommendations": ["Recommendation 1", "Recommendation 2"]
}}

Return ONLY the JSON object, no other text."""

def analyze_claim_with_llm(claim_text: str, context: str, evidence: List[Dict]) -> Dict:
    """Use local LLM for enhanced claim analysis with caching for performance."""
    # Create cache key for LLM analysis
    cache_key = get_cache_key("llm_analysis", f"{claim_text}_{len(evidence)}")
    cached = cache_get(cache_key)
    if cached:
        logging.info("Returning cached LLM analysis.")
        return cached
    
    try:
        # Prepare evidence summary
        evidence_summary = ""
        if evidence:
            evidence_summary = "\n".join([
                f"• {e.get('title', 'Unknown')} - {e.get('snippet', 'No excerpt')[:200]}..."
                for e in evidence[:5]
            ])
        else:
            evidence_summary = "No direct evidence found"
        
        prompt = ENHANCED_ANALYSIS_PROMPT.format(
            claim_text=claim_text,
            context=context[:1000],  # Limit context length
            evidence_summary=evidence_summary
        )
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 512,  # Reduced for faster processing
                "num_ctx": 2048,     # Reduced context window
                "num_batch": 1,      # Process one at a time
                "num_thread": 2      # Use 2 threads for faster processing
            }
        }
        
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=20)  # Reduced timeout
        response.raise_for_status()
        
        result = response.json()
        raw_output = result.get('response', '').strip()
        
        if not raw_output:
            return get_fallback_analysis(claim_text, evidence)
        
        # Clean and parse JSON
        json_str = raw_output.strip()
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0]
        elif '```' in json_str:
            json_str = json_str.split('```')[1].split('```')[0]
        
        try:
            analysis = json.loads(json_str)
            # Cache the result for future use
            cache_set(cache_key, analysis)
            return analysis
        except json.JSONDecodeError:
            return get_fallback_analysis(claim_text, evidence)
            
    except Exception as e:
        logging.warning(f"LLM analysis failed: {e}")
        return get_fallback_analysis(claim_text, evidence)

def get_fallback_analysis(claim_text: str, evidence: List[Dict]) -> Dict:
    """Fallback analysis when LLM is not available."""
    confidence = 50
    classification = "Unsupported"
    
    if evidence:
        confidence = min(85, 50 + len(evidence) * 10)
        if len(evidence) >= 3:
            classification = "Supported"
        elif len(evidence) >= 1:
            classification = "Partially Supported"
    
    return {
        "classification": classification,
        "confidence_score": confidence,
        "explanation_plain": f"Analysis of claim: {claim_text}. Found {len(evidence)} supporting sources.",
        "key_evidence_points": [e.get('title', 'Unknown source') for e in evidence[:3]],
        "source_quality": "Medium",
        "limitations": ["Limited evidence base", "Requires further verification"],
        "recommendations": ["Seek additional peer-reviewed sources", "Verify claims with multiple databases"]
    }

def search_evidence_for_claim(claim_text: str, original_query: str) -> List[Dict]:
    """Search for evidence supporting the claim with enhanced metadata extraction."""
    cache_key = get_cache_key("claim_evidence", f"{claim_text}_{original_query}")
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    # Extract keywords from claim
    topic_keywords = extract_topic_keywords(claim_text)
    
    # Create more targeted search queries for academic sources
    search_queries = [
        claim_text,
        f'"{claim_text[:50]}..."',
        " ".join(topic_keywords[:3]),
        f"{claim_text} research study",
        f"{claim_text} academic paper",
        f"{claim_text} journal article",
        f"{claim_text} peer reviewed",
        f"{claim_text} scientific study",
        f"{claim_text} research findings",
        f"{claim_text} academic research"
    ]
    
    all_evidence = []
    for i, query in enumerate(search_queries):
        try:
            # Use more results for academic queries
            max_results = 5 if i < 5 else 3  # More results for academic-focused queries
            results = search_web_for_evidence_fast(query, max_results=max_results)
            
            # If no results, try with a simpler query
            if not results and len(query) > 100:
                simple_query = query[:50] + "..."
                results = search_web_for_evidence_fast(simple_query, max_results=2)
            
            for result in results:
                # Extract better metadata from the result
                title = result.get('title', '')
                url = result.get('url', '')
                snippet = result.get('snippet', '')
                
                # Try to extract DOI from snippet or URL
                doi = extract_doi_from_text(snippet + " " + url)
                
                # Determine source type based on URL and content
                source_type = determine_source_type(url, title, snippet)
                
                # Extract venue information
                venue = extract_venue_from_title(title, url)
                
                # Calculate better relevance score
                relevance_score = calculate_enhanced_relevance(claim_text, title, snippet)
                
                # Skip very low relevance results
                if relevance_score < 20:
                    continue
                
                enhanced_result = {
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'query_used': query,
                    'source': 'Web Search',
                    'type': source_type,
                    'doi': doi,
                    'venue': venue,
                    'authors': 'Unknown authors',  # Would need more sophisticated extraction
                    'date': 'Unknown date',  # Would need more sophisticated extraction
                    'relevance_score': relevance_score,
                    'confidence': result.get('confidence', 50)
                }
                all_evidence.append(enhanced_result)
        except Exception as e:
            logging.warning(f"Search failed for query '{query}': {e}")
    
    # Remove duplicates and sort by relevance
    unique_evidence = []
    seen_urls = set()
    for evidence in all_evidence:
        url = evidence.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_evidence.append(evidence)
    
    # Sort by relevance score and prioritize academic sources
    def sort_key(evidence):
        base_score = evidence.get('relevance_score', 0)
        source_type = evidence.get('type', 'web')
        
        # Boost academic sources
        if source_type == 'peer-reviewed':
            return base_score + 50
        elif source_type == 'preprint':
            return base_score + 30
        elif source_type == 'conference':
            return base_score + 25
        elif source_type == 'research':
            return base_score + 20
        else:
            return base_score
    
    unique_evidence.sort(key=sort_key, reverse=True)
    
    cache_set(cache_key, unique_evidence[:10])  # Cache top 10 results
    return unique_evidence[:10]

def extract_doi_from_text(text: str) -> str:
    """Extract DOI from text if present."""
    import re
    doi_pattern = r'10\.\d+/[^\s]+'
    match = re.search(doi_pattern, text)
    return match.group(0) if match else ""

def determine_source_type(url: str, title: str, snippet: str) -> str:
    """Determine source type based on URL and content."""
    url_lower = url.lower()
    title_lower = title.lower()
    snippet_lower = snippet.lower()
    
    # Academic sources - more comprehensive list
    academic_domains = [
        'arxiv.org', 'scholar.google', 'researchgate', 'academia.edu', 'jstor.org',
        'pubmed', 'ncbi.nlm.nih.gov', 'springer', 'elsevier', 'ieee', 'acm',
        'nature.com', 'science.org', 'cell.com', 'plos.org', 'frontiersin.org',
        'wiley.com', 'sagepub.com', 'tandfonline.com', 'cambridge.org',
        'oxfordjournals.org', 'bmj.com', 'nejm.org', 'thelancet.com'
    ]
    
    if any(domain in url_lower for domain in academic_domains):
        if any(keyword in title_lower + snippet_lower for keyword in ['journal', 'article', 'study', 'research']):
            return 'peer-reviewed'
        else:
            return 'preprint'
    elif any(domain in url_lower for domain in ['conference', 'proceedings', 'workshop', 'symposium']):
        return 'conference'
    elif any(domain in url_lower for domain in ['news', 'bbc', 'cnn', 'reuters', 'guardian', 'nytimes', 'washingtonpost']):
        return 'news'
    elif any(keyword in title_lower + snippet_lower for keyword in ['research', 'study', 'analysis', 'findings', 'journal']):
        return 'research'
    else:
        return 'web'

def extract_venue_from_title(title: str, url: str) -> str:
    """Extract venue information from title and URL."""
    # Try to extract journal/conference name
    if 'journal' in title.lower() or 'proceedings' in title.lower():
        return title[:50] + "..." if len(title) > 50 else title
    elif url:
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc
            return domain.replace('www.', '')
        except:
            return "Unknown venue"
    return "Unknown venue"

def calculate_enhanced_relevance(claim_text: str, title: str, snippet: str) -> int:
    """Calculate enhanced relevance score with better filtering."""
    claim_words = set(claim_text.lower().split())
    title_words = set(title.lower().split())
    snippet_words = set(snippet.lower().split())
    
    # Filter out irrelevant content
    irrelevant_keywords = [
        'pretty', 'ugly', 'beauty', 'face', 'test', 'quiz', 'dating', 'relationship',
        'shopping', 'fashion', 'entertainment', 'celebrity', 'gossip', 'horoscope'
    ]
    
    # Check for irrelevant content
    for keyword in irrelevant_keywords:
        if keyword in title.lower() or keyword in snippet.lower():
            return 10  # Very low relevance for irrelevant content
    
    # Calculate word overlap
    title_overlap = len(claim_words.intersection(title_words))
    snippet_overlap = len(claim_words.intersection(snippet_words))
    
    # Base score
    base_score = 50
    
    # Add points for overlaps
    relevance_score = base_score + (title_overlap * 10) + (snippet_overlap * 5)
    
    # Boost technical content
    technical_keywords = ['api', 'code', 'function', 'programming', 'development', 'software', 'technical', 'aws', 'cloud', 'database']
    if any(keyword in title.lower() + snippet.lower() for keyword in technical_keywords):
        relevance_score += 20
    
    return min(100, relevance_score)

def analyze_claim(claim_text: str, original_query: str) -> Dict:
    """
    Analyze a single claim with enhanced evidence search and comprehensive output.
    Returns the enhanced JSON format with proper formatting.
    """
    # Search for evidence
    evidence = search_evidence_for_claim(claim_text, original_query)
    
    # Use LLM for enhanced analysis
    context = f"Original query: {original_query}"
    llm_analysis = analyze_claim_with_llm(claim_text, context, evidence)
    
    # Calculate additional metrics
    support_count = len(evidence)
    diversity_domains = list(set([e.get('url', '').split('/')[2] if e.get('url') else 'unknown' for e in evidence]))
    recency_score = 0.7  # Placeholder - would need actual date analysis
    contradiction_count = 0  # Placeholder - would need contradiction detection
    source_quality_score = min(1.0, support_count * 0.2)
    
    # Create comprehensive result
    result = {
        'claim': claim_text,
        'confidence': llm_analysis.get('confidence_score', 50),
        'explanation': llm_analysis.get('explanation_plain', f"Analysis of claim: {claim_text}"),
        'evidence': evidence,
        'support_count': support_count,
        'diversity_domains': diversity_domains,
        'recency_score': recency_score,
        'contradiction_count': contradiction_count,
        'source_quality_score': source_quality_score,
        'clairvox_result': {
            'classification': llm_analysis.get('classification', 'Unsupported'),
            'confidence_score': llm_analysis.get('confidence_score', 50),
            'explanation_plain': llm_analysis.get('explanation_plain', f"Analysis of claim: {claim_text}"),
            'top_evidence': evidence[:3],  # Top 3 evidence items
            'contradictions': [],  # Would be populated by contradiction detection
            'drivers': llm_analysis.get('key_evidence_points', []),
            'fabricated_terms': [],  # Would be populated by fabrication detection
            'suggested_corrections': llm_analysis.get('recommendations', []),
            'source_quality': llm_analysis.get('source_quality', 'Medium'),
            'limitations': llm_analysis.get('limitations', []),
            'search_queries_used': list(set([e.get('query_used', '') for e in evidence if e.get('query_used')]))
        }
    }
    
    return result

def analyze_text_comprehensive(text: str) -> List[Dict]:
    """
    Analyze entire text using basic system.
    Returns basic results for all claims.
    """
    # Split text into sentences for basic analysis
    sentences = text.split('.')
    results = []
    
    for sentence in sentences:
        if len(sentence.strip()) > 10:  # Only analyze meaningful sentences
            result = analyze_claim(sentence.strip(), text)
            results.append(result)
    
    return results