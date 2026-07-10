# Tool Reference

Each specialist agent has access to a **Tool Node** — a set of `@tool`-decorated Python functions that the LLM can call autonomously when it needs external data. Tools are registered with the LangGraph `ToolNode` and bound to the LLM via `.bind_tools(tools)`.

---

## Common Tools (present in most agents)

### `diagnosis_retrieval_tool`
Queries the `diagnosis_knowledge` Pinecone namespace for symptom-to-disease mappings.

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Clinical symptom description or diagnostic question |

**Returns**: Top-5 most relevant clinical diagnosis chunks as a concatenated string.

---

### `medication_retrieval_tool`
Queries the `medication_knowledge` Pinecone namespace for pharmacological data.

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Drug name, condition, or contraindication query |

**Returns**: Dosage protocols, first/second-line treatment options, and contraindications.

---

### `doctor_search_tool` / `ent_doctor_search_tool` / `psychiatrist_doctor_search_tool`
Queries the `*_geo_directory` Pinecone namespace to find local specialist clinics near the patient.

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Patient zip code or city name |

**Returns**: Clinic names, addresses, and contact numbers proximal to the patient's area.

---

### `search_tool` (Tavily Live Web Search)
Performs a real-time web search via the Tavily API. Used as a **fallback** for:
- Emerging clinical guidelines not in the static vector database.
- New FDA drug approvals or recalls.
- Accurate clinic addresses and operating hours.
- Rare or edge-case conditions with low RAG confidence.

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Search query string |

**Returns**: Web search results summarised by Tavily.

---

### `generate_medical_report` / `generate_ent_report` / `generate_psych_report` / `generate_pharmacy_report`
Generates a downloadable HTML5 + Tailwind CSS consultation report. Triggered automatically at the end of a diagnostic session.

| Parameter | Type | Description |
|---|---|---|
| `patient_name` | `str` | Patient's name |
| `diagnosis` | `str` | Confirmed or suspected diagnosis |
| `medications` | `str` | Prescribed medications and dosages |
| `notes` | `str` | Additional clinical notes |
| *(varies by agent)* | | Report template fields differ per specialist |

**Returns**: An HTML string that is rendered in the frontend as a printable report with a physician signature.

---

## Specialist-Specific Tools

### Dr. Zavian (Dermatologist) — `analyze_skin_or_report_image`

Sends an uploaded image to the **Moondream Vision Language Model API** for visual analysis.

| Parameter | Type | Description |
|---|---|---|
| `image_path` | `str` | Absolute server-side path to the uploaded image |
| `prompt` | `str` | Clinical question to ask the vision model |

**Returns**: Moondream's visual assessment of the image (lesion morphology, color, distribution, or report transcription).

**Upload directory**: `static/dermatalogist_upload/`

---

### Dr. Anees (ENT) — `analyze_ear_or_report_image`

Same Moondream integration as the Dermatologist tool, but with ENT-specific prompts.

| Parameter | Type | Description |
|---|---|---|
| `image_path` | `str` | Path to uploaded throat/ear/lab image |
| `prompt` | `str` | Clinical question |

**Upload directory**: `static/ent_upload/`

---

### Dr. Pharma (Pharmacist) — `prescription_analysis_tool`

Parses an uploaded prescription image using Moondream to extract drug names, dosages, and dosing intervals for interaction checking.

---

### Dr. Pharma (Pharmacist) — `drug_interaction_tool`

Cross-references extracted drug names against the pharmacy Pinecone index to identify contraindications and interaction risks between co-prescribed medications.

---

## Tool Registration Pattern

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

@tool
def diagnosis_retrieval_tool(query: str) -> str:
    """Retrieve clinical diagnosis information from the vector database."""
    docs = vectorstore.similarity_search(query, k=5)
    return "\n\n".join(d.page_content for d in docs)

tools = [diagnosis_retrieval_tool, medication_retrieval_tool, ...]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)
```

The LLM decides autonomously which tools to call based on the conversation context and the tool descriptions provided in the docstrings.
