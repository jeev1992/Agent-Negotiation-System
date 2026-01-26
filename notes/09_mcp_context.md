# 09 - Grounded Context: MCP

## Purpose

Prevent hallucination structurally. MCP (Model Context Protocol) is how agents ask questions about reality instead of making things up.

---

## The Problem: Agents Hallucinate

Without grounding:

```python
def seller_decide(buyer_offer: float) -> dict:
    """Seller decides based on... what exactly?"""
    
    # Where does min_price come from?
    min_price = ???
    
    # Option 1: Hardcoded (inflexible)
    min_price = 300
    
    # Option 2: From prompt (hallucination risk)
    min_price = llm.chat("What's my minimum price?")
    # LLM: "Based on market conditions, $250 seems fair"
    # WRONG - LLM made this up!
    
    # Option 3: From state (might be stale)
    min_price = state.get("min_price")  # Set when? By whom?
```

**The seller needs REAL data, not guesses.**

---

## What Is MCP?

**Model Context Protocol** is a standard for:
1. Exposing **tools** that return real data
2. Providing **prompts** with factual context
3. Giving agents **structured access** to external systems

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────────────────────────┐  │
│  │    AGENT     │         │          MCP SERVER              │  │
│  │              │ ──────► │                                  │  │
│  │  "What's my  │  call   │  ┌─────────────────────────────┐ │  │
│  │   min price?"│         │  │  TOOL: get_pricing_rules()  │ │  │
│  │              │ ◄────── │  │                             │ │  │
│  │              │ response│  │  Returns: {min: 300,        │ │  │
│  │              │         │  │           max: 600,         │ │  │
│  │              │         │  │           margin: 0.2}      │ │  │
│  └──────────────┘         │  └─────────────────────────────┘ │  │
│                           │                                  │  │
│                           │  ┌─────────────────────────────┐ │  │
│                           │  │  TOOL: get_inventory()      │ │  │
│                           │  │                             │ │  │
│                           │  │  Returns: {stock: 5,        │ │  │
│                           │  │           reserved: 2}      │ │  │
│                           │  └─────────────────────────────┘ │  │
│                           └──────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## MCP Tools vs MCP Prompts

| Concept | What It Does | Example |
|---------|--------------|---------|
| **Tool** | Returns structured data | `get_pricing_rules() → {min: 300}` |
| **Prompt** | Returns context text | `negotiation_context → "You are..."` |

Tools are for **data**. Prompts are for **instructions**.

---

## MCP Implementation

```python
# 09_context/server.py

from dataclasses import dataclass
from typing import Any


@dataclass
class PricingRules:
    """Seller's pricing constraints - from real source."""
    min_price: float
    max_price: float
    margin_required: float
    bulk_discount_threshold: int
    bulk_discount_rate: float


@dataclass
class InventoryStatus:
    """Real inventory data."""
    total_stock: int
    reserved: int
    available: int


class MCPServer:
    """
    MCP Server providing grounded context to agents.
    
    This is the SINGLE SOURCE OF TRUTH for business data.
    Agents MUST call these tools instead of guessing.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self._pricing_rules = PricingRules(
            min_price=config.get("seller_min", 300),
            max_price=config.get("seller_max", 600),
            margin_required=config.get("margin", 0.2),
            bulk_discount_threshold=config.get("bulk_threshold", 10),
            bulk_discount_rate=config.get("bulk_discount", 0.1),
        )
        self._inventory = InventoryStatus(
            total_stock=config.get("stock", 100),
            reserved=config.get("reserved", 0),
            available=config.get("stock", 100) - config.get("reserved", 0),
        )
    
    # ==================== TOOLS ====================
    
    def get_pricing_rules(self) -> dict:
        """
        Tool: Get seller's pricing rules.
        
        Returns REAL data, not hallucinated values.
        """
        return {
            "min_price": self._pricing_rules.min_price,
            "max_price": self._pricing_rules.max_price,
            "margin_required": self._pricing_rules.margin_required,
        }
    
    def get_inventory(self) -> dict:
        """
        Tool: Get current inventory status.
        """
        return {
            "total_stock": self._inventory.total_stock,
            "reserved": self._inventory.reserved,
            "available": self._inventory.available,
        }
    
    def check_price_acceptable(self, price: float) -> dict:
        """
        Tool: Check if a price meets seller requirements.
        
        Seller calls this instead of guessing.
        """
        min_price = self._pricing_rules.min_price
        
        return {
            "price": price,
            "min_required": min_price,
            "is_acceptable": price >= min_price,
            "shortfall": max(0, min_price - price),
        }
    
    def get_bulk_discount(self, quantity: int) -> dict:
        """
        Tool: Calculate bulk discount if applicable.
        """
        if quantity >= self._pricing_rules.bulk_discount_threshold:
            return {
                "applies": True,
                "discount_rate": self._pricing_rules.bulk_discount_rate,
                "reason": f"Order of {quantity} qualifies for bulk discount",
            }
        return {
            "applies": False,
            "discount_rate": 0,
            "threshold": self._pricing_rules.bulk_discount_threshold,
        }
    
    # ==================== PROMPTS ====================
    
    def get_seller_context(self) -> str:
        """
        Prompt: Provide context for seller agent.
        
        This is INSTRUCTIONS, not data.
        """
        rules = self.get_pricing_rules()
        return f"""You are a seller agent.

Your pricing constraints:
- Minimum acceptable price: ${rules['min_price']}
- Maximum starting price: ${rules['max_price']}
- Required margin: {rules['margin_required']*100}%

You MUST call get_pricing_rules() before making pricing decisions.
You MUST NOT accept prices below the minimum.
"""
    
    def get_negotiation_context(self) -> str:
        """
        Prompt: General negotiation context.
        """
        return """This is a price negotiation for a single item.
        
Rules:
- Buyer makes offers, Seller makes counter-offers
- Either party can accept or reject
- Negotiation ends on accept, reject, or max turns
- All prices must be positive numbers
"""
```

---

## Why MCP Is NOT Transport

Common confusion:

```
WRONG THINKING:
"MCP sends messages between agents"

CORRECT:
"MCP provides data to agents"
```

| Aspect | Transport (08_transport) | MCP (09_context) |
|--------|------------------------|-----------------|
| Direction | Agent ↔ Agent | Agent → Data Source |
| Content | Negotiation messages | Business data |
| Purpose | Communication | Grounding |
| Example | "I offer $300" | "Min price is $300" |

---

## Why Agents MUST Call MCP

### Without MCP (Hallucination)

```python
def seller_strategy_bad(buyer_price: float) -> dict:
    """Seller without grounding - dangerous!"""
    
    # Where does 300 come from? Hardcoded!
    min_price = 300  
    
    # What if business rules change?
    # What if this seller has different rules?
    # What if there's a sale?
    
    if buyer_price >= min_price:
        return {"type": "accept", "price": buyer_price}
    return {"type": "counter", "price": min_price * 1.2}
```

### With MCP (Grounded)

```python
def seller_strategy_good(
    buyer_price: float,
    mcp: MCPServer,
) -> dict:
    """Seller with grounding - safe!"""
    
    # Get REAL pricing rules
    rules = mcp.get_pricing_rules()
    min_price = rules["min_price"]
    
    # Check against REAL constraints
    check = mcp.check_price_acceptable(buyer_price)
    
    if check["is_acceptable"]:
        return {"type": "accept", "price": buyer_price}
    
    # Counter based on REAL data
    return {
        "type": "counter",
        "price": min_price * (1 + rules["margin_required"]),
    }
```

---

## Seller Refusal Without MCP

What happens when seller can't check constraints:

```python
# Scenario: MCP is down

def seller_strategy_no_mcp(buyer_price: float) -> dict:
    """Seller when MCP is unavailable."""
    
    # OPTION 1: Guess (DANGEROUS)
    min_price = 300  # Might be wrong!
    
    # OPTION 2: Refuse to act (SAFE)
    return {
        "type": "error",
        "reason": "Cannot verify pricing rules - MCP unavailable",
        "action": "retry_later",
    }

# The safe option: refuse rather than guess
```

---

## MCP Tool Examples

### Tool 1: Pricing Rules

```python
# Agent calls:
rules = mcp.get_pricing_rules()

# Returns:
{
    "min_price": 300.0,
    "max_price": 600.0,
    "margin_required": 0.2
}

# Agent uses:
if offer >= rules["min_price"]:
    accept()
```

### Tool 2: Price Check

```python
# Agent calls:
check = mcp.check_price_acceptable(250)

# Returns:
{
    "price": 250,
    "min_required": 300,
    "is_acceptable": False,
    "shortfall": 50
}

# Agent uses:
if not check["is_acceptable"]:
    counter(check["min_required"] + 50)
```

### Tool 3: Inventory

```python
# Agent calls:
inv = mcp.get_inventory()

# Returns:
{
    "total_stock": 100,
    "reserved": 20,
    "available": 80
}

# Agent uses:
if inv["available"] < order_quantity:
    reject("Insufficient stock")
```

---

## Mental Model

> **"MCP is how agents ask questions about reality."**

| Without MCP | With MCP |
|-------------|----------|
| Agent guesses min price | Agent asks for min price |
| Hallucination risk | Grounded in data |
| Hardcoded values | Dynamic values |
| Can't adapt | Adapts to context |

Think of MCP as the agent's **database connection**:
- Agents don't hardcode SQL results
- Agents query the database
- Same principle: query MCP for business data

---

## Integration with Other Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  05_agents                                                       │
│  │                                                              │
│  │  seller_strategy(buyer_price, mcp)                          │
│  │      │                                                       │
│  │      ├── mcp.get_pricing_rules() ──► 09_context              │
│  │      │                               Returns: {min: 300}     │
│  │      │                                                       │
│  │      └── mcp.check_price_acceptable(offer) ──► 09_context    │
│  │                                       Returns: {ok: True}    │
│  │                                                              │
│  │  Decision is GROUNDED, not guessed                          │
│  │                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## What MCP Deliberately Does NOT Do

1. **Transport**: MCP doesn't send messages between agents
2. **Orchestration**: MCP doesn't control flow
3. **Policy**: MCP doesn't enforce permissions
4. **Storage**: MCP queries sources, doesn't store state

MCP is **read-only access to truth**.

---

## Key Takeaway

> **MCP prevents hallucination by giving agents access to real data.**
>
> When an agent needs to know something factual (prices, inventory, rules), it MUST call MCP. Guessing is not acceptable in production systems.

---

## Code References

- [09_context/server.py](../09_context/server.py) - MCP server implementation
- [09_context/__init__.py](../09_context/__init__.py) - Context exports
- [05_agents/seller.py](../05_agents/seller.py) - Seller using MCP

---

## Next Steps

1. Read `10_runtime_adk.md` for lifecycle management
2. Read `05_agents_strategies.md` to see MCP in agent logic
3. Read `13_what_breaks.md` to see failures without MCP
