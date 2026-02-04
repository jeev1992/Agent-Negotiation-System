"""
06_ORCHESTRATION - ACP Workflow Layer (via LangGraph)
=====================================================

Question this layer answers:
"What runs next?"

This module implements the ORCHESTRATION aspect of IBM's Agent Communication
Protocol (ACP) using LangGraph. Together with 07_coordination (governance),
this forms our ACP implementation.

ACP has two parts in this project:
- 06_orchestration = ACP workflow orchestration (this module, via LangGraph)
- 07_coordination = ACP governance/policy

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
