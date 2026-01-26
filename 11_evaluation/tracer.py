"""
Observability Tracer
====================

Traces negotiation execution for debugging and analysis.

Uses LangSmith when available, falls back to simple logging.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import contextmanager

# Try to import LangSmith
try:
    from langsmith import traceable, Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    traceable = lambda **kwargs: lambda f: f  # No-op decorator


@dataclass
class TraceRecord:
    """A single trace record."""
    timestamp: datetime
    event_type: str
    data: Dict[str, Any]


@dataclass
class NegotiationTrace:
    """Complete trace of a negotiation."""
    session_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    records: List[TraceRecord] = field(default_factory=list)
    
    def add_event(self, event_type: str, **data) -> None:
        """Add an event to the trace."""
        self.records.append(TraceRecord(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            data=data,
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "records": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "event_type": r.event_type,
                    "data": r.data,
                }
                for r in self.records
            ],
        }


class NegotiationTracer:
    """
    Tracer for negotiation observability.
    
    Integrates with LangSmith when available.
    """
    
    def __init__(self, project_name: str = "agent-negotiation"):
        self.project_name = project_name
        self.traces: Dict[str, NegotiationTrace] = {}
        
        # Initialize LangSmith if available and configured
        self._langsmith_client = None
        if LANGSMITH_AVAILABLE and os.getenv("LANGCHAIN_API_KEY"):
            try:
                self._langsmith_client = Client()
            except Exception:
                pass
    
    def start_trace(self, session_id: str) -> NegotiationTrace:
        """Start a new trace."""
        trace = NegotiationTrace(session_id=session_id)
        trace.add_event("session_start")
        self.traces[session_id] = trace
        return trace
    
    def end_trace(self, session_id: str) -> Optional[NegotiationTrace]:
        """End a trace."""
        trace = self.traces.get(session_id)
        if trace:
            trace.ended_at = datetime.utcnow()
            trace.add_event("session_end")
        return trace
    
    def log_turn(
        self,
        session_id: str,
        turn: int,
        agent: str,
        message_type: str,
        price: Optional[float] = None,
        **extra,
    ) -> None:
        """Log a turn in the negotiation."""
        trace = self.traces.get(session_id)
        if trace:
            trace.add_event(
                "turn",
                turn=turn,
                agent=agent,
                message_type=message_type,
                price=price,
                **extra,
            )
    
    def log_outcome(
        self,
        session_id: str,
        agreed: bool,
        final_price: Optional[float] = None,
        turns: int = 0,
        reason: Optional[str] = None,
    ) -> None:
        """Log the final outcome."""
        trace = self.traces.get(session_id)
        if trace:
            trace.add_event(
                "outcome",
                agreed=agreed,
                final_price=final_price,
                turns=turns,
                reason=reason,
            )
    
    def get_trace(self, session_id: str) -> Optional[NegotiationTrace]:
        """Get a trace by session ID."""
        return self.traces.get(session_id)


# Global tracer instance
_global_tracer: Optional[NegotiationTracer] = None


def get_tracer() -> NegotiationTracer:
    """Get the global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = NegotiationTracer()
    return _global_tracer


@contextmanager
def trace_negotiation(session_id: str):
    """
    Context manager for tracing a negotiation.
    
    Usage:
        with trace_negotiation("session-123") as trace:
            run_negotiation()
    """
    tracer = get_tracer()
    trace = tracer.start_trace(session_id)
    
    try:
        yield trace
    finally:
        tracer.end_trace(session_id)
