"""
08_transport - Agent-to-Agent Communication (A2A)
=================================================

Question this layer answers:
"How do agents discover and communicate with each other?"

This module implements concepts from Google's A2A Protocol:
- Agent Cards: Capability advertisement (AgentCard)
- Discovery: Finding agents by capability (A2ARegistry)
- Messaging: Standardized format (A2AMessage)
- Task State: Tracking interactions (TaskState)

A2A is intentionally separate from business logic.

A2A does NOT:
- Know negotiation state
- Know turns
- Enforce policy (that's ACP)
- Terminate conversations
"""

from .channel import (
    # A2A Core Classes
    A2AChannel,
    A2AMessage,
    A2ARegistry,
    AgentCard,
    TaskState,
    # Pre-defined Agent Cards
    BUYER_CARD,
    SELLER_CARD,
    # Legacy (backward compatibility)
    LocalChannel,
    Message,
)

__all__ = [
    # A2A Core
    "A2AChannel",
    "A2AMessage", 
    "A2ARegistry",
    "AgentCard",
    "TaskState",
    # Pre-defined cards
    "BUYER_CARD",
    "SELLER_CARD",
    # Legacy
    "LocalChannel",
    "Message",
]
