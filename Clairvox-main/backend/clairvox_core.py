"""
Clairvox Evidence-First AI Research Assistant
Core database search and fabricated term detection module
"""

import requests
import logging
import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from difflib import SequenceMatcher
import time
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from .utils import cache_get, cache_set, get_cache_key, USER_AGENT

# Download required NLTK data
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('omw-1.4')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConceptBasedQueryGenerator:
    """Generates concept-based queries with synonyms, MeSH terms, and paraphrased queries for better search coverage"""
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.mesh_terms = self._load_mesh_terms()
        self.paraphrase_patterns = self._load_paraphrase_patterns()
    
    def _load_mesh_terms(self) -> Dict[str, List[str]]:
        """Load MeSH (Medical Subject Headings) terms for biomedical concepts"""
        return {
            'exercise': ['physical activity', 'aerobic exercise', 'cardio', 'fitness', 'workout'],
            'cognitive': ['mental', 'brain', 'neural', 'psychological', 'intellectual'],
            'memory': ['recall', 'retention', 'learning', 'cognition', 'remembering'],
            'weight': ['body weight', 'obesity', 'BMI', 'mass', 'fat'],
            'fasting': ['intermittent fasting', 'caloric restriction', 'diet', 'nutrition'],
            'inflammation': ['inflammatory', 'immune response', 'cytokines', 'swelling'],
            'diabetes': ['diabetic', 'glucose', 'insulin', 'blood sugar', 'metabolic'],
            'cancer': ['tumor', 'neoplasm', 'oncology', 'malignancy', 'carcinoma'],
            'depression': ['mood', 'mental health', 'anxiety', 'psychological distress'],
            'aging': ['elderly', 'senescence', 'longevity', 'age-related']
        }
    
    def _load_paraphrase_patterns(self) -> Dict[str, List[str]]:
        """Load paraphrase patterns for common scientific concepts"""
        return {
            'causes': ['leads to', 'results in', 'induces', 'triggers', 'promotes'],
            'prevents': ['reduces', 'decreases', 'inhibits', 'blocks', 'protects against'],
            'improves': ['enhances', 'boosts', 'increases', 'strengthens', 'optimizes'],
            'effective': ['beneficial', 'helpful', 'successful', 'useful', 'valuable'],
            'study': ['research', 'investigation', 'trial', 'experiment', 'analysis'],
            'shows': ['demonstrates', 'indicates', 'suggests', 'reveals', 'finds']
        }
    
    def extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text using NLTK with enhanced processing"""
        # Tokenize and remove stop words
        words = nltk.word_tokenize(text.lower())
        stop_words = set(nltk.corpus.stopwords.words('english'))
        words = [word for word in words if word.isalpha() and word not in stop_words]
        
        # Get lemmatized words
        lemmatized_words = [self.lemmatizer.lemmatize(word) for word in words]
        
        # Filter out very short words and common words
        filtered_words = [word for word in lemmatized_words if len(word) > 3]
        
        return list(set(filtered_words))
    
    def get_synonyms(self, word: str) -> List[str]:
        """Get synonyms for a word using WordNet and MeSH terms"""
        synonyms = set()
        
        # WordNet synonyms
        for syn in wordnet.synsets(word):
            for lemma in syn.lemmas():
                synonym = lemma.name().replace('_', ' ')
                if synonym != word and len(synonym) > 2:
                    synonyms.add(synonym)
        
        # MeSH terms
        if word in self.mesh_terms:
            synonyms.update(self.mesh_terms[word])
        
        return list(synonyms)
    
    def generate_paraphrased_queries(self, claim: str) -> List[str]:
        """Generate paraphrased versions of the claim"""
        paraphrases = []
        
        for original, alternatives in self.paraphrase_patterns.items():
            if original in claim.lower():
                for alternative in alternatives:
                    paraphrased = claim.lower().replace(original, alternative)
                    paraphrases.append(paraphrased)
        
        return paraphrases
    
    def generate_concept_queries(self, claim: str) -> List[str]:
        """Generate multiple concept-based queries for a claim with enhanced coverage"""
        concepts = self.extract_key_concepts(claim)
        queries = []
        
        # Original claim query
        queries.append(f'"{claim}"')
        
        # Paraphrased queries
        paraphrases = self.generate_paraphrased_queries(claim)
        for paraphrase in paraphrases[:3]:  # Limit to 3 paraphrases
            queries.append(f'"{paraphrase}"')
        
        # Concept-based queries with enhanced synonyms
        for concept in concepts[:5]:  # Limit to top 5 concepts
            # Add concept with synonyms
            synonyms = self.get_synonyms(concept)[:5]  # Increased from 3 to 5
            if synonyms:
                synonym_quotes = [f'"{s}"' for s in synonyms]
                synonym_query = f'"{concept}" OR {" OR ".join(synonym_quotes)}'
                queries.append(synonym_query)
            else:
                queries.append(f'"{concept}"')
        
        # Multi-concept queries (e.g., "aerobic exercise → cognitive improvement")
        if len(concepts) >= 2:
            for i in range(len(concepts) - 1):
                concept1 = concepts[i]
                concept2 = concepts[i + 1]
                multi_query = f'"{concept1}" AND "{concept2}"'
                queries.append(multi_query)
        
        # Phrase-based queries
        phrases = self._extract_phrases(claim)
        for phrase in phrases:
            queries.append(f'"{phrase}"')
        
        return queries[:12]  # Increased from 8 to 12 queries total
    
    def _extract_phrases(self, text: str) -> List[str]:
        """Extract meaningful phrases from text"""
        # Simple phrase extraction - look for 2-4 word combinations
        words = nltk.word_tokenize(text.lower())
        phrases = []
        
        for i in range(len(words) - 1):
            for j in range(i + 2, min(i + 5, len(words) + 1)):
                phrase = ' '.join(words[i:j])
                if len(phrase.split()) >= 2:
                    phrases.append(phrase)
        
        return phrases[:5]  # Limit to 5 phrases

class MetadataValidator:
    """Validates and fixes metadata extraction issues"""
    
    @staticmethod
    def extract_doi_fallback(text: str) -> Optional[str]:
        """Extract DOI using regex fallback when API fails"""
        # DOI regex pattern: 10. followed by publisher identifier and article identifier
        doi_pattern = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
        matches = re.findall(doi_pattern, text, re.IGNORECASE)
        return matches[0] if matches else None
    
    @staticmethod
    def validate_metadata(result: Dict) -> Dict:
        """Validate and fix metadata fields"""
        # Fix empty DOI
        if not result.get('doi') and result.get('url'):
            doi = MetadataValidator.extract_doi_fallback(result['url'])
            if doi:
                result['doi'] = doi
                result['url'] = f"https://doi.org/{doi}"
        
        # Fix empty title
        if not result.get('title'):
            result['title'] = "No title available"
        
        # Fix empty authors
        if not result.get('authors'):
            result['authors'] = "Unknown authors"
        
        # Fix empty venue
        if not result.get('venue'):
            result['venue'] = "Unknown venue"
        
        # Fix empty date
        if not result.get('date'):
            result['date'] = "Unknown date"
        
        # Ensure excerpt is not too long
        if result.get('excerpt') and len(result['excerpt']) > 200:
            result['excerpt'] = result['excerpt'][:200] + "..."
        
        return result

class SemanticReranker:
    """Semantic reranker for evidence relevance with improved threshold for better recall"""
    
    def __init__(self, relevance_threshold: float = 0.25):
        self.relevance_threshold = relevance_threshold
    
    def calculate_similarity(self, claim: str, evidence_text: str) -> float:
        """Calculate semantic similarity between claim and evidence"""
        # Simple word overlap similarity (can be enhanced with embeddings)
        claim_words = set(claim.lower().split())
        evidence_words = set(evidence_text.lower().split())
        
        if not claim_words or not evidence_words:
            return 0.0
        
        intersection = claim_words.intersection(evidence_words)
        union = claim_words.union(evidence_words)
        
        return len(intersection) / len(union) if union else 0.0
    
    def rerank_evidence(self, claim: str, evidence_list: List[Dict]) -> List[Dict]:
        """Rerank evidence by relevance to claim with improved partial matching"""
        if not evidence_list:
            return []
        
        # Calculate relevance scores with enhanced partial matching
        scored_evidence = []
        for evidence in evidence_list:
            # Combine title, excerpt, and venue for similarity calculation
            evidence_text = f"{evidence.get('title', '')} {evidence.get('excerpt', '')} {evidence.get('venue', '')}"
            similarity = self.calculate_similarity(claim, evidence_text)
            
            # Enhanced partial matching - check for core mechanism support
            partial_support = self._check_partial_support(claim, evidence_text)
            
            # Boost score for partial support
            if partial_support:
                similarity = min(1.0, similarity + 0.2)
            
            scored_evidence.append({
                **evidence,
                'relevance_score': similarity,
                'is_relevant': similarity >= self.relevance_threshold or partial_support,
                'partial_support': partial_support
            })
        
        # Sort by relevance score (descending)
        scored_evidence.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Filter out irrelevant evidence but keep partial support
        relevant_evidence = [e for e in scored_evidence if e['is_relevant']]
        
        # Ensure we get top 3-5 sources as requested
        top_evidence = relevant_evidence[:5]
        
        logger.info(f"Reranked {len(evidence_list)} evidence items, {len(relevant_evidence)} above threshold {self.relevance_threshold}")
        
        return top_evidence
    
    def _check_partial_support(self, claim: str, evidence_text: str) -> bool:
        """Check if evidence provides partial support for core mechanisms"""
        claim_lower = claim.lower()
        evidence_lower = evidence_text.lower()
        
        # Extract key concepts from claim
        claim_concepts = set(claim_lower.split())
        
        # Check for mechanism-related keywords
        mechanism_keywords = [
            'mechanism', 'pathway', 'process', 'function', 'effect', 'response',
            'regulation', 'activation', 'inhibition', 'modulation', 'interaction'
        ]
        
        # Check for partial concept overlap
        evidence_concepts = set(evidence_lower.split())
        concept_overlap = len(claim_concepts.intersection(evidence_concepts))
        
        # Check for mechanism keywords
        mechanism_found = any(keyword in evidence_lower for keyword in mechanism_keywords)
        
        # Partial support if there's concept overlap or mechanism keywords
        return concept_overlap >= 2 or mechanism_found

class DatabaseSearcher:
    """Handles searches across multiple academic databases with robust metadata extraction"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.metadata_validator = MetadataValidator()
        self.reranker = SemanticReranker()
        self.query_generator = ConceptBasedQueryGenerator()
        
    def search_crossref(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search CrossRef for DOIs and metadata with robust fallback"""
        cache_key = get_cache_key("crossref_search_v2", f"{query}_{max_results}")
        cached = cache_get(cache_key)
        if cached:
            return cached
            
        try:
            url = "https://api.crossref.org/works"
            params = {
                'query': query,
                'rows': min(max_results, 20),
                'mailto': 'clairvox@example.com'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('message', {}).get('items', []):
                # Robust title extraction
                title = ''
                if item.get('title'):
                    if isinstance(item['title'], list) and item['title']:
                        title = item['title'][0]
                    elif isinstance(item['title'], str):
                        title = item['title']
                
                # Robust author extraction
                authors = []
                if item.get('author'):
                    for author in item['author'][:3]:
                        given = author.get('given', '')
                        family = author.get('family', '')
                        if given or family:
                            authors.append(f"{given} {family}".strip())
                
                # Robust venue extraction
                venue = ''
                if item.get('container-title'):
                    if isinstance(item['container-title'], list) and item['container-title']:
                        venue = item['container-title'][0]
                    elif isinstance(item['container-title'], str):
                        venue = item['container-title']
                
                # Robust date extraction
                date = ''
                if item.get('published-print', {}).get('date-parts'):
                    date_parts = item['published-print']['date-parts'][0]
                    if date_parts and len(date_parts) >= 1:
                        date = str(date_parts[0])
                
                # Robust DOI extraction
                doi = item.get('DOI', '')
                if not doi:
                    # Fallback DOI extraction from URL or other fields
                    doi = self.metadata_validator.extract_doi_fallback(str(item))
                
                result = {
                    'type': 'peer-reviewed',
                    'title': title,
                    'authors': ', '.join(authors) if authors else 'Unknown authors',
                    'venue': venue,
                    'date': date,
                    'doi': doi,
                    'url': f"https://doi.org/{doi}" if doi else '',
                    'excerpt': item.get('abstract', '')[:200] if item.get('abstract') else '',
                    'source': 'CrossRef',
                    'query_used': query
                }
                
                # Validate and fix metadata
                result = self.metadata_validator.validate_metadata(result)
                results.append(result)
                
            cache_set(cache_key, results)
            return results
            
        except Exception as e:
            logger.warning(f"CrossRef search failed: {e}")
            return []
    
    def search_pubmed(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search PubMed/Europe PMC for biomedical literature with robust metadata"""
        cache_key = get_cache_key("pubmed_search_v2", f"{query}_{max_results}")
        cached = cache_get(cache_key)
        if cached:
            return cached
            
        try:
            # Use Europe PMC API (more accessible than PubMed)
            url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            params = {
                'query': query,
                'format': 'json',
                'pageSize': min(max_results, 25),
                'resultType': 'core'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('resultList', {}).get('result', []):
                # Robust author extraction
                authors = []
                if item.get('authorList', {}).get('author'):
                    for author in item['authorList']['author'][:3]:
                        if isinstance(author, str):
                            authors.append(author)
                        elif isinstance(author, dict):
                            name = author.get('fullName', '') or f"{author.get('firstName', '')} {author.get('lastName', '')}".strip()
                            if name:
                                authors.append(name)
                
                result = {
                    'type': 'peer-reviewed',
                    'title': item.get('title', ''),
                    'authors': ', '.join(authors) if authors else 'Unknown authors',
                    'venue': item.get('journalTitle', ''),
                    'date': str(item.get('pubYear', '')) if item.get('pubYear') else '',
                    'doi': item.get('doi', ''),
                    'url': f"https://europepmc.org/article/MED/{item.get('pmid', '')}" if item.get('pmid') else '',
                    'excerpt': item.get('abstractText', '')[:200] if item.get('abstractText') else '',
                    'source': 'PubMed/Europe PMC',
                    'query_used': query
                }
                
                # Validate and fix metadata
                result = self.metadata_validator.validate_metadata(result)
                results.append(result)
                
            cache_set(cache_key, results)
            return results
            
        except Exception as e:
            logger.warning(f"PubMed search failed: {e}")
            return []
    
    def search_arxiv(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search arXiv for preprints with robust metadata"""
        cache_key = get_cache_key("arxiv_search_v2", f"{query}_{max_results}")
        cached = cache_get(cache_key)
        if cached:
            return cached
            
        try:
            url = "http://export.arxiv.org/api/query"
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': min(max_results, 20),
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse XML response (simplified)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            results = []
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                title = title_elem.text if title_elem is not None else ''
                
                authors = []
                for author in entry.findall('{http://www.w3.org/2005/Atom}author')[:3]:
                    name_elem = author.find('{http://www.w3.org/2005/Atom}name')
                    if name_elem is not None:
                        authors.append(name_elem.text)
                
                published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
                date = published_elem.text[:10] if published_elem is not None else ''
                
                id_elem = entry.find('{http://www.w3.org/2005/Atom}id')
                url = id_elem.text if id_elem is not None else ''
                
                summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                excerpt = summary_elem.text[:200] if summary_elem is not None else ''
                
                result = {
                    'type': 'preprint',
                    'title': title,
                    'authors': ', '.join(authors) if authors else 'Unknown authors',
                    'venue': 'arXiv',
                    'date': date,
                    'doi': '',
                    'url': url,
                    'excerpt': excerpt,
                    'source': 'arXiv',
                    'query_used': query
                }
                
                # Validate and fix metadata
                result = self.metadata_validator.validate_metadata(result)
                results.append(result)
                
            cache_set(cache_key, results)
            return results
            
        except Exception as e:
            logger.warning(f"arXiv search failed: {e}")
            return []
    
    def search_evidence_with_reranking(self, claim: str, max_results_per_db: int = 5) -> List[Dict]:
        """Search for evidence across all databases with semantic reranking"""
        all_evidence = []
        
        # Search all databases
        crossref_results = self.search_crossref(claim, max_results_per_db)
        pubmed_results = self.search_pubmed(claim, max_results_per_db)
        arxiv_results = self.search_arxiv(claim, max_results_per_db)
        
        all_evidence.extend(crossref_results)
        all_evidence.extend(pubmed_results)
        all_evidence.extend(arxiv_results)
        
        # Apply semantic reranking
        reranked_evidence = self.reranker.rerank_evidence(claim, all_evidence)
        
        return reranked_evidence
    
    def search_evidence_comprehensive(self, claim: str, max_results_per_db: int = 5) -> List[Dict]:
        """Search for evidence using concept-based queries with synonyms"""
        all_evidence = []
        search_queries = []
        
        # Generate concept-based queries
        queries = self.query_generator.generate_concept_queries(claim)
        
        # Search each database with each query
        for query in queries:
            search_queries.append(query)
            
            # Search CrossRef
            crossref_results = self.search_crossref(query, max_results_per_db)
            all_evidence.extend(crossref_results)
            
            # Search PubMed
            pubmed_results = self.search_pubmed(query, max_results_per_db)
            all_evidence.extend(pubmed_results)
            
            # Search arXiv
            arxiv_results = self.search_arxiv(query, max_results_per_db)
            all_evidence.extend(arxiv_results)
        
        # Remove duplicates based on DOI and title
        unique_evidence = self._deduplicate_evidence_comprehensive(all_evidence)
        
        # Apply semantic reranking
        reranked_evidence = self.reranker.rerank_evidence(claim, unique_evidence)
        
        # Add search query information to each result
        for evidence in reranked_evidence:
            evidence['search_queries_used'] = search_queries
        
        return reranked_evidence
    
    def _deduplicate_evidence_comprehensive(self, evidence_list: List[Dict]) -> List[Dict]:
        """Remove duplicates based on DOI, title, and URL"""
        unique_evidence = []
        seen_dois = set()
        seen_titles = set()
        seen_urls = set()
        
        for evidence in evidence_list:
            doi = evidence.get('doi', '').lower()
            title = evidence.get('title', '').lower()
            url = evidence.get('url', '').lower()
            
            # Check for duplicates
            is_duplicate = False
            
            if doi and doi in seen_dois:
                is_duplicate = True
            elif title and title in seen_titles:
                is_duplicate = True
            elif url and url in seen_urls:
                is_duplicate = True
            
            if not is_duplicate:
                if doi:
                    seen_dois.add(doi)
                if title:
                    seen_titles.add(title)
                if url:
                    seen_urls.add(url)
                unique_evidence.append(evidence)
        
        return unique_evidence

class FabricatedTermDetector:
    """Detects fabricated terms and concepts"""
    
    def __init__(self):
        self.searcher = DatabaseSearcher()
        
    def normalize_term(self, term: str) -> str:
        """Normalize a term for searching"""
        return re.sub(r'[^\w\s]', '', term.lower().strip())
    
    def fuzzy_search(self, term: str, max_distance: int = 2) -> List[str]:
        """Generate fuzzy search variations"""
        if len(term) <= 4:
            max_distance = min(max_distance, 2)
        else:
            max_distance = min(max_distance, 4)
            
        variations = [term]
        
        # Simple character substitutions
        for i in range(len(term)):
            for char in 'aeiou':
                if char not in term[i:i+1]:
                    variations.append(term[:i] + char + term[i+1:])
        
        return variations[:10]  # Limit variations
    
    def search_term_existence(self, term: str) -> Dict:
        """Search for term existence across databases"""
        normalized_term = self.normalize_term(term)
        
        # Exact phrase search
        exact_results = {
            'crossref': len(self.searcher.search_crossref(f'"{normalized_term}"', 5)),
            'pubmed': len(self.searcher.search_pubmed(f'"{normalized_term}"', 5)),
            'arxiv': len(self.searcher.search_arxiv(f'"{normalized_term}"', 5))
        }
        
        # Fuzzy search if exact search returns 0
        fuzzy_results = {}
        if sum(exact_results.values()) == 0:
            fuzzy_variations = self.fuzzy_search(normalized_term)
            for variation in fuzzy_variations[:3]:  # Limit to 3 variations
                fuzzy_results[variation] = {
                    'crossref': len(self.searcher.search_crossref(f'"{variation}"', 3)),
                    'pubmed': len(self.searcher.search_pubmed(f'"{variation}"', 3)),
                    'arxiv': len(self.searcher.search_arxiv(f'"{variation}"', 3))
                }
        
        return {
            'term': term,
            'normalized_term': normalized_term,
            'exact_search_results': exact_results,
            'fuzzy_search_results': fuzzy_results,
            'total_exact_hits': sum(exact_results.values()),
            'total_fuzzy_hits': sum(sum(v.values()) for v in fuzzy_results.values())
        }
    
    def detect_fabricated_terms(self, text: str) -> List[Dict]:
        """Detect potentially fabricated terms in text"""
        # Extract potential technical terms (capitalized words, hyphenated terms)
        technical_terms = re.findall(r'\b[A-Z][a-zA-Z]*(?:-[A-Z][a-zA-Z]*)*\b', text)
        
        # Filter out common words
        common_words = {'The', 'This', 'That', 'These', 'Those', 'A', 'An', 'And', 'Or', 'But', 'In', 'On', 'At', 'To', 'For', 'Of', 'With', 'By'}
        technical_terms = [term for term in technical_terms if term not in common_words]
        
        fabricated_terms = []
        for term in technical_terms:
            search_result = self.search_term_existence(term)
            
            # If no exact hits and no fuzzy hits, likely fabricated
            if (search_result['total_exact_hits'] == 0 and 
                search_result['total_fuzzy_hits'] == 0):
                fabricated_terms.append({
                    'term': term,
                    'search_evidence': search_result,
                    'confidence': 'high' if len(term) > 5 else 'medium'
                })
        
        return fabricated_terms

class DomainRuleEngine:
    """Applies domain-specific plausibility rules"""
    
    def __init__(self):
        self.rules = {
            'physics': self._check_physics_rules,
            'neuroscience': self._check_neuroscience_rules,
            'statistics': self._check_statistics_rules
        }
    
    def _check_physics_rules(self, claim: str) -> Dict:
        """Check physics-related plausibility rules - only flag physically impossible claims"""
        violations = []
        
        # Only flag claims that violate fundamental physical laws
        impossible_patterns = [
            r'perpetual.*motion.*machine',
            r'energy.*from.*nothing',
            r'faster.*than.*light.*travel',
            r'instantaneous.*information.*transfer',
            r'violates.*conservation.*of.*energy',
            r'breaks.*thermodynamics'
        ]
        
        for pattern in impossible_patterns:
            if re.search(pattern, claim.lower()):
                violations.append({
                    'rule': 'fundamental_physics_violation',
                    'description': 'Claim violates fundamental physical laws',
                    'severity': 'critical'
                })
        
        return {
            'domain': 'physics',
            'violations': violations,
            'is_plausible': len(violations) == 0
        }
    
    def _check_neuroscience_rules(self, claim: str) -> Dict:
        """Check neuroscience-related plausibility rules - only flag impossible claims"""
        violations = []
        
        # Only flag claims that are scientifically impossible
        impossible_patterns = [
            r'instantaneous.*memory.*transfer',
            r'telepathic.*communication',
            r'reading.*minds.*directly',
            r'consciousness.*upload.*without.*technology'
        ]
        
        for pattern in impossible_patterns:
            if re.search(pattern, claim.lower()):
                violations.append({
                    'rule': 'neuroscience_impossibility',
                    'description': 'Claim violates known neuroscience principles',
                    'severity': 'critical'
                })
        
        return {
            'domain': 'neuroscience',
            'violations': violations,
            'is_plausible': len(violations) == 0
        }
    
    def _check_statistics_rules(self, claim: str) -> Dict:
        """Check statistics-related plausibility rules - only flag impossible claims"""
        violations = []
        
        # Only flag claims that are statistically impossible
        impossible_patterns = [
            r'correlation.*greater.*than.*1',
            r'probability.*greater.*than.*1',
            r'negative.*variance',
            r'standard.*deviation.*negative'
        ]
        
        for pattern in impossible_patterns:
            if re.search(pattern, claim.lower()):
                violations.append({
                    'rule': 'statistical_impossibility',
                    'description': 'Claim violates fundamental statistical principles',
                    'severity': 'critical'
                })
        
        return {
            'domain': 'statistics',
            'violations': violations,
            'is_plausible': len(violations) == 0
        }
    
    def check_claim_plausibility(self, claim: str) -> Dict:
        """Check claim against all domain rules"""
        results = {}
        
        for domain, rule_func in self.rules.items():
            results[domain] = rule_func(claim)
        
        # Overall plausibility
        all_plausible = all(result['is_plausible'] for result in results.values())
        critical_violations = any(
            any(v['severity'] == 'critical' for v in result['violations'])
            for result in results.values()
        )
        
        return {
            'overall_plausible': all_plausible and not critical_violations,
            'critical_violations': critical_violations,
            'domain_results': results
        }

# Global instances
db_searcher = DatabaseSearcher()
fabricated_detector = FabricatedTermDetector()
domain_engine = DomainRuleEngine()
query_generator = ConceptBasedQueryGenerator()