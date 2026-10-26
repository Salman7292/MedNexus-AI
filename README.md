
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Salman7292/MedNexus-AI/blob/main/LICENSE)
# MedNexus AI Medical Specialists

MedNexus AI is a comprehensive web platform featuring AI-powered medical specialists (Dermatology, ENT, Psychiatry, Pharmacy) that offer instant, precise diagnostics, care plans, and medical analysis.

This guide provides full instructions on how to set up, install, and run this project locally on both Windows and macOS.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation on Windows](#-windows-installation--setup)
- [Installation on macOS / Linux](#-macos--linux-installation--setup)
- [Environment Variables](#-environment-variables-env-setup)
- [Running the Application](#-running-the-application)
- [Stopping the Application](#-stopping-the-application)
- [Project Structure](#-project-structure)
- [Prompt Repository](#-prompt-repository)
- [Licence](#-licence)
- [Citation](#-citation)
- [Evaluation Scripts and Datasets](#-evaluation-scripts-and-datasets)

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Python 3.10+** (Python 3.10 is the version used for the reported evaluation; Python 3.11 also works)
- **Git** (optional, for cloning the repository)

> Note: Python 3.10 or higher is required because several pinned dependencies in `requirements.txt` (notably `langgraph==1.0.8`) require it. The exact environment used for the reported evaluation is documented in the manuscript (Code Metadata table, C5 and C6).

---

## 💻 Windows Installation & Setup

Open **Command Prompt** or **PowerShell** and follow these steps:

### 1. Navigate to your project directory
If you haven't already, navigate to the folder where the project is located:
```cmd
cd path\to\your\project_folder
```

### 2. Create a Virtual Environment
It is highly recommended to use a virtual environment to keep dependencies isolated so they don't interfere with other Python projects on your system.
```cmd
python -m venv venv
```

### 3. Activate the Virtual Environment
Activate the environment you just created. You must do this every time you work on the project.
```cmd
venv\Scripts\activate
```
*Note: Once activated, you should see `(venv)` at the beginning of your command prompt line.*

### 4. Install Dependencies
Install all the required Python packages from the `requirements.txt` file.
```cmd
pip install -r requirements.txt
```

---

## 🍏 macOS / Linux Installation & Setup

Open your **Terminal** application and follow these steps:

### 1. Navigate to your project directory
Navigate to the folder containing your project files:
```bash
cd /path/to/your/project_folder
```

### 2. Create a Virtual Environment
Create an isolated Python environment for the project:
```bash
python3 -m venv venv
```

### 3. Activate the Virtual Environment
Activate the environment. You must do this every time before running the app.
```bash
source venv/bin/activate
```
*Note: Your terminal prompt will change to show `(venv)` on the left side.*

### 4. Install Dependencies
Install all required libraries using `pip`:
```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables (.env Setup)

This project relies on several third-party APIs (Groq, Pinecone, Tavily, LangSmith, Google OAuth, etc.).

1. Ensure there is a file named `.env` in the root directory of your project.
2. If it does not exist, create one (a template is provided in `.env.example`).
3. Your `.env` file should contain the necessary API keys formatted like this:

```env
GROQ_API_KEY="your_groq_api_key_here"
PINECONE_API_KEY="your_pinecone_api_key_here"
TAVILY_API_KEY="your_tavily_api_key_here"
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your_langsmith_api_key_here"
LANGSMITH_PROJECT="Dermatlogist"
MOONDREAM_KEY="your_moondream_key_here"
GOOGLE_API_KEY="your_google_api_key_here"
GOOGLE_CLIENT_ID="your_google_client_id_here"
GOOGLE_CLIENT_SECRET="your_google_client_secret_here"
```

*(Note: Replace the placeholder values with your actual API keys if you are setting this up from scratch.)*

---

## 🚀 Running the Application

Once your virtual environment is activated and dependencies are installed, you can start the application.

### On both Windows and Mac:

Run the Flask application with the following command:
```bash
python app.py
```

You should see terminal output indicating that the server is running, usually looking like this:
```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

### Accessing the App
Open your web browser (Chrome, Firefox, Safari, Edge) and navigate to:
**http://127.0.0.1:5000** or **http://localhost:5000**

---

## 🛑 Stopping the Application

To stop the server, go back to your terminal or command prompt window and press:
**`Ctrl + C`**

To deactivate and exit your virtual environment when you are done working:
```bash
deactivate
```

---

## 📁 Project Structure

The repository is organised as follows. The names in this tree match the manuscript's Code Metadata table (C1–C8).

```
MedNexus-AI/
├── app.py                    Flask application entry point
├── dermatologist_logic.py    Dr. Zavian (Dermatology) agent logic
├── ent_logic.py              Dr. Anees (ENT) agent logic
├── psych_logic.py            Dr. Aria (Mental and Behavioural Health) agent logic
├── pharmacy_logic.py         Dr. Pharma (Clinical Pharmacology) agent logic
├── requirements.txt          Pinned runtime dependencies
├── .env.example              Template for required environment variables
├── LICENSE                   MIT Licence (full text)
├── CITATION.cff              Citation metadata
├── prompts/                  Prompt repository (see below)
│   ├── zavian/               Dr. Zavian prompts (8 files)
│   ├── anees/                Dr. Anees prompts (8 files)
│   ├── aria/                 Dr. Aria prompts (8 files)
│   ├── pharma/               Dr. Pharma prompts (11 files)
│   └── README.md             Prompt inventory and source mapping
├── evaluation_script_and_datasets/   Evaluation notebooks and query sets
├── templates/                HTML/Tailwind templates
└── static/                   Static assets (CSS, JS, uploads)
```

---

## 📝 Prompt Repository

All system prompts, tool prompts, and report templates used by the four specialist agents are stored as plain-text files in the [`prompts/`](prompts/) folder. The folder is organised as **one file per tool per specialist**, using the naming convention:

- `<tool>_prompt.txt` — retrieval-type tools (e.g. `diagnosis_retrieval_tool_prompt.txt`)
- `moondream_<speciality>_<purpose>.txt` — vision-language model prompts (e.g. `moondream_skin_or_report.txt`)
- `generate_<type>_report_template.txt` — report-generation schemas (e.g. `generate_medical_report_template.txt`)
- `system_prompt.txt` — the agent persona
- `disclaimer.txt` — the clinical safety notice

The folder layout is:

| Folder | Specialist | Files | Tools |
|---|---|---|---|
| [`prompts/zavian/`](prompts/zavian/) | Dr. Zavian (Dermatology) | 8 | 6 |
| [`prompts/anees/`](prompts/anees/) | Dr. Anees (ENT) | 8 | 6 |
| [`prompts/aria/`](prompts/aria/) | Dr. Aria (Mental and Behavioural Health) | 8 | 6 |
| [`prompts/pharma/`](prompts/pharma/) | Dr. Pharma (Clinical Pharmacology) | 11 | 9 |

The total count per folder equals the number of tools plus two additional files (`system_prompt.txt` and `disclaimer.txt`).

See [`prompts/README.md`](prompts/README.md) for a full inventory that maps each prompt file to its corresponding source file and line range in the Python codebase.

The prompt files are documented in Appendix B of the manuscript associated with this repository. The reviewer response for R1.4 points to this folder directly.

---

## 📜 Licence

This project is released under the **MIT Licence**. The full text of the licence is available at:

- [`LICENSE`](LICENSE) in the repository root
- Or directly at <https://github.com/Salman7292/MedNexus-AI/blob/main/LICENSE>

Copyright (c) 2026 The MedNexus AI Contributors.

The MIT Licence permits reuse, modification, and redistribution of the software, provided that the copyright notice and this permission notice are included in all copies or substantial portions of the software. The software is provided "as is", without warranty of any kind.

---

## 📚 Citation

If you use MedNexus AI in academic work, please cite both the software release and the accompanying SoftwareX manuscript.

Citation metadata is provided in [`CITATION.cff`](CITATION.cff) at the repository root. GitHub will automatically generate a "Cite this repository" button on the repository landing page from this file.

The version of the software corresponding to the manuscript is tagged **v1.0.0**:

- Release page: <https://github.com/Salman7292/MedNexus-AI/releases/tag/v1.0.0>
- Manuscript: *MedNexus AI: A Multi-Agent Ecosystem for Specialised Clinical Diagnostics and Automated Professional Medical Reporting*, SoftwareX (2026), manuscript number SOFTX-D-26-00845.

---

## 📊 Evaluation Scripts and Datasets

The evaluation scripts and query sets used for the retrieval and generation-quality metrics reported in the manuscript are available in the [`evaluation_script_and_datasets/`](evaluation_script_and_datasets/) folder.

The reported metrics include:

- Retrieval quality: MRR, NDCG, graded Context Recall, graded Context Precision
- Generation quality: Faithfulness, Answer Relevance, Answer Correctness, RAGAS Context Precision

The four evaluation notebooks correspond to Dr. Zavian (Dermatology), Dr. Anees (ENT), Dr. Aria (Mental and Behavioural Health), and Dr. Pharma (Clinical Pharmacology). The evaluation was run on Python 3.10.14 with the exact dependency versions pinned in `requirements.txt` at the **v1.0.0** release.

Query sets and derived files are provided where licensing permits. Copyrighted clinical textbooks and proprietary reference materials are not redistributed.

---

## 📖 Documentation

Full developer documentation is available at <https://mednexus-ai.readthedocs.io>.

---

## 📧 Support

For questions, please open an issue on the GitHub repository or contact the corresponding author:

- **Muhammad Salman** — salmanuom04@gmail.com
- **Dost Muhammad** (corresponding author) — dost.muhammad@universityofgalway.ie
