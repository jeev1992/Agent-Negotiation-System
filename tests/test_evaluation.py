"""
Tests for Evaluation Judge
==========================
"""

import pytest
import sys
import importlib.util
from pathlib import Path

# Setup path for numbered module imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def import_numbered_layer(folder_name: str):
    """Import a numbered layer folder dynamically."""
    folder_path = project_root / folder_name
    init_path = folder_path / "__init__.py"
    
    if not init_path.exists():
        raise ImportError(f"No __init__.py in {folder_name}")
    
    spec = importlib.util.spec_from_file_location(folder_name, init_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[folder_name] = module
    spec.loader.exec_module(module)
    return module


# Import evaluation module
eval_module = import_numbered_layer("11_evaluation")
NegotiationJudge = eval_module.NegotiationJudge
Judgment = eval_module.Judgment
JudgmentCriteria = eval_module.JudgmentCriteria


class TestFairnessJudgment:
    """Test fairness scoring."""
    
    def test_no_deal_fails(self):
        """No agreement should fail fairness."""
        judge = NegotiationJudge()
        result = judge.judge_fairness(
            final_price=None,
            buyer_max=500,
            seller_min=350
        )
        
        assert result.passed is False
        assert result.score == 0.0
    
    def test_fair_deal_passes(self):
        """Price at midpoint should be fair."""
        judge = NegotiationJudge()
        
        # ZOPA: 350-500, midpoint = 425
        result = judge.judge_fairness(
            final_price=425,
            buyer_max=500,
            seller_min=350
        )
        
        assert result.passed is True
        assert result.score > 0.8  # High fairness
    
    def test_extreme_price_less_fair(self):
        """Price at extreme end is less fair."""
        judge = NegotiationJudge(fairness_threshold=0.3)
        
        # Price at seller's min (buyer gets everything)
        result = judge.judge_fairness(
            final_price=350,
            buyer_max=500,
            seller_min=350
        )
        
        # Might not pass with default threshold
        assert result.score < 1.0


class TestEfficiencyJudgment:
    """Test efficiency scoring."""
    
    def test_failed_negotiation(self):
        """Failed negotiation gets zero efficiency."""
        judge = NegotiationJudge(max_acceptable_turns=10)
        result = judge.judge_efficiency(
            turns=5,
            success=False
        )
        
        assert result.passed is False
        assert result.score == 0.0
    
    def test_quick_deal_efficient(self):
        """Quick deal gets high efficiency."""
        judge = NegotiationJudge(max_acceptable_turns=10)
        result = judge.judge_efficiency(
            turns=2,
            success=True
        )
        
        assert result.score > 0.7
    
    def test_slow_deal_less_efficient(self):
        """Slow deal gets lower efficiency."""
        judge = NegotiationJudge(max_acceptable_turns=10)
        result = judge.judge_efficiency(
            turns=8,
            success=True
        )
        
        assert result.score < 0.3


class TestProtocolJudgment:
    """Test protocol adherence scoring."""
    
    def test_correct_order_passes(self):
        """Correct turn order passes."""
        judge = NegotiationJudge()
        
        messages = [
            {"agent": "buyer", "type": "offer", "price": 300},
            {"agent": "seller", "type": "counter", "price": 450},
            {"agent": "buyer", "type": "offer", "price": 350},
            {"agent": "seller", "type": "accept", "price": 350},
        ]
        
        result = judge.judge_protocol(messages)
        
        assert result.passed is True
        assert result.score == 1.0
    
    def test_wrong_order_fails(self):
        """Wrong turn order fails."""
        judge = NegotiationJudge()
        
        messages = [
            {"agent": "buyer", "type": "offer", "price": 300},
            {"agent": "buyer", "type": "offer", "price": 350},  # Wrong!
            {"agent": "seller", "type": "counter", "price": 400},
        ]
        
        result = judge.judge_protocol(messages)
        
        assert result.passed is False
        assert result.score < 1.0


class TestComprehensiveEvaluation:
    """Test full evaluation."""
    
    def test_evaluate_returns_all_criteria(self):
        """Evaluate should return judgments for all criteria."""
        judge = NegotiationJudge()
        
        messages = [
            {"agent": "buyer", "type": "offer"},
            {"agent": "seller", "type": "accept"},
        ]
        
        judgments = judge.evaluate(
            final_price=400,
            buyer_max=500,
            seller_min=350,
            turns=2,
            success=True,
            messages=messages
        )
        
        assert len(judgments) == 3
        criteria_names = {j.criteria for j in judgments}
        assert JudgmentCriteria.OUTCOME_FAIR in criteria_names
        assert JudgmentCriteria.TURNS_EFFICIENT in criteria_names
        assert JudgmentCriteria.PROTOCOL_FOLLOWED in criteria_names
    
    def test_overall_score_averaging(self):
        """Overall score should be average of components."""
        judge = NegotiationJudge()
        
        messages = [
            {"agent": "buyer"},
            {"agent": "seller"},
        ]
        
        judgments = judge.evaluate(
            final_price=425,  # Fair
            buyer_max=500,
            seller_min=350,
            turns=2,  # Efficient
            success=True,
            messages=messages
        )
        
        overall = judge.overall_score(judgments)
        
        # Should be average of component scores
        expected = sum(j.score for j in judgments) / len(judgments)
        assert overall == expected
    
    def test_summary_includes_all_criteria(self):
        """Summary should mention all criteria."""
        judge = NegotiationJudge()
        
        messages = []
        judgments = judge.evaluate(
            final_price=400,
            buyer_max=500,
            seller_min=350,
            turns=3,
            success=True,
            messages=messages
        )
        
        summary = judge.summary(judgments)
        
        assert "OUTCOME_FAIR" in summary
        assert "TURNS_EFFICIENT" in summary
        assert "PROTOCOL_FOLLOWED" in summary
        assert "Overall Score" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
