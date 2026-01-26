"""
09_context - MCP (Model Context Protocol) Layer
=============================================

Question this layer answers:
"What is objectively true?"

Seller calls MCP tools:
```python
min_price = get_bottom_line_price()
policy = get_discount_policy()
```

MCP:
- Prevents hallucination
- Enforces real constraints
- Is query-based, not conversational

MCP does NOT:
- Control flow
- Move messages
- Run agents
"""

from .server import MCPServer

# Helper function for common context retrieval
def get_market_context(server: MCPServer = None, product_id: str = "enterprise-license"):
    """Get market context from MCP server."""
    if server is None:
        server = MCPServer()
    return server.get_pricing_rules(product_id)

__all__ = ["MCPServer", "get_market_context"]
