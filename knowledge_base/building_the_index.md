# Building the Pinecone Knowledge Base Index

This guide explains how to populate the Pinecone vector databases used by MedNexus AI's RAG pipeline from scratch.

---

## Prerequisites

- A Pinecone account with at least two projects (one for specialists, one for pharmacy).
- `PINECONE_API_KEY` and `PINECONE_API_KEY_PHRAMACY` set in `.env`.
- Python virtual environment active with `requirements.txt` installed.

---

## 1. Create Pinecone Indexes

Log in to [app.pinecone.io](https://app.pinecone.io) and create the following indexes:

| Index Name | Dimension | Metric | Description |
|---|---|---|---|
| `dermatologist` | 768 | cosine | Dermatology agent knowledge |
| `ent-specialist` | 768 | cosine | ENT agent knowledge |
| `psychiatrist-specialist` | 768 | cosine | Psychiatry agent knowledge |
| `pharmacy` | 768 | cosine | Pharmacy agent knowledge |

> [!IMPORTANT]
> The dimension **must be 768** — this matches the output dimensionality of `abhinand/MedEmbed-base-v0.1`. Using a different dimension will cause a shape mismatch error at upsert time.

---

## 2. Prepare Source Documents

Organize your clinical source documents into plain text or PDF files grouped by category:

```
knowledge_sources/
├── dermatology/
│   ├── symptom_disease_mappings.txt
│   ├── medication_protocols.txt
│   └── clinic_directory.csv
├── ent/
│   ├── symptom_disease_mappings.txt
│   ├── medication_protocols.txt
│   └── clinic_directory.csv
├── psychiatry/
│   ├── symptom_disease_mappings.txt
│   ├── medication_protocols.txt
│   └── clinic_directory.csv
└── pharmacy/
    └── drug_interactions.txt
```

---

## 3. Chunk and Embed Documents

Use LangChain's `RecursiveCharacterTextSplitter` to chunk documents and `HuggingFaceEmbeddings` to generate vectors:

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.docstore.document import Document
import os

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]

embeddings = HuggingFaceEmbeddings(model_name="abhinand/MedEmbed-base-v0.1")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # tokens
    chunk_overlap=50,      # overlap to preserve context at chunk boundaries
)

def ingest_file(filepath: str, index_name: str, namespace: str):
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()

    chunks = splitter.split_text(raw_text)
    docs = [Document(page_content=chunk) for chunk in chunks]

    PineconeVectorStore.from_documents(
        documents=docs,
        embedding=embeddings,
        index_name=index_name,
        namespace=namespace,
        pinecone_api_key=PINECONE_API_KEY,
    )
    print(f"✅ Ingested {len(docs)} chunks into {index_name}/{namespace}")

# Example ingestion
ingest_file(
    "knowledge_sources/dermatology/symptom_disease_mappings.txt",
    index_name="dermatologist",
    namespace="diagnosis_knowledge",
)
ingest_file(
    "knowledge_sources/dermatology/medication_protocols.txt",
    index_name="dermatologist",
    namespace="medication_knowledge",
)
ingest_file(
    "knowledge_sources/dermatology/clinic_directory.csv",
    index_name="dermatologist",
    namespace="dermatologists_geo_directory",
)
```

Repeat for each specialist's documents and namespaces.

---

## 4. Verify the Index

After ingestion, verify the vector counts in the Pinecone dashboard or via the SDK:

```python
from pinecone import Pinecone

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("dermatologist")
print(index.describe_index_stats())
```

Expected output:
```json
{
  "namespaces": {
    "diagnosis_knowledge": {"vector_count": 1234},
    "medication_knowledge": {"vector_count": 567},
    "dermatologists_geo_directory": {"vector_count": 89}
  },
  "total_vector_count": 1890
}
```

---

## 5. Namespace Summary

| Agent | Index | Namespace | Content Type |
|---|---|---|---|
| Dermatologist | `dermatologist` | `diagnosis_knowledge` | Symptom-disease mappings |
| Dermatologist | `dermatologist` | `medication_knowledge` | Drug protocols |
| Dermatologist | `dermatologist` | `dermatologists_geo_directory` | Clinic directory |
| ENT | `ent-specialist` | `diagnosis_knowledge` | ENT symptom-disease mappings |
| ENT | `ent-specialist` | `medication_knowledge` | ENT drug protocols |
| ENT | `ent-specialist` | `ent_geo_directory` | ENT clinic directory |
| Psychiatrist | `psychiatrist-specialist` | `diagnosis_knowledge` | Mental health condition mappings |
| Psychiatrist | `psychiatrist-specialist` | `medication_knowledge` | Psychiatric drug protocols |
| Psychiatrist | `psychiatrist-specialist` | `psychiatrist_geo_directory` | Psychiatry clinic directory |
| Pharmacist | `pharmacy` | *(see pharmacy_logic.py)* | Pharmacological interaction data |

---

## 6. Chunking Recommendations

| Content Type | Chunk Size | Chunk Overlap |
|---|---|---|
| Diagnosis narratives | 400–600 chars | 50 chars |
| Drug protocol tables | 300–400 chars | 30 chars |
| Clinic directory (CSV) | 1 row per chunk | 0 |

> [!TIP]
> For geo-directory data, treat each clinic entry as a single chunk so the agent retrieves complete clinic records rather than partial addresses.
