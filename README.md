# Agent Negotiation System

A **stateful, multi-agent, policy-governed, observable** negotiation system demonstrating production agent architecture.

## The Problem We're Solving

> "Given two agents (Buyer and Seller) that need to negotiate a price, implement a system that allows them to reach agreement."

The **naive solution** looks simple:

```python
while True:
    buyer_message = buyer.respond(seller_message)
    if "DEAL" in buyer_message:
        break
    seller_message = seller.respond(buyer_message)
```

**This implementation is fundamentally broken.** See [01_baseline/naive_negotiation.py](01_baseline/naive_negotiation.py) for the full demonstration.

### What Goes Wrong

1. **Parsing Ambiguity**: "I could pay $200 or $300" - regex extracts $200
2. **Infinite Loops**: `while True` has no termination guarantee
3. **Silent Failures**: Errors don't crash, they propagate
4. **No Grounded Context**: Hardcoded prices can be wrong
5. **No Observability**: Can't see what happened or why

Run the baseline to see these failures:

```bash
python -m 01_baseline.naive_negotiation
```

## Architecture Overview

This is NOT a chatbot, NOT a single LLM call, NOT a script.

This IS a **stateful, multi-agent, policy-governed, observable system**.

Everything in this codebase exists because something breaks without it.

### Agent Communication Protocols

This project implements the three major agent communication protocols:

| Protocol | Source | Purpose | Our Module |
|----------|--------|---------|------------|
| **MCP** | Anthropic | Connect agents to tools & data ("USB port") | `09_context/` |
| **A2A** | Google | Agent discovery & inter-agent messaging ("meeting rooms") | `08_transport/` |
| **ACP** | IBM/BeeAI | Workflow orchestration & governance ("project manager") | `06_orchestration/` + `07_coordination/` |

> 📖 **Further Reading:** [Agentic AI Protocols: MCP, A2A, and ACP](https://medium.com/@manavg/agentic-ai-protocols-mcp-a2a-and-acp-ea0200eac18b) - Excellent overview of how these protocols complement each other.
>
> **Official Documentation:**
> - [MCP (Model Context Protocol)](https://modelcontextprotocol.io/introduction) - Anthropic
> - [A2A (Agent-to-Agent Protocol)](https://google.github.io/A2A/) - Google
> - [ACP (Agent Communication Protocol)](https://github.com/i-am-bee/ACP) - IBM/BeeAI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT NEGOTIATION SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  01_BASELINE     │  The Problem - naive implementation that fails           │
│                                                                             │
│  02_ARCHITECTURE │  System Overview - "How does it all fit together?"       │
│                                                                             │
│  03_PROTOCOL     │  Structured messages - "What format do we speak?"        │
│                                                                             │
│  04_FSM          │  State Machine - "When does it end?"                     │
│                                                                             │
│  05_AGENTS       │  Strategies - "What does each agent decide?"             │
│                                                                             │
│  06_ORCHESTRATION│  LangGraph - "What runs next?"                           │
│                                                                             │
│  07_COORDINATION │  ACP (Policy) - "Who is allowed to speak, and when?"    │
│                                                                             │
│  08_TRANSPORT    │  A2A - "How do agents discover and talk to each other?" │
│                                                                             │
│  09_CONTEXT      │  MCP - "What is objectively true?"                       │
│                                                                             │
│  10_RUNTIME      │  Google ADK - "How does this thing run as software?"     │
│                                                                             │
│  11_EVALUATION   │  LangSmith + Judge - "How good was it?"                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Layer Summary

| # | Module | Purpose | Note |
|---|--------|---------|------|
| 01 | `01_baseline/` | The Problem - naive implementation | [01_problem_baseline.md](notes/01_problem_baseline.md) |
| 02 | `02_architecture/` | System Overview (documentation) | [02_architecture_overview.md](notes/02_architecture_overview.md) |
| 03 | `03_protocol/` | Message Schemas & Validation | [03_protocols.md](notes/03_protocols.md) |
| 04 | `04_fsm/` | Termination Guarantees | [04_fsm_termination.md](notes/04_fsm_termination.md) |
| 05 | `05_agents/` | Strategy & Decisions | [05_agents_strategies.md](notes/05_agents_strategies.md) |
| 06 | `06_orchestration/` | LangGraph - Control Flow | [06_orchestration_langgraph.md](notes/06_orchestration_langgraph.md) |
| 07 | `07_coordination/` | ACP (Policy) - Governance | [07_coordination_acp.md](notes/07_coordination_acp.md) |
| 08 | `08_transport/` | A2A - Agent Communication | [08_transport.md](notes/08_transport.md) |
| 09 | `09_context/` | MCP - Grounded Context | [09_mcp_context.md](notes/09_mcp_context.md) |
| 10 | `10_runtime/` | Google ADK - THE SHELL | [10_runtime_adk.md](notes/10_runtime_adk.md) |
| 11 | `11_evaluation/` | LangSmith - Tracing & Scoring | [11_langsmith_evaluation.md](notes/11_langsmith_evaluation.md) |

## The Single Run Flow

```
ADK starts system (10_runtime)
   ↓
Session created
   ↓
Policy allows Buyer to speak (07_coordination)
   ↓
Message delivered via transport (08_transport)
   ↓
LangGraph executes Buyer node (06_orchestration)
   ↓
Buyer strategy decides (05_agents)
   ↓
Message created with protocol (03_protocol)
   ↓
Seller node runs, calls MCP (09_context)
   ↓
FSM checks termination (04_fsm)
   ↓
LangGraph loops or ends
   ↓
LangSmith records trace (11_evaluation)
   ↓
Judge scores outcome (11_evaluation)
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run a demo negotiation (rule-based, no API key needed)
python -m 10_runtime.runner --mode demo

# Run batch evaluation (multiple negotiations with random parameters)
python -m 10_runtime.runner --mode batch --count 10

# Run with Google ADK + Gemini (requires GOOGLE_API_KEY)
export GOOGLE_API_KEY=your_key_here
python -m 10_runtime.runner --mode adk

# Run unit tests
python -m pytest tests/ -v

# Run local evaluation (judge scoring)
python -m 11_evaluation.langsmith.run_evaluation --local
```

### Execution Modes

| Mode | Engine | Use Case | Requires API Key |
|------|--------|----------|------------------|
| `demo` | Rule-based agents | Development, learning | No |
| `batch` | Rule-based agents | Evaluation, testing | No |
| `adk` | Google ADK + Gemini | Production, LLM agents | Yes |

## Directory Structure

```
agent_negotiation_system/
├── 01_baseline/        # The Problem - naive implementation that fails
├── 02_architecture/    # System overview (documentation)
├── 03_protocol/        # Message schemas & validation
│   ├── messages.py     # Offer, Counter, Accept, Reject types
│   └── envelope.py     # Message wrapper with metadata
├── 04_fsm/             # State machine - termination guarantees
│   └── state_machine.py
├── 05_agents/          # Buyer/Seller strategies
│   ├── buyer.py        # Buyer strategy (rule-based)
│   ├── seller.py       # Seller strategy (rule-based)
│   └── adk_agents.py   # ADK agent definitions (LLM-powered)
├── 06_orchestration/   # LangGraph - control flow
│   ├── graph.py        # Negotiation graph
│   └── state.py        # State definitions
├── 07_coordination/    # ACP (Policy) - governance rules
│   └── policy.py       # Coordination policy
├── 08_transport/       # A2A - agent-to-agent communication
│   └── channel.py      # Agent communication channel
├── 09_context/         # MCP - grounded context
│   └── server.py       # MCP server implementation
├── 10_runtime/         # Google ADK - THE SHELL (entrypoint)
│   ├── runner.py       # Main CLI (demo/batch/adk modes)
│   ├── agent.py        # Re-exports ADK agents
│   └── config.py       # Configuration loader
├── 11_evaluation/      # Quality assessment
│   ├── judge.py        # Rule-based judge (deterministic)
│   └── langsmith/      # LangSmith experiments
│       ├── dataset.py      # Test scenarios
│       ├── evaluators.py   # Scoring functions
│       └── run_evaluation.py  # CLI runner
├── config/             # Configuration files
│   └── negotiation.yaml
├── notes/              # Study notes (01-13)
└── tests/              # Unit and integration tests
    ├── test_agents.py
    ├── test_fsm.py
    ├── test_policy.py
    ├── test_evaluation.py
    └── test_integration.py
```

## Test Results

The system includes **53 unit and integration tests**:

```bash
$ python -m pytest tests/ -v

tests/test_agents.py - 14 tests (buyer/seller strategies)
tests/test_fsm.py - 10 tests (state machine, termination)
tests/test_policy.py - 8 tests (coordination rules)
tests/test_evaluation.py - 11 tests (judge scoring)
tests/test_integration.py - 10 tests (end-to-end)

53 passed ✓
```

## Evaluation

Two approaches for evaluating negotiation quality:

### 1. Rule-Based Judge (Fast, Deterministic)

```python
from importlib import import_module
evaluation = import_module("11_evaluation")

judge = evaluation.NegotiationJudge()
result = judge.evaluate(
    buyer_max=400, 
    seller_min=300,
    result={"status": "agreed", "agreed_price": 350, "turns": 3}
)
print(f"Score: {result.score}")
```

### 2. LangSmith Experiments (Cloud, Dashboards)

```bash
# Run locally
python -m 11_evaluation.langsmith.run_evaluation --local

# Upload dataset to LangSmith
python -m 11_evaluation.langsmith.run_evaluation --upload

# Run experiment (results at smith.langchain.com)
python -m 11_evaluation.langsmith.run_evaluation --experiment
```

## Study Notes

The `notes/` folder contains detailed explanations following the learning progression:

| # | Note | Topic |
|---|------|-------|
| 01 | [01_problem_baseline.md](notes/01_problem_baseline.md) | Why naive implementations fail |
| 02 | [02_architecture_overview.md](notes/02_architecture_overview.md) | End-to-end system map |
| 03 | [03_protocols.md](notes/03_protocols.md) | Structured communication |
| 04 | [04_fsm_termination.md](notes/04_fsm_termination.md) | FSM & termination guarantees |
| 05 | [05_agents_strategies.md](notes/05_agents_strategies.md) | Deterministic agent logic |
| 06 | [06_orchestration_langgraph.md](notes/06_orchestration_langgraph.md) | LangGraph deep dive |
| 07 | [07_coordination_acp.md](notes/07_coordination_acp.md) | Policy-based governance |
| 08 | [08_transport.md](notes/08_transport.md) | Message delivery abstraction |
| 09 | [09_mcp_context.md](notes/09_mcp_context.md) | Grounded context with MCP |
| 10 | [10_runtime_adk.md](notes/10_runtime_adk.md) | Google ADK deep dive |
| 11 | [11_langsmith_evaluation.md](notes/11_langsmith_evaluation.md) | LangSmith deep dive |
| 12 | [12_execution_walkthrough.md](notes/12_execution_walkthrough.md) | Full execution trace |
| 13 | [13_what_breaks.md](notes/13_what_breaks.md) | Failure analysis |

## The Key Insight

> **This system separates running, deciding, coordinating, communicating, and evaluating — because mixing them always fails.**

## Requirements

- Python 3.10+
- google-adk (optional, for ADK mode with LLM agents)
- LangGraph (orchestration)
- LangSmith (optional, for cloud-based observability & experiments)

See `requirements.txt` for full dependencies.

## License

MIT
