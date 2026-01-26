"""
Transport Channel
=================

Simple in-memory message channel for local communication.

Why in-memory is fine for learning:
1. Transport complexity doesn't solve protocol problems
2. The same protocol works over any transport
3. Testing is easier with in-memory channels

In production, swap this for:
- WebSockets (real-time)
- HTTP (request/response)
- Message queues (durability)

But the PROTOCOL stays the same.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
from threading import Lock
from uuid import uuid4


@dataclass
class Message:
    """A message in the channel."""
    id: str = field(default_factory=lambda: str(uuid4()))
    sender: str = ""
    recipient: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # For request/response pairing


class LocalChannel:
    """
    In-memory message channel.
    
    This demonstrates transport as a separate concern.
    The channel moves bytes - it doesn't understand what's in them.
    """
    
    def __init__(self):
        self._messages: List[Message] = []
        self._subscribers: Dict[str, List[Callable[[Message], None]]] = {}
        self._lock = Lock()
    
    def send(self, message: Message) -> None:
        """
        Send a message through the channel.
        
        The message is already validated by protocol layer.
        Transport just moves it.
        """
        with self._lock:
            self._messages.append(message)
            
            # Notify subscribers
            recipient = message.recipient
            if recipient in self._subscribers:
                for callback in self._subscribers[recipient]:
                    try:
                        callback(message)
                    except Exception:
                        pass  # Transport doesn't care about handler errors
    
    def subscribe(
        self,
        recipient: str,
        callback: Callable[[Message], None],
    ) -> None:
        """Subscribe to messages for a recipient."""
        with self._lock:
            if recipient not in self._subscribers:
                self._subscribers[recipient] = []
            self._subscribers[recipient].append(callback)
    
    def get_messages(
        self,
        recipient: Optional[str] = None,
        sender: Optional[str] = None,
    ) -> List[Message]:
        """Get messages, optionally filtered."""
        with self._lock:
            msgs = self._messages.copy()
        
        if recipient:
            msgs = [m for m in msgs if m.recipient == recipient]
        if sender:
            msgs = [m for m in msgs if m.sender == sender]
        
        return msgs
    
    def get_conversation(self, party1: str, party2: str) -> List[Message]:
        """Get all messages between two parties."""
        with self._lock:
            return [
                m for m in self._messages
                if (m.sender == party1 and m.recipient == party2) or
                   (m.sender == party2 and m.recipient == party1)
            ]
    
    def clear(self) -> None:
        """Clear all messages (for testing)."""
        with self._lock:
            self._messages.clear()
            self._subscribers.clear()
