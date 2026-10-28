import os
import math
import logging
import threading
from typing import List, Sequence, Optional, Dict, Any
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# ==============================================================================
# RETRIEVAL & RERANKER CONFIGURATION
# ==============================================================================
K_RETRIEVE_FOR_RERANK = int(os.getenv("K_RETRIEVE_FOR_RERANK", "10"))
K_RETRIEVAL = int(os.getenv("K_RETRIEVAL", "5"))
BGE_RERANKER_MODEL = os.getenv("BGE_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
USE_RERANKER = os.getenv("USE_RERANKER", "true").strip().lower() in ("true", "1", "yes")

# Singleton state management
_reranker_instance = None
_reranker_lock = threading.Lock()
_reranker_failed = False
_reranker_device = None


def get_reranker(model_name: Optional[str] = None):
    """
    Thread-safe singleton getter for the BGE CrossEncoder reranker.
    Initializes the model once and reuses it across all requests.
    Falls back gracefully if the model cannot be loaded.
    """
    global _reranker_instance, _reranker_failed, _reranker_device

    if not USE_RERANKER or _reranker_failed:
        return None

    if _reranker_instance is None:
        with _reranker_lock:
            if _reranker_instance is None and not _reranker_failed:
                target_model = model_name or BGE_RERANKER_MODEL
                try:
                    from sentence_transformers import CrossEncoder
                    import torch

                    # Determine device safely: default to CPU or GPU if available without forcing CUDA
                    _reranker_device = "cuda" if torch.cuda.is_available() else "cpu"
                    logger.info(f"Loading BGE CrossEncoder '{target_model}' on device '{_reranker_device}'...")
                    _reranker_instance = CrossEncoder(target_model, device=_reranker_device)
                    logger.info(f"Successfully initialized BGE CrossEncoder '{target_model}'.")
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize BGE CrossEncoder '{target_model}': {e}. "
                        "Retrieval will continue using original vector similarity ranking."
                    )
                    _reranker_failed = True
                    _reranker_instance = None

    return _reranker_instance


def is_reranker_available() -> bool:
    """Returns True if the CrossEncoder model is loaded and ready."""
    return get_reranker() is not None


def get_reranker_info() -> Dict[str, Any]:
    """Returns the current operational status of the reranking subsystem."""
    return {
        "use_reranker": USE_RERANKER,
        "model_name": BGE_RERANKER_MODEL,
        "k_candidates": K_RETRIEVE_FOR_RERANK,
        "k_final": K_RETRIEVAL,
        "device": _reranker_device,
        "is_available": is_reranker_available(),
        "failed": _reranker_failed
    }


def rerank_documents(
    query: str,
    documents: Sequence[Document],
    top_k: int = K_RETRIEVAL,
    reranker: Optional[Any] = None
) -> List[Document]:
    """
    Reranks candidate documents using BGE Cross-Encoder scoring.

    Pipeline:
    1. Validates input documents and query.
    2. Builds [query, document.page_content] pairs.
    3. Obtains relevance scores from CrossEncoder.predict(pairs).
    4. Attaches score to document metadata ('rerank_score' and 'rerank_type')
       without mutating or losing original metadata.
    5. Sorts documents by score descending.
    6. Retains the top_k documents.
    7. On any error or missing reranker, returns original documents[:top_k] safely.
    """
    if not documents:
        return []

    if top_k <= 0:
        return []

    active_reranker = reranker if reranker is not None else get_reranker()

    # If reranker unavailable or only 1 document, return candidates safely
    if active_reranker is None:
        return list(documents)[:top_k]

    if len(documents) == 1:
        doc = documents[0]
        try:
            pair = [[query, str(doc.page_content or "")]]
            score = float(active_reranker.predict(pair)[0])
            if doc.metadata is None:
                doc.metadata = {}
            doc.metadata["rerank_score"] = score
            doc.metadata["rerank_type"] = "bge"
        except Exception as e:
            logger.debug(f"Single-document scoring skipped: {e}")
        return [doc]

    try:
        # Build query-document pairs
        pairs = [[query, str(doc.page_content or "")] for doc in documents]
        raw_scores = active_reranker.predict(pairs)

        scored_docs = []
        for idx, (doc, raw_score) in enumerate(zip(documents, raw_scores)):
            try:
                score = float(raw_score)
                if math.isnan(score) or math.isinf(score):
                    score = float("-inf")
            except (ValueError, TypeError):
                score = float("-inf")

            # Preserve existing metadata and attach rerank score
            if doc.metadata is None:
                doc.metadata = {}
            doc.metadata["rerank_score"] = score
            doc.metadata["rerank_type"] = "bge"
            scored_docs.append((doc, score, idx))

        # Sort descending by score; preserve original order on ties using idx
        scored_docs.sort(key=lambda item: (item[1], -item[2]), reverse=True)

        reranked = [doc for doc, score, idx in scored_docs[:top_k]]
        return reranked

    except Exception as e:
        logger.warning(f"Reranking encountered an exception ({e}). Falling back to original retrieval order.")
        return list(documents)[:top_k]


def retrieve_with_rerank(
    vector_store: Any,
    query: str,
    k_final: int = K_RETRIEVAL,
    k_candidates: int = K_RETRIEVE_FOR_RERANK,
    use_reranker: bool = USE_RERANKER,
    search_kwargs: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    Unified multi-agent retrieval function with BGE Cross-Encoder reranking.

    1. Receives the patient's medical question or clinical retrieval query.
    2. Queries Pinecone (or any compatible vector store) for k_candidates (default: 10).
    3. If reranking is enabled and candidates > 1, scores candidates with BGE Cross-Encoder.
    4. Sorts by reranker score and retains the top k_final (default: 5) documents.
    5. Returns the final documents to the calling agent.
    6. Falls back to original vector ranking if reranking fails or is disabled.
    """
    if vector_store is None:
        logger.warning("retrieve_with_rerank called with None vector_store.")
        return []

    if not query or not query.strip():
        logger.debug("retrieve_with_rerank called with empty query.")
        return []

    # Step 1: Initial retrieval from vector store
    fetch_k = k_candidates if use_reranker else k_final
    kwargs = dict(search_kwargs or {})
    kwargs["k"] = fetch_k

    try:
        retriever = vector_store.as_retriever(search_kwargs=kwargs)
        candidates = retriever.invoke(query)
    except Exception as e:
        logger.error(f"Vector store retrieval failed: {e}")
        return []

    if not candidates:
        return []

    # Step 2: Apply reranking if enabled
    if use_reranker and len(candidates) > 1:
        return rerank_documents(query, candidates, top_k=k_final)

    return candidates[:k_final]
