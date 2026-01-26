# 04 - FSMs, Invariants & Termination

## Purpose

Explain how systems stop safely. Every long-running system must know how it ends. Without explicit termination, you get infinite loops.

---

## The Problem: `while True` Never Ends

From the baseline system:

```python
while True:
    buyer_msg = buyer.respond(seller_msg)
    if "DEAL" in buyer_msg:  # String matching!
        break
    seller_msg = seller.respond(buyer_msg)
    if "DEAL" in seller_msg:
        break
    # What if they never say "DEAL"?
```

### What Goes Wrong

**Scenario: Impossible Agreement**
```
Buyer max price: $50
Seller min price: $100

Turn 1: Buyer offers $30
Turn 2: Seller counters $120
Turn 3: Buyer offers $35
Turn 4: Seller counters $115
...
Turn ∞: Still negotiating (they can NEVER agree)
```

**Scenario: String Matching Fails**
```
Buyer says: "We have a DEAL if you go to $300"
System sees: "DEAL" → breaks loop
But buyer meant: conditional deal, not acceptance!
```

---

## The Solution: Finite State Machine (FSM)

### What Is an FSM?

A **Finite State Machine** has:
1. **States**: A finite set of possible situations
2. **Transitions**: Rules for moving between states
3. **Terminal States**: States you cannot leave
4. **Guards**: Conditions that must be true for transitions

### Negotiation FSM

```
                        ┌──────────────┐
                        │     IDLE     │
                        │   (start)    │
                        └──────┬───────┘
                               │
                               │ start()
                               ▼
                        ┌──────────────┐
        ┌───────────────│ NEGOTIATING  │───────────────┐
        │               │   (active)   │               │
        │               └──────┬───────┘               │
        │                      │                       │
        │           ┌──────────┼──────────┐            │
        │           │          │          │            │
        │      accept()    reject()   max_turns        │
        │           │          │          │            │
        │           ▼          ▼          ▼            │
        │    ┌──────────┐ ┌──────────┐ ┌──────────┐    │
        │    │  AGREED  │ │  FAILED  │ │  FAILED  │    │
        │    │(terminal)│ │(terminal)│ │(terminal)│    │
        │    └──────────┘ └──────────┘ └──────────┘    │
        │                                              │
        │            continue (loop back)              │
        └──────────────────────────────────────────────┘

TERMINAL STATES have NO outgoing transitions.
Once you enter AGREED or FAILED, you cannot leave.
```

---

## The Termination Proof

This is the most important part. We can **prove** the system always terminates.

```
THEOREM: The negotiation FSM always terminates.

PROOF:
1. AGREED and FAILED are terminal states (no outgoing transitions)
2. Every non-terminal transition either:
   a) Moves to a terminal state (accept → AGREED, reject → FAILED)
   b) Increments turn_count
3. turn_count is bounded by max_turns
4. When turn_count >= max_turns, we MUST transition to FAILED
5. Therefore: All paths lead to terminal states in finite time
6. Therefore: The FSM always halts ∎

This is a FORMAL GUARANTEE, not "it probably works."
```

Compare to `while True`:
```
THEOREM: while True terminates.

PROOF:
1. Loop continues until "DEAL" appears in message
2. "DEAL" might never appear (agents might never agree)
3. Therefore: Loop might run forever
4. Therefore: NO termination guarantee ✗
```

---

## Code Implementation

```python
# 04_fsm/state_machine.py

from enum import Enum, auto
from typing import Set, Optional

class NegotiationState(Enum):
    """The finite set of states."""
    IDLE = auto()        # Not started
    NEGOTIATING = auto() # Active negotiation
    AGREED = auto()      # Terminal: deal reached
    FAILED = auto()      # Terminal: no deal


class NegotiationFSM:
    """FSM with termination guarantee."""
    
    # Valid transitions - TERMINAL STATES HAVE NONE
    TRANSITIONS = {
        NegotiationState.IDLE: {NegotiationState.NEGOTIATING},
        NegotiationState.NEGOTIATING: {
            NegotiationState.NEGOTIATING,  # continue
            NegotiationState.AGREED,        # accept
            NegotiationState.FAILED,        # reject or timeout
        },
        NegotiationState.AGREED: set(),  # TERMINAL - no transitions!
        NegotiationState.FAILED: set(),  # TERMINAL - no transitions!
    }
    
    def __init__(self, max_turns: int = 10):
        self.state = NegotiationState.IDLE
        self.turn_count = 0
        self.max_turns = max_turns
        self.agreed_price: Optional[float] = None
        self.failure_reason: Optional[str] = None
    
    @property
    def is_terminal(self) -> bool:
        """Are we in a terminal state?"""
        return self.state in {
            NegotiationState.AGREED,
            NegotiationState.FAILED
        }
    
    @property
    def is_active(self) -> bool:
        """Can negotiation continue?"""
        return self.state == NegotiationState.NEGOTIATING
    
    def start(self) -> bool:
        """Start the negotiation."""
        if self.state != NegotiationState.IDLE:
            return False
        self.state = NegotiationState.NEGOTIATING
        return True
    
    def process_turn(self) -> bool:
        """
        Process a turn. Returns False if terminated.
        
        THIS IS THE KEY TO TERMINATION:
        Every turn increments counter, bounded by max_turns.
        """
        if self.is_terminal:
            return False
        
        self.turn_count += 1
        
        # FORCED TERMINATION at max turns
        if self.turn_count >= self.max_turns:
            self.state = NegotiationState.FAILED
            self.failure_reason = f"Exceeded {self.max_turns} turns"
            return False
        
        return True
    
    def accept(self, price: float) -> bool:
        """Accept and terminate successfully."""
        if not self.is_active:
            return False
        
        self.state = NegotiationState.AGREED
        self.agreed_price = price
        return True
    
    def reject(self, reason: str) -> bool:
        """Reject and terminate with failure."""
        if not self.is_active:
            return False
        
        self.state = NegotiationState.FAILED
        self.failure_reason = reason
        return True
```

---

## Guards and Invariants

### What Is a Guard?

A **guard** is a condition that must be true for a transition to happen:

```python
def accept(self, price: float) -> bool:
    # GUARD: Can only accept from NEGOTIATING state
    if not self.is_active:
        return False  # Transition blocked
    
    self.state = NegotiationState.AGREED
    return True
```

### What Is an Invariant?

An **invariant** is a condition that must ALWAYS be true:

```python
# Invariant: If state is AGREED, agreed_price must exist
assert not (self.state == NegotiationState.AGREED and self.agreed_price is None)

# Invariant: If state is FAILED, failure_reason must exist
assert not (self.state == NegotiationState.FAILED and self.failure_reason is None)

# Invariant: turn_count never exceeds max_turns
assert self.turn_count <= self.max_turns
```

---

## FSM vs While Loop: Side by Side

### While Loop (No Guarantees)

```python
def negotiate_naive(buyer, seller):
    seller_msg = seller.initial_price()
    
    while True:  # ← No termination guarantee
        buyer_msg = buyer.respond(seller_msg)
        if "DEAL" in buyer_msg:  # ← String matching
            return "agreed"
        seller_msg = seller.respond(buyer_msg)
        if "DEAL" in seller_msg:
            return "agreed"
        # What if max turns? What if error?
```

### FSM (Guaranteed Termination)

```python
def negotiate_fsm(buyer, seller, max_turns=10):
    fsm = NegotiationFSM(max_turns=max_turns)
    fsm.start()
    
    while fsm.is_active:  # ← Terminates when FSM is terminal
        # Buyer turn
        buyer_action = buyer.decide(current_price)
        if buyer_action["type"] == "accept":
            fsm.accept(buyer_action["price"])
            break
        
        # Seller turn
        seller_action = seller.decide(buyer_action["price"])
        if seller_action["type"] == "accept":
            fsm.accept(seller_action["price"])
            break
        
        # Process turn (may terminate at max_turns)
        if not fsm.process_turn():
            break
    
    # Guaranteed: fsm.is_terminal is True
    return {
        "agreed": fsm.state == NegotiationState.AGREED,
        "price": fsm.agreed_price,
        "reason": fsm.failure_reason,
        "turns": fsm.turn_count,
    }
```

---

## Failure Reasons: Know Why It Ended

Every failure has a clear reason:

```python
class FailureReason(Enum):
    MAX_TURNS_EXCEEDED = "Exceeded maximum turns"
    BUYER_REJECTED = "Buyer rejected negotiation"
    SELLER_REJECTED = "Seller rejected negotiation"
    NO_OVERLAP = "No possible agreement (buyer max < seller min)"
    POLICY_VIOLATION = "Coordination policy violation"
    TIMEOUT = "Negotiation timed out"
```

This enables:
- **Debugging**: Why did this negotiation fail?
- **Analytics**: What's the most common failure reason?
- **Improvement**: How can we reduce MAX_TURNS_EXCEEDED failures?

---

## Mental Model: Every System Must Know How It Ends

> **"Every long-running system must know how it ends."**

| System | Termination Mechanism |
|--------|----------------------|
| Web Request | Timeout + response |
| Database Transaction | Commit or rollback |
| TCP Connection | FIN packet or timeout |
| **Agent Negotiation** | **FSM terminal states** |

Without explicit termination:
- Resources leak (memory, connections)
- Users wait forever
- Systems hang
- Costs accumulate (LLM API calls!)

---

## Key Takeaway

> **FSMs provide mathematical proof that your system terminates.**
>
> `while True` is hope. FSM is engineering.
> The difference between "it usually works" and "it always works" is the difference between a demo and a production system.

---

## Code References

- [04_fsm/state_machine.py](../04_fsm/state_machine.py) - FSM implementation
- [06_orchestration/graph.py](../06_orchestration/graph.py) - Uses FSM for termination
- [tests/test_fsm.py](../tests/test_fsm.py) - FSM tests

---

## Next Steps

1. Read `05_agents_strategies.md` to see how agents make decisions
2. Read `06_orchestration_langgraph.md` to see how orchestration uses FSM
3. Read `13_what_breaks.md` to see what happens without FSM
