"""
MCP Server - Grounded Context
=============================

Provides authoritative data that agents query before making decisions.

This is NOT for agent-to-agent communication.
This IS for agents to get FACTS.

Example:
    "What's the minimum price for enterprise?" → Query MCP
    "I offer $300" → Protocol message (not MCP)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class MCPServer:
    """
    MCP-style server providing grounded context.
    
    In production, this would connect to:
    - Real databases
    - CRM systems  
    - Pricing engines
    - Inventory systems
    
    The key insight: Agents QUERY authoritative sources,
    not rely on hardcoded or hallucinated values.
    """
    
    def __init__(self):
        # In-memory "database" for demo
        self._pricing_rules = {
            "enterprise-license": {
                "product_id": "enterprise-license",
                "base_price": 500.0,
                "min_price": 350.0,
                "max_discount_percent": 30.0,
                "requires_approval_below": 375.0,
            }
        }
        
        self._customer_segments = {
            "standard": {"discount_multiplier": 1.0, "priority": 3},
            "enterprise": {"discount_multiplier": 0.85, "priority": 1},
            "startup": {"discount_multiplier": 0.90, "priority": 2},
        }
        
        self._negotiation_history: List[Dict[str, Any]] = []
    
    def get_pricing_rules(
        self,
        product_id: str,
        customer_segment: str = "standard",
    ) -> Dict[str, Any]:
        """
        Get pricing rules for a product.
        
        This is the AUTHORITATIVE source for pricing.
        Agents should NEVER hardcode these values.
        """
        if product_id not in self._pricing_rules:
            raise ValueError(f"Unknown product: {product_id}")
        
        rules = self._pricing_rules[product_id].copy()
        
        # Apply segment discount
        segment = self._customer_segments.get(customer_segment, {"discount_multiplier": 1.0})
        effective_min = rules["min_price"] * segment["discount_multiplier"]
        
        rules["customer_segment"] = customer_segment
        rules["discount_multiplier"] = segment["discount_multiplier"]
        rules["effective_min"] = round(effective_min, 2)
        
        return rules
    
    def get_customer_segment(self, segment_id: str) -> Dict[str, Any]:
        """Get customer segment details."""
        if segment_id not in self._customer_segments:
            return {"segment_id": "standard", "discount_multiplier": 1.0, "priority": 3}
        
        return {
            "segment_id": segment_id,
            **self._customer_segments[segment_id],
        }
    
    def check_approval_required(
        self,
        product_id: str,
        proposed_price: float,
    ) -> Dict[str, Any]:
        """Check if a price requires manager approval."""
        if product_id not in self._pricing_rules:
            return {"requires_approval": True, "reason": "Unknown product"}
        
        rules = self._pricing_rules[product_id]
        threshold = rules.get("requires_approval_below", rules["min_price"])
        
        requires = proposed_price < threshold
        
        return {
            "proposed_price": proposed_price,
            "threshold": threshold,
            "requires_approval": requires,
            "reason": "Below approval threshold" if requires else None,
        }
    
    def record_negotiation(
        self,
        product_id: str,
        customer_segment: str,
        initial_offer: float,
        final_price: Optional[float],
        turns_taken: int,
        outcome: str,  # "agreed" or "failed"
    ) -> Dict[str, Any]:
        """Record a completed negotiation for analytics."""
        record = {
            "id": len(self._negotiation_history) + 1,
            "product_id": product_id,
            "customer_segment": customer_segment,
            "initial_offer": initial_offer,
            "final_price": final_price,
            "turns_taken": turns_taken,
            "outcome": outcome,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._negotiation_history.append(record)
        return {"recorded": True, "id": record["id"]}
    
    def get_negotiation_history(
        self,
        product_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get historical negotiation outcomes."""
        history = self._negotiation_history.copy()
        
        if product_id:
            history = [h for h in history if h["product_id"] == product_id]
        
        return history[-limit:]
