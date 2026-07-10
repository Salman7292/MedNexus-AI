# Agent Design Reference

MedNexus AI exposes five specialist AI agents, each implemented as an independent **LangGraph `StateGraph`** in its own `*_logic.py` module.

---

## Agent Roster

| # | Agent Name | Role | Model | Route | Database |
|---|---|---|---|---|---|
| 1 | **Dr. Zavian** | Dermatologist | `meta-llama/llama-4-scout-17b-16e-instruct` (Groq) | `/specialists/derma/consult` | `dermatologist.db` |
| 2 | **Dr. Anees** | ENT Specialist | `meta-llama/llama-4-scout-17b-16e-instruct` (Groq) | `/specialists/ent/consult` | `ent.db` |
| 3 | **Dr. Aria** | Psychiatrist | `meta-llama/llama-4-scout-17b-16e-instruct` (Groq) | `/specialists/psych/consult` | `psychiatrist.db` |
| 4 | **Dr. Pharma** | Pharmacist | `meta-llama/llama-4-scout-17b-16e-instruct` (Groq) | `/specialists/pharmacy/consult` | `pharmacy_chats.db` |
| 5 | **Dr. Alara** | General Physician (Triage) | `openai/gpt-oss-120b` (Groq) | `/specialists/general/consult` | `general.db` |

---

## Shared Architecture Pattern

Every specialist follows the same LangGraph pattern:

```
User Message
    │
    ▼
┌──────────────────────────────────────────┐
│          LangGraph StateGraph            │
│                                          │
│  ┌─────────┐      ┌──────────────────┐  │
│  │  agent  │ ───► │   tool_node      │  │
│  │  (LLM)  │ ◄─── │  (Tool Results)  │  │
│  └─────────┘      └──────────────────┘  │
│       │                                  │
│       ▼ (tools_condition = END)          │
└──────────────────────────────────────────┘
    │
    ▼
Streamed Response (SSE)
```

### State Schema

Each agent uses `MessagesState` (a LangGraph built-in). The graph is compiled with `SqliteSaver` as the checkpointer, persisting the full message history keyed by `thread_id`.

```python
from langgraph.graph import StateGraph, MessagesState
from langgraph.checkpoint.sqlite import SqliteSaver

graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")

checkpointer = SqliteSaver(conn)   # SQLite DB per specialist
app = graph.compile(checkpointer=checkpointer)
```

---

## System Prompt Design

Each agent is constrained by a **Clinical Rigor** system prompt that:

1. Assigns an unbreakable professional persona (name, specialty, hospital affiliation).
2. Requires **step-by-step differential reasoning** before any diagnosis.
3. Prohibits assumptions — the agent must call a RAG or search tool to verify clinical claims.
4. Defines the exact output format for prescriptions, referrals, and reports.
5. Instructs the model to respond concisely ("WhatsApp-style" — short, empathetic messages).

---

## Memory and Context Management

Each agent applies a **"Sandwich Windowing"** strategy to manage the context window across long conversations:

- **Retain**: First 15 messages (initial intake history — always kept).
- **Prune**: The "middle" messages are condensed/dropped beyond a threshold.
- **Retain**: Most recent 25 messages (active conversation context).

A condensation marker is inserted at the pruning boundary so the LLM understands context was summarised. This keeps token consumption bounded while preserving the clinical intake history.

---

## Agent-Specific Details

### Dr. Zavian — Dermatologist (`dermatologist_logic.py`)

- **Tools**: `analyze_skin_or_report_image`, `diagnosis_retrieval_tool`, `medication_retrieval_tool`, `doctor_search_tool`, `search_tool`, `generate_medical_report`
- **Pinecone Index**: `dermatologist`
- **Upload Directory**: `static/dermatalogist_upload/`
- **Report Signer**: "Dr. Zavian, MD, Dermatology"

### Dr. Anees — ENT Specialist (`ent_logic.py`)

- **Tools**: `analyze_ear_or_report_image`, `diagnosis_retrieval_tool`, `medication_retrieval_tool`, `ent_doctor_search_tool`, `search_tool`, `generate_ent_report`
- **Pinecone Index**: `ent-specialist`
- **Upload Directory**: `static/ent_upload/`
- **Report Signer**: "Dr. Anees, MD, ENT"

### Dr. Aria — Psychiatrist (`psych_logic.py`)

- **Tools**: `diagnosis_retrieval_tool`, `medication_retrieval_tool`, `psychiatrist_doctor_search_tool`, `search_tool`, `generate_psych_report`
- **Pinecone Index**: `psychiatrist-specialist`
- **Report Signer**: "Dr. Aria, MD, Psychiatry"

### Dr. Pharma — Pharmacist (`pharmacy_logic.py`)

- **Tools**: `prescription_analysis_tool`, `drug_interaction_tool`, `medication_retrieval_tool`, `search_tool`, `generate_pharmacy_report`
- **Pinecone Index**: `pharmacy`
- **Upload Directory**: `static/pharmacy_upload/`
- **Report Signer**: "Dr. Pharma, PharmD"

### Dr. Alara — General Physician (`general_logic.py`)

- **Tools**: *None (no RAG tools — provides triage and referral only)*
- **Pinecone Index**: *None*
- **Purpose**: Initial patient screening and routing to the correct specialist. Does not perform in-depth diagnosis.
- **Model**: `openai/gpt-oss-120b` via Groq API (different from the specialist model).
