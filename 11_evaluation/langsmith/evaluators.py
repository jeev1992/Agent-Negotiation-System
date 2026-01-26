"""
LangSmith Evaluators
====================

Evaluator functions for scoring negotiation outcomes.
These run as part of LangSmith experiments.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EvaluationResult:
    """Result from an evaluator."""
    key: str
    score: float  # 0.0 to 1.0
    comment: str


# ============================================================================
# Agreement Evaluator
# ============================================================================

def agreement_evaluator(
    run_output: Dict[str, Any],
    example: Dict[str, Any],
) -> EvaluationResult:
    """
    Did the negotiation agree/disagree correctly?
    
    Args:
        run_output: The actual result from running negotiation
        example: The expected values from dataset
        
    Returns:
        EvaluationResult with score 1.0 if correct, 0.0 if wrong
    """
    expected = example.get("expected", {})
    should_agree = expected.get("should_agree", True)
    actually_agreed = run_output.get("agreed", False)
    
    if should_agree == actually_agreed:
        return EvaluationResult(
            key="agreement_correct",
            score=1.0,
            comment=f"Correctly {'agreed' if actually_agreed else 'disagreed'}",
        )
    else:
        return EvaluationResult(
            key="agreement_correct",
            score=0.0,
            comment=f"Expected {'agreement' if should_agree else 'no agreement'}, got {'agreement' if actually_agreed else 'no agreement'}",
        )


# ============================================================================
# Fairness Evaluator
# ============================================================================

def fairness_evaluator(
    run_output: Dict[str, Any],
    example: Dict[str, Any],
) -> EvaluationResult:
    """
    Was the final price fair (within expected range)?
    """
    expected = example.get("expected", {})
    inputs = example.get("inputs", {})
    
    final_price = run_output.get("final_price")
    agreed = run_output.get("agreed", False)
    
    # If shouldn't agree, fairness is N/A
    if not expected.get("should_agree", True):
        if not agreed:
            return EvaluationResult(
                key="fairness",
                score=1.0,
                comment="Correctly no agreement (fairness N/A)",
            )
        else:
            return EvaluationResult(
                key="fairness",
                score=0.0,
                comment="Agreed when shouldn't have",
            )
    
    # Should have agreed
    if not agreed or final_price is None:
        return EvaluationResult(
            key="fairness",
            score=0.0,
            comment="No agreement reached",
        )
    
    # Check if price is in fair range
    min_fair = expected.get("min_fair_price", inputs.get("seller_min", 0))
    max_fair = expected.get("max_fair_price", inputs.get("buyer_max", float("inf")))
    
    if min_fair <= final_price <= max_fair:
        # Calculate how centered the price is (1.0 = exactly in middle)
        mid_point = (min_fair + max_fair) / 2
        range_size = max_fair - min_fair
        if range_size > 0:
            distance_from_center = abs(final_price - mid_point) / (range_size / 2)
            score = 1.0 - (distance_from_center * 0.5)  # Max penalty 0.5 for edge
        else:
            score = 1.0
        
        return EvaluationResult(
            key="fairness",
            score=score,
            comment=f"Price ${final_price:.2f} is fair (range: ${min_fair:.2f}-${max_fair:.2f})",
        )
    else:
        return EvaluationResult(
            key="fairness",
            score=0.0,
            comment=f"Price ${final_price:.2f} outside fair range ${min_fair:.2f}-${max_fair:.2f}",
        )


# ============================================================================
# Efficiency Evaluator
# ============================================================================

def efficiency_evaluator(
    run_output: Dict[str, Any],
    example: Dict[str, Any],
) -> EvaluationResult:
    """
    Was the negotiation efficient (completed in reasonable turns)?
    """
    expected = example.get("expected", {})
    inputs = example.get("inputs", {})
    
    turns_taken = run_output.get("turns", 0)
    max_turns = inputs.get("max_turns", 10)
    max_acceptable = expected.get("max_acceptable_turns", max_turns)
    
    if turns_taken <= max_acceptable:
        # Score based on how few turns used
        score = 1.0 - (turns_taken / max_acceptable) * 0.5  # Min score 0.5 at limit
        return EvaluationResult(
            key="efficiency",
            score=score,
            comment=f"Completed in {turns_taken}/{max_acceptable} acceptable turns",
        )
    else:
        # Over limit
        overage = turns_taken - max_acceptable
        score = max(0, 0.5 - overage * 0.1)  # Penalty for each extra turn
        return EvaluationResult(
            key="efficiency",
            score=score,
            comment=f"Took {turns_taken} turns (max acceptable: {max_acceptable})",
        )


# ============================================================================
# Protocol Evaluator
# ============================================================================

def protocol_evaluator(
    run_output: Dict[str, Any],
    example: Dict[str, Any],
) -> EvaluationResult:
    """
    Did agents follow the protocol (alternating turns)?
    """
    messages = run_output.get("messages", [])
    
    if not messages:
        return EvaluationResult(
            key="protocol",
            score=0.5,
            comment="No messages to evaluate",
        )
    
    violations = 0
    expected_agent = "buyer"
    
    for msg in messages:
        agent = msg.get("agent", "unknown")
        if agent != expected_agent:
            violations += 1
        expected_agent = "seller" if expected_agent == "buyer" else "buyer"
    
    if violations == 0:
        return EvaluationResult(
            key="protocol",
            score=1.0,
            comment="Perfect protocol compliance",
        )
    else:
        score = max(0, 1.0 - violations * 0.2)
        return EvaluationResult(
            key="protocol",
            score=score,
            comment=f"{violations} protocol violations",
        )


# ============================================================================
# Overall Evaluator
# ============================================================================

def overall_evaluator(
    run_output: Dict[str, Any],
    example: Dict[str, Any],
) -> EvaluationResult:
    """
    Combined overall score from all evaluators.
    """
    results = [
        agreement_evaluator(run_output, example),
        fairness_evaluator(run_output, example),
        efficiency_evaluator(run_output, example),
        protocol_evaluator(run_output, example),
    ]
    
    avg_score = sum(r.score for r in results) / len(results)
    
    return EvaluationResult(
        key="overall",
        score=avg_score,
        comment=f"Avg of {len(results)} evaluators: {', '.join(f'{r.key}={r.score:.2f}' for r in results)}",
    )


# ============================================================================
# All Evaluators (for LangSmith)
# ============================================================================

ALL_EVALUATORS = [
    agreement_evaluator,
    fairness_evaluator,
    efficiency_evaluator,
    protocol_evaluator,
    overall_evaluator,
]
