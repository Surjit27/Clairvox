# Updated tests/test_scoring.py

import sys
import os
import pytest

# Add the backend directory to the path to import from it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.verifier import compute_confidence

# Neutral quality score for tests not focused on quality
NEUTRAL_QUALITY = 0.5

def test_score_boundaries():
    """Test that the score is always clamped between 0 and 100."""
    # Test lower bound (no evidence)
    assert compute_confidence(0, 0, 0.0, 0, 0.0) == 0
    # Test lower bound with contradictions (should not go below 0)
    assert compute_confidence(0, 0, 0.0, 3, 0.0) == 0
    # Test upper bound (max everything)
    assert compute_confidence(5, 3, 1.0, 0, 1.0) == 100
    # Test high score that should not be clamped
    assert compute_confidence(3, 2, 0.8, 0, 0.7) > 50 and compute_confidence(3, 2, 0.8, 0, 0.7) < 100

def test_monotonicity_with_support():
    """Score should increase as support count increases."""
    score1 = compute_confidence(1, 1, 0.5, 0, NEUTRAL_QUALITY)
    score2 = compute_confidence(2, 1, 0.5, 0, NEUTRAL_QUALITY)
    score3 = compute_confidence(5, 1, 0.5, 0, NEUTRAL_QUALITY)
    assert score1 < score2 < score3

def test_penalty_with_contradictions():
    """Score should decrease as contradiction count increases."""
    score_base = compute_confidence(4, 3, 0.8, 0, NEUTRAL_QUALITY)
    score_c1 = compute_confidence(4, 3, 0.8, 1, NEUTRAL_QUALITY)
    score_c2 = compute_confidence(4, 3, 0.8, 2, NEUTRAL_QUALITY)
    assert score_base > score_c1 > score_c2

def test_diversity_impact():
    """Score should increase as diversity increases."""
    score_d1 = compute_confidence(3, 1, 0.7, 0, NEUTRAL_QUALITY)
    score_d2 = compute_confidence(3, 2, 0.7, 0, NEUTRAL_QUALITY)
    score_d3 = compute_confidence(3, 3, 0.7, 0, NEUTRAL_QUALITY)
    assert score_d1 < score_d2 < score_d3

def test_recency_impact():
    """Score should increase as recency increases."""
    score_r_low = compute_confidence(3, 2, 0.1, 0, NEUTRAL_QUALITY)
    score_r_mid = compute_confidence(3, 2, 0.5, 0, NEUTRAL_QUALITY)
    score_r_high = compute_confidence(3, 2, 1.0, 0, NEUTRAL_QUALITY)
    assert score_r_low < score_r_mid < score_r_high

def test_quality_impact():
    """NEW: Score should increase as source quality increases."""
    score_q_low = compute_confidence(3, 2, 0.8, 0, 0.4) # Low quality sources
    score_q_mid = compute_confidence(3, 2, 0.8, 0, 0.7) # Medium quality sources
    score_q_high = compute_confidence(3, 2, 0.8, 0, 1.0) # High quality sources
    assert score_q_low < score_q_mid < score_q_high

# In tests/test_scoring.py, replace the old test_realistic_scenario function with this one:

def test_realistic_scenario():
    """Test a typical, balanced scenario with the new formula."""
    # 3 sources, 2 domains, moderately recent, 1 contradiction, medium quality
    score = compute_confidence(3, 2, 0.6, 1, 0.7)
    # Expected: (40*3/5) + (20*2/3) + (20*0.6) + (20*0.7) - (30*1/3)
    # = 24 + 13.33 + 12 + 14 - 10 = 53.33 -> 53
    assert score == 53