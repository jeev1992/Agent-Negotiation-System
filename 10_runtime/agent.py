"""
Google ADK Agent Re-exports
===========================

This file re-exports the ADK agents from 05_agents/adk_agents.py
for compatibility with the ADK CLI (adk web, adk run).

The actual agent definitions are in 05_agents/adk_agents.py
to keep all agent logic in one place.

Run with:
    adk web                     # Web UI at localhost:8000
    adk run 10_runtime          # CLI
    python -m 10_runtime.runner --mode adk
"""

import sys
from pathlib import Path

# Add project root to path for numbered module imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from the agents module
try:
    # Try direct import first (if running as package)
    from importlib import import_module
    import importlib.util
    
    # Dynamic import for numbered module
    agents_path = project_root / "05_agents" / "adk_agents.py"
    spec = importlib.util.spec_from_file_location("adk_agents", agents_path)
    adk_agents = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adk_agents)
    
    # Re-export
    root_agent = adk_agents.root_agent
    buyer_agent = adk_agents.buyer_agent
    seller_agent = adk_agents.seller_agent
    
    # Tools
    get_pricing_rules = adk_agents.get_pricing_rules
    make_offer = adk_agents.make_offer
    make_counter_offer = adk_agents.make_counter_offer
    accept_offer = adk_agents.accept_offer
    reject_offer = adk_agents.reject_offer
    check_negotiation_state = adk_agents.check_negotiation_state
    
    ADK_AVAILABLE = adk_agents.ADK_AVAILABLE

except Exception as e:
    print(f"[Warning] Could not import ADK agents: {e}")
    root_agent = None
    buyer_agent = None
    seller_agent = None
    ADK_AVAILABLE = False
