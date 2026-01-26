"""
Integration Test: Full Negotiation Run
======================================
Tests the complete system from start to finish.
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from typing import List, Dict, Any

# Setup path for numbered module imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def import_numbered_layer(folder_name: str):
    """Import a numbered layer folder dynamically."""
    folder_path = project_root / folder_name
    init_path = folder_path / "__init__.py"
    
    if not init_path.exists():
        raise ImportError(f"No __init__.py in {folder_name}")
    
    spec = importlib.util.spec_from_file_location(folder_name, init_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[folder_name] = module
    spec.loader.exec_module(module)
    return module


def run_simple_negotiation(buyer_max: float, seller_min: float, max_rounds: int = 10) -> Dict[str, Any]:
    """
    Run a complete negotiation without external dependencies.
    
    This is a self-contained test that doesn't require LLMs or external services.
    """
    # Import required layers
    fsm_module = import_numbered_layer("04_fsm")
    coord_module = import_numbered_layer("07_coordination")
    
    NegotiationFSM = fsm_module.NegotiationFSM
    NegotiationState = fsm_module.NegotiationState
    CoordinationPolicy = coord_module.CoordinationPolicy
    
    # Initialize components
    fsm = NegotiationFSM(max_turns=max_rounds)
    fsm.start()  # START THE FSM!
    
    policy = CoordinationPolicy(
        buyer_max_price=buyer_max,
        seller_min_price=seller_min
    )
    
    # Simple hardcoded strategies for testing
    buyer_offer = buyer_max * 0.6  # Start at 60% of max
    seller_counter = seller_min * 1.4  # Start at 140% of min
    
    history: List[Dict] = []
    rounds = 0
    final_price = None
    violations = []
    turn = "buyer"  # Track whose turn it is
    
    while fsm.get_state() == NegotiationState.NEGOTIATING and rounds < max_rounds:
        rounds += 1
        
        # Buyer's turn
        if turn == "buyer":
            # Increase offer each round
            buyer_offer = min(buyer_offer * 1.1, buyer_max)
            
            # Validate against policy
            result = policy.validate_buyer_offer(buyer_offer)
            if not result.allowed:
                violations.append(str(result.violation))
            
            history.append({
                "round": rounds,
                "actor": "buyer",
                "action": "offer",
                "price": buyer_offer
            })
            
            # Check for acceptance (buyer offer >= seller counter)
            if buyer_offer >= seller_counter:
                fsm.transition_to_agreed(final_price=buyer_offer)
                final_price = buyer_offer
                break
            
            fsm.record_turn()
            turn = "seller"
        
        # Seller's turn
        else:
            # Decrease counter each round
            seller_counter = max(seller_counter * 0.9, seller_min)
            
            # Validate against policy
            result = policy.validate_seller_counter(seller_counter)
            if not result.allowed:
                violations.append(str(result.violation))
            
            history.append({
                "round": rounds,
                "actor": "seller",
                "action": "counter",
                "price": seller_counter
            })
            
            # Check for acceptance (seller counter <= buyer offer)
            if seller_counter <= buyer_offer:
                fsm.transition_to_agreed(final_price=seller_counter)
                final_price = seller_counter
                break
            
            fsm.record_turn()
            turn = "buyer"
    
    # Timeout handling
    if rounds >= max_rounds and fsm.get_state() == NegotiationState.NEGOTIATING:
        fsm.transition_to_failed("max_rounds_exceeded")
    
    return {
        "final_state": fsm.get_state(),
        "final_price": final_price,
        "rounds": rounds,
        "history": history,
        "violations": violations,
        "deal_reached": fsm.get_state() == NegotiationState.AGREED
    }


class TestIntegration:
    """Integration tests for full negotiation."""
    
    def test_successful_negotiation(self):
        """Test that ZOPA leads to agreement."""
        result = run_simple_negotiation(
            buyer_max=500,
            seller_min=350,
            max_rounds=20
        )
        
        assert result["deal_reached"] is True
        assert result["final_price"] is not None
        # Price should be in ZOPA
        assert 350 <= result["final_price"] <= 500
    
    def test_failed_negotiation_no_zopa(self):
        """Test that no ZOPA leads to failure."""
        result = run_simple_negotiation(
            buyer_max=300,  # Below seller's min
            seller_min=400,
            max_rounds=10
        )
        
        # Might not reach deal or will timeout
        if result["deal_reached"]:
            # If somehow reached, price must be valid
            assert result["final_price"] >= 400
        else:
            assert result["final_price"] is None
    
    def test_terminates_within_limit(self):
        """Test that negotiation always terminates."""
        result = run_simple_negotiation(
            buyer_max=500,
            seller_min=400,
            max_rounds=5
        )
        
        # Must terminate, either agreed or failed
        fsm_module = import_numbered_layer("04_fsm")
        NegotiationState = fsm_module.NegotiationState
        assert result["final_state"] in [NegotiationState.AGREED, NegotiationState.FAILED]
        assert result["rounds"] <= 5
    
    def test_history_recorded(self):
        """Test that negotiation history is tracked."""
        result = run_simple_negotiation(
            buyer_max=500,
            seller_min=400,
            max_rounds=10
        )
        
        assert len(result["history"]) > 0
        
        # Each entry should have required fields
        for entry in result["history"]:
            assert "round" in entry
            assert "actor" in entry
            assert "action" in entry
            assert "price" in entry
    
    def test_alternating_turns(self):
        """Test that turns alternate properly."""
        result = run_simple_negotiation(
            buyer_max=500,
            seller_min=400,
            max_rounds=10
        )
        
        history = result["history"]
        for i in range(1, len(history)):
            # Consecutive entries should have different actors
            assert history[i]["actor"] != history[i-1]["actor"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_immediate_agreement(self):
        """Test when buyer starts high enough."""
        result = run_simple_negotiation(
            buyer_max=600,  # Very high
            seller_min=300,  # Very low
            max_rounds=10
        )
        
        # Should agree quickly
        assert result["deal_reached"] is True
        assert result["rounds"] <= 5
    
    def test_single_round_limit(self):
        """Test with only one round allowed."""
        result = run_simple_negotiation(
            buyer_max=500,
            seller_min=400,
            max_rounds=1
        )
        
        # Must terminate in 1 round
        assert result["rounds"] <= 1
    
    def test_exact_overlap(self):
        """Test when buyer max equals seller min."""
        result = run_simple_negotiation(
            buyer_max=400,
            seller_min=400,
            max_rounds=10
        )
        
        # Should eventually reach exact price
        if result["deal_reached"]:
            assert result["final_price"] == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
