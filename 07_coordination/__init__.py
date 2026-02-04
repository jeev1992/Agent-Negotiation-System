"""
07_COORDINATION - ACP Governance Layer
======================================

Question this layer answers:
"Who is allowed to speak, and when?"

This module implements the GOVERNANCE aspect of IBM's Agent Communication
Protocol (ACP). Together with 06_orchestration (workflow), this forms our
ACP implementation.

ACP has two parts in this project:
- 06_orchestration = ACP workflow orchestration (via LangGraph)
- 07_coordination = ACP governance/policy (this module)

What this layer enforces:
- Turn-taking
- Allowed message types
- Max concessions
- State-dependent rules

```python
if not policy.allows(message, current_state):
    reject(message)
```

This layer:
- Sits between runtime and logic
- Guards the system against illegal actions

This layer does NOT:
- Decide execution order (that's orchestration)
- Deliver messages (that's transport)
- Loop (that's orchestration)
"""

from .policy import CoordinationPolicy, PolicyViolation, PolicyResult

__all__ = ["CoordinationPolicy", "PolicyViolation", "PolicyResult"]
