"""
Coordination Policy (ACP)
=========================

Explicit governance code that defines what actions are allowed.

This is NOT orchestration (who runs when).
This is NOT the FSM (termination).
This is NOT protocol (message validation).

This IS:
- Domain-specific rules
- Explicit, testable code
- Separate from execution flow
- The "business rules" of negotiation
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Any


class PolicyViolation(Enum):
    """Types of policy violations."""
    WRONG_TURN = auto()           # Not this agent's turn
    INVALID_MESSAGE_TYPE = auto() # Can't send this message type
    PRICE_INCREASED = auto()      # Seller raised price (not allowed)
    PRICE_DECREASED = auto()      # Buyer lowered offer (not allowed)
    BELOW_MINIMUM = auto()        # Below seller's minimum
    ABOVE_MAXIMUM = auto()        # Above buyer's maximum
    NEGOTIATION_ENDED = auto()    # Trying to act after terminal


@dataclass
class PolicyResult:
    """Result of a policy check."""
    allowed: bool
    violation: Optional[PolicyViolation] = None
    reason: str = ""


class CoordinationPolicy:
    """
    Agent Coordination Policy for negotiations.
    
    This class encodes the RULES of negotiation, separate from:
    - Execution flow (orchestration)
    - State transitions (FSM)
    - Message validation (protocol)
    
    Rules:
    ------
    1. Turn-taking: Only the expected party can act
    2. Message types: Only certain messages allowed per state
    3. Price direction: Prices must move toward agreement
    4. Bounds: Prices must stay within limits
    """
    
    def __init__(
        self,
        buyer_max_price: float = 450.0,
        seller_min_price: float = 350.0,
        require_price_progress: bool = True,
    ):
        self.buyer_max_price = buyer_max_price
        self.seller_min_price = seller_min_price
        self.require_price_progress = require_price_progress
    
    def validate_turn(
        self,
        actor: str,
        expected_actor: str,
        is_terminal: bool = False,
    ) -> PolicyResult:
        """
        Rule 1: Only the expected party can act.
        """
        if is_terminal:
            return PolicyResult(
                allowed=False,
                violation=PolicyViolation.NEGOTIATION_ENDED,
                reason="Negotiation has ended"
            )
        
        if actor != expected_actor:
            return PolicyResult(
                allowed=False,
                violation=PolicyViolation.WRONG_TURN,
                reason=f"Expected {expected_actor}, got {actor}"
            )
        
        return PolicyResult(allowed=True)
    
    def validate_buyer_offer(
        self,
        price: float,
        previous_offer: Optional[float] = None,
    ) -> PolicyResult:
        """
        Rule 3a: Buyer offers must increase (move toward agreement).
        Rule 4a: Buyer cannot exceed maximum.
        """
        if price > self.buyer_max_price:
            return PolicyResult(
                allowed=False,
                violation=PolicyViolation.ABOVE_MAXIMUM,
                reason=f"Offer ${price} exceeds buyer max ${self.buyer_max_price}"
            )
        
        if self.require_price_progress and previous_offer is not None:
            if price < previous_offer:
                return PolicyResult(
                    allowed=False,
                    violation=PolicyViolation.PRICE_DECREASED,
                    reason=f"Buyer offer decreased: ${previous_offer} → ${price}"
                )
        
        return PolicyResult(allowed=True)
    
    def validate_seller_counter(
        self,
        price: float,
        previous_counter: Optional[float] = None,
    ) -> PolicyResult:
        """
        Rule 3b: Seller counters must decrease (move toward agreement).
        Rule 4b: Seller cannot go below minimum.
        """
        if price < self.seller_min_price:
            return PolicyResult(
                allowed=False,
                violation=PolicyViolation.BELOW_MINIMUM,
                reason=f"Counter ${price} below seller min ${self.seller_min_price}"
            )
        
        if self.require_price_progress and previous_counter is not None:
            if price > previous_counter:
                return PolicyResult(
                    allowed=False,
                    violation=PolicyViolation.PRICE_INCREASED,
                    reason=f"Seller counter increased: ${previous_counter} → ${price}"
                )
        
        return PolicyResult(allowed=True)
    
    def validate_action(
        self,
        actor: str,
        expected_actor: str,
        message_type: str,
        price: Optional[float] = None,
        previous_offer: Optional[float] = None,
        previous_counter: Optional[float] = None,
        is_terminal: bool = False,
    ) -> PolicyResult:
        """
        Validate a complete action against all rules.
        
        This is the main entry point for policy validation.
        """
        # Rule 1: Turn validation
        result = self.validate_turn(actor, expected_actor, is_terminal)
        if not result.allowed:
            return result
        
        # Rule 3 & 4: Price-specific validation
        if message_type == "offer" and actor == "buyer" and price is not None:
            return self.validate_buyer_offer(price, previous_offer)
        
        if message_type == "counter" and actor == "seller" and price is not None:
            return self.validate_seller_counter(price, previous_counter)
        
        return PolicyResult(allowed=True)
