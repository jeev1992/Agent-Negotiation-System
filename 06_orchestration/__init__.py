"""
06_ORCHESTRATION - LangGraph Control Flow Layer
=============================================

Question this layer answers:
"What runs next?"

This is the heart of agent behavior.

LangGraph controls:
- Buyer → Seller → Buyer
- Looping
- Termination
- State propagation

```
buyer → seller → (continue or END)
```

LangGraph replaces the dangerous:
```python
while True:
    ...
```

LangGraph does NOT:
- Start the program (that's runtime)
- Send messages over network (that's transport)
- Enforce governance rules (that's policy)
- Load config (that's runtime)
"""

from .graph import run_negotiation, NegotiationState, create_negotiation_graph

# Alias for consistency
NegotiationGraph = create_negotiation_graph

__all__ = ["run_negotiation", "NegotiationState", "create_negotiation_graph", "NegotiationGraph"]
