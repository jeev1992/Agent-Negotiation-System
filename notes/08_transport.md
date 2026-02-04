# 08 - Transport & Distribution (A2A)

## Purpose

Clarify the difference between communication infrastructure and business logic. This module implements concepts from Google's **Agent-to-Agent (A2A) Protocol** — the standard for agent discovery and inter-agent communication.

> **A2A** handles how agents discover each other, advertise capabilities, and exchange messages. Transport moves messages; it doesn't decide meaning.

### A2A Key Concepts

| A2A Concept | Description | Our Implementation |
|-------------|-------------|--------------------|
| **Agent Cards** | Capability advertisement | `AgentCard` dataclass |
| **Discovery** | Finding other agents | `discover_agents()` method |
| **Messaging** | Standardized format | `A2AMessage` dataclass |
| **Task State** | Tracking interactions | `task_id` and `state` fields |

---

## A2A Implementation

### Agent Cards (Capability Advertisement)

In A2A, each agent publishes an "Agent Card" describing what it can do:

```python
# 08_transport/a2a.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


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
    
    # A2A-specific fields
    supported_message_types: List[str] = field(default_factory=list)
    authentication_required: bool = False


# Example Agent Cards for our negotiation system
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
```

### Agent Discovery

A2A allows agents to discover each other by capability:

```python
class A2ARegistry:
    """
    Agent registry for A2A discovery.
    
    In production, this would be a distributed service.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
    
    def register(self, card: AgentCard) -> None:
        """Register an agent's capabilities."""
        self._agents[card.agent_id] = card
    
    def discover(self, capability: str) -> List[AgentCard]:
        """Find agents with a specific capability."""
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


# Usage
registry = A2ARegistry()
registry.register(BUYER_CARD)
registry.register(SELLER_CARD)

# Find agents that can accept offers
acceptors = registry.discover("accept")
# Returns: [BUYER_CARD, SELLER_CARD]
```

### A2A Message Format

A2A defines a standard message structure:

```python
class TaskState(Enum):
    """A2A task states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class A2AMessage:
    """
    A2A-compliant message format.
    
    Follows Google's A2A specification for inter-agent communication.
    """
    # Core A2A fields
    id: str
    sender: str
    recipient: str
    task_id: str              # Groups related messages
    
    # Payload
    message_type: str         # "offer", "counter", "accept", etc.
    content: Dict[str, Any]
    
    # A2A metadata
    state: TaskState = TaskState.IN_PROGRESS
    parent_message_id: Optional[str] = None  # For threading
    requires_response: bool = True
    
    # Timestamps
    created_at: str = ""
    expires_at: Optional[str] = None


# Example: Creating an A2A offer message
def create_offer_message(
    sender: str,
    recipient: str,
    task_id: str,
    price: float,
) -> A2AMessage:
    """Create an A2A-compliant offer message."""
    from uuid import uuid4
    from datetime import datetime
    
    return A2AMessage(
        id=str(uuid4()),
        sender=sender,
        recipient=recipient,
        task_id=task_id,
        message_type="offer",
        content={"price": price, "currency": "USD"},
        state=TaskState.IN_PROGRESS,
        requires_response=True,
        created_at=datetime.utcnow().isoformat(),
    )
```

### A2A Channel (Full Implementation)

```python
class A2AChannel:
    """
    A2A-compliant communication channel.
    
    Combines agent discovery with message delivery.
    """
    
    def __init__(self):
        self.registry = A2ARegistry()
        self._messages: Dict[str, List[A2AMessage]] = {}  # Per-agent inbox
        self._tasks: Dict[str, List[A2AMessage]] = {}     # Task history
    
    def register_agent(self, card: AgentCard) -> None:
        """Register an agent with its capabilities."""
        self.registry.register(card)
        self._messages[card.agent_id] = []
    
    def discover_agents(self, capability: str) -> List[AgentCard]:
        """A2A discovery: find agents by capability."""
        return self.registry.discover(capability)
    
    def send(self, message: A2AMessage) -> None:
        """Send an A2A message."""
        # Verify recipient exists
        if message.recipient not in self._messages:
            raise ValueError(f"Unknown agent: {message.recipient}")
        
        # Deliver to recipient's inbox
        self._messages[message.recipient].append(message)
        
        # Track in task history
        if message.task_id not in self._tasks:
            self._tasks[message.task_id] = []
        self._tasks[message.task_id].append(message)
    
    def receive(self, agent_id: str) -> Optional[A2AMessage]:
        """Receive next message for an agent."""
        inbox = self._messages.get(agent_id, [])
        return inbox.pop(0) if inbox else None
    
    def get_task_history(self, task_id: str) -> List[A2AMessage]:
        """Get all messages for a task (A2A state tracking)."""
        return self._tasks.get(task_id, [])
    
    def update_task_state(self, task_id: str, state: TaskState) -> None:
        """Update the state of a task."""
        if task_id in self._tasks and self._tasks[task_id]:
            # Update latest message state
            self._tasks[task_id][-1].state = state


# Usage example
channel = A2AChannel()
channel.register_agent(BUYER_CARD)
channel.register_agent(SELLER_CARD)

# Buyer discovers who can accept offers
sellers = channel.discover_agents("accept")

# Create and send offer
offer = create_offer_message(
    sender="buyer",
    recipient="seller",
    task_id="negotiation_001",
    price=350.0,
)
channel.send(offer)

# Seller receives
msg = channel.receive("seller")
print(f"Received {msg.message_type}: ${msg.content['price']}")
```

---

## The Problem: Confusing Transport with Logic

Developers often conflate:

```python
# Is this transport or business logic?
def send_offer(offer):
    validate_offer(offer)         # ← Business logic
    serialize(offer)              # ← Transport
    encrypt(offer)                # ← Transport
    check_policy(offer)           # ← Business logic
    socket.send(offer)            # ← Transport
    wait_for_ack()                # ← Transport
    log_offer(offer)              # ← Observability
```

**Transport** is the plumbing. **Business logic** is the water.

---

## What Transport Does (and Does Not Do)

### Transport DOES:

| Responsibility | Example |
|---------------|---------|
| Deliver messages | Send bytes from A to B |
| Handle timeouts | Retry after 5 seconds |
| Manage connections | WebSocket, HTTP, in-memory |
| Serialize/deserialize | JSON, protobuf, pickle |
| Provide reliability | At-least-once delivery |
| Handle backpressure | Queue full → slow down |

### Transport DOES NOT:

| Not Responsible For | That's Handled By |
|--------------------|-------------------|
| Message validation | Protocol layer |
| Permission checks | Coordination layer |
| Business decisions | Agent layer |
| State management | Orchestration layer |
| Logging/tracing | Observability layer |

---

## Transport Implementations

### 1. In-Memory Channel (Local)

For single-process systems where agents run together:

```python
# 08_transport/local_channel.py

from queue import Queue
from dataclasses import dataclass
from typing import Any, Optional
import time


@dataclass
class Message:
    """A message in transit."""
    id: str
    sender: str
    recipient: str
    payload: Any
    timestamp: float


class LocalChannel:
    """
    In-memory message channel for local agent communication.
    
    No network, no serialization, just queues.
    """
    
    def __init__(self):
        self._queues: dict[str, Queue] = {}
        self._message_count = 0
    
    def register(self, agent_id: str) -> None:
        """Register an agent to receive messages."""
        if agent_id not in self._queues:
            self._queues[agent_id] = Queue()
    
    def send(
        self,
        sender: str,
        recipient: str,
        payload: Any,
    ) -> str:
        """
        Send a message.
        
        Returns message ID for tracking.
        """
        if recipient not in self._queues:
            raise ValueError(f"Unknown recipient: {recipient}")
        
        self._message_count += 1
        msg = Message(
            id=f"msg_{self._message_count}",
            sender=sender,
            recipient=recipient,
            payload=payload,
            timestamp=time.time(),
        )
        
        self._queues[recipient].put(msg)
        return msg.id
    
    def receive(
        self,
        agent_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[Message]:
        """
        Receive a message for this agent.
        
        Returns None if timeout expires.
        """
        if agent_id not in self._queues:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        try:
            return self._queues[agent_id].get(
                block=True,
                timeout=timeout,
            )
        except:
            return None  # Timeout
    
    def pending(self, agent_id: str) -> int:
        """Check how many messages are waiting."""
        if agent_id not in self._queues:
            return 0
        return self._queues[agent_id].qsize()
```

### 2. WebSocket Channel (Distributed)

For multi-process/multi-machine systems:

```python
# 08_transport/websocket_channel.py (conceptual)

import asyncio
import websockets
import json
from typing import Callable


class WebSocketChannel:
    """
    WebSocket-based message channel for distributed agents.
    
    Each agent connects to a central server.
    """
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.connection = None
        self.handlers: dict[str, Callable] = {}
    
    async def connect(self, agent_id: str) -> None:
        """Establish WebSocket connection."""
        self.connection = await websockets.connect(
            f"{self.server_url}?agent={agent_id}"
        )
        # Start listener
        asyncio.create_task(self._listen())
    
    async def _listen(self) -> None:
        """Listen for incoming messages."""
        async for raw in self.connection:
            msg = json.loads(raw)
            handler = self.handlers.get(msg["type"])
            if handler:
                await handler(msg)
    
    async def send(
        self,
        recipient: str,
        payload: dict,
    ) -> None:
        """Send a message via WebSocket."""
        await self.connection.send(json.dumps({
            "recipient": recipient,
            "payload": payload,
        }))
    
    def on_message(self, msg_type: str, handler: Callable) -> None:
        """Register a message handler."""
        self.handlers[msg_type] = handler
```

---

## Timeouts and Retries

### Why Timeouts Matter

Without timeouts:
```python
# This blocks forever if seller never responds
response = channel.receive("seller")  # ← Deadlock risk
```

With timeouts:
```python
response = channel.receive("seller", timeout=30.0)
if response is None:
    handle_timeout()  # ← System remains responsive
```

### Retry Logic

```python
# 08_transport/retry.py

from typing import Callable, TypeVar, Optional
import time

T = TypeVar("T")


def with_retry(
    operation: Callable[[], T],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
) -> Optional[T]:
    """
    Execute operation with exponential backoff retry.
    
    Transport concern, not business logic.
    """
    attempt = 0
    current_delay = delay
    
    while attempt < max_attempts:
        try:
            return operation()
        except Exception as e:
            attempt += 1
            if attempt >= max_attempts:
                raise
            
            time.sleep(current_delay)
            current_delay *= backoff
    
    return None


# Usage
def send_with_retry(channel, msg):
    return with_retry(
        lambda: channel.send(msg),
        max_attempts=3,
        delay=1.0,
    )
```

---

## Message Deduplication

Messages can be delivered more than once (at-least-once delivery):

```python
# 08_transport/dedup.py

class MessageDeduplicator:
    """
    Ensure each message is processed exactly once.
    
    Transport layer responsibility.
    """
    
    def __init__(self, max_cache_size: int = 10000):
        self._seen: set[str] = set()
        self._max_size = max_cache_size
    
    def is_duplicate(self, message_id: str) -> bool:
        """Check if we've seen this message."""
        if message_id in self._seen:
            return True
        
        # Track this message
        self._seen.add(message_id)
        
        # Prevent unbounded memory growth
        if len(self._seen) > self._max_size:
            # Remove oldest entries (simplified)
            self._seen = set(list(self._seen)[-self._max_size//2:])
        
        return False


# Usage in receiver
dedup = MessageDeduplicator()

def receive_message(msg: Message):
    if dedup.is_duplicate(msg.id):
        return  # Skip duplicate
    
    process_message(msg)  # Business logic
```

---

## Dropped Message Demo

What happens when transport fails:

```python
# Simulation: Unreliable channel

class UnreliableChannel(LocalChannel):
    """Channel that randomly drops messages (for testing)."""
    
    def __init__(self, drop_rate: float = 0.1):
        super().__init__()
        self.drop_rate = drop_rate
        self.dropped = []
    
    def send(self, sender: str, recipient: str, payload: Any) -> str:
        import random
        
        if random.random() < self.drop_rate:
            # Message dropped!
            self.dropped.append({
                "sender": sender,
                "recipient": recipient,
                "payload": payload,
            })
            return "dropped"  # Pretend success
        
        return super().send(sender, recipient, payload)


# Test
channel = UnreliableChannel(drop_rate=0.3)
channel.register("seller")

# Send 10 messages
for i in range(10):
    channel.send("buyer", "seller", {"offer": i * 100})

# Check results
print(f"Pending: {channel.pending('seller')}")    # ~7 messages
print(f"Dropped: {len(channel.dropped)}")          # ~3 messages
```

---

## Mental Model: Transport Is Infrastructure

> **"Transport moves messages; it doesn't decide meaning."**

| Analogy | Transport | Business Logic |
|---------|-----------|----------------|
| Mail | Postal service | Letter contents |
| Phone | Telephone lines | Conversation |
| Web | HTTP/TCP/IP | Application logic |
| **Agents** | **Channel/WebSocket** | **Negotiation strategy** |

The postal service doesn't care what's in your letter. Neither does transport.

---

## Transport vs Protocol vs Orchestration

Common confusion:

```
┌─────────────────────────────────────────────────────────────────┐
│                     LAYER RESPONSIBILITIES                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TRANSPORT (08_transport)                                        │
│  ├── How: WebSocket, HTTP, in-memory queue                      │
│  ├── Reliability: Timeout, retry, dedup                         │
│  └── Format: Serialization (JSON, protobuf)                     │
│                                                                 │
│  PROTOCOL (schemas)                                             │
│  ├── What: Message types (offer, counter, accept)               │
│  ├── Validity: Schema validation                                │
│  └── Contract: Both sides agree on format                       │
│                                                                 │
│  ORCHESTRATION (06_orchestration)                                │
│  ├── When: Turn order, timing                                   │
│  ├── Flow: State machine execution                              │
│  └── State: Message history, current price                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration Example

How transport fits into the system:

```python
# Full integration example

from 08_transport.local_channel import LocalChannel
from 08_transport.retry import with_retry
from 07_coordination.policy import CoordinationPolicy

class NegotiationSession:
    """Manages a negotiation using transport layer."""
    
    def __init__(self):
        self.channel = LocalChannel()
        self.policy = CoordinationPolicy()
        
        # Register agents
        self.channel.register("buyer")
        self.channel.register("seller")
    
    def buyer_turn(self, action: dict) -> None:
        """Execute buyer's turn."""
        # 1. Validate against policy (not transport's job)
        violation = self.policy.validate_action(
            agent="buyer",
            action=action["type"],
            state="negotiating",
        )
        if violation:
            raise PolicyViolationError(violation.reason)
        
        # 2. Send via transport (transport's job)
        with_retry(
            lambda: self.channel.send(
                sender="buyer",
                recipient="seller",
                payload=action,
            ),
            max_attempts=3,
        )
        
        # 3. Record action (policy's job)
        self.policy.record_action("buyer")
    
    def seller_receive(self, timeout: float = 30.0) -> Optional[dict]:
        """Receive message as seller."""
        msg = self.channel.receive("seller", timeout=timeout)
        
        if msg is None:
            raise TimeoutError("Seller didn't receive message in time")
        
        return msg.payload
```

---

## Key Takeaway

> **Transport is plumbing. Don't put business logic in the pipes.**
>
> When you're deciding where code belongs, ask: "Does this decide what the message MEANS, or how it GETS THERE?" Meaning = business logic. Delivery = transport.

---

## Code References

- [08_transport/local_channel.py](../08_transport/local_channel.py) - Channel implementation
- [08_transport/__init__.py](../08_transport/__init__.py) - Transport exports
- [tests/test_integration.py](../tests/test_integration.py) - Integration tests

---

## Next Steps

1. Read `09_mcp_context.md` to understand grounded data
2. Read `03_protocols.md` for message schemas
3. Read `13_what_breaks.md` to see transport failures
