# SoftwareX Original Publication: Extracted Technical Details

Here are the extracted technical details and drafts for your SoftwareX Original Publication template, based strictly on the provided project files.

### 1. Metadata Table

| Nr | Code metadata description | Metadata |
| :--- | :--- | :--- |
| **C1** | Current code version | v1.0 |
| **C2** | Permanent link to code/repository | [MISSING - NEEDS MANUAL INPUT] |
| **C3** | Permanent link to reproducible capsule | [MISSING - NEEDS MANUAL INPUT] |
| **C4** | Legal code license | [MISSING - NEEDS MANUAL INPUT] *(Note: No `LICENSE` file found in the root directory)* |
| **C5** | Code versioning system used | git |
| **C6** | Software code languages, tools, and services used | Python, JavaScript, HTML, CSS |
| **C7** | Compilation requirements, operating environments, and dependencies | `Flask>=3.0.0`, `Jinja2>=3.1.2`, `langchain`, `langchain_core`, `langchain_groq`, `langchain_pinecone`, `langchain_huggingface`, `langgraph`, `moondream`, `python-dotenv`, `pillow`, `pillow-heif`, `pillow-avif-plugin`, `flask-cors`, `tavily-python` |
| **C8** | Link to developer documentation/manual | [MISSING - NEEDS MANUAL INPUT] |
| **C9** | Support email for questions | [MISSING - NEEDS MANUAL INPUT] |

---

### 2. Abstract (Draft)
The rapid evolution of general-purpose Large Language Models presents an opportunity for digital health, yet these models often lack the clinical rigor required for specialized medical fields, resulting in potentially dangerous diagnostic hallucinations. To solve this problem, we present MedNexus AI, a decoupled multi-agent ecosystem that utilizes Agentic AI workflows (LangGraph), strictly partitioned Retrieval-Augmented Generation (RAG), and Multi-Modal Computer Vision (Moondream). By confining AI agents to specific clinical personas (e.g., Otorhinolaryngology, Dermatology) and equipping them with external data tools, MedNexus AI provides highly accurate visual lesion diagnosis, symptom evaluation, and the automatic generation of structured clinical reports. The software offers a highly reproducible framework for the scientific community to study multi-modal integration and mitigate hallucinations in high-stakes clinical AI research.

---

### 3. Software Description (Drafting Points)

**Architecture:** 
The software utilizes a decoupled, state-based, and multi-agent architecture. The backend is orchestrated by **LangGraph** (leveraging `StateGraph` for non-linear, Directed Acyclic Graph execution) and **Flask**. Memory persistence across concurrent sessions is maintained via decentralized SQLite databases (e.g., `dermatlogist.db`). The frontend employs HTML5, Vanilla JavaScript, and CSS using a mobile-first Three-Zone layout with real-time SSE token streaming and Web Speech API accessibility.

**Functionalities (Top Core Features):**
1. **Dynamic Multi-Agent Conversation:** Hosts distinct conversational specialist models (ENT, Dermatology, Psychiatry, Pharmacy) governed by rigid clinical system prompts for step-by-step reasoning.
2. **Visual Medical Analysis:** Integrates external vision language models (Moondream) to autonomously parse morphologic elements in uploaded clinical photography and transcribing printed medical or lab reports.
3. **Domain-Specific RAG Navigation:** Autonomously executes vector searches across separated Pinecone namespaces to map symptoms to diseases, check unsafe medication contraindications, and query geographic patient-to-doctor referrals.
4. **Automated Clinical Reporting:** Synthesizes the triage conversation, diagnosis, and treatment protocols into an official, digitally signed, and downloadable HTML medical prescription report.

**Sample Code:**
This snippet represents the system's primary architectural use case—building the stateful, non-linear reasoning loop (Agentic DAG) using LangGraph:

```python
# Build Graph
graph = StateGraph(ChatbotState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge('tools', 'chat_node')
```

---

### 4. Motivation & Significance

**Scientific Problem:**
The software aims to resolve the severe practical limitations of utilizing general-purpose Large Language Models (LLMs) in high-stakes healthcare settings. Specifically, it tackles the "hallucination problem," where broad LLMs frequently invent unverified clinical assumptions or propose treatment strategies lacking specialized semantic accuracy and clinical rigor.

**Related Works & Algorithms:**
*   **LangGraph (`StateGraph`)** for acyclic graph execution and agent tool orchestration.
*   **Retrieval-Augmented Generation (RAG)** utilizing **Pinecone** vector databases for semantic clinical context mapping.
*   **HuggingFace Embeddings** (`abhinand/MedEmbed-base-v0.1`) for generating vectors from domain-specific healthcare terminology.
*   **Moondream Vision Language Model** for extracting morphologic details from image inputs.
*   **Tavily API** for real-time web searches to retrieve emerging FDA drug approvals or clinical guidelines.

---

### 5. Impact & Research Questions

**New Research Questions Enabled:**
*   How does the integration of multi-modal vision parsing explicitly impact the false-positive diagnostic rates in specialized diagnostic software?
*   How effective are strictly partitioned vector namespaces (e.g., separating diseases from pharmacological data) compared to monolithic databases in preventing context-collapse?
*   Can long-term LLM hallucinations be systematically mitigated over a patient session by enforcing StateGraph tool-checkpointing and acyclic dependency loops?

**Improvements Over Existing Tools:**
Traditional conversational medical AIs rely heavily on static prompt engineering or linear LangChain pipelines. MedNexus AI significantly improves upon those tools by offering a multi-agent framework capable of **complex Directed Acyclic Graph (DAG) execution** through LangGraph. This architecture forces the LLM to pause language generation, query discrete tooling modules (like vision parsing and geographical lookups), and inject verified factual retrieval directly into memory nodes before rendering a diagnosis, presenting a far more scientifically rigid architectural paradigm.
