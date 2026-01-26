"""
08_transport - Message Delivery Layer
====================================

Question this layer answers:
"How does a message get from A to B?"

Transport responsibilities:
- Deliver messages
- Retry on failure
- Deduplicate
- Timeout handling

Transport is intentionally dumb.

Transport does NOT:
- Know negotiation state
- Know turns
- Enforce policy
- Terminate conversations
"""

from .channel import LocalChannel, Message

__all__ = ["LocalChannel", "Message"]
