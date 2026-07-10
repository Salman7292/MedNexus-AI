# Configuration & Environment Variables

MedNexus AI uses environment variables to securely store credentials for external APIs, databases, and third-party authentication services.

## Setting Up `.env`

Create a file named `.env` in the root of the project directory. Add your keys using the following layout:

```env
# Groq LLM Key
GROQ_API_KEY="your_groq_api_key"

# Pinecone Vector Store Credentials
PINECONE_API_KEY="your_primary_pinecone_api_key"
PINECONE_API_KEY_PHRAMACY="your_pharmacy_pinecone_api_key"

# Live Web Search
TAVILY_API_KEY="your_tavily_api_key"

# Vision Language Model Key
MOONDREAM_KEY="your_moondream_api_key"

# Optional Google Gemini Key
GOOGLE_API_KEY="your_google_api_key"

# Google OAuth2.0 Integration
GOOGLE_CLIENT_ID="your_google_client_id"
GOOGLE_CLIENT_SECRET="your_google_client_secret"

# LangSmith Tracing and Evaluation Metrics
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your_langsmith_api_key"
LANGSMITH_PROJECT="Dermatlogist"
```

---

## Detailed Variable Reference

### `GROQ_API_KEY`
*   **Purpose**: Authorizes requests to the Groq API, which hosts the main reasoning models (e.g. `meta-llama/llama-4-scout-17b-16e-instruct`).
*   **Where to obtain**: Create an account on [console.groq.com](https://console.groq.com/) and generate an API key.

### `PINECONE_API_KEY`
*   **Purpose**: Used to query and retrieve vector embeddings from the Pinecone indexes.
*   **Where to obtain**: Create an account on [pinecone.io](https://www.pinecone.io/) and retrieve the key from your index settings dashboard.

### `PINECONE_API_KEY_PHRAMACY`
*   **Purpose**: Secondary Pinecone key used by Dr. Pharma to access clinical guideline and toxicity vector stores (which may reside on a separate Pinecone billing account/project for scaling).
*   **Where to obtain**: Generate a separate project key on Pinecone, or reuse the primary key if using a single account setup.

### `TAVILY_API_KEY`
*   **Purpose**: Authorizes the live internet searches used for real-time FDA details or clinic lookups.
*   **Where to obtain**: Register on [tavily.com](https://tavily.com/) to get a free developer search key.

### `MOONDREAM_KEY`
*   **Purpose**: Authorizes requests to the Moondream VLM API to process images (ear canal shots, skin lesions, and printed reports).
*   **Where to obtain**: Register on [moondream.ai](https://moondream.ai/) to get an API key.

### `GOOGLE_API_KEY`
*   **Purpose**: Optional fallback variable to use Google Gemini models (e.g., `gemini-2.5-flash`).
*   **Where to obtain**: Get it from the [Google AI Studio](https://aistudio.google.com/).

### `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET`
*   **Purpose**: Integrates Google Sign-In into the login and signup routes.
*   **Where to obtain**: Configure OAuth 2.0 Credentials in the [Google Cloud Console](https://console.cloud.google.com/) under the API Credentials tab.

### `LANGSMITH_TRACING` & `LANGSMITH_API_KEY`
*   **Purpose**: Enables logging, trace tracking, and token calculation monitoring via LangSmith.
*   **Where to obtain**: Create a developer login on [smith.langchain.com](https://smith.langchain.com/) and copy your API key.
