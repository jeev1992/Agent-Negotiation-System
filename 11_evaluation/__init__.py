"""
11_evaluation - Quality Assessment Layer
=======================================

Question this layer answers:
"How good was the outcome?"

Two evaluation approaches:

1. Rule-based Judge (11_evaluation/judge.py):
   - Deterministic: same input → same score
   - Fast, no API calls
   - Good for unit tests and CI/CD
   
   ```python
   from 11_evaluation import NegotiationJudge
   judge = NegotiationJudge()
   judgments = judge.evaluate(final_price=400, ...)
   ```

2. LangSmith Experiments (11_evaluation/langsmith/):
   - Cloud-based dataset and experiments
   - Multiple evaluators with dashboards
   - Good for comparing strategies
   
   ```bash
   python -m 11_evaluation.langsmith.run_evaluation              # Local
   python -m 11_evaluation.langsmith.run_evaluation --upload     # Upload dataset
   python -m 11_evaluation.langsmith.run_evaluation --experiment # Run experiment
   ```
"""

from .judge import NegotiationJudge, Judgment, JudgmentCriteria

# LangSmith exports (optional - may not be installed)
try:
    from .langsmith import (
        NEGOTIATION_SCENARIOS,
        DATASET_NAME,
        ALL_EVALUATORS,
    )
except ImportError:
    NEGOTIATION_SCENARIOS = []
    DATASET_NAME = "negotiation-scenarios"
    ALL_EVALUATORS = []

__all__ = [
    # Rule-based judge
    "NegotiationJudge",
    "Judgment", 
    "JudgmentCriteria",
    # LangSmith
    "NEGOTIATION_SCENARIOS",
    "DATASET_NAME",
    "ALL_EVALUATORS",
]

# Aliases for compatibility
JudgeAgent = NegotiationJudge
NegotiationScore = Judgment

__all__ = ["NegotiationJudge", "Judgment", "JudgmentCriteria", "JudgeAgent", "NegotiationScore"]
