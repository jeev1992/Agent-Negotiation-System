# 05 - Agent Logic & Deterministic Strategies

## Purpose

Prevent "LLM-first" thinking. Most negotiation logic should be pure, deterministic functions that can be tested without any AI involvement.

---

## The Problem: Untestable AI Logic

When people hear "agents," they immediately think:

```python
def buyer_decide(context: str) -> str:
    """Let the LLM figure it out."""
    response = llm.chat(f"""
        You are a buyer. The seller said: {context}
        What do you do?
    """)
    return response  # Unpredictable, untestable, unexplainable
```

### Why This Is Wrong

1. **Non-deterministic**: Same input → different outputs
2. **Untestable**: Can't write unit tests for random behavior
3. **Unexplainable**: Why did it offer $350? "The LLM decided"
4. **Expensive**: Every decision costs API calls
5. **Slow**: Network round-trips for simple math

---

## The Solution: Deterministic First, AI Later

### The Principle

> **If you can write it as a pure function, don't use an LLM.**

```
┌─────────────────────────────────────────────────────────────────┐
│                    DECISION HIERARCHY                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 1: PURE FUNCTIONS (Always use)                          │
│  ─────────────────────────────────────                         │
│  • Calculate next offer price                                   │
│  • Check if price is acceptable                                 │
│  • Determine concession amount                                  │
│  • Apply negotiation strategy                                   │
│                                                                 │
│  Level 2: RULE-BASED LOGIC (Use when needed)                   │
│  ────────────────────────────────────────────                  │
│  • If price > max, reject                                       │
│  • If price < min, counter                                      │
│  • If turns > threshold, concede more                           │
│                                                                 │
│  Level 3: LLM (Use sparingly)                                  │
│  ────────────────────────────                                  │
│  • Generate human-readable messages                             │
│  • Handle unexpected situations                                 │
│  • Interpret ambiguous input (last resort)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Buyer Strategy: Pure Functions

```python
# 05_agents/buyer.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class BuyerConfig:
    """Buyer's constraints - known at start."""
    initial_offer: float    # First offer to make
    max_price: float        # Absolute maximum
    increment: float        # How much to raise each round
    concession_rate: float  # How quickly to approach max (0.0-1.0)


def calculate_next_offer(
    current_offer: float,
    max_price: float,
    increment: float,
    concession_rate: float,
    turn: int,
) -> float:
    """
    Pure function: Calculate next offer price.
    
    DETERMINISTIC: Same inputs always produce same output.
    TESTABLE: No external dependencies.
    EXPLAINABLE: Clear formula.
    """
    # Base increment
    base_raise = increment
    
    # Increase concession as turns progress
    urgency_factor = 1 + (turn * concession_rate)
    adjusted_raise = base_raise * urgency_factor
    
    # Calculate new offer
    new_offer = current_offer + adjusted_raise
    
    # Never exceed max
    return min(new_offer, max_price)


def should_accept(offer_price: float, max_price: float) -> bool:
    """
    Pure function: Should buyer accept this offer?
    
    TRIVIALLY TESTABLE:
    >>> should_accept(100, 150)
    True
    >>> should_accept(100, 50)
    False
    """
    return offer_price <= max_price


def buyer_strategy(
    config: BuyerConfig,
    seller_price: float | None,
    turn: int,
) -> dict:
    """
    Main strategy function - pure and deterministic.
    
    Returns a structured decision, not free text.
    """
    # First turn: make initial offer
    if seller_price is None:
        return {
            "type": "offer",
            "price": config.initial_offer,
            "reasoning": "Initial offer",
        }
    
    # Check if we should accept
    if should_accept(seller_price, config.max_price):
        return {
            "type": "accept",
            "price": seller_price,
            "reasoning": f"Price {seller_price} <= max {config.max_price}",
        }
    
    # Calculate next offer
    next_offer = calculate_next_offer(
        current_offer=seller_price,  # Start from their counter
        max_price=config.max_price,
        increment=config.increment,
        concession_rate=config.concession_rate,
        turn=turn,
    )
    
    # Check if we've hit our limit
    if next_offer >= config.max_price:
        return {
            "type": "final_offer",
            "price": config.max_price,
            "reasoning": f"Final offer at maximum {config.max_price}",
        }
    
    return {
        "type": "offer",
        "price": next_offer,
        "reasoning": f"Counter-offer: raised from {seller_price} to {next_offer}",
    }
```

---

## Seller Strategy: Pure Functions

```python
# 05_agents/seller.py

from dataclasses import dataclass

@dataclass
class SellerConfig:
    """Seller's constraints - known at start."""
    initial_price: float   # First asking price
    min_price: float       # Absolute minimum
    decrement: float       # How much to lower each round
    urgency_rate: float    # How quickly to approach min (0.0-1.0)


def calculate_counter_offer(
    current_price: float,
    min_price: float,
    decrement: float,
    urgency_rate: float,
    turn: int,
) -> float:
    """
    Pure function: Calculate seller's counter offer.
    
    DETERMINISTIC: Same inputs → same output.
    """
    # Base decrement
    base_drop = decrement
    
    # Increase concession as turns progress
    urgency_factor = 1 + (turn * urgency_rate)
    adjusted_drop = base_drop * urgency_factor
    
    # Calculate new price
    new_price = current_price - adjusted_drop
    
    # Never go below minimum
    return max(new_price, min_price)


def should_accept(offer_price: float, min_price: float) -> bool:
    """
    Pure function: Should seller accept this offer?
    """
    return offer_price >= min_price


def seller_strategy(
    config: SellerConfig,
    buyer_price: float | None,
    turn: int,
) -> dict:
    """
    Main strategy function - pure and deterministic.
    """
    # First turn: state initial asking price
    if buyer_price is None:
        return {
            "type": "ask",
            "price": config.initial_price,
            "reasoning": "Initial asking price",
        }
    
    # Check if we should accept
    if should_accept(buyer_price, config.min_price):
        return {
            "type": "accept",
            "price": buyer_price,
            "reasoning": f"Price {buyer_price} >= min {config.min_price}",
        }
    
    # Calculate counter offer
    counter = calculate_counter_offer(
        current_price=config.initial_price if turn == 1 else buyer_price,
        min_price=config.min_price,
        decrement=config.decrement,
        urgency_rate=config.urgency_rate,
        turn=turn,
    )
    
    # Check if we've hit our limit
    if counter <= config.min_price:
        return {
            "type": "final_offer",
            "price": config.min_price,
            "reasoning": f"Final offer at minimum {config.min_price}",
        }
    
    return {
        "type": "counter",
        "price": counter,
        "reasoning": f"Counter-offer: dropped to {counter}",
    }
```

---

## Unit Testing: The Proof

Because strategies are pure functions, we can test exhaustively:

```python
# tests/test_strategies.py

import pytest
from agents.buyer import BuyerConfig, buyer_strategy, calculate_next_offer
from agents.seller import SellerConfig, seller_strategy


class TestBuyerStrategy:
    """Test buyer behavior deterministically."""
    
    @pytest.fixture
    def config(self):
        return BuyerConfig(
            initial_offer=200,
            max_price=400,
            increment=50,
            concession_rate=0.1,
        )
    
    def test_initial_offer(self, config):
        """First turn should make initial offer."""
        result = buyer_strategy(config, seller_price=None, turn=1)
        
        assert result["type"] == "offer"
        assert result["price"] == 200  # config.initial_offer
    
    def test_accept_below_max(self, config):
        """Should accept price at or below max."""
        result = buyer_strategy(config, seller_price=350, turn=3)
        
        assert result["type"] == "accept"
        assert result["price"] == 350
    
    def test_counter_above_max(self, config):
        """Should counter if price above max."""
        result = buyer_strategy(config, seller_price=500, turn=2)
        
        assert result["type"] in ["offer", "final_offer"]
        assert result["price"] <= config.max_price
    
    def test_never_exceeds_max(self, config):
        """Offer should never exceed max price."""
        for turn in range(1, 20):
            result = buyer_strategy(config, seller_price=1000, turn=turn)
            assert result["price"] <= config.max_price


class TestSellerStrategy:
    """Test seller behavior deterministically."""
    
    @pytest.fixture
    def config(self):
        return SellerConfig(
            initial_price=500,
            min_price=300,
            decrement=30,
            urgency_rate=0.1,
        )
    
    def test_initial_price(self, config):
        """First turn should state asking price."""
        result = seller_strategy(config, buyer_price=None, turn=1)
        
        assert result["type"] == "ask"
        assert result["price"] == 500
    
    def test_accept_above_min(self, config):
        """Should accept price at or above min."""
        result = seller_strategy(config, buyer_price=350, turn=3)
        
        assert result["type"] == "accept"
        assert result["price"] == 350
    
    def test_never_below_min(self, config):
        """Counter should never go below min price."""
        for turn in range(1, 20):
            result = seller_strategy(config, buyer_price=100, turn=turn)
            assert result["price"] >= config.min_price


class TestNegotiationScenarios:
    """Test full negotiation scenarios."""
    
    def test_guaranteed_agreement(self):
        """When buyer max > seller min, should agree."""
        buyer_config = BuyerConfig(
            initial_offer=200,
            max_price=400,  # Max > seller min
            increment=50,
            concession_rate=0.1,
        )
        seller_config = SellerConfig(
            initial_price=500,
            min_price=300,  # Min < buyer max
            decrement=30,
            urgency_rate=0.1,
        )
        
        # Overlap exists: buyer can go to 400, seller can go to 300
        # They WILL meet somewhere in [300, 400]
        
        # Simulate negotiation
        buyer_price = None
        seller_price = None
        
        for turn in range(1, 20):
            # Seller turn
            seller_result = seller_strategy(seller_config, buyer_price, turn)
            if seller_result["type"] == "accept":
                assert 300 <= seller_result["price"] <= 400
                return  # Success!
            seller_price = seller_result["price"]
            
            # Buyer turn
            buyer_result = buyer_strategy(buyer_config, seller_price, turn)
            if buyer_result["type"] == "accept":
                assert 300 <= buyer_result["price"] <= 400
                return  # Success!
            buyer_price = buyer_result["price"]
        
        pytest.fail("Should have reached agreement")
    
    def test_impossible_agreement(self):
        """When buyer max < seller min, should fail."""
        buyer_config = BuyerConfig(
            initial_offer=50,
            max_price=100,  # Max < seller min
            increment=10,
            concession_rate=0.1,
        )
        seller_config = SellerConfig(
            initial_price=500,
            min_price=200,  # Min > buyer max
            decrement=30,
            urgency_rate=0.1,
        )
        
        # No overlap: buyer tops at 100, seller bottoms at 200
        # They can NEVER agree
        
        for turn in range(1, 100):
            seller_result = seller_strategy(seller_config, buyer_config.max_price, turn)
            buyer_result = buyer_strategy(buyer_config, seller_config.min_price, turn)
            
            # Neither should accept
            assert seller_result["type"] != "accept"
            assert buyer_result["type"] != "accept"
```

---

## Mental Model: Testable Code Is Debuggable Code

> **"If you can't test it deterministically, you can't debug it."**

| Property | Pure Function | LLM Call |
|----------|--------------|----------|
| Same input → same output | ✓ Yes | ✗ No |
| Unit testable | ✓ Yes | ✗ No |
| Explainable | ✓ Clear formula | ✗ "AI decided" |
| Fast | ✓ Microseconds | ✗ Seconds |
| Free | ✓ No API cost | ✗ $0.01+ per call |
| Debuggable | ✓ Print statements | ✗ Black box |

---

## When to Use LLM (Sparingly)

LLMs are appropriate for:

```python
def generate_message(decision: dict) -> str:
    """
    Use LLM to make the message sound natural.
    The DECISION is deterministic, only the WORDING is AI-generated.
    """
    if decision["type"] == "accept":
        # LLM generates friendly acceptance message
        return llm.chat(f"""
            Generate a friendly acceptance message for price ${decision['price']}.
            Keep it brief, one sentence.
        """)
    # ... etc
```

But the **decision** itself (`accept` at `$350`) is pure function output.

---

## Separation from Orchestration

Strategies are pure logic. Orchestration handles flow:

```
┌─────────────────────────────────────────────────────────────────┐
│  06_orchestration                                                │
│  "What runs next?"                                              │
│                                                                 │
│     buyer_node()                   seller_node()                │
│          │                              │                       │
│          ▼                              ▼                       │
│  ┌───────────────┐              ┌───────────────┐               │
│  │ buyer_strategy│              │seller_strategy│               │
│  │    (pure)     │              │    (pure)     │               │
│  └───────────────┘              └───────────────┘               │
│                                                                 │
│  Orchestration handles: turn order, state updates, termination  │
│  Strategies handle: what price to offer, when to accept         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Takeaway

> **Deterministic first. AI for the edges.**
>
> Your negotiation logic should be 95% pure functions and 5% LLM calls. If you can't explain why an agent made a decision, you can't fix it when it goes wrong.

---

## Code References

- [05_agents/buyer.py](../05_agents/buyer.py) - Buyer strategy implementation
- [05_agents/seller.py](../05_agents/seller.py) - Seller strategy implementation
- [tests/test_agents.py](../tests/test_agents.py) - Strategy unit tests

---

## Next Steps

1. Read `06_orchestration_langgraph.md` to see how strategies fit into flow control
2. Read `09_mcp_context.md` to see how agents get grounded data
3. Read `11_langsmith_evaluation.md` to see how strategies are evaluated
