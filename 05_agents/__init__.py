"""
05_AGENTS - Decision Layer
==========================

Question this layer answers:
"What does this agent decide?"

Two types of agents:
1. DETERMINISTIC (buyer.py, seller.py):
   - Rule-based strategies
   - Testable, no API needed
   - Pure functions
   
2. LLM-POWERED (adk_agents.py):
   - Google ADK + Gemini
   - Requires GOOGLE_API_KEY
   - Used in ADK mode

Buyer Agent:
- Makes offers
- Concedes deterministically (or via LLM)

Seller Agent:
- Accepts / counters / rejects
- Must consult MCP before countering

```python
# Deterministic
from 05_agents import buyer_strategy, seller_strategy

# LLM-powered  
from 05_agents.adk_agents import buyer_agent, seller_agent
```

Agents do NOT:
- Manage loops (that's orchestration)
- Talk to transport directly
- Know about runtime lifecycle
"""

from .buyer import buyer_strategy
from .seller import seller_strategy

# ADK agents are imported separately due to optional dependency
# from .adk_agents import buyer_agent, seller_agent, root_agent
from .buyer import buyer_strategy, BuyerStrategy
from .seller import seller_strategy, SellerStrategy

__all__ = ["buyer_strategy", "seller_strategy", "BuyerStrategy", "SellerStrategy"]
