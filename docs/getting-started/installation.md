# Installation Guide

Follow these steps to set up the development environment for MedNexus AI.

## Prerequisites

Before installing, make sure your local system has:
- **Python 3.9+** (Python 3.10 or 3.11 is highly recommended for compatibility with all LangChain/LangGraph packages).
- **Git** (optional, for checking out code).
- Active API subscriptions for **Groq**, **Pinecone**, **Tavily**, and **Moondream** (see [Configuration](configuration.md) for details).

---

## 1. Clone the Codebase

Clone the repository to your local computer (or extract the project folder):

```bash
git clone https://github.com/Salman7292/MedNexusAI.git
cd MedNexusAI
```

---

## 2. Create a Virtual Environment

It is recommended to run the project inside an isolated virtual environment to keep packages from interfering with other local Python developments.

=== "Windows (CMD)"
    ```cmd
    python -m venv venv
    venv\Scripts\activate
    ```

=== "Windows (PowerShell)"
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

=== "macOS / Linux"
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

When active, you should see `(venv)` prepended to your command line prompt.

---

## 3. Install Dependencies

Install the required web, AI, and utility libraries listed in `requirements.txt`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

!!! note
    The installation downloads standard packages (like Flask, LangGraph, and sentence-transformers). The first time you execute the embedding retriever, Python will automatically download the `abhinand/MedEmbed-base-v0.1` model weights to your local Hugging Face cache.
