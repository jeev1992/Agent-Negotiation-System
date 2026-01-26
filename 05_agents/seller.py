"""
Seller Agent Strategy
=====================

Pure decision logic for the seller.

This is STRATEGY only - no orchestration, no transport.

Key architectural rule:
The seller SHOULD query MCP for grounded context before deciding.
This prevents hallucination of pricing rules.
"""

from typing import Optional, Dict, Any


def seller_strategy(
    buyer_offer: float,
    min_price: float,
    asking_price: float,
    turn: int,
    max_turns: int,
    previous_counter: Optional[float] = None,
    mcp_server: Any = None,
) -> Dict[str, Any]:
    """
    Seller's decision strategy.
    
    Args:
        buyer_offer: Buyer's current offer
        min_price: Seller's minimum acceptable price
        asking_price: Seller's starting/list price
        turn: Current turn (0-indexed)
        max_turns: Maximum turns allowed
        previous_counter: Seller's previous counter (if any)
        mcp_server: Optional MCP server for grounded context
    
    Returns:
        Dict with "type" (counter/accept/reject) and other fields
    
    Strategy:
        1. Accept if buyer_offer >= min_price
        2. Counter with decreasing amounts (5% reduction each turn)
        3. Reject if buyer seems to be going nowhere
    """
    
    # Query MCP for grounded context (if available)
    effective_min = min_price
    if mcp_server is not None:
        try:
            pricing = mcp_server.get_pricing_rules("enterprise-license")
            effective_min = pricing.get("effective_min", min_price)
        except Exception:
            pass  # Fall back to provided min_price
    
    # Accept if offer meets minimum
    if buyer_offer >= effective_min:
        return {
            "type": "accept",
            "price": buyer_offer,
            "message": "Accepted buyer's offer",
        }
    
    # Calculate counter offer
    if previous_counter is None:
        # First counter: small concession from asking
        new_counter = asking_price * 0.98
    else:
        # Subsequent counters: move toward buyer
        gap = previous_counter - buyer_offer
        concession = gap * 0.3  # Give up 30% of the gap
        new_counter = previous_counter - concession
    
    # Don't go below minimum
    new_counter = max(new_counter, effective_min)
    new_counter = round(new_counter, 2)
    
    # Check if negotiation is hopeless
    if turn >= max_turns - 2:
        # Getting close to end, consider final stance
        if buyer_offer < effective_min * 0.8:
            # Buyer is way below minimum, not worth continuing
            return {
                "type": "reject",
                "reason": "Offer too far below acceptable range",
            }
    
    return {
        "type": "counter",
        "price": new_counter,
        "original_price": buyer_offer,
        "message": f"Counter offer #{turn + 1}",
    }


class SellerStrategy:
    """
    Object-oriented wrapper for seller strategy.
    
    Provides stateful tracking of negotiation progress.
    """
    
    def __init__(self, min_price: float, asking_price: float = None, mcp_server: Any = None):
        self.min_price = min_price
        self.asking_price = asking_price or min_price * 1.4
        self.mcp_server = mcp_server
        self.previous_counter = None
        self.turn = 0
    
    def decide(self, buyer_offer: float, max_turns: int = 10) -> Dict[str, Any]:
        """Make a decision based on buyer's offer."""
        result = seller_strategy(
            buyer_offer=buyer_offer,
            min_price=self.min_price,
            asking_price=self.asking_price,
            turn=self.turn,
            max_turns=max_turns,
            previous_counter=self.previous_counter,
            mcp_server=self.mcp_server,
        )
        
        if result["type"] == "counter":
            self.previous_counter = result["price"]
            self.turn += 1
        
        return result
    
    def reset(self):
        """Reset state for new negotiation."""
        self.previous_counter = None
        self.turn = 0
