"""
Tests for Agent Strategies
==========================
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


# Import agents module
agents_module = import_numbered_layer("05_agents")
buyer_strategy = agents_module.buyer_strategy
seller_strategy = agents_module.seller_strategy
BuyerStrategy = agents_module.BuyerStrategy
SellerStrategy = agents_module.SellerStrategy


class TestBuyerStrategyFunction:
    """Test buyer strategy pure function."""
    
    def test_accept_good_price(self):
        """Buyer accepts if seller price <= max."""
        result = buyer_strategy(
            current_offer=400,
            max_price=500,
            turn=0,
            max_turns=10
        )
        
        assert result["type"] == "accept"
        assert result["price"] == 400
    
    def test_offer_when_price_too_high(self):
        """Buyer makes offer when seller price > max."""
        result = buyer_strategy(
            current_offer=600,
            max_price=500,
            turn=0,
            max_turns=10
        )
        
        assert result["type"] == "offer"
        assert result["price"] <= 500
    
    def test_first_offer_is_low(self):
        """First offer should be around 60% of max."""
        result = buyer_strategy(
            current_offer=600,
            max_price=500,
            turn=0,
            max_turns=10,
            previous_offer=None
        )
        
        # First offer at 60% of 500 = 300
        assert result["type"] == "offer"
        assert 250 <= result["price"] <= 350
    
    def test_subsequent_offers_increase(self):
        """Subsequent offers should be higher than previous."""
        result = buyer_strategy(
            current_offer=600,
            max_price=500,
            turn=1,
            max_turns=10,
            previous_offer=300
        )
        
        assert result["type"] == "offer"
        assert result["price"] > 300


class TestSellerStrategyFunction:
    """Test seller strategy pure function."""
    
    def test_accept_good_offer(self):
        """Seller accepts if offer >= min price."""
        result = seller_strategy(
            buyer_offer=400,
            min_price=350,
            asking_price=500,
            turn=0,
            max_turns=10
        )
        
        assert result["type"] == "accept"
        assert result["price"] == 400
    
    def test_counter_when_offer_too_low(self):
        """Seller counters when offer < min price."""
        result = seller_strategy(
            buyer_offer=250,
            min_price=350,
            asking_price=500,
            turn=0,
            max_turns=10
        )
        
        assert result["type"] == "counter"
        assert result["price"] >= 350
    
    def test_counter_decreases_over_time(self):
        """Counter offers should decrease as negotiation progresses."""
        first_counter = seller_strategy(
            buyer_offer=250,
            min_price=350,
            asking_price=500,
            turn=0,
            max_turns=10,
            previous_counter=None
        )
        
        second_counter = seller_strategy(
            buyer_offer=300,
            min_price=350,
            asking_price=500,
            turn=1,
            max_turns=10,
            previous_counter=first_counter["price"]
        )
        
        assert first_counter["type"] == "counter"
        assert second_counter["type"] == "counter"
        assert second_counter["price"] < first_counter["price"]


class TestBuyerStrategyClass:
    """Test BuyerStrategy stateful class."""
    
    def test_decide_accept(self):
        """Test accept decision."""
        buyer = BuyerStrategy(max_price=500)
        result = buyer.decide(seller_price=400)
        
        assert result["type"] == "accept"
    
    def test_decide_offer(self):
        """Test offer decision."""
        buyer = BuyerStrategy(max_price=500)
        result = buyer.decide(seller_price=600)
        
        assert result["type"] == "offer"
        assert result["price"] <= 500
    
    def test_tracks_turn(self):
        """Test turn tracking."""
        buyer = BuyerStrategy(max_price=500)
        
        assert buyer.turn == 0
        buyer.decide(seller_price=600)
        assert buyer.turn == 1
    
    def test_reset(self):
        """Test reset functionality."""
        buyer = BuyerStrategy(max_price=500)
        buyer.decide(seller_price=600)
        buyer.decide(seller_price=580)
        
        buyer.reset()
        assert buyer.turn == 0
        assert buyer.previous_offer is None


class TestSellerStrategyClass:
    """Test SellerStrategy stateful class."""
    
    def test_decide_accept(self):
        """Test accept decision."""
        seller = SellerStrategy(min_price=350)
        result = seller.decide(buyer_offer=400)
        
        assert result["type"] == "accept"
    
    def test_decide_counter(self):
        """Test counter decision."""
        seller = SellerStrategy(min_price=350, asking_price=500)
        result = seller.decide(buyer_offer=250)
        
        assert result["type"] == "counter"
        assert result["price"] >= 350
    
    def test_reset(self):
        """Test reset functionality."""
        seller = SellerStrategy(min_price=350, asking_price=500)
        seller.decide(buyer_offer=250)
        
        seller.reset()
        assert seller.turn == 0
        assert seller.previous_counter is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
