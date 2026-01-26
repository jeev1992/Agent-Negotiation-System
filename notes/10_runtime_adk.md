# 10 - Runtime & Lifecycle: Google ADK (Framework Deep Dive)

## Purpose

Explain how agent systems run as software. ADK manages lifecycle, configuration, and execution modes—it's the outermost shell.

---

## What Is a Runtime?

A **runtime** is the environment that:
1. **Starts** your application
2. **Configures** it with settings
3. **Manages** its lifecycle (init → run → shutdown)
4. **Provides** execution modes (demo, batch, production)

```
┌─────────────────────────────────────────────────────────────────┐
│                         RUNTIME                                 │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    YOUR APPLICATION                     │   │
│   │                                                         │   │
│   │   Orchestration, Agents, FSM, Transport, etc.           │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   Runtime handles: startup, config, modes, shutdown             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Google ADK Mental Model

> **"ADK is Kubernetes-like for agent systems."**

| Kubernetes | Google ADK |
|------------|------------|
| Runs containers | Runs agents |
| Manages pods | Manages sessions |
| Handles config | Handles config |
| Health checks | Agent monitoring |
| Scaling | Multi-session execution |

ADK is **infrastructure**, not business logic.

---

## What ADK Does

| Responsibility | Example |
|---------------|---------|
| **Entrypoint** | `python -m 10_runtime.runner` |
| **Config loading** | Read YAML/env vars |
| **Mode selection** | demo, batch, adk |
| **Session management** | Create, run, cleanup |
| **Lifecycle hooks** | initialize(), shutdown() |
| **Error handling** | Graceful shutdown, fallback modes |

---

## What ADK Does NOT Do

| Not Responsible | Handled By |
|----------------|------------|
| Negotiation logic | 05_agents |
| Flow control | 06_orchestration |
| Message format | 03_protocol |
| Permissions | 07_coordination |
| Termination rules | 04_fsm |

---

## Runtime Architecture

The system has **two runtime classes**:

1. **`ADKRuntime`** - Real Google ADK with Gemini LLM
2. **`NegotiationRuntime`** - Fallback with rule-based agents

```python
# 10_runtime/runner.py

from dataclasses import dataclass
from typing import Optional


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


class ADKRuntime:
    """
    Real Google ADK runtime.
    
    Uses google-adk's Runner to execute LLM agents.
    Requires GOOGLE_API_KEY environment variable.
    """
    
    async def initialize(self) -> bool:
        """Initialize ADK runtime with Gemini agents."""
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from .agent import root_agent  # ADK agent definitions
        
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=root_agent,
            app_name="negotiation_system",
            session_service=self._session_service,
        )
        return True
    
    async def run_negotiation(self, prompt: str) -> dict:
        """Run negotiation using ADK with LLM."""
        session = await self._session_service.create_session(...)
        
        async for event in self._runner.run_async(...):
            # Process LLM responses
            pass
        
        return result


class NegotiationRuntime:
    """
    Fallback runtime when ADK is not available.
    
    Uses rule-based agents for educational purposes.
    Does NOT require API keys.
    """
    
    def __init__(self, config: RuntimeConfig):
        self.runtime_config = config
        self._initialized = False
        self._mcp_server = None      # Grounded context
        self._policy = None          # Coordination rules
    
    def initialize(self) -> None:
        """Initialize components: MCP server, policy."""
        # Load config from YAML
        self.system_config = load_config(self.runtime_config.config_path)
        
        # Initialize MCP (grounded context)
        context_module = import_layer("09_context")
        self._mcp_server = context_module.MCPServer()
        
        # Initialize coordination policy
        coord_module = import_layer("07_coordination")
        self._policy = coord_module.CoordinationPolicy()
        
        self._initialized = True
    
    def create_session(self, **kwargs) -> Session:
        """Create a negotiation session with config."""
        return Session(
            buyer_max_price=kwargs.get("buyer_max_price", 
                                       self.system_config.agents.buyer_max_price),
            seller_min_price=kwargs.get("seller_min_price",
                                        self.system_config.agents.seller_min_price),
            max_turns=kwargs.get("max_turns",
                                self.system_config.limits.max_turns),
        )
    
    def run_session(self, session: Session) -> Session:
        """Run negotiation using 06_orchestration or fallback."""
        try:
            # Try full orchestration (LangGraph)
            orch_module = import_layer("06_orchestration")
            result = orch_module.run_negotiation(...)
        except ImportError:
            # Fallback to simple loop
            self._run_simple_negotiation(session)
        
        return session
    
    def shutdown(self) -> None:
        """Clean shutdown."""
        self._initialized = False
```

---

## CLI Entrypoint

```python
def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Agent Negotiation System")
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
    config = RuntimeConfig(mode=args.mode, ...)
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
```

---

## Config Loading

### YAML Configuration

```yaml
# config/negotiation.yaml

mode: demo
buyer_max: 400
seller_min: 300
max_turns: 10
log_level: INFO
trace_enabled: true

# Environment-specific overrides
production:
  trace_enabled: true
  log_level: WARNING
  
development:
  trace_enabled: false
  log_level: DEBUG
```

### Environment Variables

```bash
# Override config with env vars
export NEGOTIATION_MODE=batch
export NEGOTIATION_BUYER_MAX=500
export NEGOTIATION_TRACE_ENABLED=true

python -m 10_runtime.runner
```

---

## Execution Modes

The system supports **three execution modes**, each serving a different purpose:

| Mode | Engine | Use Case | Requires API Key |
|------|--------|----------|-----------------|
| `demo` | Rule-based agents | Development, learning | No |
| `batch` | Rule-based agents | Evaluation, testing | No |
| `adk` | Google ADK + Gemini | Production, LLM agents | Yes |

---

### Demo Mode (Default)

Single session with verbose output. Uses **deterministic rule-based agents** so no API key needed.

**When to use:** Learning, development, debugging.

```bash
$ python -m 10_runtime.runner --mode demo

==================================================
DEMO MODE (rule-based agents)
==================================================

[Runtime] Initializing (fallback mode)...
[Runtime] MCP server ready
[Runtime] Coordination policy ready
[Runtime] Ready

[Negotiation] Starting
  Buyer max: $450.00
  Seller min: $350.00
  Seller asking: $500.00

[Turn 1] Buyer: {'type': 'counter', 'price': 225.0}
[Turn 1] Seller: {'type': 'counter', 'price': 485.0}
[Turn 2] Buyer: {'type': 'counter', 'price': 288.75}
[Turn 2] Seller: {'type': 'counter', 'price': 453.25}
[Turn 3] Buyer: {'type': 'counter', 'price': 352.0}
[Turn 3] Seller: {'type': 'accept', 'price': 352.0}

[Result] Agreement: $352.00

==================================================
SUMMARY
==================================================
Session: abc123-...
Agreed: Yes
Final Price: $352.00
Turns: 3
Duration: 5.23ms
==================================================
[Runtime] Shutting down...
```

---

### Batch Mode

Multiple sessions with random buyer budgets. For **statistical evaluation**.

**When to use:** Testing success rates, collecting metrics, regression testing.

```bash
$ python -m 10_runtime.runner --mode batch --count 10

==================================================
BATCH MODE (10 negotiations)
==================================================

[Runtime] Initializing (fallback mode)...
[Runtime] Ready

  [1] ✓ $367.33 (4 turns)
  [2] ✓ $358.92 (3 turns)
  [3] ✗ N/A (10 turns)
  [4] ✓ $371.25 (5 turns)
  [5] ✓ $362.50 (4 turns)
  ...

==================================================
BATCH SUMMARY
==================================================
Total: 10
Success Rate: 80.0%
Avg Price: $362.22
Avg Turns: 4.8
==================================================
```

Key batch options:
- `--count N` - Number of negotiations to run (default: 10)
- `--quiet` - Suppress per-turn output

---

### ADK Mode (LLM-Powered)

Uses **real Google ADK** with **Gemini LLM** for intelligent agents.

**When to use:** Production, exploring LLM capabilities, comparing with rule-based.

**Prerequisites:**
1. Install: `pip install google-adk`
2. Set API key: `export GOOGLE_API_KEY=your_key`

```bash
$ python -m 10_runtime.runner --mode adk

==================================================
ADK MODE (Google ADK + Gemini)
==================================================

[ADK] Runtime initialized
[ADK] Agent: negotiation_orchestrator
[ADK] Sub-agents: ['buyer', 'seller']

[ADK] Starting negotiation...
[ADK] Prompt: Start a negotiation for an enterprise software license...

[Buyer] I'd like to purchase the enterprise license. My budget allows 
up to $400. What's your asking price?

[Seller] Our enterprise license is $500, but I can see you're serious.
Let me check what flexibility we have...

[Tool Call] get_pricing_rules()
→ {"min_price": 350, "max_discount": 30%}

[Seller] I can offer $425 given your interest.

[Buyer] That's above my budget. Would you consider $375?

[Seller] Let me meet you in the middle - $400?

[Buyer] Deal! $400 works for my budget.

==================================================
ADK RESULT
==================================================
Session: adk-session-001
==================================================
```

**Fallback behavior:** If ADK or API key unavailable, automatically falls back to demo mode with instructions.

---

### Mode Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                     EXECUTION MODES                             │
├────────────┬─────────────┬─────────────┬───────────────────────┤
│            │    DEMO     │    BATCH    │         ADK           │
├────────────┼─────────────┼─────────────┼───────────────────────┤
│ Agents     │ Rule-based  │ Rule-based  │ LLM (Gemini)          │
│ Sessions   │ 1           │ N (random)  │ 1                     │
│ Output     │ Verbose     │ Summary     │ Conversational        │
│ API Key    │ No          │ No          │ Yes (Google)          │
│ Use Case   │ Learning    │ Evaluation  │ Production            │
│ Latency    │ ~5ms        │ ~5ms/each   │ ~2-5s (LLM calls)     │
└────────────┴─────────────┴─────────────┴───────────────────────┘
```

---

## Call Stack Diagram

```
main()
│
├── load_config()
│   └── Read YAML, env vars, CLI args
│
├── NegotiationRuntime(config)
│   └── Store config, prepare state
│
├── runtime.initialize()
│   ├── MCPServer()           ─► 09_context
│   ├── CoordinationPolicy()  ─► 07_coordination
│   └── init_tracing()        ─► observability
│
├── runtime.run_session(session_id)
│   │
│   ├── create_negotiation_graph()  ─► 06_orchestration
│   │   ├── buyer_node()            ─► 05_agents
│   │   ├── seller_node()           ─► 05_agents
│   │   └── router()                ─► 04_fsm
│   │
│   └── graph.invoke(initial_state)
│       └── Execute until terminal
│
└── runtime.shutdown()
    └── Cleanup, flush traces
```

---

## Lifecycle Ownership

The runtime OWNS the lifecycle:

```
STARTUP                    RUNNING                    SHUTDOWN
───────►                   ───────────────────►       ───────►

┌──────────┐   ┌─────────────────────────────┐   ┌──────────┐
│Initialize│   │      Run Sessions           │   │ Shutdown │
│          │   │                             │   │          │
│ • Config │   │  Session 1 ─► Session 2 ─►  │   │ • Flush  │
│ • MCP    │   │                             │   │ • Cleanup│
│ • Policy │   │  (runtime is running)       │   │ • Report │
│ • Trace  │   │                             │   │          │
└──────────┘   └─────────────────────────────┘   └──────────┘

     │                    │                           │
     │    RUNTIME RESPONSIBILITY                      │
     └────────────────────┴───────────────────────────┘
```

---

## Common Misconceptions (Important!)

### ❌ "ADK replaces LangGraph"

**Wrong.** They're different layers:

| Aspect | ADK | LangGraph |
|--------|-----|-----------|
| Level | Application shell | Workflow engine |
| Scope | Full lifecycle | Single workflow |
| Concern | How to run | How to orchestrate |

ADK **contains** LangGraph, not replaces it.

### ❌ "ADK is orchestration"

**Wrong.** ADK starts orchestration:

```python
# ADK does this:
runtime.initialize()
result = runtime.run_session()  # ← Calls orchestration
runtime.shutdown()

# Orchestration does this:
graph.invoke(state)  # ← The actual flow control
```

### ❌ "ADK is just a main() function"

**Partially right.** ADK is a **structured** main() with:
- Configuration management
- Lifecycle hooks
- Mode selection
- Session management
- Error handling

---

## Integration with Real Google ADK

When using actual Google ADK with Gemini:

```python
# 10_runtime/agent.py

from google.adk.agents import Agent

# Define agents using ADK
root_agent = Agent(
    name="negotiation_orchestrator",
    model="gemini-2.0-flash",
    description="Orchestrates buyer and seller negotiation",
    sub_agents=[buyer_agent, seller_agent],
    tools=[get_pricing_rules, make_offer, accept_offer],
)

buyer_agent = Agent(
    name="buyer",
    model="gemini-2.0-flash",
    description="Negotiates to buy at lowest price",
    instruction="You are a buyer. Your max budget is {max_price}.",
)

seller_agent = Agent(
    name="seller",
    model="gemini-2.0-flash", 
    description="Negotiates to sell at highest price",
    instruction="You are a seller. Your min price is {min_price}.",
)
```

---

## Key Takeaway

> **ADK is the outermost shell. It runs the system; it doesn't define the logic.**
>
> Think of ADK as the "power button" and "control panel" for your agent system. It turns things on, configures them, and monitors them—but the actual negotiation happens in the layers inside.

---

## Code References

- [10_runtime/runner.py](../10_runtime/runner.py) - Main runtime
- [10_runtime/agent.py](../10_runtime/agent.py) - ADK agent definitions
- [config/negotiation.yaml](../config/negotiation.yaml) - Configuration

---

## Next Steps

1. Read `11_langsmith_evaluation.md` for observability
2. Read `06_orchestration_langgraph.md` to see what ADK calls
3. Read `12_execution_walkthrough.md` for full trace
