"""
BASELINE SYSTEM: Naive Negotiation Implementation
==================================================

This file intentionally demonstrates how most first-attempt agent systems fail.
It represents the "obvious" implementation that seems reasonable but breaks down
in practice.

╔══════════════════════════════════════════════════════════════════════════════╗
║  THIS CODE IS INTENTIONALLY BROKEN - IT IS THE PROBLEM WE'RE SOLVING         ║
╚══════════════════════════════════════════════════════════════════════════════╝

INTENTIONAL PROBLEMS IN THIS CODE:
1. Raw string communication between agents
2. No schema validation - messages can be anything
3. No state machine - just a while True loop
4. No turn limits - can loop forever
5. Ambiguous parsing - regex on free-form text
6. No termination guarantees
7. Silent failures when parsing goes wrong
8. No grounded context - prices are hardcoded
9. No observability - can't see what happened
10. No evaluation - can't measure quality

This is the MOTIVATING FAILURE that drives the entire 10-layer architecture.

Run with:
    python -m baseline.naive_negotiation
"""

import re
import random
from typing import Optional, Tuple


class NaiveBuyer:
    """
    A naive buyer agent that communicates via raw strings.
    
    PROBLEMS:
    - No structured message format
    - State is implicit and easy to corrupt
    - Strategy is entangled with parsing logic
    - No access to market data (hardcoded max price)
    """
    
    def __init__(self, name: str, max_price: float):
        self.name = name
        self.max_price = max_price
        self.current_offer = None
    
    def make_initial_offer(self) -> str:
        """Generate initial offer as raw string."""
        # Start at 60% of max price
        self.current_offer = self.max_price * 0.6
        return f"I'd like to buy the software license. My offer is ${self.current_offer:.2f}"
    
    def respond_to_counter(self, seller_message: str) -> str:
        """
        Parse seller's response and decide next action.
        
        PROBLEM: This regex parsing is fragile and will fail on:
        - Different currency formats ($100 vs 100 USD vs €100)
        - Typos ("$100" vs "$ 100" vs "$100.00")
        - Unexpected message structures
        - Non-English responses
        - Multiple prices in one message
        """
        # Try to extract price from seller's message
        price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', seller_message)
        
        if not price_match:
            # ╔═══════════════════════════════════════════════════════════╗
            # ║  SILENT FAILURE: We don't know what the seller said       ║
            # ║  but we'll just... keep going? This is a bug.             ║
            # ╚═══════════════════════════════════════════════════════════╝
            return f"I'm confused. Let me offer ${self.current_offer:.2f} again."
        
        seller_price = float(price_match.group(1).replace(',', ''))
        
        if seller_price <= self.max_price:
            return f"ACCEPT: I'll take it at ${seller_price:.2f}"
        
        # Increase our offer by 10%
        self.current_offer = min(self.current_offer * 1.1, self.max_price)
        
        if self.current_offer >= self.max_price:
            return f"My final offer is ${self.current_offer:.2f}. Take it or leave it."
        
        return f"How about ${self.current_offer:.2f}? That's my counter-offer."


class NaiveSeller:
    """
    A naive seller agent that communicates via raw strings.
    
    PROBLEMS:
    - No access to grounded context (pricing rules, inventory, CRM)
    - No validation of buyer's messages
    - Can be manipulated by malformed input
    - Hardcoded minimum price (should come from database/MCP)
    """
    
    def __init__(self, name: str, min_price: float, asking_price: float):
        self.name = name
        self.min_price = min_price  # PROBLEM: Should come from MCP, not hardcoded
        self.asking_price = asking_price
        self.current_price = asking_price
    
    def respond_to_offer(self, buyer_message: str) -> str:
        """
        Parse buyer's offer and respond.
        
        PROBLEM: This parsing is extremely brittle.
        """
        # Check for acceptance
        if "ACCEPT" in buyer_message.upper():
            price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', buyer_message)
            if price_match:
                accepted_price = float(price_match.group(1).replace(',', ''))
                return f"DEAL! Sold at ${accepted_price:.2f}"
        
        # Try to extract offered price
        price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', buyer_message)
        
        if not price_match:
            # ╔═══════════════════════════════════════════════════════════╗
            # ║  SILENT FAILURE: Can't parse, but we continue anyway      ║
            # ╚═══════════════════════════════════════════════════════════╝
            return f"I didn't catch that. The price is ${self.current_price:.2f}"
        
        offered_price = float(price_match.group(1).replace(',', ''))
        
        # Accept if at or above minimum
        if offered_price >= self.min_price:
            return f"DEAL! I accept ${offered_price:.2f}"
        
        # Counter offer - reduce by 5%
        self.current_price = max(self.current_price * 0.95, self.min_price)
        
        if "final" in buyer_message.lower():
            if offered_price >= self.min_price * 0.95:
                return f"DEAL! I'll accept ${offered_price:.2f}"
            return f"I can't go that low. My minimum is ${self.min_price:.2f}. REJECT."
        
        return f"I can offer ${self.current_price:.2f}. That's a fair price."


def run_naive_negotiation(
    buyer: NaiveBuyer,
    seller: NaiveSeller,
    verbose: bool = True
) -> Tuple[bool, Optional[float], int]:
    """
    Run a naive negotiation between buyer and seller.
    
    PROBLEMS:
    1. while True loop - NO TERMINATION GUARANTEE
    2. No turn limit - can run forever
    3. String parsing for termination - fragile
    4. No state tracking - hard to debug
    5. No observability - can't see what happened
    6. No evaluation - can't measure quality
    
    Returns:
        (success: bool, final_price: Optional[float], turns: int)
    """
    if verbose:
        print("\n" + "="*60)
        print("NAIVE NEGOTIATION (Intentionally Broken)")
        print("="*60 + "\n")
    
    turn = 0
    current_message = buyer.make_initial_offer()
    is_buyer_turn = False  # Buyer just went
    
    if verbose:
        print(f"[Turn {turn}] {buyer.name}: {current_message}")
    
    # ╔═══════════════════════════════════════════════════════════════════╗
    # ║  DANGER: while True with no guaranteed exit condition!            ║
    # ║  This can run FOREVER if agents never agree.                       ║
    # ╚═══════════════════════════════════════════════════════════════════╝
    while True:
        turn += 1
        
        # Emergency exit (bandaid, not a fix)
        if turn > 100:
            if verbose:
                print(f"\n[EMERGENCY] Exceeded 100 turns, forcing exit")
            return False, None, turn
        
        if is_buyer_turn:
            current_message = buyer.respond_to_counter(current_message)
            speaker = buyer.name
        else:
            current_message = seller.respond_to_offer(current_message)
            speaker = seller.name
        
        if verbose:
            print(f"[Turn {turn}] {speaker}: {current_message}")
        
        # Check for deal or rejection (fragile string parsing!)
        if "DEAL" in current_message.upper():
            price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', current_message)
            final_price = float(price_match.group(1).replace(',', '')) if price_match else None
            if verbose:
                print(f"\n✓ Deal reached at ${final_price:.2f} after {turn} turns")
            return True, final_price, turn
        
        if "REJECT" in current_message.upper():
            if verbose:
                print(f"\n✗ Negotiation failed after {turn} turns")
            return False, None, turn
        
        is_buyer_turn = not is_buyer_turn


def demonstrate_failure_modes():
    """
    Demonstrate the various failure modes of naive negotiation.
    """
    print("\n" + "="*70)
    print("FAILURE MODE DEMONSTRATIONS")
    print("="*70)
    
    # Failure Mode 1: Ambiguous parsing
    print("\n--- FAILURE 1: Ambiguous Message Parsing ---")
    message = "I want the $500 enterprise plan but my budget is $300"
    price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', message)
    print(f"Message: '{message}'")
    print(f"Regex extracts: ${price_match.group(1) if price_match else 'None'}")
    print(f"PROBLEM: Extracted $500 but buyer meant $300!")
    
    # Failure Mode 2: Infinite loop risk
    print("\n--- FAILURE 2: No Agreement Possible ---")
    print("Buyer max price: $50")
    print("Seller min price: $100")
    print("These agents can NEVER agree!")
    print("Without emergency exit, the loop would run FOREVER.")
    
    # Failure Mode 3: Silent parsing failure
    print("\n--- FAILURE 3: Silent Parsing Failure ---")
    message = "My offer is three hundred dollars"
    price_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', message)
    print(f"Message: '{message}'")
    print(f"Regex extracts: {price_match}")
    print("PROBLEM: Agent continues without knowing the price!")
    
    # Failure Mode 4: No grounded context
    print("\n--- FAILURE 4: Hardcoded Prices (No MCP) ---")
    print("Seller's min_price=350 is hardcoded")
    print("In production, this should come from:")
    print("  - Database (via MCP)")
    print("  - CRM system")
    print("  - Dynamic pricing engine")
    print("PROBLEM: Prices can be stale or wrong!")


def main():
    """Run demonstration of naive negotiation problems."""
    
    # Demo 1: Successful negotiation (when it works)
    print("\n" + "="*70)
    print("DEMO 1: When It Works (By Luck)")
    print("="*70)
    
    buyer = NaiveBuyer("Alice", max_price=500.0)
    seller = NaiveSeller("Bob", min_price=350.0, asking_price=600.0)
    
    success, price, turns = run_naive_negotiation(buyer, seller)
    
    # Demo 2: Impossible agreement
    print("\n" + "="*70)
    print("DEMO 2: Impossible Agreement (No ZOPA)")
    print("="*70)
    
    buyer = NaiveBuyer("Alice", max_price=200.0)
    seller = NaiveSeller("Bob", min_price=500.0, asking_price=600.0)
    
    success, price, turns = run_naive_negotiation(buyer, seller)
    
    # Demo 3: Failure mode demonstrations
    demonstrate_failure_modes()
    
    # Summary
    print("\n" + "="*70)
    print("WHY THIS MATTERS")
    print("="*70)
    print("""
The naive implementation has these fundamental problems:

Layer 0 (System): No clear system boundaries or responsibilities
Layer 1 (Runtime): No lifecycle management, no config loading
Layer 2 (Coordination): No turn-taking rules, no policy enforcement
Layer 3 (Transport): Direct function calls, no abstraction
Layer 4 (Orchestration): while True loop instead of proper graph
Layer 5 (Agents): Strategy mixed with parsing logic
Layer 6 (Context): Hardcoded values instead of MCP queries
Layer 7 (FSM): No state machine, no termination guarantee
Layer 8 (Observability): No tracing, no visibility
Layer 9 (Evaluation): No quality measurement

The 10-layer architecture solves ALL of these problems.
    """)


if __name__ == "__main__":
    main()
