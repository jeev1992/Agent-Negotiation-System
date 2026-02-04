# 07 - Coordination & Governance (ACP - Policy Layer)

## Purpose

Introduce policy as first-class code. This module implements the **governance aspect** of IBM's Agent Communication Protocol (ACP). While orchestration (06) handles workflow execution, coordination handles what's allowed.

> **Note on Protocols:** ACP encompasses both orchestration AND governance. In this project:
> - `06_orchestration/` = ACP's workflow orchestration (implemented via LangGraph)
> - `07_coordination/` = ACP's policy & governance layer

---

## The Problem: Orchestration ≠ Permission

Consider this scenario:

```python
# Orchestration says: "It's seller's turn"
# But seller sends: "buyer, give me $1000 or I'll spam you"

# Should this be allowed?
```

**Orchestration** knows *who* should act next.
**Coordination** knows *what* actions are permitted.

```
┌─────────────────────────────────────────────────────────────────┐
│                     THE DIFFERENCE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ORCHESTRATION (06_orchestration):                               │
│  "It's seller's turn to respond"                                │
│                                                                 │
│  COORDINATION (07_coordination):                                 │
│  "Seller can only: accept, counter, or reject"                  │
│  "Seller cannot: make offers, skip turns, change topics"        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Communication Protocol (ACP) - Governance Layer

ACP (IBM/BeeAI) is a protocol for workflow orchestration, task delegation, and stateful sessions. This module implements the **governance/policy** aspect of ACP:

1. **Who** can participate
2. **What** actions are allowed per state
3. **When** actions can happen (turn-taking)
4. **How** violations are handled

> **Full ACP** = Orchestration (`06_orchestration/`) + Governance (`07_coordination/`)

### ACP Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      ACP POLICY                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PARTICIPANTS                                                   │
│  ├── buyer: Can make offers, accept, reject                     │
│  └── seller: Can counter, accept, reject                        │
│                                                                 │
│  STATE PERMISSIONS                                              │
│  ├── IDLE → Only "start" action allowed                         │
│  ├── NEGOTIATING → offer, counter, accept, reject               │
│  ├── AGREED → No actions allowed (terminal)                     │
│  └── FAILED → No actions allowed (terminal)                     │
│                                                                 │
│  TURN RULES                                                     │
│  ├── Buyer acts on odd turns                                    │
│  └── Seller acts on even turns                                  │
│                                                                 │
│  CONSTRAINTS                                                    │
│  ├── Prices must be positive                                    │
│  ├── Counters must differ from previous price                   │
│  └── No consecutive actions from same agent                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Policy Implementation

```python
# 07_coordination/policy.py

from dataclasses import dataclass
from typing import Literal, Optional
from enum import Enum

class Permission(Enum):
    """What an agent is allowed to do."""
    OFFER = "offer"
    COUNTER = "counter"
    ACCEPT = "accept"
    REJECT = "reject"


@dataclass
class PolicyViolation:
    """Details about why an action was rejected."""
    agent: str
    action: str
    reason: str
    state: str


class CoordinationPolicy:
    """
    The constitution of the agent system.
    
    Every action must be validated against this policy.
    """
    
    # Which actions each role can perform
    ROLE_PERMISSIONS = {
        "buyer": {Permission.OFFER, Permission.ACCEPT, Permission.REJECT},
        "seller": {Permission.COUNTER, Permission.ACCEPT, Permission.REJECT},
    }
    
    # Which actions are allowed in each state
    STATE_PERMISSIONS = {
        "idle": set(),  # Nothing allowed until started
        "negotiating": {
            Permission.OFFER,
            Permission.COUNTER,
            Permission.ACCEPT,
            Permission.REJECT,
        },
        "agreed": set(),  # Terminal - nothing allowed
        "failed": set(),  # Terminal - nothing allowed
    }
    
    def __init__(self):
        self.last_actor: Optional[str] = None
        self.turn_count: int = 0
    
    def validate_action(
        self,
        agent: str,
        action: str,
        state: str,
        price: Optional[float] = None,
    ) -> Optional[PolicyViolation]:
        """
        Validate an action against the policy.
        
        Returns None if valid, PolicyViolation if not.
        """
        permission = Permission(action)
        
        # Check 1: Is this agent registered?
        if agent not in self.ROLE_PERMISSIONS:
            return PolicyViolation(
                agent=agent,
                action=action,
                reason=f"Unknown agent: {agent}",
                state=state,
            )
        
        # Check 2: Does the agent have this permission?
        if permission not in self.ROLE_PERMISSIONS[agent]:
            return PolicyViolation(
                agent=agent,
                action=action,
                reason=f"{agent} cannot perform {action}",
                state=state,
            )
        
        # Check 3: Is this action allowed in current state?
        if permission not in self.STATE_PERMISSIONS.get(state, set()):
            return PolicyViolation(
                agent=agent,
                action=action,
                reason=f"Action {action} not allowed in state {state}",
                state=state,
            )
        
        # Check 4: Is it this agent's turn?
        if self.last_actor == agent:
            return PolicyViolation(
                agent=agent,
                action=action,
                reason=f"{agent} cannot act twice in a row",
                state=state,
            )
        
        # Check 5: Price constraints
        if price is not None and price <= 0:
            return PolicyViolation(
                agent=agent,
                action=action,
                reason=f"Price must be positive, got {price}",
                state=state,
            )
        
        # All checks passed
        return None
    
    def record_action(self, agent: str) -> None:
        """Record that an agent took an action (for turn tracking)."""
        self.last_actor = agent
        self.turn_count += 1
    
    def can_act(self, agent: str, state: str) -> bool:
        """Quick check if agent can act at all."""
        if state not in ["negotiating"]:
            return False
        if self.last_actor == agent:
            return False
        return True
```

---

## Turn-Taking Rules

Why turn-taking matters:

```
WITHOUT TURN-TAKING:                WITH TURN-TAKING:
─────────────────────────────────────────────────────────
Buyer: I offer $300                 Buyer: I offer $300
Buyer: Actually $350                ← BLOCKED: not your turn
Buyer: Wait, $400                   Seller: I counter $500
Seller: ???                         Buyer: I offer $350
                                    ...
```

### Turn Enforcement

```python
def whose_turn(turn_count: int, last_actor: str | None) -> str:
    """Determine whose turn it is."""
    if last_actor is None:
        return "buyer"  # Buyer starts
    return "seller" if last_actor == "buyer" else "buyer"


class CoordinationPolicy:
    def validate_turn(self, agent: str) -> Optional[PolicyViolation]:
        """Check if it's this agent's turn."""
        expected = whose_turn(self.turn_count, self.last_actor)
        
        if agent != expected:
            return PolicyViolation(
                agent=agent,
                action="any",
                reason=f"Expected {expected} to act, not {agent}",
                state="negotiating",
            )
        return None
```

---

## State-Action Matrix

Visual representation of what's allowed:

```
                    │  offer  │ counter │ accept  │ reject  │
────────────────────┼─────────┼─────────┼─────────┼─────────┤
IDLE                │    ✗    │    ✗    │    ✗    │    ✗    │
NEGOTIATING         │    ✓    │    ✓    │    ✓    │    ✓    │
AGREED              │    ✗    │    ✗    │    ✗    │    ✗    │
FAILED              │    ✗    │    ✗    │    ✗    │    ✗    │

                    │  buyer  │ seller  │
────────────────────┼─────────┼─────────┤
offer               │    ✓    │    ✗    │
counter             │    ✗    │    ✓    │
accept              │    ✓    │    ✓    │
reject              │    ✓    │    ✓    │
```

---

## Rejection Paths: What Happens on Violation

```python
def handle_action(
    policy: CoordinationPolicy,
    agent: str,
    action: dict,
    state: str,
) -> dict:
    """Process an action with policy validation."""
    
    # Validate against policy
    violation = policy.validate_action(
        agent=agent,
        action=action["type"],
        state=state,
        price=action.get("price"),
    )
    
    if violation:
        # Policy rejected the action
        return {
            "success": False,
            "error": violation.reason,
            "original_action": action,
            # Action is NOT applied to state
        }
    
    # Policy approved - record and proceed
    policy.record_action(agent)
    return {
        "success": True,
        "action": action,
        # Action IS applied to state
    }
```

### Violation Example

```python
# Scenario: Seller tries to make an offer
policy = CoordinationPolicy()

result = handle_action(
    policy=policy,
    agent="seller",
    action={"type": "offer", "price": 400},  # Seller can't offer!
    state="negotiating",
)

# Result:
# {
#     "success": False,
#     "error": "seller cannot perform offer",
#     "original_action": {"type": "offer", "price": 400}
# }
```

---

## Policy vs Orchestration vs FSM

These three concepts are often confused:

| Concept | Question | Example |
|---------|----------|---------|
| **Orchestration** | What runs next? | "buyer_node, then seller_node" |
| **Coordination** | Is this allowed? | "seller cannot make offers" |
| **FSM** | Should we stop? | "max turns reached → terminal" |

```
┌─────────────────────────────────────────────────────────────────┐
│                     EXECUTION FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. ORCHESTRATION: "It's seller's turn"                         │
│                     │                                           │
│                     ▼                                           │
│  2. SELLER decides: {"type": "offer", "price": 400}             │
│                     │                                           │
│                     ▼                                           │
│  3. COORDINATION: "Rejected! Seller cannot offer."              │
│                     │                                           │
│                     ▼                                           │
│  4. SELLER retries: {"type": "counter", "price": 450}           │
│                     │                                           │
│                     ▼                                           │
│  5. COORDINATION: "Approved."                                   │
│                     │                                           │
│                     ▼                                           │
│  6. FSM: "Still negotiating, continue."                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Mental Model: ACP Governance Is the Constitution

> **"ACP's governance layer is the constitution of the agent system."**

Just like a constitution:
- Defines who can participate
- Limits what actions are allowed
- Provides checks and balances
- Can't be overridden by participants

```
GOVERNMENT          │  AGENT SYSTEM
────────────────────┼──────────────────────
Constitution        │  Coordination Policy
Citizens            │  Agents
Laws                │  State permissions
Elections           │  Turn-taking
Courts              │  Violation handlers
```

---

## Integration with Orchestration

```python
# 06_orchestration/graph.py with policy integration

from 07_coordination.policy import CoordinationPolicy

def create_negotiation_graph(policy: CoordinationPolicy):
    """Graph that respects coordination policy."""
    
    def buyer_node(state: NegotiationState) -> dict:
        # Check policy before acting
        if not policy.can_act("buyer", state["fsm_state"]):
            raise PolicyViolationError("Buyer cannot act")
        
        # Generate action
        action = buyer_strategy(state)
        
        # Validate action
        violation = policy.validate_action(
            agent="buyer",
            action=action["type"],
            state=state["fsm_state"],
            price=action.get("price"),
        )
        
        if violation:
            # Handle violation (retry, fail, etc.)
            raise PolicyViolationError(violation.reason)
        
        # Record successful action
        policy.record_action("buyer")
        
        return {"messages": state["messages"] + [action]}
    
    # ... rest of graph
```

---

## Key Takeaway

> **Orchestration is traffic direction. Governance is law enforcement.**
>
> Without ACP governance, agents could cheat, spam, or violate protocol. The coordination policy ensures that even if agent logic is buggy, the system maintains integrity.
>
> **Remember:** Full ACP = `06_orchestration` (workflow) + `07_coordination` (governance)

---

## Code References

- [07_coordination/policy.py](../07_coordination/policy.py) - Policy implementation
- [06_orchestration/graph.py](../06_orchestration/graph.py) - Policy integration
- [tests/test_policy.py](../tests/test_policy.py) - Policy tests

---

## Next Steps

1. Read `08_transport.md` to understand message delivery
2. Read `06_orchestration_langgraph.md` to see graph structure
3. Read `13_what_breaks.md` to see failures without policy
