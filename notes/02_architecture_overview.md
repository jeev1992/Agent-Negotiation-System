# 02 - Architecture Overview (End-to-End)

## Purpose

Give learners the map before the territory. Before diving into any single layer, you need to see how all 9 layers connect.

---

## The Full System at a Glance

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AGENT NEGOTIATION SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  11_evaluation                                                           │   │
│   │  "How good was it?" - Judge scoring, LangSmith experiments              │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      ▲                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  observability                                                        │   │
│   │  "What happened?" - Tracing, logging, LangSmith                         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      ▲                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  10_runtime (Google ADK)                                                 │   │
│   │  "How does it run?" - THE SHELL, lifecycle, config                      │   │
│   │                                                                         │   │
│   │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│   │   │  07_coordination (ACP)                                           │   │   │
│   │   │  "What's allowed?" - Policy, governance, permissions            │   │   │
│   │   │                                                                 │   │   │
│   │   │   ┌─────────────────────────────────────────────────────────┐   │   │   │
│   │   │   │  06_orchestration (LangGraph)                            │   │   │   │
│   │   │   │  "What runs next?" - Flow control, state graph          │   │   │   │
│   │   │   │                                                         │   │   │   │
│   │   │   │   ┌─────────────────────────────────────────────────┐   │   │   │   │
│   │   │   │   │  05_agents                                       │   │   │   │   │
│   │   │   │   │  "What to decide?" - Pure strategy functions    │   │   │   │   │
│   │   │   │   │                                                 │   │   │   │   │
│   │   │   │   │   ┌───────────────┐   ┌───────────────┐         │   │   │   │   │
│   │   │   │   │   │ 09_context     │   │ 04_fsm         │         │   │   │   │   │
│   │   │   │   │   │ (MCP)         │   │ Termination   │         │   │   │   │   │
│   │   │   │   │   │ Grounded Data │   │ Guarantees    │         │   │   │   │   │
│   │   │   │   │   └───────────────┘   └───────────────┘         │   │   │   │   │
│   │   │   │   └─────────────────────────────────────────────────┘   │   │   │   │
│   │   │   └─────────────────────────────────────────────────────────┘   │   │   │
│   │   └─────────────────────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  08_transport                                                            │   │
│   │  "How do messages move?" - Channels, delivery, retry                    │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Who Owns What Responsibility

| Layer | Question | Responsibility | Does NOT Do |
|-------|----------|----------------|-------------|
| **10_runtime** | "How does it run?" | Lifecycle, config, modes | Negotiation logic |
| **07_coordination** | "What's allowed?" | Policy enforcement, permissions | Flow control |
| **08_transport** | "How do messages move?" | Delivery, retry, timeout | Message meaning |
| **06_orchestration** | "What runs next?" | Flow control, state graph | Business decisions |
| **05_agents** | "What to decide?" | Strategy, calculations | Infrastructure |
| **09_context** | "What's true?" | Grounded data from sources | Agent logic |
| **04_fsm** | "When does it stop?" | Terminal states, transitions | Negotiation flow |
| **observability** | "What happened?" | Tracing, logging | Affecting behavior |
| **11_evaluation** | "How good was it?" | Scoring, judging | Changing outcomes |

---

## The Execution Timeline

What happens when you run `python -m 10_runtime.runner --mode demo`:

```
TIME →
─────────────────────────────────────────────────────────────────────────────────►

Phase 1: STARTUP
┌─────────────────────────────────────────────────────────────────────────────────┐
│  10_runtime loads config                                                         │
│  10_runtime initializes 09_context (MCP server)                                   │
│  10_runtime initializes 07_coordination (policy)                                  │
│  10_runtime creates session                                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

Phase 2: NEGOTIATION
┌─────────────────────────────────────────────────────────────────────────────────┐
│  10_runtime calls 06_orchestration.run_negotiation()                              │
│    │                                                                            │
│    ├── Turn 1: 06_orchestration calls buyer_node()                               │
│    │     └── 05_agents.buyer_strategy() returns offer                            │
│    │     └── 04_fsm checks: still NEGOTIATING                                    │
│    │                                                                            │
│    ├── Turn 1: 06_orchestration calls seller_node()                              │
│    │     └── 09_context.get_pricing_rules() returns min_price                    │
│    │     └── 05_agents.seller_strategy() returns counter                         │
│    │     └── 04_fsm checks: still NEGOTIATING                                    │
│    │                                                                            │
│    ├── Turn 2-4: repeat...                                                      │
│    │                                                                            │
│    └── Turn 5: seller accepts                                                   │
│          └── 04_fsm transitions to AGREED (terminal)                             │
│          └── 06_orchestration returns result                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

Phase 3: EVALUATION
┌─────────────────────────────────────────────────────────────────────────────────┐
│  observability traces are sent to LangSmith                                   │
│  11_evaluation.judge scores the outcome                                          │
│  10_runtime prints summary                                                       │
│  10_runtime.shutdown()                                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## The Call Stack (Who Calls Who)

```
main()
└── NegotiationRuntime(config)
    └── runtime.initialize()
    │   ├── load_config()           # 10_runtime/config.py
    │   ├── MCPServer()             # 09_context/server.py
    │   └── CoordinationPolicy()    # 07_coordination/policy.py
    │
    └── runtime.run_session(session)
        └── run_negotiation()       # 06_orchestration/graph.py
            │
            ├── buyer_node(state)
            │   └── buyer_strategy() # 05_agents/buyer.py
            │   └── fsm.process_turn() # 04_fsm/state_machine.py
            │
            ├── seller_node(state)
            │   └── mcp.get_pricing_rules() # 09_context/server.py
            │   └── seller_strategy() # 05_agents/seller.py
            │   └── fsm.process_turn() # 04_fsm/state_machine.py
            │
            └── router(state) → "continue" or "done"
```

---

## Mental Model: This Is a Distributed System

> **"This is a distributed system with agents inside it."**

Don't think of this as "two chatbots talking." Think of it as:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DISTRIBUTED SYSTEM                           │
│                                                                 │
│  ┌──────────┐     message      ┌──────────┐                    │
│  │  Agent A │ ◄──────────────► │  Agent B │                    │
│  └──────────┘                  └──────────┘                    │
│       │                             │                          │
│       │                             │                          │
│       ▼                             ▼                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    SHARED STATE                         │   │
│  │  • FSM state (NEGOTIATING, AGREED, FAILED)              │   │
│  │  • Turn counter                                         │   │
│  │  • Message history                                      │   │
│  │  • Agreed price (if any)                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Governed by: POLICY (who can do what)                          │
│  Controlled by: ORCHESTRATOR (what runs when)                   │
│  Grounded by: MCP (what is objectively true)                    │
│  Terminated by: FSM (when does it end)                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

This mental model explains why:
- You need **protocols** (agents must agree on message format)
- You need **coordination** (agents must take turns)
- You need **grounded context** (agents must agree on facts)
- You need **termination** (the system must eventually stop)

---

## Data Flow: One Message's Journey

When buyer makes an offer:

```
05_agents/buyer.py
    │
    │  buyer_strategy() returns {"type": "offer", "price": 300}
    ▼
06_orchestration/graph.py
    │
    │  Adds to state["messages"], updates state
    ▼
08_transport/channel.py
    │
    │  Message delivered (in-memory for local)
    ▼
06_orchestration/graph.py
    │
    │  seller_node() receives via state
    ▼
09_context/server.py
    │
    │  Seller calls MCP: "What's my min price?"
    │  MCP returns: {"min_price": 350}
    ▼
05_agents/seller.py
    │
    │  seller_strategy() returns {"type": "counter", "price": 450}
    ▼
04_fsm/state_machine.py
    │
    │  FSM checks: still NEGOTIATING (not terminal)
    ▼
06_orchestration/graph.py
    │
    │  router() returns "continue" → back to buyer
    ▼
observability/tracer.py
    │
    │  Turn logged to LangSmith
```

---

## The Eleven Modules

Each module answers exactly ONE question:

| # | Module | Question |
|---|--------|----------|
| 01 | BASELINE | "What fails without architecture?" |
| 02 | ARCHITECTURE | "How do all the pieces connect?" |
| 03 | PROTOCOL | "What format do messages use?" |
| 04 | FSM | "Are we allowed to continue?" |
| 05 | AGENTS | "What does this agent decide?" |
| 06 | ORCHESTRATION | "What runs next?" |
| 07 | COORDINATION | "Who is allowed to act?" |
| 08 | TRANSPORT | "How does a message get from A to B?" |
| 09 | CONTEXT | "What is objectively true?" |
| 10 | RUNTIME | "How does this thing run as software?" |
| 11 | EVALUATION | "How good was the outcome?" |

If you can't answer "which layer handles this?", your architecture is wrong.

---

## Key Takeaway

> **Each layer answers ONE question. Together they form a system.**
>
> The layers are ordered by dependency, not by importance. Runtime wraps everything. Evaluation happens last. But when you're debugging, you work from the inside out: agents → orchestration → runtime.

---

## Next Steps

1. Read `03_protocols.md` to understand structured communication
2. Read `04_fsm_termination.md` to understand termination guarantees
3. Read `06_orchestration_langgraph.md` for the LangGraph deep dive
