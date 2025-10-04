"""
Clairvox Robust Unit Tests
Comprehensive test suite for all components with mock datasets
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.clairvox_core import (
    MetadataValidator, SemanticReranker, DatabaseSearcher, 
    FabricatedTermDetector, DomainRuleEngine
)
from backend.clairvox_analyzer import ClairvoxAnalyzer, EvidenceWeightedConfidence
from backend.verifier import analyze_claim, analyze_text_comprehensive

class TestMetadataValidator(unittest.TestCase):
    """Test metadata validation and DOI extraction"""
    
    def setUp(self):
        self.validator = MetadataValidator()
    
    def test_extract_doi_fallback(self):
        """Test DOI extraction with regex fallback"""
        # Valid DOI patterns
        test_cases = [
            ("10.1038/nature12345", "10.1038/nature12345"),
            ("DOI: 10.1000/182", "10.1000/182"),
            ("https://doi.org/10.1371/journal.pone.0123456", "10.1371/journal.pone.0123456"),
            ("No DOI here", None),
            ("10.1234/invalid", "10.1234/invalid")
        ]
        
        for text, expected in test_cases:
            result = self.validator.extract_doi_fallback(text)
            self.assertEqual(result, expected)
    
    def test_validate_metadata(self):
        """Test metadata validation and fixing"""
        # Test case with missing fields
        incomplete_result = {
            'title': '',
            'authors': '',
            'venue': '',
            'date': '',
            'doi': '',
            'url': 'https://doi.org/10.1038/test123',
            'excerpt': 'A' * 300  # Too long excerpt
        }
        
        validated = self.validator.validate_metadata(incomplete_result)
        
        # Check that empty fields are filled
        self.assertEqual(validated['title'], "No title available")
        self.assertEqual(validated['authors'], "Unknown authors")
        self.assertEqual(validated['venue'], "Unknown venue")
        self.assertEqual(validated['date'], "Unknown date")
        
        # Check DOI extraction from URL
        self.assertEqual(validated['doi'], "10.1038/test123")
        
        # Check excerpt truncation
        self.assertTrue(len(validated['excerpt']) <= 203)  # 200 + "..."
        self.assertTrue(validated['excerpt'].endswith("..."))

class TestSemanticReranker(unittest.TestCase):
    """Test semantic reranking functionality"""
    
    def setUp(self):
        self.reranker = SemanticReranker(relevance_threshold=0.5)
    
    def test_calculate_similarity(self):
        """Test similarity calculation"""
        # High similarity case
        claim = "intermittent fasting weight loss"
        evidence = "intermittent fasting helps with weight loss in humans"
        similarity = self.reranker.calculate_similarity(claim, evidence)
        self.assertGreater(similarity, 0.5)
        
        # Low similarity case
        claim = "intermittent fasting weight loss"
        evidence = "quantum physics particle acceleration"
        similarity = self.reranker.calculate_similarity(claim, evidence)
        self.assertLess(similarity, 0.3)
        
        # Empty case
        similarity = self.reranker.calculate_similarity("", "test")
        self.assertEqual(similarity, 0.0)
    
    def test_rerank_evidence(self):
        """Test evidence reranking"""
        claim = "intermittent fasting weight loss"
        evidence_list = [
            {
                'title': 'Quantum Physics',
                'excerpt': 'particle acceleration',
                'venue': 'Physics Journal'
            },
            {
                'title': 'Intermittent Fasting Study',
                'excerpt': 'weight loss benefits',
                'venue': 'Nutrition Journal'
            },
            {
                'title': 'Fasting Research',
                'excerpt': 'metabolic effects',
                'venue': 'Health Journal'
            }
        ]
        
        reranked = self.reranker.rerank_evidence(claim, evidence_list)
        
        # Should be sorted by relevance
        self.assertTrue(len(reranked) > 0)
        self.assertTrue(reranked[0]['relevance_score'] >= reranked[-1]['relevance_score'])
        
        # Should have relevance scores
        for evidence in reranked:
            self.assertIn('relevance_score', evidence)
            self.assertIn('is_relevant', evidence)

class TestDatabaseSearcher(unittest.TestCase):
    """Test database search functionality with mocks"""
    
    def setUp(self):
        self.searcher = DatabaseSearcher()
    
    @patch('backend.clairvox_core.requests.Session.get')
    def test_search_crossref_robust_metadata(self, mock_get):
        """Test CrossRef search with robust metadata extraction"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'message': {
                'items': [
                    {
                        'title': ['Test Article'],
                        'author': [
                            {'given': 'John', 'family': 'Doe'},
                            {'given': 'Jane', 'family': 'Smith'}
                        ],
                        'container-title': ['Nature'],
                        'published-print': {'date-parts': [[2023]]},
                        'DOI': '10.1038/test123',
                        'abstract': 'This is a test abstract about research findings.'
                    }
                ]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        results = self.searcher.search_crossref("test query", 5)
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Check robust metadata extraction
        self.assertEqual(result['title'], 'Test Article')
        self.assertEqual(result['authors'], 'John Doe, Jane Smith')
        self.assertEqual(result['venue'], 'Nature')
        self.assertEqual(result['date'], '2023')
        self.assertEqual(result['doi'], '10.1038/test123')
        self.assertEqual(result['source'], 'CrossRef')
        self.assertEqual(result['query_used'], 'test query')
    
    @patch('backend.clairvox_core.requests.Session.get')
    def test_search_crossref_missing_doi_fallback(self, mock_get):
        """Test CrossRef search with DOI fallback"""
        # Mock response with missing DOI but URL
        mock_response = Mock()
        mock_response.json.return_value = {
            'message': {
                'items': [
                    {
                        'title': ['Test Article'],
                        'author': [],
                        'container-title': [],
                        'published-print': {'date-parts': [[]]},
                        'DOI': '',  # Missing DOI
                        'abstract': 'Test abstract'
                    }
                ]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        results = self.searcher.search_crossref("test query", 5)
        
        # Should still have valid metadata after validation
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['title'], 'Test Article')
        self.assertEqual(result['authors'], 'Unknown authors')
        self.assertEqual(result['venue'], 'Unknown venue')

class TestDomainRuleEngine(unittest.TestCase):
    """Test domain-specific plausibility rules"""
    
    def setUp(self):
        self.engine = DomainRuleEngine()
    
    def test_physics_rules_ftl_violation(self):
        """Test physics rules for faster-than-light violations"""
        test_cases = [
            ("Instantaneous knowledge transfer across any distance", True),
            ("Faster than light information transmission", True),
            ("Real time communication any distance", True),
            ("Normal internet communication", False),
            ("Regular email sending", False)
        ]
        
        for claim, should_violate in test_cases:
            result = self.engine._check_physics_rules(claim)
            if should_violate:
                self.assertFalse(result['is_plausible'])
                self.assertTrue(len(result['violations']) > 0)
                self.assertEqual(result['violations'][0]['rule'], 'no-communication_theorem')
            else:
                self.assertTrue(result['is_plausible'])
                self.assertEqual(len(result['violations']), 0)
    
    def test_neuroscience_rules_memory_transfer(self):
        """Test neuroscience rules for memory transfer claims"""
        test_cases = [
            ("Human memory transfer has been achieved", True),
            ("Direct memory transplant between humans", True),
            ("Consciousness transfer human subjects", True),
            ("Memory research in mice", False),
            ("Brain imaging studies", False)
        ]
        
        for claim, should_violate in test_cases:
            result = self.engine._check_neuroscience_rules(claim)
            if should_violate:
                self.assertFalse(result['is_plausible'])
                self.assertTrue(len(result['violations']) > 0)
                self.assertEqual(result['violations'][0]['rule'], 'human_memory_transfer')
            else:
                self.assertTrue(result['is_plausible'])
    
    def test_statistics_rules_precision(self):
        """Test statistics rules for suspicious precision"""
        test_cases = [
            ("The study showed 92.47% accuracy", True),
            ("Results indicate 85% success rate", False),
            ("Precision of 99.123% was achieved", True),
            ("About 90% of participants", False)
        ]
        
        for claim, should_violate in test_cases:
            result = self.engine._check_statistics_rules(claim)
            if should_violate:
                self.assertFalse(result['is_plausible'])
                self.assertTrue(len(result['violations']) > 0)
                self.assertEqual(result['violations'][0]['rule'], 'suspicious_precision')
            else:
                self.assertTrue(result['is_plausible'])
    
    def test_check_claim_plausibility_integration(self):
        """Test overall claim plausibility checking"""
        # Physically implausible claim
        implausible_claim = "Instantaneous knowledge transfer across any distance"
        result = self.engine.check_claim_plausibility(implausible_claim)
        
        self.assertFalse(result['overall_plausible'])
        self.assertTrue(result['critical_violations'])
        self.assertIn('physics', result['domain_results'])
        
        # Plausible claim
        plausible_claim = "Regular email communication works well"
        result = self.engine.check_claim_plausibility(plausible_claim)
        
        self.assertTrue(result['overall_plausible'])
        self.assertFalse(result['critical_violations'])

class TestEvidenceWeightedConfidence(unittest.TestCase):
    """Test evidence-weighted confidence algorithm"""
    
    def test_classify_evidence_type(self):
        """Test evidence type classification"""
        test_cases = [
            ({
                'type': 'peer-reviewed',
                'venue': 'Nature',
                'url': 'https://nature.com'
            }, 'peer_reviewed_primary_human'),
            ({
                'type': 'preprint',
                'url': 'https://arxiv.org'
            }, 'preprint'),
            ({
                'type': 'peer-reviewed',
                'venue': 'Conference Proceedings',
                'url': 'https://ieee.org'
            }, 'conference_proceedings'),
            ({
                'type': 'news',
                'url': 'https://nature.com/news'
            }, 'reputable_news'),
            ({
                'type': 'blog',
                'url': 'https://blog.example.com'
            }, 'blog_social_media')
        ]
        
        for evidence, expected_type in test_cases:
            result_type = EvidenceWeightedConfidence.classify_evidence_type(evidence)
            self.assertEqual(result_type, expected_type)
    
    def test_calculate_confidence_score(self):
        """Test confidence score calculation with exact weights"""
        # High-quality evidence
        evidence_list = [
            {
                'type': 'peer-reviewed',
                'venue': 'Nature',
                'doi': '10.1038/test123'
            },
            {
                'type': 'preprint',
                'url': 'https://arxiv.org'
            }
        ]
        contradictions = []
        
        score, drivers = EvidenceWeightedConfidence.calculate_confidence_score(evidence_list, contradictions)
        
        # Should get high score: 50 (peer-reviewed) + 20 (preprint) = 70
        self.assertEqual(score, 70)
        self.assertTrue(len(drivers) > 0)
        
        # Test with contradictions
        contradictions = [{'source': 'test', 'detail': 'contradiction'}]
        score, drivers = EvidenceWeightedConfidence.calculate_confidence_score(evidence_list, contradictions)
        
        # Should be penalized: 70 - 70 (contradiction) = 0
        self.assertEqual(score, 0)
        self.assertTrue(any('contradicted' in driver for driver in drivers))
    
    def test_get_confidence_color(self):
        """Test confidence color mapping"""
        test_cases = [
            (0, "red"),
            (15, "orange"),
            (50, "yellow"),
            (85, "green")
        ]
        
        for score, expected_color in test_cases:
            color = EvidenceWeightedConfidence.get_confidence_color(score)
            self.assertEqual(color, expected_color)
    
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
        
        # Weakly supported
        classification = EvidenceWeightedConfidence.get_classification(50, fabricated_terms, plausibility_result)
        self.assertEqual(classification, "Weakly Supported")
        
        # Unsupported
        classification = EvidenceWeightedConfidence.get_classification(20, fabricated_terms, plausibility_result)
        self.assertEqual(classification, "Unsupported")

class TestClairvoxAnalyzer(unittest.TestCase):
    """Test main Clairvox analyzer with domain-rule pre-validation"""
    
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
        test_cases = [
            ("Does intermittent fasting work?", "intermittent fasting work"),
            ("What is the effect of exercise?", "effect exercise"),
            ("How does memory work?", "memory work")
        ]
        
        for claim, expected in test_cases:
            normalized = self.analyzer._normalize_claim(claim)
            self.assertEqual(normalized, expected)
    
    @patch.object(ClairvoxAnalyzer, 'search_evidence')
    @patch.object(ClairvoxAnalyzer, 'search_contradictions')
    def test_analyze_claim_domain_rule_short_circuit(self, mock_contradictions, mock_evidence):
        """Test that domain rules short-circuit analysis for implausible claims"""
        mock_contradictions.return_value = []
        mock_evidence.return_value = []
        
        # Physically implausible claim
        claim_data = {
            'original_claim': 'Instantaneous knowledge transfer across any distance',
            'normalized_claim': 'instantaneous knowledge transfer across any distance'
        }
        
        result = self.analyzer.analyze_claim(claim_data)
        
        # Should short-circuit and not call search methods
        mock_evidence.assert_not_called()
        mock_contradictions.assert_not_called()
        
        # Should return implausible result
        self.assertEqual(result['classification'], 'Physically Implausible')
        self.assertEqual(result['confidence_score'], 0)
        self.assertEqual(result['confidence_color'], 'red')
        self.assertIn('domain_violations', result)
    
    @patch.object(ClairvoxAnalyzer, 'search_evidence')
    @patch.object(ClairvoxAnalyzer, 'search_contradictions')
    def test_analyze_claim_fabricated_short_circuit(self, mock_contradictions, mock_evidence):
        """Test that fabricated terms short-circuit analysis"""
        mock_contradictions.return_value = []
        mock_evidence.return_value = []
        
        # Mock fabricated term detection
        with patch.object(self.analyzer.fabricated_detector, 'detect_fabricated_terms') as mock_detect:
            mock_detect.return_value = [{'term': 'fabricated_term', 'search_evidence': {}}]
            
            claim_data = {
                'original_claim': 'The fabricated_term device works',
                'normalized_claim': 'fabricated_term device works'
            }
            
            result = self.analyzer.analyze_claim(claim_data)
            
            # Should short-circuit and not call search methods
            mock_evidence.assert_not_called()
            mock_contradictions.assert_not_called()
            
            # Should return fabricated result
            self.assertEqual(result['classification'], 'Fabricated')
            self.assertEqual(result['confidence_score'], 0)
            self.assertEqual(result['confidence_color'], 'red')
            self.assertIn('fabricated_terms', result)
            self.assertIn('fabricated_term_evidence', result)

class TestJSONSchemaValidation(unittest.TestCase):
    """Test JSON schema validation"""
    
    def test_mandatory_json_format(self):
        """Test that output matches mandatory JSON format"""
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

class TestIntegrationTests(unittest.TestCase):
    """Integration tests for the complete system"""
    
    @patch('backend.verifier.clairvox_analyzer')
    def test_analyze_claim_integration(self, mock_analyzer):
        """Test analyze_claim integration"""
        # Mock the analyzer result
        mock_result = {
            'original_claim': 'Test claim',
            'normalized_claim': 'test claim',
            'classification': 'Supported',
            'confidence_score': 75,
            'confidence_color': 'green',
            'drivers': ['peer-reviewed primary found'],
            'top_evidence': [{'title': 'Test Paper', 'doi': '10.1038/test'}],
            'fabricated_terms': [],
            'replication_status': 'replicated',
            'contradictions': [],
            'explanation_plain': 'Strong evidence found',
            'suggested_corrections': 'No corrections needed',
            'search_actions': 'Searched databases'
        }
        mock_analyzer.analyze_claim.return_value = mock_result
        
        result = analyze_claim('Test claim', 'original query')
        
        # Check legacy format compatibility
        self.assertEqual(result['claim'], 'Test claim')
        self.assertEqual(result['confidence'], 75)
        self.assertIn('clairvox_result', result)
        self.assertEqual(result['clairvox_result'], mock_result)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestMetadataValidator,
        TestSemanticReranker,
        TestDatabaseSearcher,
        TestDomainRuleEngine,
        TestEvidenceWeightedConfidence,
        TestClairvoxAnalyzer,
        TestJSONSchemaValidation,
        TestFabricatedDetectionPrecision,
        TestIntegrationTests
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")


