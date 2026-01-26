"""
Orchestration Graph
===================

LangGraph-based orchestration for negotiation.

The graph structure:

    ┌─────────┐
    │  START  │
    └────┬────┘
         │
         ▼
    ┌─────────┐     ┌─────────────┐
    │  buyer  │────►│   router    │
    └─────────┘     └──────┬──────┘
         ▲                 │
         │                 ├──► END (agreed)
         │                 │
         │                 ├──► END (failed)
         │                 │
    ┌────┴────┐            │
    │  seller │◄───────────┘
    └─────────┘
"""

from typing import TypedDict, Dict, Any, Optional, List, Literal
from dataclasses import dataclass

# Try to import LangGraph
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"


# ============================================================================
# Graph State
# ============================================================================

class NegotiationState(TypedDict):
    """State managed by the graph."""
    # Configuration
    buyer_max_price: float
    seller_min_price: float
    seller_asking_price: float
    max_turns: int
    
    # Current state
    current_turn: int
    whose_turn: Literal["buyer", "seller"]
    current_offer: float
    previous_buyer_offer: Optional[float]
    previous_seller_counter: Optional[float]
    
    # Results
    agreed: bool
    final_price: Optional[float]
    failure_reason: Optional[str]
    
    # Message log
    messages: List[Dict[str, Any]]


# ============================================================================
# Node Functions
# ============================================================================

def buyer_node(state: NegotiationState) -> Dict[str, Any]:
    """
    Execute buyer's turn.
    
    This node:
    1. Reads current state
    2. Calls buyer strategy (separate module)
    3. Returns state updates
    
    It does NOT:
    - Decide whose turn is next (that's routing)
    - Check if negotiation should end (that's router)
    """
    from _5_agents import buyer_strategy
    
    # Get buyer's decision
    response = buyer_strategy(
        current_offer=state["current_offer"],
        max_price=state["buyer_max_price"],
        turn=state["current_turn"],
        max_turns=state["max_turns"],
        previous_offer=state.get("previous_buyer_offer"),
    )
    
    # Build message record
    message = {
        "turn": state["current_turn"],
        "agent": "buyer",
        "message": response,
    }
    
    # Return state updates
    updates = {
        "messages": state["messages"] + [message],
        "whose_turn": "seller",
    }
    
    if response.get("type") == "offer":
        updates["previous_buyer_offer"] = response["price"]
    elif response.get("type") == "accept":
        updates["agreed"] = True
        updates["final_price"] = response["price"]
    elif response.get("type") == "reject":
        updates["failure_reason"] = "Buyer rejected"
    
    return updates


def seller_node(state: NegotiationState) -> Dict[str, Any]:
    """Execute seller's turn."""
    from _5_agents import seller_strategy
    
    # Get the buyer's last offer from messages
    buyer_offer = state.get("previous_buyer_offer", state["seller_asking_price"])
    
    # Get seller's decision
    response = seller_strategy(
        buyer_offer=buyer_offer,
        min_price=state["seller_min_price"],
        asking_price=state["seller_asking_price"],
        turn=state["current_turn"],
        max_turns=state["max_turns"],
        previous_counter=state.get("previous_seller_counter"),
    )
    
    # Build message record
    message = {
        "turn": state["current_turn"],
        "agent": "seller",
        "message": response,
    }
    
    # Return state updates
    updates = {
        "messages": state["messages"] + [message],
        "whose_turn": "buyer",
        "current_turn": state["current_turn"] + 1,
    }
    
    if response.get("type") == "counter":
        updates["current_offer"] = response["price"]
        updates["previous_seller_counter"] = response["price"]
    elif response.get("type") == "accept":
        updates["agreed"] = True
        updates["final_price"] = response["price"]
    elif response.get("type") == "reject":
        updates["failure_reason"] = "Seller rejected"
    
    return updates


def router(state: NegotiationState) -> str:
    """
    Determine next node based on state.
    
    This is pure ROUTING logic - separate from business logic.
    """
    # Check for terminal states
    if state.get("agreed"):
        return "end"
    
    if state.get("failure_reason"):
        return "end"
    
    if state["current_turn"] >= state["max_turns"]:
        return "end"
    
    # Continue to appropriate party
    if state["whose_turn"] == "seller":
        return "seller"
    else:
        return "buyer"


# ============================================================================
# Graph Builder
# ============================================================================

def create_negotiation_graph():
    """Create the LangGraph negotiation graph."""
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("LangGraph not available. Install with: pip install langgraph")
    
    graph = StateGraph(NegotiationState)
    
    # Add nodes
    graph.add_node("buyer", buyer_node)
    graph.add_node("seller", seller_node)
    
    # Entry point
    graph.set_entry_point("buyer")
    
    # Conditional edges from buyer
    graph.add_conditional_edges(
        "buyer",
        router,
        {
            "seller": "seller",
            "buyer": "buyer",
            "end": END,
        }
    )
    
    # Conditional edges from seller
    graph.add_conditional_edges(
        "seller",
        router,
        {
            "buyer": "buyer",
            "seller": "seller",
            "end": END,
        }
    )
    
    return graph.compile()


# ============================================================================
# Main Entry Point (called by Runtime)
# ============================================================================

def run_negotiation(
    buyer_max_price: float = 450.0,
    seller_min_price: float = 350.0,
    seller_asking_price: float = 500.0,
    max_turns: int = 10,
    strategy: str = "rule",
    mcp_server: Any = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run a negotiation using the orchestration graph.
    
    This is called by the Runtime layer.
    """
    # Initial state
    initial_state: NegotiationState = {
        "buyer_max_price": buyer_max_price,
        "seller_min_price": seller_min_price,
        "seller_asking_price": seller_asking_price,
        "max_turns": max_turns,
        "current_turn": 0,
        "whose_turn": "buyer",
        "current_offer": seller_asking_price,
        "previous_buyer_offer": None,
        "previous_seller_counter": None,
        "agreed": False,
        "final_price": None,
        "failure_reason": None,
        "messages": [],
    }
    
    if LANGGRAPH_AVAILABLE:
        # Use LangGraph
        graph = create_negotiation_graph()
        final_state = graph.invoke(initial_state)
    else:
        # Fallback to simple loop
        final_state = _run_simple_loop(initial_state, verbose)
    
    # Print messages if verbose
    if verbose:
        for msg in final_state["messages"]:
            agent = msg["agent"]
            content = msg["message"]
            print(f"[Turn {msg['turn'] + 1}] {agent.capitalize()}: {content}")
        
        print()
        if final_state["agreed"]:
            print(f"[Result] Agreement: ${final_state['final_price']:.2f}")
        else:
            reason = final_state.get("failure_reason", "Max turns reached")
            print(f"[Result] No agreement ({reason})")
    
    return {
        "agreed": final_state["agreed"],
        "final_price": final_state["final_price"],
        "turns": final_state["current_turn"],
        "messages": final_state["messages"],
    }


def _run_simple_loop(state: NegotiationState, verbose: bool) -> NegotiationState:
    """Fallback when LangGraph is not available."""
    while True:
        # Check termination
        if state["agreed"] or state.get("failure_reason"):
            break
        if state["current_turn"] >= state["max_turns"]:
            state["failure_reason"] = "Max turns exceeded"
            break
        
        # Run appropriate node
        if state["whose_turn"] == "buyer":
            updates = buyer_node(state)
        else:
            updates = seller_node(state)
        
        # Apply updates
        for key, value in updates.items():
            state[key] = value
    
    return state
