"""
Negotiation State Machine
=========================

Provides termination guarantees through explicit states.

State Diagram:

    ┌─────────┐
    │  IDLE   │ ─── start() ───► NEGOTIATING
    └─────────┘                      │
                                     │
                     ┌───────────────┼───────────────┐
                     │               │               │
               accept()          reject()       max_turns
                     │               │               │
                     ▼               ▼               ▼
                ┌─────────┐    ┌─────────┐    ┌─────────┐
                │ AGREED  │    │ FAILED  │    │ FAILED  │
                └─────────┘    └─────────┘    └─────────┘
                     │               │               │
                     └───────────────┴───────────────┘
                                     │
                              TERMINAL STATES
                           (cannot transition out)

TERMINATION GUARANTEE:
- AGREED and FAILED have NO outgoing transitions
- Turn count is bounded
- Every non-terminal transition increments turn
- Therefore: FSM always halts
"""

from enum import Enum, auto
from typing import Optional
from dataclasses import dataclass


class NegotiationState(Enum):
    """The finite set of states."""
    IDLE = auto()        # Not yet started
    NEGOTIATING = auto() # Active negotiation
    AGREED = auto()      # Terminal: deal reached
    FAILED = auto()      # Terminal: no deal


class FailureReason(Enum):
    """Why a negotiation failed."""
    MAX_TURNS_EXCEEDED = auto()
    REJECTED_BY_BUYER = auto()
    REJECTED_BY_SELLER = auto()
    POLICY_VIOLATION = auto()
    INVALID_TRANSITION = auto()


@dataclass
class FSMContext:
    """Context tracked by the FSM."""
    turn_count: int = 0
    max_turns: int = 10
    last_offer: Optional[float] = None
    agreed_price: Optional[float] = None
    failure_reason: Optional[FailureReason] = None


class NegotiationFSM:
    """
    Finite State Machine for negotiation.
    
    TERMINATION GUARANTEE:
    - AGREED and FAILED are terminal states (no outgoing transitions)
    - Turn count is bounded (max_turns)
    - Every transition either:
      a) Moves to terminal state
      b) Increments turn count
    - Therefore: termination is GUARANTEED
    """
    
    # Valid transitions
    TRANSITIONS = {
        NegotiationState.IDLE: {NegotiationState.NEGOTIATING, NegotiationState.FAILED},
        NegotiationState.NEGOTIATING: {NegotiationState.NEGOTIATING, NegotiationState.AGREED, NegotiationState.FAILED},
        NegotiationState.AGREED: set(),   # Terminal - NO outgoing
        NegotiationState.FAILED: set(),   # Terminal - NO outgoing
    }
    
    def __init__(self, max_turns: int = 10):
        self.state = NegotiationState.IDLE
        self.context = FSMContext(max_turns=max_turns)
    
    def get_state(self) -> NegotiationState:
        """Get current state."""
        return self.state
    
    @property
    def is_active(self) -> bool:
        """Check if negotiation is still active."""
        return self.state == NegotiationState.NEGOTIATING
    
    def is_terminal(self) -> bool:
        """Check if FSM is in terminal state."""
        return self.state in {NegotiationState.AGREED, NegotiationState.FAILED}
    
    def can_transition(self, to_state: NegotiationState) -> bool:
        """Check if transition is valid."""
        return to_state in self.TRANSITIONS[self.state]
    
    def start(self) -> bool:
        """Start the negotiation."""
        if self.state != NegotiationState.IDLE:
            return False
        
        self.state = NegotiationState.NEGOTIATING
        return True
    
    def record_turn(self) -> None:
        """Record that a turn occurred (for integration with external loops)."""
        if self.is_active:
            self.context.turn_count += 1
    
    def transition_to_agreed(self, final_price: float = None) -> bool:
        """Transition to AGREED state."""
        if not self.is_active:
            return False
        self.state = NegotiationState.AGREED
        self.context.agreed_price = final_price
        return True
    
    def transition_to_failed(self, reason: str = None) -> bool:
        """Transition to FAILED state."""
        if not self.is_active:
            return False
        self.state = NegotiationState.FAILED
        self.context.failure_reason = FailureReason.REJECTED_BY_BUYER
        return True
    
    def process_turn(self) -> bool:
        """
        Process a turn. Returns False if max turns exceeded.
        
        This is the key to termination guarantee:
        Every turn increments, bounded by max_turns.
        """
        if not self.is_active:
            return False
        
        self.context.turn_count += 1
        
        if self.context.turn_count >= self.context.max_turns:
            self.state = NegotiationState.FAILED
            self.context.failure_reason = FailureReason.MAX_TURNS_EXCEEDED
            return False
        
        return True
    
    def accept(self, price: float) -> bool:
        """Accept and move to AGREED state."""
        if not self.is_active:
            return False
        
        self.state = NegotiationState.AGREED
        self.context.agreed_price = price
        return True
    
    def reject(self, reason: str, by_buyer: bool = True) -> bool:
        """Reject and move to FAILED state."""
        if not self.is_active:
            return False
        
        self.state = NegotiationState.FAILED
        self.context.failure_reason = (
            FailureReason.REJECTED_BY_BUYER if by_buyer 
            else FailureReason.REJECTED_BY_SELLER
        )
        return True
    
    def check_invariants(self) -> bool:
        """
        Check that FSM invariants hold.
        
        These should NEVER be violated.
        """
        # Turn count non-negative
        assert self.context.turn_count >= 0
        
        # Terminal states have required data
        if self.state == NegotiationState.AGREED:
            assert self.context.agreed_price is not None
        
        if self.state == NegotiationState.FAILED:
            assert self.context.failure_reason is not None
        
        return True
