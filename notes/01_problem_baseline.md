# 01 - The Problem & Baseline Failure

## Purpose

Create emotional + intellectual motivation. Understand WHY we need this architecture by seeing what fails without it.

---

## What People Naively Build

When people hear "build an agent system," they immediately think:

```python
# "Just make them talk to each other!"

buyer = ChatBot("You are a buyer. Negotiate for the best price.")
seller = ChatBot("You are a seller. Maximize profit.")

while True:
    buyer_msg = buyer.chat(seller_msg)
    seller_msg = seller.chat(buyer_msg)
    if "deal" in buyer_msg.lower():
        break
```

This seems reasonable. It's simple. It works in demos.

**It will catastrophically fail in production.**

---

## The Baseline System

```python
# baseline/naive_negotiation.py

import re

class NaiveBuyer:
    """Buyer that uses string matching and hope."""
    
    def __init__(self, max_price: float):
        self.max_price = max_price
        self.current_offer = max_price * 0.5
    
    def respond(self, seller_message: str) -> str:
        # Try to extract price from free text
        price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', seller_message)
        
        if price_match:
            seller_price = float(price_match.group(1).replace(',', ''))
            
            if seller_price <= self.max_price:
                return f"DEAL! I accept ${seller_price:.2f}"
            
            # Raise offer
            self.current_offer = min(self.current_offer * 1.1, self.max_price)
            return f"Too high. I offer ${self.current_offer:.2f}"
        
        # Can't parse - just repeat offer
        return f"I didn't understand. My offer is ${self.current_offer:.2f}"


class NaiveSeller:
    """Seller that uses string matching and hope."""
    
    def __init__(self, min_price: float):
        self.min_price = min_price
        self.current_ask = min_price * 2
    
    def respond(self, buyer_message: str) -> str:
        price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', buyer_message)
        
        if price_match:
            buyer_price = float(price_match.group(1).replace(',', ''))
            
            if buyer_price >= self.min_price:
                return f"DEAL! Sold for ${buyer_price:.2f}"
            
            # Lower ask
            self.current_ask = max(self.current_ask * 0.9, self.min_price)
            return f"I can't go that low. How about ${self.current_ask:.2f}?"
        
        return f"I need a number. My price is ${self.current_ask:.2f}"


def naive_negotiate(buyer_max: float, seller_min: float) -> str:
    """Run a naive negotiation. What could go wrong?"""
    buyer = NaiveBuyer(buyer_max)
    seller = NaiveSeller(seller_min)
    
    seller_msg = f"I'm selling for ${seller.current_ask:.2f}"
    
    for turn in range(100):  # "100 should be enough"
        buyer_msg = buyer.respond(seller_msg)
        print(f"Buyer: {buyer_msg}")
        
        if "DEAL" in buyer_msg:
            return "SUCCESS"
        
        seller_msg = seller.respond(buyer_msg)
        print(f"Seller: {seller_msg}")
        
        if "DEAL" in seller_msg:
            return "SUCCESS"
    
    return "FAILED - Max turns"
```

---

## One Successful Run

When conditions are right, it works:

```
$ python baseline/naive_negotiation.py --buyer-max 500 --seller-min 300

Seller: I'm selling for $600.00
Buyer: Too high. I offer $250.00
Seller: I can't go that low. How about $540.00?
Buyer: Too high. I offer $275.00
Seller: I can't go that low. How about $486.00?
Buyer: Too high. I offer $302.50
Seller: I can't go that low. How about $437.40?
Buyer: Too high. I offer $332.75
Seller: I can't go that low. How about $393.66?
Buyer: Too high. I offer $366.03
Seller: DEAL! Sold for $366.03

Result: SUCCESS
```

**Great! Ship it!** ...right?

---

## One Broken Run: Infinite Loop

Same code, different numbers:

```
$ python baseline/naive_negotiation.py --buyer-max 100 --seller-min 200

Seller: I'm selling for $400.00
Buyer: Too high. I offer $50.00
Seller: I can't go that low. How about $360.00?
Buyer: Too high. I offer $55.00
Seller: I can't go that low. How about $324.00?
...
(50 turns later)
...
Buyer: Too high. I offer $100.00
Seller: I can't go that low. How about $200.00?
Buyer: Too high. I offer $100.00     ← STUCK AT MAX
Seller: I can't go that low. How about $200.00?  ← STUCK AT MIN
Buyer: Too high. I offer $100.00
Seller: I can't go that low. How about $200.00?
... (loops forever until turn 100)

Result: FAILED - Max turns
```

**Problem**: No overlap between buyer max ($100) and seller min ($200). The system has no way to detect or handle this. It loops until an arbitrary limit.

---

## Another Broken Run: Ambiguous Interpretation

```
$ python baseline/naive_negotiation.py --buyer-max 500 --seller-min 300

Seller: I'm selling for $600.00
Buyer: Too high. I offer $250.00
Seller: I was hoping for at least $500, but I could do $450 if you're serious.
Buyer: I didn't understand. My offer is $250.00  ← TWO PRICES, CONFUSED
Seller: I need a number. My price is $405.00
Buyer: Too high. I offer $275.00
Seller: Between $350 and $400 would work for me.
Buyer: Too high. I offer $302.50  ← EXTRACTED $350, WRONG ONE
```

**Problem**: Free text has multiple prices. Regex extracts the wrong one.

---

## The Two Failure Modes

### Failure Mode 1: Infinite Loops

| Cause | Symptom | Why It Happens |
|-------|---------|----------------|
| No overlap | Stuck at boundaries | No detection mechanism |
| Parsing fails | Repeated "I don't understand" | Regex can't parse |
| Logic bugs | Same offer repeated | No progress detection |

**Root cause**: No formal termination condition.

### Failure Mode 2: Ambiguous Interpretation

| Input | Expected | Actual | Why |
|-------|----------|--------|-----|
| "$300 to $400" | Range | $300 | First match |
| "Not $500, try $400" | $400 | $500 | First match |
| "400 dollars" | $400 | Nothing | No $ sign |
| "DEAL!" | Accept | Nothing | No price |

**Root cause**: Free text is inherently ambiguous.

---

## Mental Model

> **"Agents fail not because LLMs are bad, but because systems are undefined."**

The baseline fails because:
1. **No protocol**: Agents don't agree on message format
2. **No FSM**: No formal states or termination conditions  
3. **No policy**: Anyone can say anything anytime
4. **No grounding**: Agents make up prices from thin air

These aren't AI problems. These are **systems engineering** problems.

---

## The Costs of Failure

| Failure | Cost |
|---------|------|
| Infinite loop | Unbounded API spend ($$$) |
| Wrong interpretation | Incorrect business outcomes |
| No termination | Hung systems, angry users |
| State loss | Can't resume, can't debug |
| No observability | "It just stopped working" |

---

## What We Need

| Problem | Solution | Layer |
|---------|----------|-------|
| Infinite loops | FSM with terminal states | 04_fsm |
| Ambiguous messages | Typed protocols | 03_protocol |
| No turn control | Coordination policy | 07_coordination |
| Made-up data | MCP grounding | 09_context |
| Scattered flow | LangGraph orchestration | 06_orchestration |
| No lifecycle | ADK runtime | 10_runtime |
| Can't debug | LangSmith tracing | observability |
| Can't measure | Evaluation framework | 11_evaluation |

---

## Key Takeaway

> **The baseline demonstrates that "making agents talk" is the easy part. Making them talk RELIABLY, TERMINABLY, and CORRECTLY requires systems engineering.**

Don't start with LLMs. Start with the system design.

---

## Next Steps

1. Read `02_architecture_overview.md` for the full system map
2. Read `03_protocols.md` to see how structured messages solve ambiguity
3. Read `04_fsm_termination.md` to see how FSMs guarantee termination
