"""
Judge Agent
===========

Evaluates negotiation outcomes for quality.

This is a DETERMINISTIC judge (rule-based).
For LLM-as-judge, see the llm_judge module.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Dict, Any


class JudgmentCriteria(Enum):
    """Criteria for judging negotiations."""
    OUTCOME_FAIR = auto()       # Was the outcome fair to both parties?
    PROTOCOL_FOLLOWED = auto()  # Were message protocols followed?
    TURNS_EFFICIENT = auto()    # Was the negotiation efficient?
    POLICY_COMPLIANT = auto()   # Were coordination rules followed?


@dataclass
class Judgment:
    """A judge's assessment on one criterion."""
    criteria: JudgmentCriteria
    passed: bool
    score: float  # 0.0 to 1.0
    explanation: str


class NegotiationJudge:
    """
    Rule-based judge for evaluating negotiations.
    
    This is DETERMINISTIC - same input always gives same output.
    Use for testing and regression detection.
    """
    
    def __init__(
        self,
        max_acceptable_turns: int = 10,
        fairness_threshold: float = 0.3,  # Accept 30-70% split
    ):
        self.max_acceptable_turns = max_acceptable_turns
        self.fairness_threshold = fairness_threshold
    
    def judge_fairness(
        self,
        final_price: Optional[float],
        buyer_max: float,
        seller_min: float,
    ) -> Judgment:
        """
        Judge whether the outcome is fair.
        
        Fair = price is within acceptable range for both parties,
        and the surplus is split reasonably.
        """
        if final_price is None:
            return Judgment(
                criteria=JudgmentCriteria.OUTCOME_FAIR,
                passed=False,
                score=0.0,
                explanation="No agreement reached",
            )
        
        # Check valid range
        if final_price < seller_min or final_price > buyer_max:
            return Judgment(
                criteria=JudgmentCriteria.OUTCOME_FAIR,
                passed=False,
                score=0.0,
                explanation=f"Price ${final_price} outside valid range [${seller_min}, ${buyer_max}]",
            )
        
        # Calculate efficiency (how surplus was split)
        price_range = buyer_max - seller_min
        if price_range <= 0:
            return Judgment(
                criteria=JudgmentCriteria.OUTCOME_FAIR,
                passed=True,
                score=1.0,
                explanation="No negotiation range (price fixed)",
            )
        
        # 0 = buyer got everything, 1 = seller got everything
        efficiency = (final_price - seller_min) / price_range
        
        # Fair if within threshold of 50%
        fairness = 1.0 - abs(efficiency - 0.5) * 2
        passed = self.fairness_threshold <= efficiency <= (1 - self.fairness_threshold)
        
        return Judgment(
            criteria=JudgmentCriteria.OUTCOME_FAIR,
            passed=passed,
            score=fairness,
            explanation=f"Seller got {efficiency*100:.0f}% of surplus",
        )
    
    def judge_efficiency(
        self,
        turns: int,
        success: bool,
    ) -> Judgment:
        """Judge whether negotiation was efficient."""
        if not success:
            return Judgment(
                criteria=JudgmentCriteria.TURNS_EFFICIENT,
                passed=False,
                score=0.0,
                explanation=f"Failed after {turns} turns",
            )
        
        # Score based on how many turns used
        efficiency = max(0, 1 - turns / self.max_acceptable_turns)
        passed = turns <= self.max_acceptable_turns // 2
        
        return Judgment(
            criteria=JudgmentCriteria.TURNS_EFFICIENT,
            passed=passed,
            score=efficiency,
            explanation=f"Completed in {turns}/{self.max_acceptable_turns} turns",
        )
    
    def judge_protocol(
        self,
        messages: List[Dict[str, Any]],
    ) -> Judgment:
        """Judge whether protocol was followed."""
        issues = []
        
        expected_agent = "buyer"  # Buyer starts
        
        for i, msg in enumerate(messages):
            agent = msg.get("agent", "unknown")
            
            # Check turn order
            if agent != expected_agent:
                issues.append(f"Turn {i}: Expected {expected_agent}, got {agent}")
            
            # Alternate
            expected_agent = "seller" if expected_agent == "buyer" else "buyer"
        
        if issues:
            return Judgment(
                criteria=JudgmentCriteria.PROTOCOL_FOLLOWED,
                passed=False,
                score=1.0 - len(issues) / max(len(messages), 1),
                explanation=f"Protocol violations: {issues[0]}...",
            )
        
        return Judgment(
            criteria=JudgmentCriteria.PROTOCOL_FOLLOWED,
            passed=True,
            score=1.0,
            explanation="All messages followed protocol",
        )
    
    def evaluate(
        self,
        final_price: Optional[float],
        buyer_max: float,
        seller_min: float,
        turns: int,
        success: bool,
        messages: List[Dict[str, Any]],
    ) -> List[Judgment]:
        """
        Comprehensive evaluation of a negotiation.
        
        Returns judgments on all criteria.
        """
        return [
            self.judge_fairness(final_price, buyer_max, seller_min),
            self.judge_efficiency(turns, success),
            self.judge_protocol(messages),
        ]
    
    def overall_score(self, judgments: List[Judgment]) -> float:
        """Calculate overall score from judgments."""
        if not judgments:
            return 0.0
        return sum(j.score for j in judgments) / len(judgments)
    
    def summary(self, judgments: List[Judgment]) -> str:
        """Generate a summary of judgments."""
        lines = ["Evaluation Summary:", "-" * 40]
        
        for j in judgments:
            status = "✓" if j.passed else "✗"
            lines.append(f"  {status} {j.criteria.name}: {j.score:.2f} - {j.explanation}")
        
        overall = self.overall_score(judgments)
        lines.append("-" * 40)
        lines.append(f"  Overall Score: {overall:.2f}")
        
        return "\n".join(lines)
