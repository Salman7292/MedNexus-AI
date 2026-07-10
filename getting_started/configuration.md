# Configuration Reference

All runtime configuration is loaded from a `.env` file in the project root via `python-dotenv`. The application reads this file at startup in `app.py` and each `*_logic.py` module.

---

## Required Variables

| Variable | Description | Where to Get |
|---|---|---|
| `GROQ_API_KEY` | API key for the Groq inference platform. Used by all five agents for LLM calls. | [console.groq.com](https://console.groq.com) |
| `PINECONE_API_KEY` | Main Pinecone API key. Used by the Dermatologist, ENT, Psychiatrist, and General Physician agents. | [app.pinecone.io](https://app.pinecone.io) |
| `PINECONE_API_KEY_PHRAMACY` | Separate Pinecone API key for the Pharmacy agent (different Pinecone project/index). | [app.pinecone.io](https://app.pinecone.io) |
| `TAVILY_API_KEY` | API key for the Tavily live web search tool. | [tavily.com](https://tavily.com) |
| `MOONDREAM_KEY` | JWT token for the Moondream Vision Language Model API. | [moondream.ai](https://moondream.ai) |

## Optional / OAuth Variables

| Variable | Description | Required? |
|---|---|---|
| `GOOGLE_API_KEY` | Google Generative AI key (currently a fallback; not used in production flow). | Optional |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID for Google Sign-In. | Required for Google login |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret for Google Sign-In. | Required for Google login |

## LangSmith Tracing Variables

| Variable | Description | Default |
|---|---|---|
| `LANGSMITH_TRACING` | Enable LangSmith trace logging (`true`/`false`). | `false` |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint. | `https://api.smith.langchain.com` |
| `LANGSMITH_API_KEY` | LangSmith authentication key. | — |
| `LANGSMITH_PROJECT` | Project name visible in LangSmith dashboard. | `Dermatlogist` |

> [!NOTE]
> LangSmith tracing is useful during development for inspecting LangGraph step-by-step reasoning chains. Set `LANGSMITH_TRACING=false` in production to avoid leaking patient prompts to third-party services.

---

## Pinecone Index Configuration

Each specialist agent connects to a specific Pinecone **index** and **namespace**:

| Agent | Pinecone Index | Namespaces |
|---|---|---|
| Dr. Zavian (Dermatologist) | `dermatologist` | `diagnosis_knowledge`, `medication_knowledge`, `dermatologists_geo_directory` |
| Dr. Anees (ENT) | `ent-specialist` | `diagnosis_knowledge`, `medication_knowledge`, `ent_geo_directory` |
| Dr. Aria (Psychiatrist) | `psychiatrist-specialist` | `diagnosis_knowledge`, `medication_knowledge`, `psychiatrist_geo_directory` |
| Dr. Pharma (Pharmacist) | `pharmacy` | varies — see `pharmacy_logic.py` |
| Dr. Alara (General Physician) | *(no RAG tools)* | — |

> [!IMPORTANT]
> Index names are **hard-coded** in each `*_logic.py` file. If you create indices with different names in Pinecone, you must update those files accordingly. See `knowledge_base/building_the_index.md` for index creation instructions.

---

## Flask Application Settings

The following can be set as environment variables or edited directly in `app.py`:

| Setting | Default | Description |
|---|---|---|
| `SECRET_KEY` | Auto-generated | Flask session signing key. Set to a fixed value in production. |
| `FLASK_DEBUG` | `False` | Enable Flask debug mode (auto-reload, tracebacks). **Never enable in production.** |
| `PORT` | `5000` | The port Flask listens on. |

---

## Sample `.env` File

```dotenv
# Groq (all LLM calls)
GROQ_API_KEY="gsk_..."

# Pinecone (Dermatologist, ENT, Psychiatry, General)
PINECONE_API_KEY="pcsk_..."

# Pinecone (Pharmacy — separate project)
PINECONE_API_KEY_PHRAMACY="pcsk_..."

# Tavily live search
TAVILY_API_KEY="tvly-..."

# Moondream vision
MOONDREAM_KEY="eyJ..."

# Google OAuth (optional)
GOOGLE_CLIENT_ID="....apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="GOCSPX-..."

# LangSmith tracing (optional)
LANGSMITH_TRACING=false
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY="lsv2_..."
LANGSMITH_PROJECT="MedNexusAI"
```
