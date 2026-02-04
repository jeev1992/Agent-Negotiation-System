"""
Tests for ACP Governance Layer (Coordination Policy)
=====================================================
"""

import pytest
import sys
import importlib.util
from pathlib import Path

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


# Import coordination module
coord_module = import_numbered_layer("07_coordination")
CoordinationPolicy = coord_module.CoordinationPolicy
PolicyViolation = coord_module.PolicyViolation
PolicyResult = coord_module.PolicyResult


class TestTurnPolicy:
    """Test turn-taking rules."""
    
    def test_correct_turn_allowed(self):
        """Correct actor should be allowed."""
        policy = CoordinationPolicy()
        result = policy.validate_turn("buyer", "buyer")
        
        assert result.allowed is True
        assert result.violation is None
    
    def test_wrong_turn_rejected(self):
        """Wrong actor should be rejected."""
        policy = CoordinationPolicy()
        result = policy.validate_turn("seller", "buyer")
        
        assert result.allowed is False
        assert result.violation == PolicyViolation.WRONG_TURN
    
    def test_terminal_state_blocks(self):
        """Actions after terminal should be blocked."""
        policy = CoordinationPolicy()
        result = policy.validate_turn("buyer", "buyer", is_terminal=True)
        
        assert result.allowed is False
        assert result.violation == PolicyViolation.NEGOTIATION_ENDED


class TestBuyerPolicy:
    """Test buyer-specific rules."""
    
    def test_offer_within_max_allowed(self):
        """Offer within max should be allowed."""
        policy = CoordinationPolicy(buyer_max_price=450)
        result = policy.validate_buyer_offer(400)
        
        assert result.allowed is True
    
    def test_offer_above_max_rejected(self):
        """Offer above max should be rejected."""
        policy = CoordinationPolicy(buyer_max_price=450)
        result = policy.validate_buyer_offer(500)
        
        assert result.allowed is False
        assert result.violation == PolicyViolation.ABOVE_MAXIMUM
    
    def test_decreasing_offer_rejected(self):
        """Decreasing offer should be rejected."""
        policy = CoordinationPolicy(buyer_max_price=450)
        result = policy.validate_buyer_offer(350, previous_offer=400)
        
        assert result.allowed is False
        assert result.violation == PolicyViolation.PRICE_DECREASED


class TestSellerPolicy:
    """Test seller-specific rules."""
    
    def test_counter_above_min_allowed(self):
        """Counter above min should be allowed."""
        policy = CoordinationPolicy(seller_min_price=350)
        result = policy.validate_seller_counter(400)
        
        assert result.allowed is True
    
    def test_counter_below_min_rejected(self):
        """Counter below min should be rejected."""
        policy = CoordinationPolicy(seller_min_price=350)
        result = policy.validate_seller_counter(300)
        
        assert result.allowed is False
        assert result.violation == PolicyViolation.BELOW_MINIMUM
    
    def test_increasing_counter_rejected(self):
        """Increasing counter should be rejected."""
        policy = CoordinationPolicy(seller_min_price=350)
        result = policy.validate_seller_counter(450, previous_counter=400)
        
        assert result.allowed is False
        assert result.violation == PolicyViolation.PRICE_INCREASED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
