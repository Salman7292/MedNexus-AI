# RAG Pipeline

MedNexus AI uses a **Retrieval-Augmented Generation (RAG)** pipeline to ground each specialist agent's responses in validated clinical knowledge, preventing hallucinations.

---

## Overview

```
User Query
    │
    ▼
Embedding Model (MedEmbed-base-v0.1)
    │
    ▼
Pinecone Similarity Search (top-5 chunks, k=5)
    │
    ▼
Retrieved Chunks → LLM (synthesizes clinical response)
    │
    ▼
Grounded Clinical Answer
```

> [!NOTE]
> The deployed pipeline does **not** include a cross-encoder reranking stage. Retrieved chunks are passed directly to the LLM. This design minimises latency for real-time SSE streaming. Future versions may add BGE reranking as an optional middleware layer.

---

## Embedding Model

| Property | Value |
|---|---|
| Model | `abhinand/MedEmbed-base-v0.1` |
| Provider | HuggingFace (`langchain-huggingface`) |
| Dimensionality | 768 |
| Domain | Medical / clinical text |
| Download | Automatic on first run; cached by `sentence-transformers` |

**Why MedEmbed?** General-purpose embedding models (e.g., `text-embedding-ada-002`) under-perform on medical terminology. `MedEmbed-base-v0.1` is fine-tuned on medical corpora, producing better semantic neighbours for clinical queries.

---

## Vector Store — Pinecone

Each specialist uses a dedicated Pinecone **index** partitioned into multiple **namespaces**:

| Agent | Index | Namespaces |
|---|---|---|
| Dr. Zavian (Dermatologist) | `dermatologist` | `diagnosis_knowledge`, `medication_knowledge`, `dermatologists_geo_directory` |
| Dr. Anees (ENT) | `ent-specialist` | `diagnosis_knowledge`, `medication_knowledge`, `ent_geo_directory` |
| Dr. Aria (Psychiatrist) | `psychiatrist-specialist` | `diagnosis_knowledge`, `medication_knowledge`, `psychiatrist_geo_directory` |
| Dr. Pharma (Pharmacist) | `pharmacy` | varies — see `pharmacy_logic.py` |

### Namespace Purposes

| Namespace | Content |
|---|---|
| `diagnosis_knowledge` | Symptom → differential diagnosis mappings, ICD codes, clinical presentations |
| `medication_knowledge` | Drug names, dosage protocols, first/second-line treatment guidelines, contraindications |
| `*_geo_directory` | Local specialist clinic names, addresses, phone numbers, zip-code anchors |

---

## Retrieval Call (Code Pattern)

Each tool invokes the vector store like this:

```python
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="abhinand/MedEmbed-base-v0.1")

vectorstore = PineconeVectorStore(
    index_name="dermatologist",
    embedding=embeddings,
    namespace="diagnosis_knowledge",
    pinecone_api_key=os.environ["PINECONE_API_KEY"],
)

docs = vectorstore.similarity_search(query, k=5)
context = "\n\n".join(d.page_content for d in docs)
```

The `context` string is injected into the tool's return value, which LangGraph feeds back to the LLM on the next reasoning step.

---

## Evaluation Metrics

The `evaluation/` directory contains a RAG evaluation harness that measures retrieval quality at **k=5**:

| Metric | Description |
|---|---|
| **Precision@5** | Fraction of top-5 retrieved chunks that are relevant |
| **Recall@5** | Fraction of all relevant chunks captured in top-5 |
| **MRR** | Mean Reciprocal Rank of the first relevant result |
| **Hit Rate@5** | Binary: was at least one relevant chunk retrieved? |
| **NDCG@5** | Normalised Discounted Cumulative Gain — quality-weighted ranking |

Run evaluation:
```bash
python evaluation/run_eval.py
```

> [!TIP]
> Evaluation is run against the **raw retrieval stage only** (similarity search), not the full agent response. This isolates retrieval quality from LLM synthesis quality.
