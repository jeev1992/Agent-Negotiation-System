"""
Runtime - The ADK Shell
========================

This is THE SHELL - the entrypoint that wraps the entire system.

Google ADK is the runtime. It provides:
- Agent lifecycle management
- Session management
- Tool execution
- LLM integration

This file provides:
- Programmatic access to ADK (for testing, batch runs)
- CLI that wraps ADK
- Fallback mode when ADK/API not available

Run methods:
    1. ADK CLI (recommended):
       adk web
       adk run 10_runtime
    
    2. Programmatic:
       python -m 10_runtime.runner --mode demo
       python -m 10_runtime.runner --mode adk
"""

import argparse
import asyncio
import time
import sys
import importlib.util
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from uuid import uuid4

from .config import load_config, Config


# ============================================================================
# Dynamic Import Helper (for numbered modules)
# ============================================================================

def import_layer(layer_name: str):
    """Import a numbered layer dynamically."""
    project_root = Path(__file__).parent.parent
    folder_path = project_root / layer_name
    init_path = folder_path / "__init__.py"
    
    if not init_path.exists():
        raise ImportError(f"Layer {layer_name} not found")
    
    spec = importlib.util.spec_from_file_location(layer_name, init_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[layer_name] = module
    spec.loader.exec_module(module)
    return module


# ============================================================================
# Runtime Configuration
# ============================================================================

@dataclass
class RuntimeConfig:
    """Runtime configuration (how to run, not what to negotiate)."""
    mode: str = "demo"              # demo, batch, adk
    strategy: str = "rule"          # rule, llm
    transport: str = "local"        # local, websocket
    config_path: Optional[str] = None
    verbose: bool = True
    batch_count: int = 10
    
    # LLM settings (when strategy="llm" or mode="adk")
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.7


# ============================================================================
# Session (one negotiation)
# ============================================================================

@dataclass
class Session:
    """A single negotiation session."""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    
    # Configuration
    buyer_max_price: float = 450.0
    seller_min_price: float = 350.0
    seller_asking_price: float = 500.0
    max_turns: int = 10
    
    # Results
    agreed: bool = False
    final_price: Optional[float] = None
    turns_taken: int = 0
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timing
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


# ============================================================================
# ADK Runtime (Real Google ADK)
# ============================================================================

class ADKRuntime:
    """
    Real Google ADK runtime.
    
    Uses google-adk's Runner to execute agents.
    Requires GOOGLE_API_KEY environment variable.
    """
    
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self._runner = None
        self._session_service = None
    
    async def initialize(self) -> bool:
        """Initialize ADK runtime."""
        try:
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from .agent import root_agent
            
            self._session_service = InMemorySessionService()
            self._runner = Runner(
                agent=root_agent,
                app_name="negotiation_system",
                session_service=self._session_service,
            )
            print("[ADK] Runtime initialized")
            print(f"[ADK] Agent: {root_agent.name}")
            print(f"[ADK] Sub-agents: {[a.name for a in root_agent.sub_agents]}")
            return True
            
        except ImportError as e:
            print(f"[ADK] Not available: {e}")
            print("[ADK] Install with: pip install google-adk")
            return False
        except Exception as e:
            print(f"[ADK] Error: {e}")
            return False
    
    async def run_negotiation(self, prompt: str = None) -> Dict[str, Any]:
        """Run a negotiation using ADK."""
        from google.adk.runners import Runner
        from google.genai import types
        
        if not self._runner:
            raise RuntimeError("ADK not initialized")
        
        # Create session
        session = await self._session_service.create_session(
            app_name="negotiation_system",
            user_id="demo_user",
        )
        
        # Default prompt
        if not prompt:
            prompt = """Start a negotiation for an enterprise software license.
            
The buyer has a maximum budget of $450.
The seller's minimum price is $350 (from pricing rules).

Run the negotiation until a deal is reached or 5 rounds pass."""
        
        # Run the agent
        print(f"\n[ADK] Starting negotiation...")
        print(f"[ADK] Prompt: {prompt[:100]}...")
        print()
        
        content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
        
        result_text = ""
        async for event in self._runner.run_async(
            session_id=session.id,
            user_id="demo_user",
            new_message=content,
        ):
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(part.text)
                        result_text += part.text
        
        return {
            "session_id": session.id,
            "result": result_text,
        }


# ============================================================================
# Fallback Runtime (No ADK)
# ============================================================================

class NegotiationRuntime:
    """
    Fallback runtime when ADK is not available.
    
    Uses rule-based agents for educational purposes.
    Does NOT require API keys.
    """
    
    def __init__(self, config: RuntimeConfig):
        self.runtime_config = config
        self.system_config: Optional[Config] = None
        self._initialized = False
        
        # Components (lazy loaded)
        self._mcp_server = None
        self._policy = None
    
    def initialize(self) -> None:
        """Initialize the runtime."""
        if self._initialized:
            return
        
        print("[Runtime] Initializing (fallback mode)...")
        
        # Load system configuration
        self.system_config = load_config(self.runtime_config.config_path)
        
        # Initialize MCP server (grounded context)
        try:
            context_module = import_layer("09_context")
            self._mcp_server = context_module.MCPServer()
            print("[Runtime] MCP server ready")
        except ImportError:
            pass
        
        # Initialize coordination policy
        try:
            coord_module = import_layer("07_coordination")
            self._policy = coord_module.CoordinationPolicy()
            print("[Runtime] Coordination policy ready")
        except ImportError:
            pass
        
        self._initialized = True
        print("[Runtime] Ready\n")
    
    def create_session(self, **kwargs) -> Session:
        """Create a new negotiation session."""
        return Session(
            buyer_max_price=kwargs.get("buyer_max_price", self.system_config.agents.buyer_max_price),
            seller_min_price=kwargs.get("seller_min_price", self.system_config.agents.seller_min_price),
            seller_asking_price=kwargs.get("seller_asking_price", self.system_config.agents.seller_asking_price),
            max_turns=kwargs.get("max_turns", self.system_config.limits.max_turns),
        )
    
    def run_session(self, session: Session) -> Session:
        """Run a negotiation session using rule-based agents."""
        session.start_time = time.time()
        
        if self.runtime_config.verbose:
            print(f"[Negotiation] Starting")
            print(f"  Buyer max: ${session.buyer_max_price:.2f}")
            print(f"  Seller min: ${session.seller_min_price:.2f}")
            print(f"  Seller asking: ${session.seller_asking_price:.2f}")
            print()
        
        try:
            # Try to use full orchestration
            orch_module = import_layer("06_orchestration")
            result = orch_module.run_negotiation(
                buyer_max_price=session.buyer_max_price,
                seller_min_price=session.seller_min_price,
                seller_asking_price=session.seller_asking_price,
                max_turns=session.max_turns,
                strategy=self.runtime_config.strategy,
                mcp_server=self._mcp_server,
                verbose=self.runtime_config.verbose,
            )
            session.agreed = result.get("agreed", False)
            session.final_price = result.get("final_price")
            session.turns_taken = result.get("turns", 0)
            session.messages = result.get("messages", [])
            
        except ImportError:
            # Fallback to simple negotiation
            self._run_simple_negotiation(session)
        
        session.end_time = time.time()
        return session
    
    def _run_simple_negotiation(self, session: Session) -> None:
        """Fallback simple negotiation without full orchestration."""
        agents_module = import_layer("05_agents")
        fsm_module = import_layer("04_fsm")
        
        buyer_strategy = agents_module.buyer_strategy
        seller_strategy = agents_module.seller_strategy
        NegotiationFSM = fsm_module.NegotiationFSM
        
        fsm = NegotiationFSM(max_turns=session.max_turns)
        fsm.start()
        
        current_price = session.seller_asking_price
        previous_offer = None
        
        for turn in range(session.max_turns):
            if not fsm.is_active:
                break
            
            session.turns_taken = turn + 1
            
            # Buyer's turn
            buyer_msg = buyer_strategy(
                current_offer=current_price,
                max_price=session.buyer_max_price,
                turn=turn,
                max_turns=session.max_turns,
                previous_offer=previous_offer,
            )
            
            session.messages.append({"turn": turn, "agent": "buyer", "message": buyer_msg})
            
            if self.runtime_config.verbose:
                print(f"[Turn {turn + 1}] Buyer: {buyer_msg}")
            
            if buyer_msg.get("type") == "accept":
                fsm.accept(buyer_msg["price"])
                session.agreed = True
                session.final_price = buyer_msg["price"]
                break
            
            if buyer_msg.get("type") == "reject":
                fsm.reject("Buyer rejected")
                break
            
            previous_offer = buyer_msg.get("price")
            
            # Seller's turn
            seller_msg = seller_strategy(
                buyer_offer=buyer_msg["price"],
                min_price=session.seller_min_price,
                asking_price=session.seller_asking_price,
                turn=turn,
                max_turns=session.max_turns,
            )
            
            session.messages.append({"turn": turn, "agent": "seller", "message": seller_msg})
            
            if self.runtime_config.verbose:
                print(f"[Turn {turn + 1}] Seller: {seller_msg}")
            
            if seller_msg.get("type") == "accept":
                fsm.accept(seller_msg["price"])
                session.agreed = True
                session.final_price = seller_msg["price"]
                break
            
            if seller_msg.get("type") == "reject":
                fsm.reject("Seller rejected")
                break
            
            current_price = seller_msg.get("price", current_price)
        
        if self.runtime_config.verbose:
            print()
            if session.agreed:
                print(f"[Result] Agreement: ${session.final_price:.2f}")
            else:
                print(f"[Result] No agreement after {session.turns_taken} turns")
    
    def shutdown(self) -> None:
        """Clean shutdown."""
        print("[Runtime] Shutting down...")
        self._initialized = False


# ============================================================================
# CLI Entrypoints
# ============================================================================

def run_demo(runtime: NegotiationRuntime) -> None:
    """Run a single demo negotiation (rule-based)."""
    print("=" * 50)
    print("DEMO MODE (rule-based agents)")
    print("=" * 50 + "\n")
    
    session = runtime.create_session()
    runtime.run_session(session)
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Session: {session.session_id}")
    print(f"Agreed: {'Yes' if session.agreed else 'No'}")
    print(f"Final Price: ${session.final_price:.2f}" if session.final_price else "Final Price: N/A")
    print(f"Turns: {session.turns_taken}")
    print(f"Duration: {session.duration_ms():.2f}ms")
    print("=" * 50)


async def run_adk_mode() -> None:
    """Run using real Google ADK with LLM agents."""
    print("=" * 50)
    print("ADK MODE (Google ADK + Gemini)")
    print("=" * 50 + "\n")
    
    config = RuntimeConfig(mode="adk")
    adk = ADKRuntime(config)
    
    if not await adk.initialize():
        print("\n[Error] ADK not available. Falling back to demo mode.")
        print("To use ADK mode:")
        print("  1. pip install google-adk")
        print("  2. Set GOOGLE_API_KEY environment variable")
        print("  3. Or run: adk web")
        return
    
    result = await adk.run_negotiation()
    
    print("\n" + "=" * 50)
    print("ADK RESULT")
    print("=" * 50)
    print(f"Session: {result['session_id']}")
    print("=" * 50)


def run_batch(runtime: NegotiationRuntime, count: int) -> None:
    """Run multiple negotiations for evaluation."""
    import random
    
    print("=" * 50)
    print(f"BATCH MODE ({count} negotiations)")
    print("=" * 50 + "\n")
    
    results = []
    
    for i in range(count):
        buyer_max = random.uniform(300, 500)
        
        session = runtime.create_session(buyer_max_price=buyer_max)
        runtime.run_session(session)
        results.append(session)
        
        if runtime.runtime_config.verbose:
            status = "✓" if session.agreed else "✗"
            price = f"${session.final_price:.2f}" if session.final_price else "N/A"
            print(f"  [{i+1}] {status} {price} ({session.turns_taken} turns)")
    
    # Summary
    agreed = sum(1 for s in results if s.agreed)
    avg_price = sum(s.final_price for s in results if s.final_price) / agreed if agreed else 0
    avg_turns = sum(s.turns_taken for s in results) / len(results)
    
    print("\n" + "=" * 50)
    print("BATCH SUMMARY")
    print("=" * 50)
    print(f"Total: {count}")
    print(f"Success Rate: {100 * agreed / count:.1f}%")
    print(f"Avg Price: ${avg_price:.2f}" if avg_price else "Avg Price: N/A")
    print(f"Avg Turns: {avg_turns:.1f}")
    print("=" * 50)


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Agent Negotiation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m 10_runtime.runner --mode demo     # Rule-based demo
  python -m 10_runtime.runner --mode adk      # Google ADK with Gemini
  python -m 10_runtime.runner --mode batch    # Batch evaluation
  
ADK CLI (requires google-adk):
  adk web                                    # Web UI
  adk run 10_runtime                          # Run agent
"""
    )
    
    parser.add_argument("--mode", choices=["demo", "batch", "adk"], default="demo",
                        help="demo=rule-based, adk=Google ADK with LLM, batch=evaluation")
    parser.add_argument("--strategy", choices=["rule", "llm"], default="rule")
    parser.add_argument("--count", type=int, default=10, help="Batch count")
    parser.add_argument("--config", type=str, help="Config file path")
    parser.add_argument("--quiet", action="store_true")
    
    args = parser.parse_args()
    
    # ADK mode uses async
    if args.mode == "adk":
        asyncio.run(run_adk_mode())
        return
    
    # Other modes use sync fallback runtime
    config = RuntimeConfig(
        mode=args.mode,
        strategy=args.strategy,
        config_path=args.config,
        verbose=not args.quiet,
        batch_count=args.count,
    )
    
    runtime = NegotiationRuntime(config)
    
    try:
        runtime.initialize()
        
        if args.mode == "demo":
            run_demo(runtime)
        elif args.mode == "batch":
            run_batch(runtime, args.count)
    
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    main()
