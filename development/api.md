# Developer Guide — Adding a New Specialist Agent

This guide walks through extending MedNexus AI with a new specialist agent from scratch.

---

## Overview of Required Changes

To add a new agent (e.g., **Dr. Cardia, Cardiologist**) you need:

1. A new `*_logic.py` module defining the LangGraph graph, tools, and system prompt.
2. A new Pinecone index with the relevant namespaces.
3. A new HTML template in `templates/`.
4. A new JavaScript file in `static/js/`.
5. Routes registered in `app.py`.

---

## Step 1: Create the Logic Module

Copy an existing logic file (e.g., `dermatologist_logic.py`) and adapt:

```python
# cardiology_logic.py

import os
import sqlite3
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver

# ── Configuration ──────────────────────────────────────────────────
DB_NAME = "cardiology.db"
PINECONE_INDEX = "cardiology"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

embeddings = HuggingFaceEmbeddings(model_name="abhinand/MedEmbed-base-v0.1")
llm = ChatGroq(model=MODEL)

# ── Vector Stores ───────────────────────────────────────────────────
diag_store = PineconeVectorStore(
    index_name=PINECONE_INDEX,
    embedding=embeddings,
    namespace="diagnosis_knowledge",
    pinecone_api_key=os.environ["PINECONE_API_KEY"],
)

# ── Tools ───────────────────────────────────────────────────────────
@tool
def diagnosis_retrieval_tool(query: str) -> str:
    """Retrieve cardiology diagnosis information from the vector database."""
    docs = diag_store.similarity_search(query, k=5)
    return "\n\n".join(d.page_content for d in docs)

tools = [diagnosis_retrieval_tool]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)

# ── System Prompt ────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Dr. Cardia, a board-certified Cardiologist..."""

# ── Graph ─────────────────────────────────────────────────────────────
def call_model(state: MessagesState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
checkpointer = SqliteSaver(conn)
cardiology_app = graph.compile(checkpointer=checkpointer)
```

---

## Step 2: Register Routes in `app.py`

```python
from cardiology_logic import cardiology_app

SPECIALISTS = {
    # ... existing specialists ...
    "cardiology": {
        "name": "Dr. Cardia",
        "title": "Cardiologist",
        "app": cardiology_app,
    }
}

@app.route("/specialists/cardio/consult")
@login_required
def cardiology_consult():
    return render_template("cardiology.html")
```

In the `/chat` route's specialist dispatch:

```python
elif specialist == "cardiology":
    graph = cardiology_app
```

---

## Step 3: Create the HTML Template

Copy `templates/dermatologist.html` → `templates/cardiology.html` and update:
- Page title and meta description.
- Specialist name references (Dr. Cardia).
- The `<script src>` tag to point to `static/js/cardiology.js`.
- Color scheme / gradient classes if desired.

---

## Step 4: Create the JavaScript File

Copy `static/js/dermatologist.js` → `static/js/cardiology.js` and update:
- Welcome message text and avatar alt text.
- The `SPECIALIST` constant (used in the `/chat` payload): `const SPECIALIST = "cardiology";`
- Report download filename.
- Any specialist-specific UI text.

---

## Step 5: Populate the Pinecone Index

Create a `cardiology` index in Pinecone (dimension: 768, metric: cosine) and ingest your source documents. See `knowledge_base/building_the_index.md` for the full ingestion script.

---

## Code Style Conventions

| Convention | Detail |
|---|---|
| Logic file naming | `<specialty>_logic.py` |
| DB file naming | `<specialty>.db` or `<specialty>_chats.db` |
| Upload directory | `static/<specialty>_upload/` |
| Template naming | `templates/<specialty>.html` |
| JS file naming | `static/js/<specialty>.js` |
| Tool naming | snake_case, descriptive verb phrases |
| System prompt | Defined as a module-level constant `SYSTEM_PROMPT` |

---

## Running Tests

After adding a new agent, verify:

```bash
# 1. Import check — ensure no syntax/import errors
python -c "from cardiology_logic import cardiology_app; print('OK')"

# 2. Smoke test the retrieval tool
python - <<'EOF'
from cardiology_logic import diagnosis_retrieval_tool
result = diagnosis_retrieval_tool.invoke({"query": "chest pain symptoms"})
print(result[:300])
EOF

# 3. Start the app and test the new route
python app.py
# Navigate to http://localhost:5000/specialists/cardio/consult
```
