# MedNexus AI Developer Manual

Welcome to the official developer manual and technical documentation for **MedNexus AI**, a state-of-the-art medical AI ecosystem.

MedNexus AI shifts the paradigm of general-purpose chatbots by introducing a **multi-agent medical team** where specialist clinical agents (Dermatology, ENT, Psychiatry, and Pharmacy) run inside structured, cyclic decision loops (**LangGraph**) backed by localized, validated medical databases (**Retrieval-Augmented Generation / RAG**) and visual models (**Moondream VLM**).

This documentation website contains the technical details of the ecosystem's architecture, APIs, deployment guides, and RAG evaluation pipelines.

---

## Technical Highlights

*   **Stateful Agentic Loops**: Each specialist is modeled as an independent `StateGraph` in LangGraph, enabling cyclic reasoning (think → query tool → evaluate → ask follow-up).
*   **Medical-Specific Vector Storage**: RAG searches query Pinecone vector stores embedded using `abhinand/MedEmbed-base-v0.1` (768 dimensions), a model pre-trained specifically on clinical text.
*   **Session Persistence**: LangGraph thread history is checkpointed into dedicated local SQLite databases (`dermatologist.db`, `ent.db`, etc.) for seamless multi-turn conversations.
*   **Multi-Modal Evaluation**: Diagnostic pipelines are verified against RAG datasets using both vector retrieval metrics (Precision@k, NDCG) and LLM-assisted generation metrics (Faithfulness, Correctness).

---

## Manual Navigation Structure

To get started, follow these sections:

*   **[Getting Started](getting-started/installation.md)**: Standard guide to install, configure environment variables, and run MedNexus AI locally.
*   **[Architecture Details](architecture/overview.md)**: Deep dive into the 6-layer design, LangGraph StateGraph cycles, specialist system prompts, and the Dr. Pharma six-stage pipeline.
*   **[API & Tools Reference](api-reference/endpoints.md)**: Reference sheet for the REST and SSE endpoints, tool signatures, and automatically generated Python code documentation.
*   **[Developer Guides](guides/adding-a-new-specialty.md)**: Instruction sheets on extending the platform with a new specialist agent, executing the RAG evaluation notebooks, and deploying to production.
