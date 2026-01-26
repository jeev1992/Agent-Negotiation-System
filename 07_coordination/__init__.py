"""
07_COORDINATION - Agent Coordination Policy (ACP)
================================================

Question this layer answers:
"Who is allowed to speak, and when?"

This is where ACP (coordination policy) lives.

What it enforces:
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
