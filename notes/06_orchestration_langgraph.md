# 06 - Orchestration: LangGraph (Framework Deep Dive)

## Purpose

Teach what LangGraph actually is and what it's for. LangGraph is the most misunderstood component—it's not an agent framework, it's a stateful execution engine.

---

## What Is Orchestration?

**Orchestration** answers: "What runs next?"

```
WITHOUT ORCHESTRATION:                WITH ORCHESTRATION:
─────────────────────────────────────────────────────────
while True:                           graph.invoke(state)
    buyer_msg = buyer.respond()       
    if done(buyer_msg):               Graph knows:
        break                         - buyer_node runs first
    seller_msg = seller.respond()     - then seller_node
    if done(seller_msg):              - then router decides
        break                         - when to stop
    # Where's the state?
    # Where's the history?
```

---

## Why `while True` Fails

```python
# Baseline: Implicit state, scattered logic

def negotiate():
    history = []  # Where is this managed?
    turn = 0      # Who increments this?
    
    while True:   # When does this end?
        turn += 1
        buyer_msg = buyer.respond(history)
        history.append(buyer_msg)
        
        if "DEAL" in buyer_msg:  # String matching!
            break
        
        seller_msg = seller.respond(history)
        history.append(seller_msg)
        
        if "DEAL" in seller_msg:
            break
        
        # What if turn > 100? Infinite loop.
        # What if buyer throws exception? State lost.
        # What if we need to pause and resume? Can't.
```

---

## LangGraph: The Solution

### Core Concepts

| Concept | What It Is | Analogy |
|---------|------------|---------|
| **StateGraph** | A directed graph of nodes | A flowchart |
| **Node** | A function that transforms state | A box in the flowchart |
| **Edge** | A connection between nodes | An arrow |
| **Conditional Edge** | Edge that depends on state | A diamond (decision) |
| **State** | Shared data passed between nodes | The clipboard you carry |

### Minimal LangGraph Example

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

# 1. Define the state schema
class NegotiationState(TypedDict):
    """State that flows through the graph."""
    messages: list[dict]
    current_price: float | None
    turn_count: int
    status: Literal["active", "agreed", "failed"]


# 2. Define nodes (functions)
def buyer_node(state: NegotiationState) -> dict:
    """Buyer makes a decision."""
    decision = buyer_strategy(
        current_price=state["current_price"],
        turn=state["turn_count"],
    )
    
    # Return UPDATES to state, not full state
    return {
        "messages": state["messages"] + [{"sender": "buyer", **decision}],
        "current_price": decision["price"],
        "turn_count": state["turn_count"] + 1,
        "status": "agreed" if decision["type"] == "accept" else "active",
    }


def seller_node(state: NegotiationState) -> dict:
    """Seller responds to buyer."""
    decision = seller_strategy(
        buyer_price=state["current_price"],
        turn=state["turn_count"],
    )
    
    return {
        "messages": state["messages"] + [{"sender": "seller", **decision}],
        "current_price": decision["price"],
        "status": "agreed" if decision["type"] == "accept" else "active",
    }


# 3. Define routing logic
def router(state: NegotiationState) -> Literal["buyer", "done"]:
    """Decide what runs next."""
    if state["status"] != "active":
        return "done"
    if state["turn_count"] >= 10:
        return "done"
    return "buyer"


# 4. Build the graph
def create_negotiation_graph() -> StateGraph:
    graph = StateGraph(NegotiationState)
    
    # Add nodes
    graph.add_node("buyer", buyer_node)
    graph.add_node("seller", seller_node)
    
    # Add edges
    graph.add_edge("buyer", "seller")  # buyer → seller (always)
    graph.add_conditional_edges(
        "seller",
        router,
        {
            "buyer": "buyer",  # continue → back to buyer
            "done": END,       # done → end graph
        }
    )
    
    # Set entry point
    graph.set_entry_point("buyer")
    
    return graph.compile()


# 5. Run the graph
graph = create_negotiation_graph()

result = graph.invoke({
    "messages": [],
    "current_price": None,
    "turn_count": 0,
    "status": "active",
})

print(f"Final status: {result['status']}")
print(f"Final price: {result['current_price']}")
print(f"Total turns: {result['turn_count']}")
```

---

## Graph Visualization

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
            ┌───────│    buyer    │
            │       │    node     │
            │       └──────┬──────┘
            │              │
            │              ▼
            │       ┌─────────────┐
            │       │   seller    │
            │       │    node     │
            │       └──────┬──────┘
            │              │
            │              ▼
            │       ┌─────────────┐
            │       │   router    │◄─────── Conditional
            │       │  (decide)   │         Edge
            │       └──────┬──────┘
            │              │
            │      ┌───────┴───────┐
            │      │               │
            │  "buyer"          "done"
            │      │               │
            └──────┘               ▼
                            ┌─────────────┐
                            │     END     │
                            └─────────────┘
```

---

## State Management

### The Problem with Manual State

```python
# Manual state management is error-prone

history = []
turn = 0
price = None

# What if buyer_respond throws? State is inconsistent.
buyer_msg = buyer_respond(price)
history.append(buyer_msg)  # Might forget this
turn += 1                   # Might forget this
price = extract_price(buyer_msg)  # Might fail
```

### LangGraph State Management

```python
# LangGraph manages state atomically

class NegotiationState(TypedDict):
    messages: Annotated[list, operator.add]  # Append-only
    current_price: float | None
    turn_count: int
    status: str

def buyer_node(state: NegotiationState) -> dict:
    # Return only the CHANGES
    return {
        "messages": [new_message],     # Auto-appended
        "current_price": new_price,    # Updated
        "turn_count": state["turn_count"] + 1,  # Incremented
    }
    
# LangGraph:
# 1. Validates state schema
# 2. Applies updates atomically
# 3. Handles reducers (like append-only lists)
# 4. Preserves state on errors
```

---

## Conditional Edges: Decision Points

```python
def router(state: NegotiationState) -> str:
    """
    Router function determines next node.
    
    This replaces scattered if/else logic in while loops.
    """
    # Terminal conditions
    if state["status"] == "agreed":
        return "done"
    if state["status"] == "failed":
        return "done"
    if state["turn_count"] >= MAX_TURNS:
        return "done"
    
    # Continue negotiation
    return "buyer"


graph.add_conditional_edges(
    source="seller",
    path=router,
    path_map={
        "buyer": "buyer",
        "done": END,
    }
)
```

---

## LangGraph Mental Model

> **"LangGraph is a stateful execution engine, not an agent framework."**

| LangGraph IS | LangGraph IS NOT |
|--------------|------------------|
| A state machine runner | An AI framework |
| A flow controller | A chatbot builder |
| A graph executor | An LLM wrapper |
| A state manager | A prompt engineer |

Think of it as **Kubernetes for workflows**:
- Kubernetes runs containers
- LangGraph runs nodes
- Both manage state, handle failures, control flow

---

## Common Misconceptions (Important!)

### ❌ "LangGraph manages transport"

**Wrong.** Transport is how messages move between machines. LangGraph runs on a single machine and passes state in memory.

```python
# This is NOT what LangGraph does:
langgraph.send_message_to_seller(msg)  # ← WRONG

# This IS what LangGraph does:
graph.invoke(state)  # Execute nodes in order
```

### ❌ "LangGraph is Google ADK"

**Wrong.** They're completely different:

| Aspect | LangGraph | Google ADK |
|--------|-----------|------------|
| Purpose | Flow control | Lifecycle management |
| Scope | One workflow | Full application |
| Level | Middleware | Framework |
| Analogy | Express routes | Django |

### ❌ "LangGraph replaces while loops"

**Partially right.** LangGraph doesn't just replace `while True`—it adds:
- Explicit state schema
- Visual graph structure
- Checkpoint/resume capability
- Error isolation
- Observability hooks

---

## How LangGraph Fits in This Project

```
┌─────────────────────────────────────────────────────────────────┐
│  10_runtime (ADK)                                                │
│  │                                                              │
│  └── Calls 06_orchestration.run_negotiation()                    │
│       │                                                         │
│       └── LangGraph executes the negotiation workflow           │
│            │                                                    │
│            ├── buyer_node calls 05_agents.buyer_strategy()       │
│            ├── seller_node calls 05_agents.seller_strategy()     │
│            └── router checks 04_fsm for termination              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

LangGraph is ONE layer—it handles orchestration. It doesn't know about:
- How to start the application (10_runtime)
- Who is allowed to speak (07_coordination)
- How messages are delivered (08_transport)
- What the agents decide (05_agents)
- When to terminate (04_fsm)

---

## What LangGraph Deliberately Does NOT Do

1. **Agent logic**: LangGraph doesn't know what a "good offer" is
2. **Transport**: LangGraph doesn't send messages over networks
3. **Policy enforcement**: LangGraph doesn't check permissions
4. **Termination logic**: LangGraph calls your router, doesn't define it
5. **Evaluation**: LangGraph doesn't judge outcomes

This separation is **by design**. Each layer has one job.

---

## Full Integration Example

```python
# 06_orchestration/graph.py

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from 05_agents.buyer import buyer_strategy
from 05_agents.seller import seller_strategy
from 04_fsm.state_machine import NegotiationFSM


class NegotiationState(TypedDict):
    messages: list[dict]
    buyer_price: float | None
    seller_price: float | None
    turn: int
    fsm_state: str


def create_negotiation_graph(
    buyer_config: dict,
    seller_config: dict,
    max_turns: int = 10,
) -> StateGraph:
    """Create the negotiation orchestration graph."""
    
    fsm = NegotiationFSM(max_turns=max_turns)
    
    def buyer_node(state: NegotiationState) -> dict:
        """Execute buyer strategy."""
        decision = buyer_strategy(
            config=buyer_config,
            seller_price=state["seller_price"],
            turn=state["turn"],
        )
        
        return {
            "messages": state["messages"] + [{"sender": "buyer", **decision}],
            "buyer_price": decision["price"],
        }
    
    def seller_node(state: NegotiationState) -> dict:
        """Execute seller strategy."""
        decision = seller_strategy(
            config=seller_config,
            buyer_price=state["buyer_price"],
            turn=state["turn"],
        )
        
        return {
            "messages": state["messages"] + [{"sender": "seller", **decision}],
            "seller_price": decision["price"],
            "turn": state["turn"] + 1,
        }
    
    def router(state: NegotiationState) -> str:
        """Determine next step based on FSM."""
        last_msg = state["messages"][-1] if state["messages"] else {}
        
        # Check for acceptance
        if last_msg.get("type") == "accept":
            return "done"
        
        # Check turn limit
        if state["turn"] >= max_turns:
            return "done"
        
        return "continue"
    
    # Build graph
    graph = StateGraph(NegotiationState)
    graph.add_node("buyer", buyer_node)
    graph.add_node("seller", seller_node)
    
    graph.set_entry_point("buyer")
    graph.add_edge("buyer", "seller")
    graph.add_conditional_edges(
        "seller",
        router,
        {"continue": "buyer", "done": END},
    )
    
    return graph.compile()


# Usage
graph = create_negotiation_graph(buyer_config, seller_config)
result = graph.invoke({
    "messages": [],
    "buyer_price": None,
    "seller_price": None,
    "turn": 0,
    "fsm_state": "negotiating",
})
```

---

## Key Takeaway

> **LangGraph is a stateful execution engine.**
>
> It replaces `while True` with explicit graphs, gives you state management, and enables debugging through visualization. But it doesn't replace your agent logic, transport, or runtime—those are separate concerns.

---

## Code References

- [06_orchestration/graph.py](../06_orchestration/graph.py) - Main graph implementation
- [06_orchestration/state.py](../06_orchestration/state.py) - State definitions
- [tests/test_integration.py](../tests/test_integration.py) - Integration tests

---

## Next Steps

1. Read `07_coordination_acp.md` to understand policy enforcement
2. Read `10_runtime_adk.md` to see how ADK wraps the graph
3. Read `12_execution_walkthrough.md` for a full trace
