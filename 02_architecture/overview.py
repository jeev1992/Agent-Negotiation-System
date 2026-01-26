"""
Architecture Overview - End-to-End System Map

This module provides visual documentation of the system architecture.
It doesn't contain executable code, but serves as the reference point
for understanding how all layers connect.

See: notes/02_architecture_overview.md for detailed explanation
"""

LAYER_MAP = """
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT NEGOTIATION SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  01_BASELINE     │  The Problem - naive implementation that fails           │
│                                                                             │
│  02_ARCHITECTURE │  This layer - system overview (no code)                  │
│                                                                             │
│  03_PROTOCOL     │  Structured messages - "What format do we speak?"        │
│                                                                             │
│  04_FSM          │  State Machine - "When does it end?"                     │
│                                                                             │
│  05_AGENTS       │  Strategies - "What does each agent decide?"             │
│                                                                             │
│  06_ORCHESTRATION│  LangGraph - "What runs next?"                           │
│                                                                             │
│  07_COORDINATION │  ACP - "Who is allowed to speak, and when?"              │
│                                                                             │
│  08_TRANSPORT    │  Channels - "How does a message get from A to B?"        │
│                                                                             │
│  09_CONTEXT      │  MCP - "What is objectively true?"                       │
│                                                                             │
│  10_RUNTIME      │  Google ADK - "How does this thing run as software?"     │
│                                                                             │
│  11_EVALUATION   │  LangSmith + Judge - "How good was it?"                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
"""

EXECUTION_FLOW = """
┌──────────────┐
│  10_RUNTIME  │  ADK starts system
└──────┬───────┘
       ▼
┌──────────────┐
│07_COORDINATION│  Policy allows Buyer to speak
└──────┬───────┘
       ▼
┌──────────────┐
│ 08_TRANSPORT │  Message delivered
└──────┬───────┘
       ▼
┌──────────────┐
│06_ORCHESTRATION│  LangGraph executes Buyer node
└──────┬───────┘
       ▼
┌──────────────┐
│  05_AGENTS   │  Buyer strategy decides
└──────┬───────┘
       ▼
┌──────────────┐
│ 03_PROTOCOL  │  Message created with schema
└──────┬───────┘
       ▼
┌──────────────┐
│ 09_CONTEXT   │  Seller calls MCP for data
└──────┬───────┘
       ▼
┌──────────────┐
│   04_FSM     │  Check termination
└──────┬───────┘
       ▼
┌──────────────┐
│11_EVALUATION │  Judge scores outcome
└──────────────┘
"""

RESPONSIBILITY_MATRIX = {
    "01_baseline": "Demonstrate the problem",
    "02_architecture": "Document the solution",
    "03_protocol": "Define message schemas",
    "04_fsm": "Guarantee termination",
    "05_agents": "Make decisions",
    "06_orchestration": "Control flow",
    "07_coordination": "Enforce policy",
    "08_transport": "Deliver messages",
    "09_context": "Provide grounded data",
    "10_runtime": "Manage lifecycle",
    "11_evaluation": "Measure quality",
}


def print_architecture():
    """Print the architecture diagram."""
    print(LAYER_MAP)


def print_flow():
    """Print the execution flow."""
    print(EXECUTION_FLOW)


def get_layer_responsibility(layer: str) -> str:
    """Get the responsibility of a specific layer."""
    return RESPONSIBILITY_MATRIX.get(layer, "Unknown layer")


if __name__ == "__main__":
    print_architecture()
    print("\n" + "="*70 + "\n")
    print_flow()
