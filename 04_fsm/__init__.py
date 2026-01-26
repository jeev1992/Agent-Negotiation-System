"""
04_FSM - State Machine Safety Layer
===================================

Question this layer answers:
"Are we allowed to continue?"

FSM enforces:
- Max turns
- Valid transitions
- Termination reasons

```python
if turns > max_turns:
    state = FAILED
```

This is what GUARANTEES the system stops.

FSM provides a termination PROOF:
- AGREED and FAILED are terminal states
- Every transition either ends or increments turn
- Turns are bounded by max_turns
- Therefore: termination is GUARANTEED
"""

from .state_machine import NegotiationFSM, NegotiationState, FailureReason

# Alias for clarity in tests
FSMState = NegotiationState

__all__ = ["NegotiationFSM", "NegotiationState", "FailureReason", "FSMState"]
