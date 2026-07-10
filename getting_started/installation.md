# Installation Guide

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.9 |
| pip | latest |
| Git | any |
| Modern web browser | Chrome / Edge recommended (Web Speech API) |

> [!NOTE]
> MedNexus AI runs entirely on CPU for embedding inference. No GPU is required. Moondream vision calls are handled via external API.

---

## 1. Clone the Repository

```bash
git clone https://github.com/<your-org>/mednexai.git
cd mednexai
```

## 2. Create and Activate a Virtual Environment

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

The `requirements.txt` installs the following main packages:

| Package | Purpose |
|---|---|
| `Flask>=3.0.0` | Web framework |
| `langgraph` | Agentic workflow orchestration |
| `langchain-groq` | Groq LLM integration |
| `langchain-pinecone` | Pinecone vector store integration |
| `langchain-huggingface` | MedEmbed embeddings |
| `moondream` | Vision language model client |
| `tavily-python` | Live web search |
| `pinecone-client` | Pinecone SDK |
| `sentence-transformers` | Embedding utilities |
| `pillow`, `pillow-heif`, `pillow-avif-plugin` | Image processing |
| `authlib`, `requests` | Google OAuth |
| `Flask-Limiter`, `Flask-WTF`, `bleach` | Security middleware |

## 4. Configure Environment Variables

Copy `.env.example` to `.env` (or create `.env` from scratch) and fill in all keys. See `getting_started/configuration.md` for a full description of every variable.

```bash
cp .env.example .env
# Edit .env with your API keys
```

> [!IMPORTANT]
> **Never commit `.env` to version control.** It contains secret API keys. The `.gitignore` should exclude it by default.

## 5. First Run

```bash
python app.py
```

The Flask development server starts at `http://127.0.0.1:5000` by default. Open a browser and navigate to:

```
http://localhost:5000
```

You should see the MedNexus AI landing page with links to all five specialist interfaces.

> [!TIP]
> The HuggingFace embedding model (`abhinand/MedEmbed-base-v0.1`) is downloaded on the **first run** only and cached locally by the `sentence-transformers` library. Allow a few minutes for the initial download (~400 MB).

## 6. Troubleshooting Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Missing package | Re-run `pip install -r requirements.txt` inside the venv |
| Pinecone 401 errors | Wrong API key or index name | Check `PINECONE_API_KEY` and index names in `*_logic.py` |
| Groq rate-limit errors | Free-tier quota exceeded | Wait or upgrade Groq plan |
| Speech API not working | Non-HTTPS or wrong browser | Use Chrome over `localhost` or deploy with HTTPS |
| `sqlite3.OperationalError` | Database file missing | Run the app once; SQLite files are auto-created |
