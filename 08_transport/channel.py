"""
A2A Communication Channel
=========================

This module implements concepts from Google's Agent-to-Agent (A2A) Protocol:
- Agent Cards: Capability advertisement
- Discovery: Finding agents by capability  
- Standardized messaging: A2AMessage format
- Task state tracking: Grouping related messages

Simple in-memory channel for local communication.

Why in-memory is fine for learning:
1. A2A concepts work over any transport
2. The same patterns apply to production transports
3. Testing is easier with in-memory channels

In production, swap this for:
- WebSockets (real-time A2A)
- HTTP with Agent Cards (full A2A spec)
- Message queues (durability)

But the A2A PATTERNS stay the same.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
from threading import Lock
from uuid import uuid4
from enum import Enum


# =============================================================================
# A2A Agent Cards - Capability Advertisement
# =============================================================================

@dataclass
class AgentCard:
    """
    A2A Agent Card - describes an agent's capabilities.
    
    In production A2A, this would be served via HTTP at a well-known URL.
    Here we use a simplified in-memory registry.
    """
    agent_id: str
    name: str
    description: str
    capabilities: List[str]  # What this agent can do
    endpoint: str            # How to reach this agent
    version: str = "1.0"
    supported_message_types: List[str] = field(default_factory=list)


# Pre-defined Agent Cards for negotiation
BUYER_CARD = AgentCard(
    agent_id="buyer",
    name="Buyer Agent",
    description="Negotiates to purchase items at best price",
    capabilities=["make_offer", "accept", "reject", "counter"],
    endpoint="local://buyer",
    supported_message_types=["offer", "counter", "accept", "reject"],
)

SELLER_CARD = AgentCard(
    agent_id="seller",
    name="Seller Agent", 
    description="Negotiates to sell items at best price",
    capabilities=["counter", "accept", "reject"],
    endpoint="local://seller",
    supported_message_types=["offer", "counter", "accept", "reject"],
)


# =============================================================================
# A2A Task State
# =============================================================================

class TaskState(Enum):
    """A2A task states for tracking negotiation progress."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


# =============================================================================
# A2A Message Format
# =============================================================================

@dataclass
class A2AMessage:
    """
    A2A-compliant message format.
    
    Follows Google's A2A specification for inter-agent communication.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    sender: str = ""
    recipient: str = ""
    task_id: str = ""                    # Groups related messages
    message_type: str = ""               # "offer", "counter", "accept", etc.
    content: Dict[str, Any] = field(default_factory=dict)
    state: TaskState = TaskState.IN_PROGRESS
    parent_message_id: Optional[str] = None
    requires_response: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


# Legacy alias for backward compatibility
Message = A2AMessage


# =============================================================================
# A2A Registry - Agent Discovery
# =============================================================================

class A2ARegistry:
    """
    Agent registry for A2A discovery.
    
    Allows agents to find each other by capability.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
    
    def register(self, card: AgentCard) -> None:
        """Register an agent's capabilities."""
        self._agents[card.agent_id] = card
    
    def discover(self, capability: str) -> List[AgentCard]:
        """A2A Discovery: find agents with a specific capability."""
        return [
            card for card in self._agents.values()
            if capability in card.capabilities
        ]
    
    def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        """Get a specific agent's card."""
        return self._agents.get(agent_id)
    
    def list_all(self) -> List[AgentCard]:
        """List all registered agents."""
        return list(self._agents.values())


# =============================================================================
# A2A Channel - Full Implementation
# =============================================================================

class A2AChannel:
    """
    A2A-compliant communication channel.
    
    Combines agent discovery with message delivery.
    This is the main class for A2A inter-agent communication.
    """
    
    def __init__(self):
        self.registry = A2ARegistry()
        self._messages: Dict[str, List[A2AMessage]] = {}  # Per-agent inbox
        self._tasks: Dict[str, List[A2AMessage]] = {}     # Task history
        self._subscribers: Dict[str, List[Callable[[A2AMessage], None]]] = {}
        self._lock = Lock()
    
    def register_agent(self, card: AgentCard) -> None:
        """Register an agent with its capabilities (A2A Agent Card)."""
        with self._lock:
            self.registry.register(card)
            self._messages[card.agent_id] = []
    
    def discover_agents(self, capability: str) -> List[AgentCard]:
        """A2A Discovery: find agents by capability."""
        return self.registry.discover(capability)
    
    def send(self, message: A2AMessage) -> None:
        """Send an A2A message."""
        with self._lock:
            # Verify recipient exists
            if message.recipient not in self._messages:
                raise ValueError(f"Unknown agent: {message.recipient}")
            
            # Deliver to recipient's inbox
            self._messages[message.recipient].append(message)
            
            # Track in task history
            if message.task_id:
                if message.task_id not in self._tasks:
                    self._tasks[message.task_id] = []
                self._tasks[message.task_id].append(message)
            
            # Notify subscribers
            if message.recipient in self._subscribers:
                for callback in self._subscribers[message.recipient]:
                    try:
                        callback(message)
                    except Exception:
                        pass
    
    def receive(self, agent_id: str) -> Optional[A2AMessage]:
        """Receive next message for an agent."""
        with self._lock:
            inbox = self._messages.get(agent_id, [])
            return inbox.pop(0) if inbox else None
    
    def subscribe(
        self,
        agent_id: str,
        callback: Callable[[A2AMessage], None],
    ) -> None:
        """Subscribe to messages for an agent."""
        with self._lock:
            if agent_id not in self._subscribers:
                self._subscribers[agent_id] = []
            self._subscribers[agent_id].append(callback)
    
    def get_task_history(self, task_id: str) -> List[A2AMessage]:
        """Get all messages for a task (A2A state tracking)."""
        with self._lock:
            return self._tasks.get(task_id, []).copy()
    
    def update_task_state(self, task_id: str, state: TaskState) -> None:
        """Update the state of a task."""
        with self._lock:
            if task_id in self._tasks and self._tasks[task_id]:
                self._tasks[task_id][-1].state = state
    
    def get_messages(
        self,
        recipient: Optional[str] = None,
        sender: Optional[str] = None,
    ) -> List[A2AMessage]:
        """Get messages, optionally filtered."""
        with self._lock:
            all_msgs = []
            for inbox in self._messages.values():
                all_msgs.extend(inbox)
        
        if recipient:
            all_msgs = [m for m in all_msgs if m.recipient == recipient]
        if sender:
            all_msgs = [m for m in all_msgs if m.sender == sender]
        
        return all_msgs
    
    def clear(self) -> None:
        """Clear all messages (for testing)."""
        with self._lock:
            for inbox in self._messages.values():
                inbox.clear()
            self._tasks.clear()


# =============================================================================
# Legacy LocalChannel - Backward Compatibility
# =============================================================================

class LocalChannel:
    """
    Legacy in-memory message channel.
    
    Kept for backward compatibility. New code should use A2AChannel.
    """
    
    def __init__(self):
        self._channel = A2AChannel()
        # Auto-register buyer and seller
        self._channel.register_agent(BUYER_CARD)
        self._channel.register_agent(SELLER_CARD)
    
    def send(self, message: A2AMessage) -> None:
        """Send a message through the channel."""
        self._channel.send(message)
    
    def subscribe(
        self,
        recipient: str,
        callback: Callable[[A2AMessage], None],
    ) -> None:
        """Subscribe to messages for a recipient."""
        self._channel.subscribe(recipient, callback)
    
    def get_messages(
        self,
        recipient: Optional[str] = None,
        sender: Optional[str] = None,
    ) -> List[A2AMessage]:
        """Get messages, optionally filtered."""
        return self._channel.get_messages(recipient, sender)
    
    def get_conversation(self, party1: str, party2: str) -> List[A2AMessage]:
        """Get all messages between two parties."""
        all_msgs = self._channel.get_messages()
        return [
            m for m in all_msgs
            if (m.sender == party1 and m.recipient == party2) or
               (m.sender == party2 and m.recipient == party1)
        ]
    
    def clear(self) -> None:
        """Clear all messages (for testing)."""
        self._channel.clear()
