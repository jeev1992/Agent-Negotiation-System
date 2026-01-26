"""
10_runtime - Google ADK Layer
============================

This is THE SHELL - Google ADK runtime.

Run methods:
    1. ADK CLI (recommended, requires API key):
       adk web                    # Web UI
       adk run 10_runtime          # CLI
    
    2. Programmatic:
       python -m 10_runtime.runner --mode demo   # Rule-based (no API key)
       python -m 10_runtime.runner --mode adk    # ADK with Gemini

What ADK does:
- Agent lifecycle management
- Session management  
- Tool execution
- LLM integration (Gemini)

What ADK does NOT do:
- Run negotiation logic (that's agents)
- Manage turns (that's orchestration)
- Validate messages (that's protocol)
"""

from .runner import NegotiationRuntime, RuntimeConfig, ADKRuntime
from .config import load_config

# ADK looks for root_agent in agent.py
try:
    from .agent import root_agent, buyer_agent, seller_agent
except ImportError:
    # ADK not installed
    root_agent = buyer_agent = seller_agent = None

__all__ = [
    "NegotiationRuntime", 
    "RuntimeConfig", 
    "ADKRuntime",
    "load_config",
    "root_agent",
    "buyer_agent", 
    "seller_agent",
]
