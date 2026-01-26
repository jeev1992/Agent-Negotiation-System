# 13 - What Breaks If You Remove X (Failure Analysis)

## Purpose

Deepen intuition via subtraction. By understanding what each layer prevents, you understand why it exists.

---

## Mental Model

> **"Architecture exists to prevent specific failures."**

Every layer in this system exists because something BREAKS without it. Not "might break" or "could be suboptimal"—actually BREAKS.

---

## Failure Summary Table

| Remove This | What Breaks | Failure Mode |
|-------------|-------------|--------------|
| **FSM** | Infinite loops | System never terminates |
| **Coordination (ACP)** | Illegal actions | Agents cheat, spam, corrupt state |
| **Protocol** | Ambiguous messages | Misinterpretation, silent failures |
| **Transport** | No distribution | Can't scale, can't separate |
| **MCP** | Hallucination | Agents make up data |
| **Orchestration** | Scattered flow | Spaghetti code, untraceable |
| **Runtime (ADK)** | No lifecycle | Can't start, config, or stop |
| **Observability** | Blind debugging | "It just stopped working" |
| **Evaluation** | Unknown quality | No idea if it's good or bad |

---

## 1. No FSM → Infinite Loops

### What FSM Does
- Defines terminal states (AGREED, FAILED)
- Enforces max_turns limit
- Guarantees termination

### Without FSM

```python
# Baseline code without FSM
while True:
    buyer_msg = buyer.respond(seller_msg)
    if "DEAL" in buyer_msg:  # String matching!
        break
    seller_msg = seller.respond(buyer_msg)
    if "DEAL" in seller_msg:
        break
    # WHAT IF THEY NEVER SAY "DEAL"?
```

### The Failure

```
Buyer max: $100
Seller min: $200

Turn 1: Buyer offers $50
Turn 2: Seller counters $250
Turn 3: Buyer offers $55
Turn 4: Seller counters $245
...
Turn 100: Buyer offers $100 (stuck at max)
Turn 101: Seller counters $200 (stuck at min)
Turn 102: (continues forever)
Turn 103: (continues forever)
...
Turn ∞: STILL RUNNING
```

**Result**: System never terminates. API costs grow unbounded. Users wait forever.

### The Fix (FSM)

```python
# With FSM
fsm = NegotiationFSM(max_turns=10)

while fsm.is_active:  # GUARANTEED to become False
    buyer_action = buyer.decide()
    if buyer_action["type"] == "accept":
        fsm.accept(buyer_action["price"])  # → AGREED (terminal)
    else:
        fsm.process_turn()  # Increments counter, may → FAILED
```

---

## 2. No ACP → Illegal Actions

### What ACP Does
- Enforces turn-taking
- Limits allowed actions per role
- Validates action parameters

### Without ACP

```python
# No coordination policy
def seller_turn(state):
    # Seller can do ANYTHING
    return {"type": "offer", "price": -1000}  # ILLEGAL
    # Or
    return {"type": "hack", "steal": "buyer_wallet"}  # ???
```

### The Failure

```
Turn 1: Buyer offers $300
Turn 1: Seller responds
Turn 1: Buyer responds again (ILLEGAL - not their turn!)
Turn 1: Buyer responds again
Turn 1: Buyer responds again
Turn 1: Buyer offers $0 (ILLEGAL - below min)
Turn 2: Seller counters with -$500 (ILLEGAL - negative)

State: CORRUPTED
Trust: ZERO
```

### The Fix (ACP)

```python
# With coordination policy
violation = policy.validate_action(
    agent="buyer",
    action="offer",
    state="negotiating",
    price=300,
)

if violation:
    raise PolicyViolationError(violation.reason)
    # "buyer cannot act twice in a row"
    # "price must be positive"
```

---

## 3. No Protocol → Ambiguous Messages

### What Protocol Does
- Defines message schemas
- Enables validation
- Eliminates parsing ambiguity

### Without Protocol

```python
# Free text messages
seller_message = "I could do somewhere between $300 and $400, maybe $350?"

# Buyer tries to parse
price = extract_price(seller_message)  
# Returns: $300? $400? $350? WHO KNOWS
```

### The Failure

```
Seller: "Not $500, but I could go to $400"
Buyer extracts: $500 (WRONG - first number)
Buyer thinks: "Seller wants $500, that's too high"
Buyer: "I can't do $500"
Seller: "I said $400!"
Buyer: "You said $500"
(Negotiation fails due to miscommunication)
```

### The Fix (Protocol)

```python
# Structured messages
@dataclass
class Counter:
    type: Literal["counter"] = "counter"
    price: float  # Unambiguous
    message: str  # Optional human text

seller_response = Counter(price=400.0, message="Best I can do")
# Buyer reads: seller_response.price → 400.0 (EXACT)
```

---

## 4. No Transport → No Distribution

### What Transport Does
- Moves messages between processes/machines
- Handles timeouts, retries, failures
- Enables scaling

### Without Transport

```python
# Everything in one function
def negotiate():
    buyer = Buyer()
    seller = Seller()
    
    # Direct function calls - no separation
    result = seller.respond(buyer.offer())
    
    # PROBLEM: What if seller is on different machine?
    # PROBLEM: What if seller takes 30 seconds?
    # PROBLEM: What if network fails?
```

### The Failure

```
# Trying to scale
Server 1: Running buyer
Server 2: Running seller

# Without transport:
buyer.send_to_seller(offer)  # HOW?
# No mechanism to cross process boundary
# No way to handle timeout
# No way to retry on failure
```

### The Fix (Transport)

```python
# With transport layer
channel = WebSocketChannel("ws://server2:8080")
channel.send(recipient="seller", payload=offer, timeout=30)

# Transport handles:
# - Serialization
# - Network delivery
# - Timeout (30s)
# - Retry on failure
```

---

## 5. No MCP → Hallucination

### What MCP Does
- Provides grounded data from real sources
- Prevents agents from making up facts
- Single source of truth

### Without MCP

```python
# Seller without grounding
def seller_decide(buyer_offer):
    # Where does min_price come from?
    min_price = 300  # HARDCODED - what if it changed?
    
    # Or worse, ask the LLM
    min_price = llm.chat("What's a good minimum price?")
    # LLM: "I think $250 is fair" - HALLUCINATED!
```

### The Failure

```
Real business rule: min_price = $350 (updated yesterday)
Hardcoded value: min_price = $300 (stale)

Seller accepts $320 thinking it's above minimum
Business loses $30 per sale
Seller has no idea they're violating rules
```

### The Fix (MCP)

```python
# With MCP
rules = mcp.get_pricing_rules()  # From real database
min_price = rules["min_price"]   # Always current: $350

if buyer_offer < min_price:
    counter(min_price)  # Correct behavior
```

---

## 6. No Orchestration → Spaghetti Code

### What Orchestration Does
- Explicit flow control
- Visual graph structure
- State management
- Checkpointing

### Without Orchestration

```python
# Spaghetti negotiation
def negotiate():
    state = {}
    while True:
        if state.get("phase") == "buyer":
            result = buyer_logic(state)
            if result == "done":
                break
            state["phase"] = "seller"
        elif state.get("phase") == "seller":
            result = seller_logic(state)
            if result == "done":
                break
            state["phase"] = "buyer"
        # Where's the state schema?
        # Where's error handling?
        # How do you debug this?
```

### The Failure

```
Bug report: "Negotiation stuck after turn 7"

Developer: "Let me check the logs"
Logs: "buyer_logic called, seller_logic called, buyer_logic called..."
Developer: "What was the state at turn 7?"
Logs: (no state captured)
Developer: "How do I reproduce this?"
(impossible without explicit state management)
```

### The Fix (Orchestration)

```python
# With LangGraph
graph = StateGraph(NegotiationState)
graph.add_node("buyer", buyer_node)
graph.add_node("seller", seller_node)
graph.add_edge("buyer", "seller")
graph.add_conditional_edges("seller", router, {...})

# Benefits:
# - Visual graph structure
# - Explicit state schema
# - Automatic tracing
# - Can checkpoint and resume
```

---

## 7. No ADK → No Production Story

### What ADK Does
- Application lifecycle (init → run → shutdown)
- Configuration management
- Execution modes
- Graceful error handling

### Without ADK

```python
# No runtime structure
if __name__ == "__main__":
    # How do I configure this?
    buyer_max = 400  # Hardcoded
    
    # How do I run different modes?
    negotiate()  # One mode only
    
    # How do I clean up?
    # (nothing)
    
    # How do I handle errors?
    # (crashes)
```

### The Failure

```
Production deployment:
1. How do I set buyer_max per environment? → Can't
2. How do I run batch evaluation? → Can't
3. How do I gracefully shutdown? → Ctrl+C and pray
4. How do I integrate with monitoring? → No hooks
5. How do I manage multiple sessions? → Manual
```

### The Fix (ADK)

```python
# With runtime
runtime = NegotiationRuntime(config)
try:
    runtime.initialize()  # Setup hooks
    runtime.run_session() # Managed execution
finally:
    runtime.shutdown()    # Guaranteed cleanup

# Modes:
# --mode demo (single session, verbose)
# --mode batch (multiple sessions, metrics)
# --mode production (full monitoring)
```

---

## 8. No Observability → Blind System

### What Observability Does
- Records execution traces
- Captures timing, inputs, outputs
- Enables post-hoc debugging

### Without Observability

```python
# No tracing
def negotiate():
    # Stuff happens
    result = do_negotiation()
    return result
    # What happened inside?
    # How long did each step take?
    # What were the intermediate values?
    # ¯\_(ツ)_/¯
```

### The Failure

```
User: "The negotiation failed"
Developer: "What happened?"
User: "I don't know, it just said 'failed'"
Developer: "What were the offers?"
User: "I don't know"
Developer: "What turn did it fail on?"
User: "I don't know"
Developer: "..." (starts adding print statements)
```

### The Fix (Observability)

```python
# With LangSmith tracing
@traceable(name="negotiation")
def negotiate():
    ...

# After failure:
# 1. Open LangSmith dashboard
# 2. Find session by ID
# 3. See every call, every input, every output
# 4. Identify exact point of failure
# 5. Fix with confidence
```

---

## 9. No Evaluation → Unknown Quality

### What Evaluation Does
- Measures outcome quality
- Compares versions
- Proves correctness

### Without Evaluation

```python
# Ship and pray
def negotiate():
    result = do_negotiation()
    print(f"Done: {result}")
    # Is this good?
    # Better than yesterday's version?
    # Would it pass QA?
    # WHO KNOWS
```

### The Failure

```
v1.0: Ships to production
v1.1: "Improved" negotiation logic
v1.2: "Fixed" edge cases

Actual results:
v1.0: 85% deal rate, $340 avg price
v1.1: 72% deal rate, $310 avg price (WORSE!)
v1.2: 68% deal rate, $290 avg price (EVEN WORSE!)

But nobody measured, so nobody noticed.
Lost revenue: $50,000/month
```

### The Fix (Evaluation)

```python
# With evaluation framework
results = evaluate(
    target=negotiate,
    dataset="negotiation_scenarios",
    evaluators=[agreement_rate, fairness, efficiency],
)

# v1.0: score 0.85
# v1.1: score 0.72 ← REGRESSION DETECTED, DON'T SHIP
# v1.2: score 0.68 ← REGRESSION DETECTED, DON'T SHIP
```

---

## Summary: Architecture as Failure Prevention

```
┌─────────────────────────────────────────────────────────────────┐
│              WHAT EACH LAYER PREVENTS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  04_FSM         │  Infinite loops, unbounded execution          │
│  07_COORDINATION│  Illegal actions, turn violations             │
│  03_PROTOCOL    │  Message ambiguity, parsing failures          │
│  08_TRANSPORT   │  Single-process limitation                    │
│  09_CONTEXT     │  Hallucination, stale data                    │
│  06_ORCHESTRATION│  Spaghetti flow, state chaos                  │
│  10_RUNTIME     │  No lifecycle, no config, no modes            │
│  (observability)│  Blind debugging, mystery failures            │
│  11_EVALUATION  │  Unknown quality, silent regressions          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Takeaway

> **Architecture exists to prevent specific failures.**
>
> If you can't articulate what BREAKS without a component, you don't understand why it exists. Every layer in this system has a failure it prevents. That's why the layer is there.

---

## Exercise: Try Removing Layers

1. Remove FSM's max_turns check → Watch infinite loop
2. Remove policy validation → Watch illegal actions
3. Remove MCP → Watch hardcoded values diverge
4. Remove tracing → Try debugging a failure

The best way to understand architecture is to break it intentionally.

---

## Final Thought

```
"Why do we have 11 modules?"

Because we have 11 different concerns to address.

Each module exists to prevent ONE class of failure.
Together, they create a system that fails gracefully
instead of catastrophically.

That's engineering.
```
