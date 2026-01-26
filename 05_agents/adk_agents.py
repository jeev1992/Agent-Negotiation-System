"""
Google ADK Agent Definitions
============================

This file defines the LLM-powered ADK agents for the negotiation system.

These agents use Google's Gemini model for decision-making, as opposed to
the deterministic strategies in buyer.py and seller.py.

Structure:
    - root_agent: Orchestrates the negotiation
    - buyer_agent: Negotiates to buy (sub-agent)
    - seller_agent: Negotiates to sell (sub-agent)

Two modes of operation:
    1. Deterministic (buyer.py, seller.py): Testable, no API needed
    2. LLM-powered (this file): Uses Gemini, requires GOOGLE_API_KEY

Run with:
    adk web                     # Web UI
    adk run 10_runtime          # CLI
    python -m 10_runtime.runner --mode adk  # Programmatic
"""

from typing import Dict, Any

# Try to import ADK - it's optional
try:
    from google.adk.agents import Agent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    Agent = None


# ============================================================================
# TOOLS - Functions the agents can call
# ============================================================================

def get_pricing_rules(product_id: str = "enterprise-license") -> Dict[str, Any]:
    """
    Get pricing rules from MCP (grounded context).
    
    This is a TOOL the agent calls to get authoritative data.
    Prevents hallucination of pricing information.
    
    Args:
        product_id: The product to get pricing for
        
    Returns:
        dict with base_price, min_price, max_discount_percent
    """
    # In production, this would query a real database via MCP
    pricing_data = {
        "enterprise-license": {
            "product_id": "enterprise-license",
            "base_price": 500.0,
            "min_price": 350.0,
            "max_discount_percent": 30.0,
            "requires_approval_below": 375.0,
        }
    }
    
    if product_id not in pricing_data:
        return {
            "status": "error",
            "error_message": f"Unknown product: {product_id}"
        }
    
    return {
        "status": "success",
        "pricing": pricing_data[product_id]
    }


def make_offer(price: float, message: str = "") -> Dict[str, Any]:
    """
    Make an offer in the negotiation.
    
    Args:
        price: The price being offered
        message: Optional message to accompany the offer
        
    Returns:
        dict with the offer details
    """
    return {
        "status": "success",
        "action": "offer",
        "price": price,
        "message": message
    }


def make_counter_offer(price: float, original_price: float, message: str = "") -> Dict[str, Any]:
    """
    Make a counter-offer in response to an offer.
    
    Args:
        price: The counter-offer price
        original_price: The price being countered
        message: Optional message
        
    Returns:
        dict with counter-offer details
    """
    return {
        "status": "success", 
        "action": "counter",
        "price": price,
        "original_price": original_price,
        "message": message
    }


def accept_offer(price: float) -> Dict[str, Any]:
    """
    Accept an offer and close the negotiation.
    
    Args:
        price: The accepted price
        
    Returns:
        dict with acceptance details
    """
    return {
        "status": "success",
        "action": "accept",
        "price": price,
        "message": f"Deal closed at ${price:.2f}"
    }


def reject_offer(reason: str) -> Dict[str, Any]:
    """
    Reject the negotiation and walk away.
    
    Args:
        reason: Why the offer is being rejected
        
    Returns:
        dict with rejection details
    """
    return {
        "status": "success",
        "action": "reject",
        "reason": reason
    }


def check_negotiation_state(
    current_turn: int,
    max_turns: int,
    buyer_offer: float = None,
    seller_counter: float = None,
) -> Dict[str, Any]:
    """
    Check the current state of the negotiation.
    
    Args:
        current_turn: Current turn number
        max_turns: Maximum allowed turns
        buyer_offer: Last offer from buyer
        seller_counter: Last counter from seller
        
    Returns:
        dict with state information
    """
    turns_remaining = max_turns - current_turn
    
    state = {
        "status": "success",
        "current_turn": current_turn,
        "max_turns": max_turns,
        "turns_remaining": turns_remaining,
        "is_final_turn": turns_remaining <= 1,
    }
    
    if buyer_offer and seller_counter:
        state["gap"] = seller_counter - buyer_offer
        state["midpoint"] = (buyer_offer + seller_counter) / 2
    
    return state


# ============================================================================
# AGENT DEFINITIONS (only if ADK is available)
# ============================================================================

if ADK_AVAILABLE:
    # Buyer Agent
    buyer_agent = Agent(
        name="buyer_agent",
        model="gemini-2.0-flash",
        description="A buyer agent negotiating to purchase a software license.",
        instruction="""You are a buyer negotiating to purchase an enterprise software license.

Your goal is to get the best price possible while staying within your budget.

RULES:
1. Your maximum budget is $450. NEVER offer more than this.
2. Start with a low offer (around 60% of your max budget).
3. Increase your offers gradually (about 8-10% each turn).
4. Always use the make_offer or accept_offer tools to take action.
5. If the seller's price is at or below your budget, consider accepting.
6. Keep track of the negotiation state using check_negotiation_state.

STRATEGY:
- Be patient but assertive
- Don't reveal your maximum budget
- If running out of turns, make a final strong offer
""",
        tools=[
            make_offer,
            accept_offer,
            reject_offer,
            check_negotiation_state,
        ],
    )


    # Seller Agent
    seller_agent = Agent(
        name="seller_agent", 
        model="gemini-2.0-flash",
        description="A seller agent negotiating to sell a software license.",
        instruction="""You are a seller negotiating to sell an enterprise software license.

Your goal is to maximize the sale price while closing the deal.

RULES:
1. ALWAYS call get_pricing_rules first to know your minimum price. Never go below it.
2. Start with your asking price (from pricing rules).
3. Decrease your counter-offers gradually (about 5% each turn).
4. Always use make_counter_offer or accept_offer tools to respond.
5. If buyer's offer is at or above your minimum, consider accepting.
6. Check negotiation state to know how many turns remain.

STRATEGY:
- Query pricing rules to get your floor price
- Be firm but willing to negotiate
- If running out of turns, consider offers closer to your minimum
- Never counter with a HIGHER price than your previous counter
""",
        tools=[
            get_pricing_rules,
            make_counter_offer,
            accept_offer,
            reject_offer,
            check_negotiation_state,
        ],
    )


    # Root agent that orchestrates the negotiation
    root_agent = Agent(
        name="negotiation_orchestrator",
        model="gemini-2.0-flash",
        description="Orchestrates a negotiation between buyer and seller agents.",
        instruction="""You are a negotiation orchestrator managing a price negotiation.

Your role is to:
1. Facilitate the negotiation between buyer and seller
2. Ensure turns alternate properly (buyer first, then seller, etc.)
3. Track the state of the negotiation
4. Announce when a deal is reached or the negotiation fails

The negotiation flow:
1. Buyer makes an initial offer
2. Seller responds with counter-offer or acceptance
3. Continue until: deal reached, rejection, or max turns exceeded

Keep the negotiation moving and summarize progress after each turn.
""",
        sub_agents=[buyer_agent, seller_agent],
        tools=[check_negotiation_state],
    )

else:
    # Placeholders when ADK is not available
    buyer_agent = None
    seller_agent = None
    root_agent = None
