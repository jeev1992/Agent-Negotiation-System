"""
Buyer Agent Strategy
====================

Pure decision logic for the buyer.

This is STRATEGY only - no orchestration, no transport.
"""

from typing import Optional, Dict, Any


def buyer_strategy(
    current_offer: float,
    max_price: float,
    turn: int,
    max_turns: int,
    previous_offer: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Buyer's decision strategy.
    
    Args:
        current_offer: Seller's current price
        max_price: Buyer's maximum budget
        turn: Current turn (0-indexed)
        max_turns: Maximum turns allowed
        previous_offer: Buyer's previous offer (if any)
    
    Returns:
        Dict with "type" (offer/accept/reject) and other fields
    
    Strategy:
        1. Start at 60% of max_price
        2. Increase by 8% each turn
        3. Accept if seller's price <= max_price
        4. Reject if no progress possible
    """
    
    # If seller's price is acceptable, accept
    if current_offer <= max_price:
        return {
            "type": "accept",
            "price": current_offer,
            "message": "Accepted seller's price",
        }
    
    # Calculate new offer
    if previous_offer is None:
        # First offer: start at 60% of max
        new_offer = max_price * 0.60
    else:
        # Subsequent offers: increase by 8%
        new_offer = previous_offer * 1.08
    
    # Cap at max price
    new_offer = min(new_offer, max_price)
    new_offer = round(new_offer, 2)
    
    # Check if we've reached our max and seller won't budge
    if turn >= max_turns - 1 and new_offer >= max_price * 0.95:
        # Last turn, make final offer at max
        return {
            "type": "offer",
            "price": max_price,
            "message": "Final offer at maximum budget",
        }
    
    return {
        "type": "offer",
        "price": new_offer,
        "message": f"Offer #{turn + 1}",
    }


class BuyerStrategy:
    """
    Object-oriented wrapper for buyer strategy.
    
    Provides stateful tracking of negotiation progress.
    """
    
    def __init__(self, max_price: float, initial_offer: float = None):
        self.max_price = max_price
        self.initial_offer = initial_offer or max_price * 0.6
        self.previous_offer = None
        self.turn = 0
    
    def decide(self, seller_price: float, max_turns: int = 10) -> Dict[str, Any]:
        """Make a decision based on seller's price."""
        result = buyer_strategy(
            current_offer=seller_price,
            max_price=self.max_price,
            turn=self.turn,
            max_turns=max_turns,
            previous_offer=self.previous_offer,
        )
        
        if result["type"] == "offer":
            self.previous_offer = result["price"]
            self.turn += 1
        
        return result
    
    def reset(self):
        """Reset state for new negotiation."""
        self.previous_offer = None
        self.turn = 0
