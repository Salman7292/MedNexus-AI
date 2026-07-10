# Troubleshooting Guide

This section outlines fixes for common issues encountered during MedNexus AI installation, configuration, or execution.

---

## 1. Web Application & Flask Failures

### Port 5000 Already in Use
By default, Flask binds to port `5000`. On macOS, this port may be occupied by the AirPlay Receiver.
*   **Fix**: Run Flask on a different port by modifying the startup execution command in [app.py](file:///d:/archive/mednexai_3rd_version/mednexai_3rd_version/app.py):
    ```python
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5001))  # Bind to 5001 instead
        app.run(debug=True, host='0.0.0.0', port=port)
    ```

### CSRF Validation Token Errors
If AJAX/JSON POST requests fail with `400 Bad Request` or "CSRF token missing":
*   **Fix**: Verify that your fetch headers contain the CSRF token extracted from the HTML metadata:
    ```javascript
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    fetch('/chat', {
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        ...
    });
    ```

---

## 2. Agentic RAG & Pinecone Issues

### Shape/Dimensionality Mismatches
When performing searches or upserts, the API returns: `PineconeValidationError: vector size must be 768`.
*   **Fix**: MedNexus AI uses `abhinand/MedEmbed-base-v0.1` which outputs vectors of length **768**. Ensure your Pinecone index is configured with exactly **768 dimensions** and **cosine similarity** metric. Do not use 1536 (OpenAI size).

### Pinecone "Namespace Not Found" or Empty Retrieval
*   **Fix**: Verify that your `.env` contains the correct keys and that you have populated the correct namespace (e.g. `diagnosis_knowledge` vs `medication_knowledge`) using the ingestion script details in [Knowledge Base](architecture/knowledge-base.md).

---

## 3. SQLite Database Locking

### OperationalError: database is locked
This happens if multiple concurrent threads try to write to a single SQLite database without proper isolation settings.
*   **Fix**: Ensure your database connection settings in each logic module contain `check_same_thread=False`:
    ```python
    conn = sqlite3.connect("dermatologist.db", check_same_thread=False)
    ```
