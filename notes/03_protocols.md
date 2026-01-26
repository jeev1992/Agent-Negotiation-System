# 03 - Protocols & Structured Communication

## Purpose

Explain why free text is unacceptable in agent systems. Protocols are contracts—without them, agents cannot reliably communicate.

---

## The Problem: Free Text is Ambiguous

From the baseline system:

```python
def respond_to_counter(self, seller_message: str) -> str:
    # Try to extract price from seller's message
    price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', seller_message)
    
    if not price_match:
        # SILENT FAILURE - we don't know what the seller said
        return f"I'm confused. Let me offer ${self.current_offer:.2f} again."
```

### What Goes Wrong

| Input Message | Regex Extracts | Intended Meaning | Result |
|--------------|----------------|------------------|--------|
| "I'll take $500" | $500 | Accept at $500 | ✓ Works |
| "Not $500, maybe $400" | $500 | Counter at $400 | ✗ Wrong price |
| "Budget is between $300 and $500" | $300 | Range hint | ✗ Wrong price |
| "I can do 400 dollars" | (nothing) | Offer $400 | ✗ Fails to parse |
| "DEAL!" | (nothing) | Accept | ✗ No price found |

**Free text is fundamentally unreliable.**

---

## The Solution: Structured Messages

### What Is a Protocol?

A **protocol** is a contract between sender and receiver:
- **Syntax**: What the message looks like (schema)
- **Semantics**: What the message means (types)
- **Validation**: Is this message valid?

### Message Schemas as Contracts

```python
# Protocol: Negotiation Messages

from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class Offer(BaseModel):
    """Buyer makes an offer."""
    type: Literal["offer"] = "offer"
    price: float = Field(gt=0, description="Offered price in USD")
    message: str = Field(default="", description="Optional message")

class Counter(BaseModel):
    """Seller counters with a different price."""
    type: Literal["counter"] = "counter"
    price: float = Field(gt=0, description="Counter price in USD")
    original_price: float = Field(gt=0, description="Price being countered")
    message: str = Field(default="")

class Accept(BaseModel):
    """Accept the current offer/counter."""
    type: Literal["accept"] = "accept"
    price: float = Field(gt=0, description="Accepted price")
    message: str = Field(default="")

class Reject(BaseModel):
    """Reject and end negotiation."""
    type: Literal["reject"] = "reject"
    reason: str = Field(description="Why negotiation is ending")
```

### No Parsing Needed

```python
# OLD WAY (broken)
price_match = re.search(r'\$?([\d,]+)', message)
price = float(price_match.group(1)) if price_match else None

# NEW WAY (reliable)
offer = Offer(price=300.0, message="Initial offer")
print(offer.price)  # 300.0 - guaranteed to exist and be valid
```

---

## Envelope vs Payload

Every message has two parts:

```
┌─────────────────────────────────────────────────────────────────┐
│  ENVELOPE (metadata about the message)                          │
├─────────────────────────────────────────────────────────────────┤
│  • message_id: "abc123"                                         │
│  • sender: "buyer"                                              │
│  • recipient: "seller"                                          │
│  • timestamp: "2024-01-15T10:30:00Z"                            │
│  • session_id: "session_xyz"                                    │
├─────────────────────────────────────────────────────────────────┤
│  PAYLOAD (the actual content)                                   │
├─────────────────────────────────────────────────────────────────┤
│  • type: "offer"                                                │
│  • price: 300.0                                                 │
│  • message: "Initial offer"                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Why Separate Them?

| Envelope | Payload |
|----------|---------|
| Who sent it? | What did they say? |
| When? | What type of action? |
| To whom? | What values? |
| For which session? | Business content |

The **transport layer** cares about envelopes.
The **agent layer** cares about payloads.

```python
@dataclass
class MessageEnvelope:
    """Wrapper for all messages."""
    id: str
    sender: str
    recipient: str
    timestamp: datetime
    payload: Union[Offer, Counter, Accept, Reject]
    session_id: str
```

---

## Validation: Fail Fast, Fail Loud

### Without Validation (Silent Failures)

```python
def process_message(msg: dict):
    price = msg.get("price")  # Might be None
    if price:
        # What if price is negative?
        # What if price is a string?
        do_something(price)
```

### With Validation (Explicit Failures)

```python
from pydantic import ValidationError

def process_message(data: dict):
    try:
        offer = Offer(**data)
        # If we get here, offer.price is guaranteed to be:
        # - Present
        # - A float
        # - Greater than 0
        do_something(offer.price)
    except ValidationError as e:
        # Explicit, catchable, debuggable
        raise InvalidMessageError(f"Bad offer: {e}")
```

### Validation Error Example

```python
# This will fail with a clear error
Offer(price=-100)
# ValidationError: price must be greater than 0

# This will also fail
Offer(price="three hundred")
# ValidationError: value is not a valid float
```

---

## Type Discrimination: Knowing What You Have

How do you know if a message is an Offer or a Counter?

### The Wrong Way (String Matching)

```python
if "offer" in message.lower():
    handle_offer(message)
elif "counter" in message.lower():
    handle_counter(message)
# What if message is "I counter-offer" ?
```

### The Right Way (Discriminated Union)

```python
from typing import Union, Literal

NegotiationMessage = Union[Offer, Counter, Accept, Reject]

def handle_message(msg: NegotiationMessage):
    match msg.type:
        case "offer":
            return handle_offer(msg)  # msg is Offer
        case "counter":
            return handle_counter(msg)  # msg is Counter
        case "accept":
            return handle_accept(msg)  # msg is Accept
        case "reject":
            return handle_reject(msg)  # msg is Reject
```

The `type` field is a **discriminator**—it tells you which variant you have.

---

## Mental Model: Schemas Are APIs

> **"Schemas are to agents what APIs are to services."**

When two microservices communicate:
- They agree on an API contract (OpenAPI/Swagger)
- They validate requests and responses
- Invalid data is rejected with clear errors

Agent communication is the same:
- Agents agree on message schemas (Pydantic)
- Messages are validated on send and receive
- Invalid messages are rejected with clear errors

```
Microservices:           Agent Systems:
─────────────────────────────────────────
REST API Spec     ↔     Message Schemas
JSON Schema       ↔     Pydantic Models
HTTP Status Codes ↔     Message Types
Request Validation ↔    Payload Validation
```

---

## Full Example: Valid vs Invalid

### Valid Message Flow

```python
# Buyer creates offer
offer = Offer(price=300.0, message="Initial offer")
# ✓ Valid: price > 0, type is "offer"

# Wrap in envelope
envelope = MessageEnvelope(
    id=str(uuid4()),
    sender="buyer",
    recipient="seller",
    timestamp=datetime.utcnow(),
    payload=offer,
    session_id="session_123"
)

# Seller receives, extracts payload
received = envelope.payload
assert received.type == "offer"
assert received.price == 300.0
# ✓ No parsing, no regex, no ambiguity
```

### Invalid Message Rejection

```python
# Attempt 1: Negative price
try:
    Offer(price=-100)
except ValidationError:
    print("Rejected: price must be positive")

# Attempt 2: Missing required field
try:
    Accept()  # price is required
except ValidationError:
    print("Rejected: price is required")

# Attempt 3: Wrong type
try:
    Offer(price="three hundred")
except ValidationError:
    print("Rejected: price must be a number")
```

---

## Why This Matters: Before and After

### Before (Baseline)

```python
def parse_message(text: str) -> dict:
    """Unreliable parsing."""
    price = None
    match = re.search(r'\$?(\d+)', text)
    if match:
        price = float(match.group(1))
    
    action = "unknown"
    if "accept" in text.lower():
        action = "accept"
    elif "counter" in text.lower():
        action = "counter"
    elif "offer" in text.lower():
        action = "offer"
    
    return {"action": action, "price": price}
    # Problems: price might be None, action might be "unknown"
```

### After (Protocol)

```python
def create_offer(price: float, message: str = "") -> Offer:
    """Reliable, validated offer creation."""
    return Offer(price=price, message=message)
    # Guaranteed: price is float > 0, type is "offer"

def process_message(msg: NegotiationMessage) -> Response:
    """Type-safe message handling."""
    match msg.type:
        case "offer":
            return handle_offer(msg)
        case "counter":
            return handle_counter(msg)
        case "accept":
            return handle_accept(msg)
        case "reject":
            return handle_reject(msg)
    # Exhaustive: no "unknown" case possible
```

---

## Key Takeaway

> **Schemas eliminate ambiguity. Validation catches errors early.**
>
> If two agents can't agree on message format, they can't negotiate. Protocols are not optional—they're the foundation of reliable communication.

---

## Code References

- [03_protocol/messages.py](../03_protocol/messages.py) - Message type definitions
- [08_transport/local_channel.py](../08_transport/local_channel.py) - Handles message envelopes
- [07_coordination/policy.py](../07_coordination/policy.py) - Validates message contents

---

## Next Steps

1. Read `04_fsm_termination.md` to understand how FSMs ensure termination
2. Read `05_agents_strategies.md` to see how agents use these protocols
3. Read `07_coordination_acp.md` to see how policy validates messages
