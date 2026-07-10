# Running Evaluations

MedNexus AI provides a complete evaluation harness inside the `evaluation_script_and_datasets/` directory. This allows developers to measure vector retrieval effectiveness and LLM generation faithfulness.

---

## Evaluation Folder Structure

```text
evaluation_script_and_datasets/
├── evaluation_dataset/
│   ├── dermatology_evaluation_dataset).csv
│   ├── dr_pharma_evaluation_dataset.csv
│   ├── ent_evaluation_dataset.csv
│   └── psychiatrist_evaluation_dataset.csv
├── dermatlogy-evaluation.ipynb
├── ent-evaluation.ipynb
├── phrama-evaluation.ipynb
└── physitry-evaluation.ipynb
```

---

## Evaluated Metrics

The notebooks evaluate performance across two distinct pipelines:

### 1. Vector Retrieval Stage (k=5)
Measures the relevance of the raw context retrieved from the Pinecone vector index before it is passed to the LLM:
*   **Precision@k & Recall@k**: Binary measures indicating whether relevant chunks exist in the top-$k$ returned segments.
*   **Context Recall (continuous)**: Calculated as the maximum cosine similarity between the ground truth and the retrieved chunks.
*   **Context Precision (continuous)**: Calculated as the mean cosine similarity of all retrieved chunks.
*   **Mean Reciprocal Rank (MRR)**: Measures how high up the first relevant chunk appears.
*   **NDCG (Normalized Discounted Cumulative Gain)**: Graded score penalizing relevant results placed at lower ranks.

### 2. LLM Generation Stage (RAGAS-style)
Measures the quality and safety of the final generated response:
*   **Faithfulness**: Computes the percentage of claims in the generated response that are directly backed by the retrieved context. (Scores below 0.7 indicate hallucination risk).
*   **Answer Correctness**: Semantic correctness of the generated response compared to the ground truth.
*   **Context Precision**: Evaluator-assessed ratio of relevant content within the context.
*   **Answer Relevance**: Evaluates whether the generated response directly addresses the user's question.
*   **Context Recall**: Proportion of ground truth facts present in the retrieved context.

---

## Advanced Configurations

The evaluation framework supports tuning the RAG performance with the following options:

### BGE Reranker
By default, the evaluation integrates **`BAAI/bge-reranker-v2-m3`** via the `CrossEncoder` library.
*   *Purpose*: Performs deep cross-attention comparison between the query and the top-10 retrieved segments to rerank the top-5 most relevant chunks.
*   *Toggling*: Set `USE_RERANKER = True` in the notebook configuration cells.

### Semantic Chunking
*   *Purpose*: Replaces fixed-size character splitting with a dynamic semantic thresholding splitter (`SemanticChunker`) from `langchain_experimental`. Uses `MedEmbed-base-v0.1` embeddings to determine natural semantic breaks in document paragraphs.

---

## Executing the Evaluations

1.  **Activate Environment**: Make sure your virtual environment is active with dependencies installed.
2.  **Launch Jupyter**: Run `jupyter notebook` in your terminal and open the desired evaluation file (e.g. `dermatlogy-evaluation.ipynb`).
3.  **Configure API Keys**: The notebooks load keys via `.env` files. Ensure `GROQ_API_KEY`, `PINECONE_API_KEY`, and `PINECONE_API_KEY_PHRAMACY` are loaded.
4.  **Run All Cells**: The script will:
    *   Load the evaluation dataset (CSV format).
    *   Initialize the `MedEmbed` model and Pinecone retrieval retriever.
    *   For each query: retrieve documents, query the Groq LLM to generate responses, and run LLM evaluations using prompt templates.
    *   Output final summary metrics, save CSV sheets, and plot 9 comprehensive visual graphs (saved as `evaluation_plots.png`).
