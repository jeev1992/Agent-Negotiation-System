"""
Message Schemas for Negotiation Protocol

This module defines the structured message types used in negotiation.
All communication between agents uses these validated types.

Why typed messages?
- No parsing ambiguity
- Automatic validation
- Type-safe handling
- Self-documenting API
"""

from dataclasses import dataclass, field
from typing import Literal, Union
from datetime import datetime


# ============================================================
# PAYLOAD TYPES - The actual content of messages
# ============================================================

@dataclass
class Offer:
    """
    Buyer makes an offer to purchase.
    
    Example:
        offer = Offer(price=300.0, message="Initial offer")
    """
    type: Literal["offer"] = field(default="offer", init=False)
    price: float
    message: str = ""
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")


@dataclass
class Counter:
    """
    Seller counters with a different price.
    
    Example:
        counter = Counter(price=450.0, original_price=300.0)
    """
    type: Literal["counter"] = field(default="counter", init=False)
    price: float
    original_price: float
    message: str = ""
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")
        if self.original_price <= 0:
            raise ValueError(f"Original price must be positive, got {self.original_price}")


@dataclass
class Accept:
    """
    Accept the current offer/counter and complete the deal.
    
    Example:
        accept = Accept(price=350.0, message="Deal!")
    """
    type: Literal["accept"] = field(default="accept", init=False)
    price: float
    message: str = ""
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")


@dataclass
class Reject:
    """
    Reject and end negotiation without a deal.
    
    Example:
        reject = Reject(reason="Price too high")
    """
    type: Literal["reject"] = field(default="reject", init=False)
    reason: str
    final_offer: float | None = None


# Union type for all negotiation messages
NegotiationMessage = Union[Offer, Counter, Accept, Reject]


# ============================================================
# MESSAGE PARSING - Convert dicts to typed messages
# ============================================================

def parse_message(data: dict) -> NegotiationMessage:
    """
    Parse a dictionary into a typed message.
    
    Args:
        data: Dictionary with 'type' field and message-specific fields
        
    Returns:
        Typed message object
        
    Raises:
        ValueError: If message type is unknown or validation fails
        
    Example:
        msg = parse_message({"type": "offer", "price": 300})
        assert isinstance(msg, Offer)
        assert msg.price == 300
    """
    msg_type = data.get("type")
    
    if msg_type == "offer":
        return Offer(
            price=data["price"],
            message=data.get("message", ""),
        )
    elif msg_type == "counter":
        return Counter(
            price=data["price"],
            original_price=data.get("original_price", 0),
            message=data.get("message", ""),
        )
    elif msg_type == "accept":
        return Accept(
            price=data["price"],
            message=data.get("message", ""),
        )
    elif msg_type == "reject":
        return Reject(
            reason=data.get("reason", "No reason given"),
            final_offer=data.get("final_offer"),
        )
    else:
        raise ValueError(f"Unknown message type: {msg_type}")


def to_dict(msg: NegotiationMessage) -> dict:
    """
    Convert a typed message to a dictionary.
    
    Example:
        offer = Offer(price=300)
        d = to_dict(offer)
        assert d == {"type": "offer", "price": 300, "message": ""}
    """
    if isinstance(msg, Offer):
        return {"type": "offer", "price": msg.price, "message": msg.message}
    elif isinstance(msg, Counter):
        return {
            "type": "counter",
            "price": msg.price,
            "original_price": msg.original_price,
            "message": msg.message,
        }
    elif isinstance(msg, Accept):
        return {"type": "accept", "price": msg.price, "message": msg.message}
    elif isinstance(msg, Reject):
        return {"type": "reject", "reason": msg.reason, "final_offer": msg.final_offer}
    else:
        raise ValueError(f"Unknown message type: {type(msg)}")


# ============================================================
# VALIDATION HELPERS
# ============================================================

def is_terminal_message(msg: NegotiationMessage) -> bool:
    """Check if this message ends the negotiation."""
    return isinstance(msg, (Accept, Reject))


def get_price(msg: NegotiationMessage) -> float | None:
    """Extract price from any message type."""
    if isinstance(msg, (Offer, Counter, Accept)):
        return msg.price
    elif isinstance(msg, Reject):
        return msg.final_offer
    return None
