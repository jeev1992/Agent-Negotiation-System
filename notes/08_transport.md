# 08 - Transport & Distribution

## Purpose

Clarify the difference between communication infrastructure and business logic. Transport moves messages; it doesn't decide meaning.

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
