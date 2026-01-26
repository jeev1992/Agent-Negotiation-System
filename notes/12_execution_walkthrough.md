# 12 - Putting It All Together (Execution Walkthrough)

## Purpose

Reinforce integration understanding by walking through one complete negotiation, showing how every layer contributes.

---

## The Scenario

```
BUYER:  Max willing to pay $400
SELLER: Min willing to accept $300

Overlap: $300-$400 (agreement is possible)
```

---

## Full Execution Timeline

```
TIME ─────────────────────────────────────────────────────────────────────────────►

T=0ms    STARTUP
         ├── python -m 10_runtime.runner --mode demo
         ├── [10_RUNTIME] Load config: buyer_max=400, seller_min=300
         ├── [10_RUNTIME] Initialize MCPServer
         ├── [10_RUNTIME] Initialize CoordinationPolicy
         └── [10_RUNTIME] Initialize LangSmith tracing

T=50ms   SESSION START
         └── [10_RUNTIME] run_session("demo_001")
             └── [06_ORCHESTRATION] create_negotiation_graph()

T=55ms   TURN 1: BUYER
         ├── [06_ORCHESTRATION] buyer_node(state)
         ├── [07_COORDINATION] policy.can_act("buyer", "negotiating") → True
         ├── [05_AGENTS] buyer_strategy(seller_price=None, turn=1)
         │   └── Returns: {type: "offer", price: 200.0}
         ├── [07_COORDINATION] policy.validate_action("buyer", "offer") → OK
         ├── [04_FSM] fsm.process_turn() → still NEGOTIATING
         ├── [OBSERVABILITY] trace: buyer_turn completed in 12ms
         └── State: {turn: 1, buyer_price: 200, status: "active"}

T=70ms   TURN 1: SELLER
         ├── [06_ORCHESTRATION] seller_node(state)
         ├── [07_COORDINATION] policy.can_act("seller", "negotiating") → True
         ├── [09_CONTEXT] mcp.get_pricing_rules()
         │   └── Returns: {min_price: 300, max_price: 600}
         ├── [09_CONTEXT] mcp.check_price_acceptable(200)
         │   └── Returns: {is_acceptable: False, shortfall: 100}
         ├── [05_AGENTS] seller_strategy(buyer_price=200, min_price=300)
         │   └── Returns: {type: "counter", price: 500.0}
         ├── [07_COORDINATION] policy.validate_action("seller", "counter") → OK
         ├── [04_FSM] fsm.process_turn() → still NEGOTIATING
         ├── [OBSERVABILITY] trace: seller_turn completed in 25ms
         └── State: {turn: 1, seller_price: 500, status: "active"}

T=100ms  TURN 2: BUYER
         ├── [06_ORCHESTRATION] router(state) → "continue"
         ├── [06_ORCHESTRATION] buyer_node(state)
         ├── [05_AGENTS] buyer_strategy(seller_price=500, turn=2)
         │   └── Logic: 500 > max(400), raise offer
         │   └── Returns: {type: "offer", price: 275.0}
         └── State: {turn: 2, buyer_price: 275, status: "active"}

T=120ms  TURN 2: SELLER
         ├── [09_CONTEXT] mcp.check_price_acceptable(275)
         │   └── Returns: {is_acceptable: False, shortfall: 25}
         ├── [05_AGENTS] seller_strategy(buyer_price=275)
         │   └── Logic: 275 < min(300), counter lower
         │   └── Returns: {type: "counter", price: 437.5}
         └── State: {turn: 2, seller_price: 437.5, status: "active"}

T=140ms  TURN 3: BUYER
         ├── [05_AGENTS] buyer_strategy(seller_price=437.5, turn=3)
         │   └── Logic: 437.5 > max(400), but getting closer
         │   └── Returns: {type: "offer", price: 340.0}
         └── State: {turn: 3, buyer_price: 340, status: "active"}

T=155ms  TURN 3: SELLER
         ├── [09_CONTEXT] mcp.check_price_acceptable(340)
         │   └── Returns: {is_acceptable: True}  ← ABOVE MIN!
         ├── [05_AGENTS] seller_strategy(buyer_price=340)
         │   └── Logic: 340 >= min(300), ACCEPT!
         │   └── Returns: {type: "accept", price: 340.0}
         ├── [04_FSM] fsm.accept(340) → transitions to AGREED
         ├── [OBSERVABILITY] trace: negotiation completed
         └── State: {turn: 3, agreed_price: 340, status: "agreed"}

T=160ms  TERMINATION
         ├── [06_ORCHESTRATION] router(state) → "done" (terminal state)
         └── [06_ORCHESTRATION] graph returns final state

T=165ms  EVALUATION
         ├── [11_EVALUATION] judge.evaluate(buyer_max=400, seller_min=300, result)
         │   ├── agreed: True ✓
         │   ├── fairness: 0.80 (price 340, midpoint 350)
         │   ├── efficiency: 0.70 (3 turns)
         │   └── score: 0.85 PASSED
         └── [OBSERVABILITY] evaluation logged to LangSmith

T=170ms  SHUTDOWN
         ├── [10_RUNTIME] runtime.shutdown()
         ├── [OBSERVABILITY] flush_traces()
         └── [10_RUNTIME] Print summary

TOTAL DURATION: 170ms
```

---

## Message-by-Message Walkthrough

### Message 1: Buyer's Opening Offer

```python
# 05_agents/buyer.py
buyer_strategy(seller_price=None, turn=1)

# Internal logic:
# - No seller price yet → make initial offer
# - Initial offer = 50% of max = $200

return {
    "type": "offer",
    "price": 200.0,
    "reasoning": "Initial offer at 50% of budget"
}
```

**State after:**
```python
{
    "messages": [{"sender": "buyer", "type": "offer", "price": 200}],
    "buyer_price": 200,
    "seller_price": None,
    "turn": 1,
    "status": "active"
}
```

### Message 2: Seller's Counter

```python
# 05_agents/seller.py
seller_strategy(buyer_price=200, turn=1, min_price=300)

# Internal logic:
# - 200 < 300 (min), cannot accept
# - Counter at initial asking price $500

return {
    "type": "counter",
    "price": 500.0,
    "reasoning": "Below minimum, countering high"
}
```

**State after:**
```python
{
    "messages": [
        {"sender": "buyer", "type": "offer", "price": 200},
        {"sender": "seller", "type": "counter", "price": 500}
    ],
    "buyer_price": 200,
    "seller_price": 500,
    "turn": 1,
    "status": "active"
}
```

### Messages 3-4: Continued Negotiation

| Turn | Sender | Type | Price | Logic |
|------|--------|------|-------|-------|
| 2 | Buyer | offer | $275 | 500 > max, raise by increment |
| 2 | Seller | counter | $437.50 | 275 < min, lower by decrement |
| 3 | Buyer | offer | $340 | Still below seller, keep raising |
| 3 | Seller | **accept** | $340 | **340 >= 300 (min), ACCEPT!** |

### Message 6: Acceptance

```python
# 05_agents/seller.py
seller_strategy(buyer_price=340, turn=3, min_price=300)

# Internal logic:
# - 340 >= 300 (min), CAN ACCEPT!
# - Accept immediately

return {
    "type": "accept",
    "price": 340.0,
    "reasoning": "Price meets minimum requirement"
}

# 04_fsm/state_machine.py
fsm.accept(340)
# State transitions: NEGOTIATING → AGREED (terminal)
```

---

## State Evolution

```
Turn 0 (Initial)           Turn 1                    Turn 2                    Turn 3 (Final)
───────────────────────────────────────────────────────────────────────────────────────────────

messages: []               messages: [B:200, S:500]  messages: [..., B:275,   messages: [..., B:340,
buyer_price: null          buyer_price: 200          S:437.5]                  S:accept:340]
seller_price: null         seller_price: 500         buyer_price: 275          agreed_price: 340
turn: 0                    turn: 1                   seller_price: 437.5       turn: 3
status: active             status: active            turn: 2                   status: AGREED
                                                     status: active
```

---

## Layer Responsibility Summary

| Layer | What It Did | How Many Times |
|-------|-------------|----------------|
| **10_RUNTIME** | Started system, ran session, shut down | 1 |
| **07_COORDINATION** | Validated 6 actions, enforced turns | 6 |
| **08_TRANSPORT** | (In-memory, implicit in state passing) | N/A |
| **06_ORCHESTRATION** | Routed between nodes, managed state | 7 calls |
| **05_AGENTS** | Made decisions (3 buyer, 3 seller) | 6 |
| **09_CONTEXT** | Provided pricing rules, checked prices | 3 |
| **04_FSM** | Checked termination, transitioned to AGREED | 6 checks |
| **OBSERVABILITY** | Traced all calls | Full session |
| **11_EVALUATION** | Scored final result | 1 |

---

## Mental Model: Each Layer Answers One Question

```
TURN 3, SELLER'S DECISION:

┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Q: "What runs next?"                                           │
│  A: 06_ORCHESTRATION → seller_node                              │
│                                                                 │
│  Q: "Is seller allowed to act?"                                 │
│  A: 07_COORDINATION → Yes, it's seller's turn                   │
│                                                                 │
│  Q: "What's the real minimum price?"                            │
│  A: 09_CONTEXT (MCP) → $300                                     │
│                                                                 │
│  Q: "Is $340 acceptable?"                                       │
│  A: 09_CONTEXT (MCP) → Yes, 340 >= 300                          │
│                                                                 │
│  Q: "What should seller do?"                                    │
│  A: 05_AGENTS → Accept at $340                                  │
│                                                                 │
│  Q: "Is 'accept' allowed for seller?"                           │
│  A: 07_COORDINATION → Yes                                       │
│                                                                 │
│  Q: "Does accepting end negotiation?"                           │
│  A: 04_FSM → Yes, transition to AGREED (terminal)               │
│                                                                 │
│  Q: "What happened?"                                            │
│  A: OBSERVABILITY → Logged everything                          │
│                                                                 │
│  Q: "How good was this?"                                        │
│  A: 11_EVALUATION → Score 0.85, PASSED                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## What Would Have Happened Differently?

### If buyer_max was $250 (no overlap):

```
Turn 3: Buyer offers $250 (max)
Turn 3: Seller counters $300 (min)
Turn 4: Buyer offers $250 (stuck at max)
Turn 4: Seller counters $300 (stuck at min)
...
Turn 10: FSM → max_turns reached → FAILED
```

### If policy was disabled:

```
Turn 1: Buyer offers $200
Turn 1: Buyer offers $300 (ILLEGAL - consecutive!)
Turn 1: Buyer offers $400 (ILLEGAL!)
# System corrupted, no fairness
```

### If MCP was unavailable:

```
Turn 1: Seller needs min_price
Turn 1: MCP call fails
Turn 1: Seller refuses to act → "Cannot verify pricing"
# Graceful degradation, not hallucination
```

---

## Key Takeaway

> **Each layer answered ONE question. Together they formed a working system.**
>
> The negotiation succeeded not because any single layer was smart, but because each layer did its job correctly and passed control to the next.

---

## Code References

- Run this yourself: `python -m 10_runtime.runner --mode demo`
- View traces: Check LangSmith dashboard
- See evaluation: `python -m 11_evaluation.langsmith.run_evaluation --local`

---

## Next Steps

1. Read `13_what_breaks.md` to see what fails without each layer
2. Try modifying `config/negotiation.yaml` and re-running
3. Add your own scenarios to `11_evaluation/langsmith/dataset.py`
