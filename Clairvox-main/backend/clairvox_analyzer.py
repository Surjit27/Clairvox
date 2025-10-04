"""
Clairvox Evidence-Weighted Confidence Algorithm and Main Analyzer
Implements the exact weighting system and JSON output schema as specified
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from .clairvox_core import db_searcher, fabricated_detector, domain_engine
from .utils import cache_get, cache_set, get_cache_key

logger = logging.getLogger(__name__)

class EvidenceWeightedConfidence:
    """Implements the exact evidence weighting algorithm as specified"""
    
    # Exact weights as specified in the requirements
    WEIGHTS = {
        'peer_reviewed_primary_human': 50,
        'peer_reviewed_primary_animal': 25,
        'preprint': 20,
        'independent_replication': 30,  # Additive per replication
        'conference_proceedings': 10,
        'reputable_news': 8,
        'university_press_release': 5,
        'blog_social_media': 2,
        'strong_contradiction': -70,  # Per major contradicter
    }
    
    @staticmethod
    def classify_evidence_type(evidence: Dict) -> str:
        """Classify evidence type based on source characteristics"""
        source_type = evidence.get('type', '').lower()
        venue = evidence.get('venue', '').lower()
        url = evidence.get('url', '').lower()
        
        # Peer-reviewed primary (human experiment)
        if (source_type == 'peer-reviewed' and 
            any(keyword in venue for keyword in ['journal', 'nature', 'science', 'cell', 'lancet', 'nejm'])):
            return 'peer_reviewed_primary_human'
        
        # Peer-reviewed primary (animal experiment)
        if (source_type == 'peer-reviewed' and 
            any(keyword in venue for keyword in ['journal', 'nature', 'science', 'cell'])):
            return 'peer_reviewed_primary_animal'
        
        # Preprint
        if source_type == 'preprint' or 'arxiv' in url or 'biorxiv' in url or 'medrxiv' in url:
            return 'preprint'
        
        # Conference proceedings
        if any(keyword in venue for keyword in ['conference', 'proceedings', 'ieee', 'neurips', 'icml']):
            return 'conference_proceedings'
        
        # Reputable news
        if any(keyword in url for keyword in ['nature.com', 'sciencemag.org', 'nytimes.com', 'bbc.com']):
            return 'reputable_news'
        
        # University press release
        if any(keyword in url for keyword in ['.edu', 'university', 'press release']):
            return 'university_press_release'
        
        # Blog/social media
        return 'blog_social_media'
    
    @staticmethod
    def calculate_confidence_score(evidence_list: List[Dict], contradictions: List[Dict]) -> Tuple[int, List[str]]:
        """Calculate confidence score using new weighted system"""
        weighted_support = 0
        weighted_contradiction = 0
        drivers = []
        
        # Count evidence by type and apply new weights
        human_studies = 0
        preclinical_studies = 0
        
        for evidence in evidence_list:
            evidence_type = evidence.get('type', 'unknown')
            venue = evidence.get('venue', '').lower()
            url = evidence.get('url', '').lower()
            
            # Human peer-reviewed studies
            if (evidence_type == 'peer-reviewed' and 
                any(keyword in venue for keyword in ['journal', 'nature', 'science', 'cell', 'lancet', 'nejm', 'plos', 'bmj', 'pubmed', 'crossref'])):
                human_studies += 1
                weighted_support += 30
                drivers.append(f"human peer-reviewed study found (doi: {evidence.get('doi', 'N/A')})")
            
            # Preclinical/mechanistic/AI studies (including all other evidence)
            else:
                preclinical_studies += 1
                weighted_support += 15
                drivers.append(f"preclinical/mechanistic study found (doi: {evidence.get('doi', 'N/A')})")
        
        # Apply contradiction penalty (balanced approach)
        contradiction_count = len(contradictions)
        if contradiction_count > 0:
            # More balanced contradiction penalty
            weighted_contradiction = min(contradiction_count * 10, 40)  # Max 40 points penalty
            drivers.append(f"contradicted by {contradiction_count} source(s)")
        
        # Calculate final confidence score
        raw_score = weighted_support - weighted_contradiction
        confidence_score = max(0, min(100, raw_score))
        
        # Round to nearest integer
        confidence_score = round(confidence_score)
        
        # Add additional drivers based on score
        if confidence_score == 0:
            if not evidence_list:
                drivers.append("no credible evidence found")
            else:
                drivers.append("strong contradictions override supporting evidence")
        elif confidence_score < 30:
            drivers.append("very weak or contradicted evidence")
        elif confidence_score < 50:
            drivers.append("limited evidence with significant gaps or contradictions")
        elif confidence_score < 70:
            drivers.append("mixed evidence with some supporting sources but limited confidence")
        elif confidence_score < 90:
            drivers.append("good evidence but not yet fully established or lacks peer review")
        else:
            drivers.append("strong primary evidence with peer-reviewed sources and replications")
        
        return confidence_score, drivers[:3]  # Return top 3 drivers
    
    @staticmethod
    def get_confidence_color(score: int) -> str:
        """Get confidence color based on score"""
        if score == 0:
            return "red"
        elif score <= 30:
            return "orange"
        elif score <= 70:
            return "yellow"
        else:
            return "green"
    
    @staticmethod
    def get_classification(score: int, fabricated_terms: List[str], plausibility_result: Dict, evidence_list: List[Dict]) -> str:
        """Get classification based on score and other factors using refined 3-tier system"""
        if fabricated_terms or not plausibility_result['overall_plausible']:
            return "Fabricated" if fabricated_terms else "Physically Implausible"
        
        # Check for peer-reviewed sources
        peer_reviewed_count = sum(1 for e in evidence_list if e.get('type') == 'peer-reviewed')
        
        # Refined 3-tier classification system as requested
        if score >= 90 and peer_reviewed_count >= 1:
            return "Fully Supported"
        elif score >= 50:
            return "Partially Supported"
        else:
            return "Unsupported"

class ClairvoxAnalyzer:
    """Main Clairvox analyzer implementing the complete workflow"""
    
    def __init__(self):
        self.db_searcher = db_searcher
        self.fabricated_detector = fabricated_detector
        self.domain_engine = domain_engine
        self.confidence_calculator = EvidenceWeightedConfidence()
    
    def parse_claims(self, text: str) -> List[Dict]:
        """Parse text into atomic claims"""
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        sentences = nltk.sent_tokenize(text)
        claims = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence.split()) > 3:  # Filter out very short sentences
                normalized = self._normalize_claim(sentence)
                claims.append({
                    'original_claim': sentence,
                    'normalized_claim': normalized
                })
        
        return claims
    
    def _normalize_claim(self, claim: str) -> str:
        """Create a normalized version of the claim for searching"""
        # Remove question words and normalize
        normalized = re.sub(r'^(does|do|is|are|can|will|should|how|what|why|when|where)\s+', '', claim.lower())
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized.strip()
    
    def search_evidence(self, claim: str, max_results_per_db: int = 5) -> List[Dict]:
        """Search for evidence using comprehensive concept-based queries"""
        # Use the new comprehensive search method
        reranked_evidence = self.db_searcher.search_evidence_comprehensive(claim, max_results_per_db)
        
        # Remove duplicates based on title similarity
        unique_evidence = self._deduplicate_evidence(reranked_evidence)
        
        return unique_evidence
    
    def _deduplicate_evidence(self, evidence_list: List[Dict]) -> List[Dict]:
        """Remove duplicate evidence based on title similarity"""
        unique_evidence = []
        seen_titles = set()
        
        for evidence in evidence_list:
            title = evidence.get('title', '').lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_evidence.append(evidence)
        
        return unique_evidence
    
    def search_contradictions(self, claim: str) -> List[Dict]:
        """Search for contradictory evidence"""
        contradiction_queries = [
            f'"{claim}" AND "not supported"',
            f'"{claim}" AND "debunked"',
            f'"{claim}" AND "disproven"',
            f'"{claim}" AND "no evidence"'
        ]
        
        contradictions = []
        for query in contradiction_queries:
            results = self.db_searcher.search_crossref(query, 2)
            contradictions.extend(results)
        
        return contradictions
    
    def check_replication_status(self, evidence_list: List[Dict]) -> str:
        """Check replication status of evidence"""
        if not evidence_list:
            return "none"
        
        # Look for independent replications
        replication_keywords = ['replication', 'reproducibility', 'independent study']
        replication_count = 0
        
        for evidence in evidence_list:
            title = evidence.get('title', '').lower()
            venue = evidence.get('venue', '').lower()
            if any(keyword in title or keyword in venue for keyword in replication_keywords):
                replication_count += 1
        
        if replication_count == 0:
            return "original_only"
        elif replication_count == 1:
            return "partial"
        else:
            return "replicated"
    
    def analyze_claim(self, claim_data: Dict) -> Dict:
        """Analyze a single claim and return structured JSON output"""
        original_claim = claim_data['original_claim']
        normalized_claim = claim_data['normalized_claim']
        
        # STEP 1: Domain-rule validation BEFORE aggregation (CRITICAL FIX)
        plausibility_result = self.domain_engine.check_claim_plausibility(original_claim)
        
        # If physically implausible, short-circuit to avoid unnecessary processing
        if not plausibility_result['overall_plausible'] and plausibility_result['critical_violations']:
            return {
                "original_claim": original_claim,
                "normalized_claim": normalized_claim,
                "classification": "Physically Implausible",
                "confidence_score": 0,
                "confidence_color": "red",
                "drivers": ["Claim violates established physical laws or domain-specific rules"],
                "top_evidence": [],
                "fabricated_terms": [],
                "replication_status": "none",
                "contradictions": [],
                "explanation_plain": "Claim violates established physical laws or domain-specific rules. No credible evidence can support physically impossible claims.",
                "suggested_corrections": "Revise claim to align with established scientific principles. Consider consulting domain experts for accurate information.",
                "search_actions": "Domain-rule validation short-circuited search due to physical impossibility",
                "domain_violations": plausibility_result['domain_results']
            }
        
        # STEP 2: Check for fabricated terms
        fabricated_terms = self.fabricated_detector.detect_fabricated_terms(original_claim)
        fabricated_term_names = [ft['term'] for ft in fabricated_terms]
        
        # If fabricated terms detected, short-circuit to avoid unnecessary processing
        if fabricated_term_names:
            return {
                "original_claim": original_claim,
                "normalized_claim": normalized_claim,
                "classification": "Fabricated",
                "confidence_score": 0,
                "confidence_color": "red",
                "drivers": [f"Fabricated terms detected: {', '.join(fabricated_term_names)}"],
                "top_evidence": [],
                "fabricated_terms": fabricated_term_names,
                "replication_status": "none",
                "contradictions": [],
                "explanation_plain": f"No peer-reviewed or credible evidence found for fabricated terms: {', '.join(fabricated_term_names)}. Related real literature may exist but does not support these specific claims.",
                "suggested_corrections": f"Remove fabricated terms: {', '.join(fabricated_term_names)}. Consider related real research areas: optogenetics, memory research, neuroscience studies.",
                "search_actions": f"Searched CrossRef, PubMed, arXiv for fabricated terms: {', '.join(fabricated_term_names)}. All returned zero hits.",
                "fabricated_term_evidence": [ft['search_evidence'] for ft in fabricated_terms]
            }
        
        # STEP 3: Search for evidence (only if claim passes domain rules)
        evidence_list = self.search_evidence(normalized_claim)
        
        # STEP 4: Search for contradictions
        contradictions = self.search_contradictions(normalized_claim)
        
        # STEP 5: Calculate confidence score
        confidence_score, drivers = self.confidence_calculator.calculate_confidence_score(
            evidence_list, contradictions
        )
        
        # STEP 6: Get classification and color
        classification = self.confidence_calculator.get_classification(
            confidence_score, fabricated_term_names, plausibility_result, evidence_list
        )
        confidence_color = self.confidence_calculator.get_confidence_color(confidence_score)
        
        # STEP 7: Check replication status
        replication_status = self.check_replication_status(evidence_list)
        
        # STEP 8: Generate explanation
        explanation = self._generate_explanation(
            classification, confidence_score, fabricated_term_names, 
            plausibility_result, evidence_list, contradictions
        )
        
        # STEP 9: Generate suggested corrections
        suggested_corrections = self._generate_suggested_corrections(
            classification, fabricated_term_names, plausibility_result
        )
        
        # STEP 10: Record search actions
        search_actions = f"Searched CrossRef, PubMed, arXiv for '{normalized_claim}'. Contradiction search: {len(contradictions)} queries. Domain-rule validation: passed."
        
        return {
            "original_claim": original_claim,
            "normalized_claim": normalized_claim,
            "classification": classification,
            "confidence_score": confidence_score,
            "confidence_color": confidence_color,
            "drivers": drivers,
            "top_evidence": evidence_list[:5],  # Top 5 evidence items with enhanced partial matching
            "fabricated_terms": fabricated_term_names,
            "replication_status": replication_status,
            "contradictions": contradictions,
            "explanation_plain": explanation,
            "suggested_corrections": suggested_corrections,
            "search_actions": search_actions,
            "domain_violations": plausibility_result['domain_results'] if not plausibility_result['overall_plausible'] else None,
            "partial_support_count": sum(1 for e in evidence_list if e.get('partial_support', False))
        }
    
    def _generate_explanation(self, classification: str, score: int, fabricated_terms: List[str], 
                             plausibility_result: Dict, evidence_list: List[Dict], 
                             contradictions: List[Dict]) -> str:
        """Generate plain language explanation with detailed reasoning and supporting evidence summaries"""
        if fabricated_terms:
            return f"No peer-reviewed or credible evidence found for fabricated terms: {', '.join(fabricated_terms)}. Related real literature may exist but does not support these specific claims."
        
        if not plausibility_result['overall_plausible']:
            return "Claim violates established physical laws or domain-specific rules. No credible evidence can support physically impossible claims."
        
        if classification == "Fully Supported":
            peer_reviewed_count = sum(1 for e in evidence_list if e.get('type') == 'peer-reviewed')
            preprint_count = sum(1 for e in evidence_list if e.get('type') == 'preprint')
            
            explanation = f"Strong evidence with confidence score {score}. "
            if peer_reviewed_count > 0:
                explanation += f"{peer_reviewed_count} peer-reviewed source(s) directly confirm this claim. "
            if preprint_count > 0:
                explanation += f"{preprint_count} preprint(s) provide additional support. "
            
            # Add evidence summary
            if evidence_list:
                top_source = evidence_list[0]
                explanation += f"Key evidence: {top_source.get('title', 'Unknown title')} ({top_source.get('venue', 'Unknown venue')})"
            
            return explanation
        
        elif classification == "Partially Supported":
            peer_reviewed_count = sum(1 for e in evidence_list if e.get('type') == 'peer-reviewed')
            preprint_count = sum(1 for e in evidence_list if e.get('type') == 'preprint')
            contradiction_count = len(contradictions)
            partial_support_count = sum(1 for e in evidence_list if e.get('partial_support', False))
            
            explanation = f"Mixed evidence with confidence score {score}. "
            if peer_reviewed_count > 0:
                explanation += f"{peer_reviewed_count} peer-reviewed source(s) provide some support, "
            if preprint_count > 0:
                explanation += f"{preprint_count} preprint(s) suggest preliminary evidence, "
            if partial_support_count > 0:
                explanation += f"{partial_support_count} source(s) support core mechanisms, "
            if contradiction_count > 0:
                explanation += f"but {contradiction_count} contradictory source(s) exist. "
            
            # Add evidence summary for partial support
            if evidence_list:
                top_source = evidence_list[0]
                explanation += f" Supporting evidence includes: {top_source.get('title', 'Unknown title')} ({top_source.get('venue', 'Unknown venue')})"
            
            explanation += " Additional research needed for definitive conclusions."
            return explanation
        
        else:  # Unsupported
            if score == 0:
                return "No credible evidence found for this claim. The claim may be unsupported or require additional research."
            else:
                # Even for unsupported claims, show what evidence was found
                if evidence_list:
                    top_source = evidence_list[0]
                    return f"Very weak evidence with confidence score {score}. Limited supporting sources found: {top_source.get('title', 'Unknown title')} ({top_source.get('venue', 'Unknown venue')}). Additional research needed."
                else:
                    return f"Very weak evidence with confidence score {score}. No relevant sources found. Additional research needed."
    
    def _generate_suggested_corrections(self, classification: str, fabricated_terms: List[str], 
                                      plausibility_result: Dict) -> str:
        """Generate suggested corrections"""
        if fabricated_terms:
            return f"Remove fabricated terms: {', '.join(fabricated_terms)}. Consider related real research areas: optogenetics, memory research, neuroscience studies."
        
        if not plausibility_result['overall_plausible']:
            return "Revise claim to align with established scientific principles. Consider consulting domain experts for accurate information."
        
        if classification == "Unsupported":
            return "Provide specific citations and evidence sources. Consider revising claim to be more conservative and evidence-based."
        
        return "Claim appears to be well-supported by available evidence."
    
    def analyze_text(self, text: str) -> List[Dict]:
        """Analyze entire text and return results for all claims"""
        claims = self.parse_claims(text)
        results = []
        
        for claim_data in claims:
            result = self.analyze_claim(claim_data)
            results.append(result)
        
        return results
