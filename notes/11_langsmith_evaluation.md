# 11 - Observability & Evaluation: LangSmith (Framework Deep Dive)

## Purpose

Prove correctness and quality. LangSmith provides tracing to see what happened and evaluation to measure how good it was.

---

## The Problem: Logs Aren't Enough

Traditional logging:

```python
logger.info("Buyer made offer")
logger.info("Seller responded")
logger.info("Negotiation complete")

# Questions logs CAN'T answer:
# - What was the exact offer amount?
# - How long did seller take to respond?
# - What was the full chain of decisions?
# - Is this outcome better than yesterday's?
```

**Logs tell you THAT something happened. Traces tell you WHAT happened.**

---

## Tracing vs Metrics vs Logs

| Concept | What It Shows | Example |
|---------|---------------|---------|
| **Logs** | Events occurred | "Buyer made offer" |
| **Metrics** | Aggregated numbers | "95th percentile latency: 200ms" |
| **Traces** | Full execution path | "Buyer→Strategy→MCP→Decision→Message" |

---

## LangSmith Mental Model

> **"LangSmith is the black box flight recorder for agents."**

Like an airplane's flight recorder:
- Records everything that happens
- Enables post-hoc analysis
- Helps understand failures
- Provides evidence for improvement

```
┌─────────────────────────────────────────────────────────────────┐
│                      LANGSMITH                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  TRACING: What happened?                                │    │
│  │                                                         │    │
│  │  Session: abc123                                        │    │
│  │  ├── buyer_node (120ms)                                 │    │
│  │  │   ├── buyer_strategy (5ms)                           │    │
│  │  │   └── returned: {type: "offer", price: 300}          │    │
│  │  ├── seller_node (2100ms)                               │    │
│  │  │   ├── mcp.get_pricing_rules (10ms)                   │    │
│  │  │   ├── seller_strategy (8ms)                          │    │
│  │  │   └── returned: {type: "counter", price: 450}        │    │
│  │  └── ... 4 more turns ...                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  EVALUATION: How good was it?                           │    │
│  │                                                         │    │
│  │  Dataset: negotiation_scenarios (10 examples)           │    │
│  │  ├── Scenario 1: Easy overlap     → Score: 0.95         │    │
│  │  ├── Scenario 2: Tight margin     → Score: 0.82         │    │
│  │  ├── Scenario 3: No overlap       → Score: 0.70         │    │
│  │  └── Average: 0.82                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tracing Implementation

```python
# observability/tracer.py

from langsmith import Client, traceable
from datetime import datetime
from typing import Any
import os

# Initialize LangSmith client
client = Client(
    api_key=os.environ.get("LANGSMITH_API_KEY"),
)


@traceable(name="negotiation_session")
def trace_session(session_id: str, func, *args, **kwargs):
    """Wrap a session in a trace."""
    return func(*args, **kwargs)


@traceable(name="buyer_turn")
def trace_buyer_turn(turn: int, state: dict) -> dict:
    """Trace a buyer's turn."""
    from 05_agents.buyer import buyer_strategy
    
    result = buyer_strategy(
        seller_price=state.get("seller_price"),
        turn=turn,
    )
    
    return result


@traceable(name="seller_turn")
def trace_seller_turn(turn: int, state: dict, mcp) -> dict:
    """Trace a seller's turn."""
    from 05_agents.seller import seller_strategy
    
    # MCP call is automatically traced
    rules = mcp.get_pricing_rules()
    
    result = seller_strategy(
        buyer_price=state.get("buyer_price"),
        turn=turn,
        min_price=rules["min_price"],
    )
    
    return result


def init_tracing():
    """Initialize tracing at startup."""
    print("[Tracing] LangSmith tracing enabled")


def flush_traces():
    """Flush pending traces at shutdown."""
    print("[Tracing] Flushing traces to LangSmith")
```

---

## Trace Example (Text Representation)

```
TRACE: negotiation_session (session_id: demo_001)
│
├── START: 2024-01-15T10:30:00.000Z
│
├── buyer_turn (turn: 1)
│   ├── input: {seller_price: null, turn: 1}
│   ├── duration: 5ms
│   └── output: {type: "offer", price: 200.0}
│
├── seller_turn (turn: 1)
│   ├── input: {buyer_price: 200.0, turn: 1}
│   ├── mcp.get_pricing_rules
│   │   ├── duration: 2ms
│   │   └── output: {min_price: 300, max_price: 600}
│   ├── duration: 15ms
│   └── output: {type: "counter", price: 500.0}
│
├── buyer_turn (turn: 2)
│   ├── input: {seller_price: 500.0, turn: 2}
│   ├── duration: 4ms
│   └── output: {type: "offer", price: 275.0}
│
├── seller_turn (turn: 2)
│   ├── duration: 12ms
│   └── output: {type: "counter", price: 437.5}
│
├── buyer_turn (turn: 3)
│   ├── duration: 4ms
│   └── output: {type: "offer", price: 340.0}
│
├── seller_turn (turn: 3)
│   ├── duration: 10ms
│   └── output: {type: "accept", price: 340.0}
│
├── END: 2024-01-15T10:30:00.150Z
│
└── SUMMARY:
    ├── total_duration: 150ms
    ├── turns: 3
    ├── result: agreed
    └── final_price: 340.0
```

---

## Evaluation: Judge Agents

### Why Judge Agents?

Human evaluation doesn't scale. Automated evaluation with rules:

```python
# 11_evaluation/judge.py

from dataclasses import dataclass
from typing import Literal


@dataclass
class EvaluationResult:
    """Result of evaluating a negotiation."""
    score: float  # 0.0 to 1.0
    passed: bool  # score >= threshold
    metrics: dict
    feedback: str


class NegotiationJudge:
    """
    Rule-based judge for negotiation outcomes.
    
    Deterministic: same input → same score.
    """
    
    def evaluate(
        self,
        buyer_max: float,
        seller_min: float,
        result: dict,
    ) -> EvaluationResult:
        """Evaluate a negotiation result."""
        
        metrics = {}
        
        # Metric 1: Agreement reached?
        agreed = result.get("status") == "agreed"
        metrics["agreed"] = agreed
        
        # Metric 2: Price fairness
        if agreed:
            price = result["agreed_price"]
            midpoint = (buyer_max + seller_min) / 2
            
            # How close to midpoint? (1.0 = exactly fair)
            max_deviation = (buyer_max - seller_min) / 2
            actual_deviation = abs(price - midpoint)
            fairness = 1.0 - (actual_deviation / max_deviation) if max_deviation > 0 else 1.0
            metrics["fairness"] = fairness
        else:
            metrics["fairness"] = 0.0
        
        # Metric 3: Efficiency (fewer turns = better)
        turns = result.get("turns", 10)
        efficiency = max(0, 1.0 - (turns / 10))  # 10 turns = 0, 1 turn = 0.9
        metrics["efficiency"] = efficiency
        
        # Metric 4: Within bounds?
        if agreed:
            price = result["agreed_price"]
            within_bounds = seller_min <= price <= buyer_max
            metrics["within_bounds"] = within_bounds
        else:
            metrics["within_bounds"] = True  # N/A
        
        # Overall score
        if not agreed and buyer_max >= seller_min:
            # Should have agreed but didn't
            score = 0.3
            feedback = "Failed to reach agreement despite overlap"
        elif agreed:
            score = (
                0.4 * metrics["fairness"] +
                0.3 * metrics["efficiency"] +
                0.3 * (1.0 if metrics["within_bounds"] else 0.0)
            )
            feedback = f"Agreed at ${result['agreed_price']:.2f}, fairness={metrics['fairness']:.2f}"
        else:
            # No overlap - correct to fail
            score = 0.7
            feedback = "Correctly identified no viable agreement"
        
        return EvaluationResult(
            score=score,
            passed=score >= 0.7,
            metrics=metrics,
            feedback=feedback,
        )
```

---

## Batch Evaluation with Datasets

```python
# 11_evaluation/langsmith/dataset.py

NEGOTIATION_SCENARIOS = [
    {
        "id": "easy_overlap",
        "buyer_max": 500,
        "seller_min": 300,
        "expected": "agreed",
        "description": "Large overlap - should always agree",
    },
    {
        "id": "tight_margin",
        "buyer_max": 320,
        "seller_min": 300,
        "expected": "agreed",
        "description": "Small overlap - should agree but tight",
    },
    {
        "id": "no_overlap",
        "buyer_max": 200,
        "seller_min": 300,
        "expected": "failed",
        "description": "No overlap - should fail gracefully",
    },
    {
        "id": "exact_match",
        "buyer_max": 300,
        "seller_min": 300,
        "expected": "agreed",
        "description": "Exact boundary - edge case",
    },
    {
        "id": "large_gap",
        "buyer_max": 1000,
        "seller_min": 100,
        "expected": "agreed",
        "description": "Large gap - test efficiency",
    },
]


def create_dataset(client):
    """Create dataset in LangSmith."""
    dataset = client.create_dataset(
        "negotiation_scenarios",
        description="Test scenarios for negotiation system",
    )
    
    for scenario in NEGOTIATION_SCENARIOS:
        client.create_example(
            dataset_id=dataset.id,
            inputs={
                "buyer_max": scenario["buyer_max"],
                "seller_min": scenario["seller_min"],
            },
            outputs={
                "expected_outcome": scenario["expected"],
            },
        )
    
    return dataset
```

---

## Running Experiments

```python
# 11_evaluation/langsmith/run_evaluation.py

from langsmith import Client
from langsmith.evaluation import evaluate

def run_negotiation(inputs: dict) -> dict:
    """Run a negotiation with given inputs."""
    from 10_runtime.runner import NegotiationRuntime, RuntimeConfig
    
    config = RuntimeConfig(
        mode="demo",
        buyer_max=inputs["buyer_max"],
        seller_min=inputs["seller_min"],
        max_turns=10,
    )
    
    runtime = NegotiationRuntime(config)
    runtime.initialize()
    result = runtime.run_session("eval")
    runtime.shutdown()
    
    return result


def outcome_evaluator(run, example) -> dict:
    """Evaluate if outcome matches expected."""
    expected = example.outputs["expected_outcome"]
    actual = run.outputs.get("status", "unknown")
    
    return {
        "key": "correct_outcome",
        "score": 1.0 if actual == expected else 0.0,
    }


def fairness_evaluator(run, example) -> dict:
    """Evaluate price fairness."""
    if run.outputs.get("status") != "agreed":
        return {"key": "fairness", "score": 0.0}
    
    buyer_max = example.inputs["buyer_max"]
    seller_min = example.inputs["seller_min"]
    price = run.outputs["agreed_price"]
    
    midpoint = (buyer_max + seller_min) / 2
    deviation = abs(price - midpoint)
    max_dev = (buyer_max - seller_min) / 2
    
    fairness = 1.0 - (deviation / max_dev) if max_dev > 0 else 1.0
    
    return {"key": "fairness", "score": fairness}


def run_experiment():
    """Run full evaluation experiment."""
    client = Client()
    
    results = evaluate(
        run_negotiation,
        data="negotiation_scenarios",
        evaluators=[
            outcome_evaluator,
            fairness_evaluator,
        ],
        experiment_prefix="negotiation_v1",
    )
    
    print(f"\nExperiment: {results.experiment_name}")
    print(f"Scenarios: {len(results.results)}")
    print(f"Average score: {results.aggregate_metrics['correct_outcome']:.2f}")
```

---

## Score Comparisons

```
┌─────────────────────────────────────────────────────────────────┐
│           EXPERIMENT COMPARISON: v1 vs v2                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Scenario          │  v1 Score  │  v2 Score  │  Change          │
│  ──────────────────┼────────────┼────────────┼────────────────  │
│  easy_overlap      │    0.92    │    0.95    │    +0.03 ✓       │
│  tight_margin      │    0.78    │    0.85    │    +0.07 ✓       │
│  no_overlap        │    0.70    │    0.70    │     0.00 =       │
│  exact_match       │    0.65    │    0.82    │    +0.17 ✓       │
│  large_gap         │    0.88    │    0.91    │    +0.03 ✓       │
│  ──────────────────┼────────────┼────────────┼────────────────  │
│  AVERAGE           │    0.79    │    0.85    │    +0.06 ✓       │
│                                                                 │
│  Verdict: v2 is better across all scenarios                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## What LangSmith Does NOT Do

1. **Affect behavior**: LangSmith observes, doesn't intervene
2. **Store business data**: Only traces and metrics
3. **Replace testing**: Supplements, doesn't replace unit tests
4. **Make decisions**: Provides data for humans to decide

---

## Integration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  10_runtime                                                      │
│  │                                                              │
│  └── run_session()                                              │
│       │                                                         │
│       ├── @traceable ──────────────────► observability        │
│       │   Records: inputs, outputs,       (LangSmith)           │
│       │   duration, errors                                      │
│       │                                                         │
│       └── result ──────────────────────► 11_evaluation           │
│           │                               (Judge)               │
│           │                                                     │
│           └── score, feedback ──────────► LangSmith             │
│               Stored as experiment        (Comparison)          │
│               results                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Takeaway

> **LangSmith is your flight recorder. It doesn't fly the plane; it tells you what happened.**
>
> Tracing shows execution. Evaluation shows quality. Together they prove your system works—or tell you exactly how it doesn't.

---

## Code References

- [11_evaluation/judge.py](../11_evaluation/judge.py) - Judge implementation
- [11_evaluation/langsmith/](../11_evaluation/langsmith/) - LangSmith integration
- [10_runtime/runner.py](../10_runtime/runner.py) - Runtime with tracing support

---

## Next Steps

1. Read `12_execution_walkthrough.md` for full traced example
2. Read `13_what_breaks.md` to see observability gaps
3. Run `python -m 11_evaluation.langsmith.run_evaluation --local`
