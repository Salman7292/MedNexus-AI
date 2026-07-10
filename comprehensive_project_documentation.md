# Complete Project Documentation: MedNexus AI (MedNexus AI)

## 1. Project Overview & Significance
**MedNexus AI (MedNexus AI)** is a state-of-the-art medical ecosystem that shifts the paradigm from generalized chatbots to highly specialized, rigorous clinical AI agents. It addresses the critical issue of AI "hallucinations" in healthcare by partitioning medical expertise into dedicated, tool-augmented software agents. By combining **Retrieval-Augmented Generation (RAG)**, **Agentic AI workflows (LangGraph)**, and **Multi-Modal Computer Vision (Moondream)**, it provides expert-level consultations, symptom evaluation, visual lesion diagnosis, and automated generation of structured clinical reports.

---

## 2. System Architecture
The application follows a modern, decoupled architecture allowing complex reasoning loops without comprising user experience.

### 2.1 Backend Layer
*   **Framework:** Python with Flask.
*   **AI Orchestration:** LangGraph (using `StateGraph` for complex, non-linear directed acyclic graph execution) and LangChain.
*   **Memory & Persistence:** SQLite via LangGraph's `SqliteSaver` checkpointing. Thread persistence is stored in specialist-specific databases (e.g., `dermatlogist.db`, `ent.db`, `psych.db`, `chatbot.db`).

### 2.2 Artificial Intelligence & LLMs
*   **Groq Kimi-k2-instruct-0905:** Primary LLM for specialists requiring empathetic, nuanced, and visually-aware consultations (Psychiatrist and Dermatologist).
*   **Llama-3.3-70b-versatile:** Powers the AI Pharmacist and General Physician for high-speed, accurate reasoning.
*   **Llama-3.1-8b-instant:** Optional high-speed fallback.
*   **Embedding Model:** `abhinand/MedEmbed-base-v0.1` (via HuggingFace) to accurately capture the semantic context of clinical verbiage into vectors.
*   **Multi-Modal Vision:** Moondream Vision Language Model API for parsing morphological elements of clinical photos or transcribing lab results.

### 2.3 Knowledge Bases & Data Storage
*   **Vector Database:** Pinecone.
*   **RAG Namespaces:**
    *   `diagnosis_knowledge`: Symptom-to-disease mappings, clinical presentation, and differential diagnosis.
    *   `medication_knowledge`: Pharmacological data, safe medication protocols, contraindications, and dosages.
    *   `geo_directory`: Location-based directory for referring patients to local human specialists based on zip code.

### 2.4 Frontend Layer
*   **Languages:** HTML5, Vanilla JavaScript, and Vanilla CSS (featuring a Tailwind-inspired glassmorphism aesthetic).
*   **Real-time Streaming:** Server-Sent Events (SSE) stream the AI's tokens incrementally to mimic a natural conversational flow.
*   **Accessibility:** Native browser Web Speech API provides text-to-speech (TTS) output and speech-to-text (STT) dictation out of the box.
*   **Architecture:** Mobile-first "Three-Zone" layout comprising Navigation, Chat Interface, and Context/Tools pane.

---

## 3. The Multi-Agent Ecosystem (AI Specialists)
The system hosts individualized conversational specialist models governed by strict clinical rigor prompts demanding step-by-step reasoning.

### ðŸ©º Dr. Anees (AI ENT Specialist)
*   **Persona:** Senior ENT Clinical Assistant. Direct, empathetic, uses plain English.
*   **Specialty:** Ear, Nose, and Throat (Sinus, Hearing, Throat Assessment).
*   **Core Tools:** `diagnosis_retrieval_tool`, `medication_retrieval_tool`, `doctor_search_tool`, `analyze_ent_or_report_image`, `generate_medical_report`.

### ðŸ§´ Dr. Zavian (AI Dermatologist)
*   **Persona:** Expert Consultant Dermatologist. Focuses on skin morphology and aesthetic health.
*   **Specialty:** Acne, rashes, lesions, and suspicious skin markings.
*   **Core Tools:** `diagnosis_retrieval_tool`, `medication_retrieval_tool`, `doctor_search_tool`, `analyze_skin_or_report_image`, `generate_medical_report`.

### ðŸ§  Dr. Aria (AI Psychiatrist)
*   **Persona:** Compassionate Consultant Psychiatrist.
*   **Specialty:** Mental and behavioral health, anxiety, mood tracking, therapy guidance.
*   **Core Tools:** `diagnosis_retrieval_tool`, `medication_retrieval_tool`, `doctor_search_tool`, `analyze_medical_report_image`, `generate_medical_report`.

### ðŸ’Š Dr. Phram (AI Pharmacist)
*   **Persona:** Advanced Pharmaceutical Specialist. Focuses on safety, precision, and minimizing risks.
*   **Specialty:** Pharmacology, toxicology, drug interactions, and dosage precision.
*   **Core Tools:** `check_drug_interactions`, `get_dosage_info`, `generate_pharmacy_report`.

### ðŸ  Dr. Alara (General Physician)
*   **Persona:** Primary Care & Referrals Expert.
*   **Specialty:** Family medicine and initial health screening.
*   **Role:** Acts as the initial triage point, guiding patients to the correct specialist based on broad symptoms.

---

## 4. Comprehensive Toolset
The agents are equipped with a "Tool Node" that the LLM queries whenever it lacks native confidence or needs verified clinical evidence.

1.  **Vision Language Models (`analyze_skin_or_report_image` / `analyze_ent_or_report_image` / `analyze_medical_report_image`):** Uses Moondream to automate the examination of uploaded clinical photography or printed lab results.
2.  **Diagnosis Retrieval (`diagnosis_retrieval_tool`):** Internal RAG tool querying pinecone to confirm the relationship between visual/verbal symptoms and diseases.
3.  **Medication Retrieval (`medication_retrieval_tool`):** Internal RAG tool to fetch approved first-line mitigation strategies, check dosages, and verify contraindications.
4.  **Doctor Search (`doctor_search_tool`):** Queries the `geo_directory` using the patient's area/zip code to recommend local human specialists for physical biopsies or follow-ups.
5.  **Live Web Search (`search_tool` via Tavily API):** Acts as a dynamic fallback and realtime knowledge retrieval mechanism. Pulls emerging clinical guidelines, sudden FDA drug approval changes, or live clinic operating hours to bypass static LLM knowledge cutoffs.
6.  **Pharmaceutical Precision Tools (`check_drug_interactions` & `get_dosage_info`):** Dedicated tools for the Pharmacist agent to calculate exact dosages based on age/weight and flag dangerous drug combinations.
7.  **Medical Report Generation (`generate_medical_report` / `generate_pharmacy_report`):** Autonomously compiles the diagnostic evaluation, medical protocols, and clinic addresses into an official, downloadable HTML-based digital prescription, securely signed by the respective AI Doctor. Incorporates `html2canvas` for easy image downloading by patients.

---

## 5. Agentic Loop & Typical Workflow
Unlike traditional linear chatbots, MedNexus AI utilizes LangGraph to create non-linear reasoning cycles (Directed Acyclic Graphs).

**Example Workflow (Dermatologist):**
1.  **Input:** Patient dictates symptoms via Web Speech API and uploads a photograph of a facial rash.
2.  **Vision Processing:** LangGraph pauses language response and routes the image to the Tool Node (`analyze_skin_or_report_image`). Moondream parses the photo and returns visual morphological symptoms (e.g., suggesting contact dermatitis).
3.  **RAG Validation:** The agent queries `diagnosis_retrieval_tool` to cross-reference visual findings with clinical data in Pinecone.
4.  **Medication Check:** The agent queries `medication_retrieval_tool` to retrieve safe, first-line treatments like topical corticosteroids.
5.  **Referral Check:** Recognizing the rash is facial, the agent uses `doctor_search_tool` with the patient's zip code to find a local specialist.
6.  **Reporting:** Finally, `generate_medical_report` synthesizes all findings into a structured HTML report.
7.  **Output:** The final synthesized response is streamed to the user via SSE, simultaneously read aloud via TTS.

---

## 6. Directory Structure

| Folder/File | Purpose |
| :--- | :--- |
| `app.py` | Main entry point, Flask routes, session/history API, frontend serving. |
| `ent_logic.py` | LangGraph definition, state, and specific tools for the ENT Specialist. |
| `dermatologist_logic.py` | LangGraph definition/tools for the Dermatologist Specialist. |
| `psych_logic.py` | LangGraph definition/tools for the AI Psychiatrist. |
| `pharmacy_logic.py` | LangGraph definition/tools for the AI Pharmacist. |
| `general_logic.py` | LangGraph definition/tools for the General Physician. |
| `static/` | Frontend assets (JS app logic, CSS stylesheets, images, generated reports, uploaded patient photos). |
| `templates/` | Jinja2 HTML templates for the different specialist interfaces (e.g., `dermatologist.html`, `psych.html`, `ent.html`). |
| `requirements.txt` | Core Python dependencies (LangChain, LangGraph, Flask, Groq, Moondream, Pinecone, etc.). |
| `*.db` files | SQLite databases storing the conversational checkpoints and history for each distinct specialist node. |
| `softwarex_article.md` | Academic paper outlining the system architecture, motivation, and reproducible impacts. |
| `research_paper_draft.md` | Research notes and draft for the MedNexus multi-agent orchestration methodology. |
