# Adding a New Specialty Agent

This guide describes how to extend the MedNexus AI platform by adding a new specialist agent (e.g. **Dr. Cardia, Cardiologist**) without modifying the core state graph patterns.

---

## Extension Overview

Adding a new specialist involves:
1.  **Creating the Logic module**: `cardiology_logic.py` detailing the graph state, prompt, and tool registration.
2.  **Configuring SQLite persistence**: Allocating a unique local `.db` file (e.g. `cardiology.db`).
3.  **Populating Pinecone Index**: Creating a Pinecone index with the necessary namespaces.
4.  **Registering Flask routes**: Setting up consult serving templates and dispatch keys inside `app.py`.
5.  **Building Frontend layouts**: Creating a template page and matching client JS scripts.

---

## Step-by-Step Implementation

### 1. Write the Cardiology Logic Engine
Copy an existing specialist engine (like [dermatologist_logic.py](file:///d:/archive/mednexai_3rd_version/mednexai_3rd_version/dermatologist_logic.py)) to `cardiology_logic.py`. Update the following settings:

```python
# cardiology_logic.py
DB_NAME = "cardiology.db"

# Update vector store retrieval settings
def get_cardio_store():
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index_name="cardiology",
        embedding=get_embeddings(),
        namespace="diagnosis_knowledge"
    )
```

Define a rigorous, specialist-specific system prompt and register the tools:
```python
SYSTEM_PROMPT = """ROLE: You are Dr. Cardia, a board-certified Cardiologist..."""

@tool
def heart_rate_calc(beats: int, seconds: int) -> int:
    """Calculates heart beats per minute."""
    return int((beats / seconds) * 60)

tools = [get_cardio_store, heart_rate_calc, generate_cardio_report]
```

Build, configure, and compile the graph:
```python
graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "agent")
...
checkpointer = SqliteSaver(conn)
cardiology_compiled = graph.compile(checkpointer=checkpointer)
```

---

### 2. Set Up the Pinecone Index
Create a new index in your Pinecone dashboard:
*   **Name**: `cardiology`
*   **Dimensions**: `768` (matching `MedEmbed-base-v0.1`)
*   **Metric**: `cosine`

Ingest documents (symptoms, drugs, clinic directories) into namespaces: `diagnosis_knowledge`, `medication_knowledge`, and `cardiology_geo_directory` (refer to the [Ingestion Guide](../architecture/knowledge-base.md)).

---

### 3. Register routing in `app.py`
Add the new specialist to `DOCTORS` dictionary in [app.py](file:///d:/archive/mednexai_3rd_version/mednexai_3rd_version/app.py):

```python
DOCTORS['cardio'] = {
    'id': 'cardio',
    'name': 'Dr. Cardia',
    'title': 'AI Cardiologist',
    'specialty': 'Cardiology & Heart Health',
    ...
}
```

Import your module, and update `/chat`, `/threads`, `/history`, and `/edit` routes inside `app.py` to support the dispatch key:

```python
import cardiology_logic as cardio_logic_module

# Inside /chat route dispatch:
if specialist == 'cardio':
    current_logic = cardio_logic_module
```

Add a rendering route for the consultation view:
```python
@app.route('/specialists/cardio/consult')
@login_required
def cardio_consult():
    return render_template('cardiology.html', username=session['username'])
```

---

### 4. Create templates and scripts
1.  **Template**: Copy `templates/dermatalogist.html` to `templates/cardiology.html`. Update title and reference headings, and load `static/js/cardiology.js`.
2.  **JavaScript**: Copy `static/js/dermatalogist.js` to `static/js/cardiology.js`. Set:
    ```javascript
    const SPECIALIST = "cardio";
    ```
    This ensures that message payloads submitted to `/chat` use the correct backend dispatch routing.
