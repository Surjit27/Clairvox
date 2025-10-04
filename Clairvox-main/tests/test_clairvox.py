"""
Clairvox Unit Tests
Tests for fabricated detection, schema validation, and core functionality
"""

import unittest
import json
from unittest.mock import Mock, patch
from backend.clairvox_core import FabricatedTermDetector, DomainRuleEngine, DatabaseSearcher
from backend.clairvox_analyzer import ClairvoxAnalyzer, EvidenceWeightedConfidence
from backend.verifier import analyze_claim, analyze_text_comprehensive

class TestFabricatedTermDetector(unittest.TestCase):
    """Test fabricated term detection functionality"""
    
    def setUp(self):
        self.detector = FabricatedTermDetector()
    
    def test_normalize_term(self):
        """Test term normalization"""
        self.assertEqual(self.detector.normalize_term("Neural Photon Resonance"), "neural photon resonance")
        self.assertEqual(self.detector.normalize_term("Gravito-Electroencephalography!"), "gravito electroencephalography")
    
    def test_fuzzy_search(self):
        """Test fuzzy search variations"""
        variations = self.detector.fuzzy_search("neural")
        self.assertIn("neural", variations)
        self.assertTrue(len(variations) <= 10)
    
    @patch('backend.clairvox_core.db_searcher')
    def test_search_term_existence(self, mock_searcher):
        """Test term existence search"""
        # Mock search results
        mock_searcher.search_crossref.return_value = []
        mock_searcher.search_pubmed.return_value = []
        mock_searcher.search_arxiv.return_value = []
        
        result = self.detector.search_term_existence("fabricated_term")
        
        self.assertEqual(result['term'], "fabricated_term")
        self.assertEqual(result['total_exact_hits'], 0)
        self.assertEqual(result['total_fuzzy_hits'], 0)
    
    def test_detect_fabricated_terms(self):
        """Test fabricated term detection in text"""
        text = "The Neural Photon Resonance Chamber uses Gravito-Electroencephalography."
        
        with patch.object(self.detector, 'search_term_existence') as mock_search:
            mock_search.return_value = {
                'term': 'test',
                'total_exact_hits': 0,
                'total_fuzzy_hits': 0
            }
            
            fabricated_terms = self.detector.detect_fabricated_terms(text)
            
            # Should detect capitalized technical terms
            self.assertTrue(len(fabricated_terms) > 0)

class TestDomainRuleEngine(unittest.TestCase):
    """Test domain-specific plausibility rules"""
    
    def setUp(self):
        self.engine = DomainRuleEngine()
    
    def test_physics_rules_ftl_violation(self):
        """Test physics rules for faster-than-light violations"""
        claim = "Instantaneous knowledge transfer across any distance"
        result = self.engine._check_physics_rules(claim)
        
        self.assertFalse(result['is_plausible'])
        self.assertTrue(len(result['violations']) > 0)
        self.assertEqual(result['violations'][0]['rule'], 'no-communication_theorem')
    
    def test_neuroscience_rules_memory_transfer(self):
        """Test neuroscience rules for memory transfer claims"""
        claim = "Human memory transfer has been achieved"
        result = self.engine._check_neuroscience_rules(claim)
        
        self.assertFalse(result['is_plausible'])
        self.assertTrue(len(result['violations']) > 0)
        self.assertEqual(result['violations'][0]['rule'], 'human_memory_transfer')
    
    def test_statistics_rules_precision(self):
        """Test statistics rules for suspicious precision"""
        claim = "The study showed 92.47% accuracy"
        result = self.engine._check_statistics_rules(claim)
        
        self.assertFalse(result['is_plausible'])
        self.assertTrue(len(result['violations']) > 0)
        self.assertEqual(result['violations'][0]['rule'], 'suspicious_precision')
    
    def test_check_claim_plausibility(self):
        """Test overall claim plausibility checking"""
        claim = "Instantaneous knowledge transfer across any distance"
        result = self.engine.check_claim_plausibility(claim)
        
        self.assertFalse(result['overall_plausible'])
        self.assertTrue(result['critical_violations'])

class TestEvidenceWeightedConfidence(unittest.TestCase):
    """Test evidence-weighted confidence algorithm"""
    
    def test_classify_evidence_type(self):
        """Test evidence type classification"""
        # Peer-reviewed primary human
        evidence = {
            'type': 'peer-reviewed',
            'venue': 'Nature',
            'url': 'https://nature.com'
        }
        evidence_type = EvidenceWeightedConfidence.classify_evidence_type(evidence)
        self.assertEqual(evidence_type, 'peer_reviewed_primary_human')
        
        # Preprint
        evidence = {
            'type': 'preprint',
            'url': 'https://arxiv.org'
        }
        evidence_type = EvidenceWeightedConfidence.classify_evidence_type(evidence)
        self.assertEqual(evidence_type, 'preprint')
    
    def test_calculate_confidence_score(self):
        """Test confidence score calculation"""
        evidence_list = [
            {
                'type': 'peer-reviewed',
                'venue': 'Nature',
                'doi': '10.1038/test'
            }
        ]
        contradictions = []
        
        score, drivers = EvidenceWeightedConfidence.calculate_confidence_score(evidence_list, contradictions)
        
        self.assertEqual(score, 50)  # Should get full weight for peer-reviewed primary
        self.assertTrue(len(drivers) > 0)
    
    def test_get_confidence_color(self):
        """Test confidence color mapping"""
        self.assertEqual(EvidenceWeightedConfidence.get_confidence_color(0), "red")
        self.assertEqual(EvidenceWeightedConfidence.get_confidence_color(15), "orange")
        self.assertEqual(EvidenceWeightedConfidence.get_confidence_color(50), "yellow")
        self.assertEqual(EvidenceWeightedConfidence.get_confidence_color(85), "green")
    
    def test_get_classification(self):
        """Test classification logic"""
        # Fabricated terms
        fabricated_terms = ["fabricated_term"]
        plausibility_result = {'overall_plausible': True}
        classification = EvidenceWeightedConfidence.get_classification(80, fabricated_terms, plausibility_result)
        self.assertEqual(classification, "Fabricated")
        
        # Physically implausible
        fabricated_terms = []
        plausibility_result = {'overall_plausible': False}
        classification = EvidenceWeightedConfidence.get_classification(80, fabricated_terms, plausibility_result)
        self.assertEqual(classification, "Physically Implausible")
        
        # Supported
        plausibility_result = {'overall_plausible': True}
        classification = EvidenceWeightedConfidence.get_classification(80, fabricated_terms, plausibility_result)
        self.assertEqual(classification, "Supported")

class TestClairvoxAnalyzer(unittest.TestCase):
    """Test main Clairvox analyzer"""
    
    def setUp(self):
        self.analyzer = ClairvoxAnalyzer()
    
    def test_parse_claims(self):
        """Test claim parsing"""
        text = "This is a claim. This is another claim!"
        claims = self.analyzer.parse_claims(text)
        
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0]['original_claim'], "This is a claim.")
        self.assertEqual(claims[1]['original_claim'], "This is another claim!")
    
    def test_normalize_claim(self):
        """Test claim normalization"""
        claim = "Does intermittent fasting work?"
        normalized = self.analyzer._normalize_claim(claim)
        self.assertEqual(normalized, "intermittent fasting work")
    
    @patch('backend.clairvox_analyzer.db_searcher')
    def test_search_evidence(self, mock_searcher):
        """Test evidence search"""
        mock_searcher.search_crossref.return_value = []
        mock_searcher.search_pubmed.return_value = []
        mock_searcher.search_arxiv.return_value = []
        
        evidence = self.analyzer.search_evidence("test claim")
        self.assertEqual(len(evidence), 0)
    
    def test_check_replication_status(self):
        """Test replication status checking"""
        evidence_list = [
            {'title': 'Original Study', 'venue': 'Nature'},
            {'title': 'Replication Study', 'venue': 'Science'}
        ]
        
        status = self.analyzer.check_replication_status(evidence_list)
        self.assertEqual(status, "replicated")
    
    @patch('backend.clairvox_analyzer.db_searcher')
    @patch('backend.clairvox_analyzer.fabricated_detector')
    @patch('backend.clairvox_analyzer.domain_engine')
    def test_analyze_claim(self, mock_domain_engine, mock_detector, mock_searcher):
        """Test complete claim analysis"""
        # Mock all dependencies
        mock_detector.detect_fabricated_terms.return_value = []
        mock_domain_engine.check_claim_plausibility.return_value = {'overall_plausible': True}
        mock_searcher.search_crossref.return_value = []
        mock_searcher.search_pubmed.return_value = []
        mock_searcher.search_arxiv.return_value = []
        
        claim_data = {
            'original_claim': 'Test claim',
            'normalized_claim': 'test claim'
        }
        
        result = self.analyzer.analyze_claim(claim_data)
        
        # Check required fields
        required_fields = [
            'original_claim', 'normalized_claim', 'classification', 
            'confidence_score', 'confidence_color', 'drivers',
            'top_evidence', 'fabricated_terms', 'replication_status',
            'contradictions', 'explanation_plain', 'suggested_corrections',
            'search_actions'
        ]
        
        for field in required_fields:
            self.assertIn(field, result)

class TestJSONSchemaValidation(unittest.TestCase):
    """Test JSON schema validation"""
    
    def test_mandatory_json_format(self):
        """Test that output matches mandatory JSON format"""
        # This would be a real test with actual data
        # For now, we'll test the structure
        
        expected_schema = {
            "original_claim": str,
            "normalized_claim": str,
            "classification": str,
            "confidence_score": int,
            "confidence_color": str,
            "drivers": list,
            "top_evidence": list,
            "fabricated_terms": list,
            "replication_status": str,
            "contradictions": list,
            "explanation_plain": str,
            "suggested_corrections": str,
            "search_actions": str
        }
        
        # Test that our analyzer produces the right structure
        analyzer = ClairvoxAnalyzer()
        claim_data = {
            'original_claim': 'Test claim',
            'normalized_claim': 'test claim'
        }
        
        with patch.object(analyzer, 'search_evidence') as mock_search:
            mock_search.return_value = []
            
            result = analyzer.analyze_claim(claim_data)
            
            for field, expected_type in expected_schema.items():
                self.assertIn(field, result)
                self.assertIsInstance(result[field], expected_type)

class TestFabricatedDetectionPrecision(unittest.TestCase):
    """Test fabricated detection precision as required"""
    
    def test_fabricated_case_example(self):
        """Test the specific fabricated case from requirements"""
        text = """
        The neural photon resonance chamber uses gravito-electroencephalography 
        to achieve ultraviolet-pi band synchronization for memory transfer.
        """
        
        analyzer = ClairvoxAnalyzer()
        
        with patch.object(analyzer.fabricated_detector, 'search_term_existence') as mock_search:
            # Mock zero hits for all fabricated terms
            mock_search.return_value = {
                'term': 'test',
                'total_exact_hits': 0,
                'total_fuzzy_hits': 0
            }
            
            claims = analyzer.parse_claims(text)
            result = analyzer.analyze_claim(claims[0])
            
            # Should detect fabricated terms
            self.assertTrue(len(result['fabricated_terms']) > 0)
            self.assertIn(result['classification'], ['Fabricated', 'Physically Implausible'])
            self.assertEqual(result['confidence_score'], 0)

if __name__ == '__main__':
    unittest.main()


