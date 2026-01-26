"""
Message Envelope - Metadata wrapper for all messages

The envelope contains routing and tracking information.
The payload contains the actual message content.

Envelope = WHO, WHEN, WHERE
Payload = WHAT
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from .messages import NegotiationMessage, to_dict, parse_message


@dataclass
class MessageEnvelope:
    """
    Wrapper for all messages with routing metadata.
    
    Attributes:
        id: Unique message identifier
        sender: Who sent this message
        recipient: Who should receive this message
        timestamp: When the message was created
        session_id: Which negotiation session this belongs to
        payload: The actual message content
        
    Example:
        from messages import Offer
        
        offer = Offer(price=300)
        envelope = MessageEnvelope(
            sender="buyer",
            recipient="seller",
            session_id="session_123",
            payload=offer,
        )
    """
    sender: str
    recipient: str
    session_id: str
    payload: NegotiationMessage
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Serialize envelope to dictionary."""
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": to_dict(self.payload),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MessageEnvelope":
        """Deserialize envelope from dictionary."""
        return cls(
            id=data["id"],
            sender=data["sender"],
            recipient=data["recipient"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            payload=parse_message(data["payload"]),
        )


def create_envelope(
    sender: str,
    recipient: str,
    session_id: str,
    payload: NegotiationMessage,
) -> MessageEnvelope:
    """
    Factory function to create an envelope.
    
    Example:
        envelope = create_envelope(
            sender="buyer",
            recipient="seller",
            session_id="sess_001",
            payload=Offer(price=300),
        )
    """
    return MessageEnvelope(
        sender=sender,
        recipient=recipient,
        session_id=session_id,
        payload=payload,
    )
