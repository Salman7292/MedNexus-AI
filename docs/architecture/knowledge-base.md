# Knowledge Base, Embeddings & RAG Ingestion

MedNexus AI uses Retrieval-Augmented Generation (RAG) to ensure that agent responses are grounded in clinical literature rather than static LLM training data.

---

## Vector Store Schema

The system connects to **Pinecone** indexes configured with the following properties:
*   **Dimensions**: 768 (matching the output size of the embedding model).
*   **Metric**: Cosine Similarity.
*   **Indices**:
    *   `dermatologist` (Dermatology data)
    *   `ent-specialist` (ENT data)
    *   `psychiatrist-specialist` (Psychiatry data)
    *   `pharmacy` (Pharmacy data)

---

## Embedding Model: MedEmbed-base-v0.1

The pipeline utilizes **`abhinand/MedEmbed-base-v0.1`** (loaded from HuggingFace via `langchain-huggingface`).

### Why MedEmbed?
Standard embedding models (like OpenAI `text-embedding-ada-002`) are trained on generic web corpora and frequently lose clinical precision. `MedEmbed-base-v0.1` is trained specifically on medical texts, ensuring that synonyms (e.g., *hives* vs. *urticaria*, or *throat inflammation* vs. *pharyngitis*) resolve closer together in the vector space.

---

## Chunking & Ingestion Pipeline

Ingesting clinical documents consists of:
1.  **Parsing Text**: Reading text files or parsing CSV directories.
2.  **Splitting**: Chunking text using LangChain `RecursiveCharacterTextSplitter`.
    *   *Symptom & Medication files*: Chunk size = **500 characters**, chunk overlap = **50 characters** (to maintain context across split points).
    *   *Clinic Directories (CSV)*: Splitting is configured at **1 row per chunk** with **0 overlap**, ensuring that addresses and phone numbers do not get split across multiple chunks.
3.  **Uploading**: Initializing the `PineconeVectorStore` with the correct credentials and namespace, and uploading the generated embeddings.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.docstore.document import Document

# Ingestion pattern example
embeddings = HuggingFaceEmbeddings(model_name="abhinand/MedEmbed-base-v0.1")
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

def ingest(filepath, index_name, namespace):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    chunks = splitter.split_text(text)
    docs = [Document(page_content=chunk) for chunk in chunks]
    
    PineconeVectorStore.from_documents(
        documents=docs,
        embedding=embeddings,
        index_name=index_name,
        namespace=namespace
    )
```

---

## Namespace Architecture Reference

Refer to this directory map when uploading or reading data:

| Index Name | Namespace | Content Description |
| :--- | :--- | :--- |
| `dermatologist` | `diagnosis_knowledge` | Dermatology symptom-to-disease mappings |
| `dermatologist` | `medication_knowledge` | Dermatology topical treatment/care guidelines |
| `dermatologist` | `dermatologists_geo_directory` | Regional dermatology clinic locations |
| `ent-specialist` | `diagnosis_knowledge` | Ear, nose, throat symptom details |
| `ent-specialist` | `medication_knowledge` | ENT treatment drug and dosage parameters |
| `ent-specialist` | `ent_geo_directory` | ENT clinic directories |
| `psychiatrist-specialist` | `diagnosis_knowledge` | Mental health symptoms and clinical presentations |
| `psychiatrist-specialist` | `medication_knowledge` | Psychiatric treatment rules and contraindications |
| `psychiatrist-specialist` | `psychiatrist_geo_directory` | Local psychiatric clinics directory |
| `pharmacy` | `drugs_core` | Core pharmacology files (Martindale, Katzung) |
| `pharmacy` | `dosage_guidelines` | Drug dosing tables (BNF guidelines) |
| `pharmacy` | `drug_interactions` | Co-prescription hazards |
| `pharmacy` | `contraindications` | Allergies, pregnancy warnings |
| `pharmacy` | `side_effects_toxicity` | Side effects & adverse reactions (Secondary Key) |
| `pharmacy` | `clinical_guidelines` | Diagnosis standard treatments (Secondary Key) |
