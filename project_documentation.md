# MedNexus AI - Project Documentation

## Project Overview
**MedNexus AI** is a state-of-the-art medical ecosystem featuring multiple specialized AI agents designed to assist both patients and clinical staff. The platform combines advanced Retrieval-Augmented Generation (RAG), multi-modal vision analysis, and real-time interactive features to provide a premium medical consultation experience.

---

## ðŸ—ï¸ System Architecture

### Backend Stack
- **Framework**: Python/Flask
- **AI Orchestration**: LangGraph (for complex agentic workflows) & LangChain
- **LLMs**: 
  - **Llama-3.3-70b-versatile**: Powers the AI Pharmacist and General Physician for high-speed, accurate reasoning.
  - **Kimi-k2-instruct**: Dedicated to the AI Psychiatrist and Dermatologist for nuanced, empathetic, and visually-aware consultations.
  - **Llama-3.1-8b-instant**: (Optional) High-speed fallback for general queries.
  - **Google Gemini**: Integrated for high-performance backups and complex image processing.
- **Vector Database**: Pinecone (Namespaces: `medication_knowledge`, `diagnosis_knowledge`, `geo_directory`)
- **Persistence**: SQLite (Checkpoints for LangGraph and global conversation history)
- **Search**: Tavily AI (External medical search and local clinic discovery)
- **Computer Vision**: Moondream (Multi-modal analysis for patient photos and medical reports)

### Frontend Stack
- **Styling**: Vanilla CSS (Tailwind-inspired glassmorphism)
- **Logic**: Vanilla JavaScript
- **Features**: 
  - **Real-time Streaming**: Server-Sent Events (SSE) for incremental AI responses.
  - **Web Speech API**: Integrated Text-to-Speech (TTS) and Speech-to-Text (STT).
  - **Responsive Design**: Mobile-first "Three-Zone" architecture (Navigation, Chat, Context/Tools).

---

## ðŸ¤– AI Specialists

Each specialist is a dedicated LangGraph agent with its own persona and specialized toolset.

### ðŸ©º Dr. Anees (AI ENT Specialist)
- **Persona**: Senior ENT Clinical Assistant. Direct, empathetic, and uses plain English.
- **Specialty**: Ear, Nose, and Throat (Sinus, Hearing, Throat Assessment).
- **Core Tools**:
  - `diagnosis_retrieval_tool`: RAG tool for ENT-specific diagnostic data.
  - `medication_retrieval_tool`: RAG tool for ENT pharmacological protocols.
  - `doctor_search_tool`: Local search for otolaryngologists.
  - `analyze_ent_or_report_image`: Multi-modal analysis of ear/throat photos.
  - `generate_medical_report`: High-fidelity HTML report generator.

### ðŸ§´ Dr. Zavian (AI Dermatologist)
- **Persona**: Expert Dermatologist. Focuses on skin morphology and aesthetic health.
- **Specialty**: Acne, rashes, lesions, and suspicious skin markings.
- **Core Tools**:
  - `diagnosis_retrieval_tool`: RAG tool for dermatology diagnosis.
  - `medication_retrieval_tool`: RAG tool for skin treatments.
  - `doctor_search_tool`: Discovery of local dermatologists.
  - `analyze_skin_or_report_image`: Specialist image analysis.
  - `generate_medical_report`: Formal dermatology consultation report.

### ðŸ§  Dr. Aria (AI Psychiatrist)
- **Persona**: Compassionate Consultant Psychiatrist. Focuses on mental and behavioral health.
- **Specialty**: Anxiety, mood tracking, cognitive support, and therapy guidance.
- **Core Tools**:
  - `diagnosis_retrieval_tool`: RAG tool for psychiatric symptom identification.
  - `medication_retrieval_tool`: RAG tool for pharmacological treatments.
  - `doctor_search_tool`: Discovery of local therapists and psychiatric clinics.
  - `analyze_medical_report_image`: Vision tool for analyzing lab results or psychological assessments.
  - `generate_medical_report`: Professional psychiatric consultation report.

### ðŸ’Š Dr. Phram (AI Pharmacist)
- **Persona**: Advanced Pharmaceutical Specialist. Focuses on safety and precision.
- **Specialty**: Pharmacology, toxicology, and drug interactions.
- **Core Tools**:
  - `check_drug_interactions`: Critical tool for detecting dangerous medication combinations.
  - `get_dosage_info`: Provides precision dosage adjustments based on age and weight.
  - `generate_pharmacy_report`: Detailed analysis of a patient's medication regimen.

### ðŸ  Dr. Alara (General Physician)
- **Persona**: Primary Care & Referrals Expert. Professional and thorough.
- **Specialty**: Family medicine and initial health screening.
- **Role**: Serves as the first point of contact, guiding patients to the correct specialist based on symptoms.

---

## âœ¨ Key Features

### ðŸ“‹ Professional Medical Reports
- **Dynamic HTML**: Generates high-fidelity, printable consultation reports directly in the chat.
- **Automated Summarization**: Extracts diagnosis, meds, and care steps from the conversation.
- **Digital Download**: Integrated `html2canvas` logic allows patients to download reports as images.

### ðŸ‘ï¸ Multi-modal Vision Analysis
- **Image Processing**: Patients can upload photos of skin conditions or medical reports.
- **OCR & Diagnosis**: The AI transcribes values from lab results and describes findings from clinical photos.

### ðŸŽ™ï¸ Audio Interaction Suite
- **Text-to-Speech (TTS)**: Patients can listen to AI responses. 
- **Speech Recognition**: Voice input capabilities for hands-free patient queries.

### ðŸ”„ Intelligent Session Management
- **Thread Persistence**: Conversation history is stored in specialist-specific SQLite databases.
- **Message Editing**: Real-time logic allowing patients to edit previous messages and trigger AI re-evaluation (state truncation).

---

## ðŸ“‚ Directory Structure

| Folder/File | Purpose |
| :--- | :--- |
| `app.py` | Main entry point, Flask routes, session/history API. |
| `ent_logic.py` | LangGraph definition/tools for the ENT Specialist. |
| `dermatologist_logic.py` | LangGraph definition/tools for the Dermatologist Specialist. |
| `psych_logic.py` | LangGraph definition/tools for the AI Psychiatrist. |
| `pharmacy_logic.py` | LangGraph definition/tools for the AI Pharmacist. |
| `general_logic.py` | LangGraph definition/tools for the General Physician. |
| `static/` | Frontend assets (JS, CSS, Images, Avatars, Uploads). |
| `templates/` | Jinja2 HTML templates for each specialist interface. |
| `requirements.txt` | Core dependencies (LangChain, LangGraph, Flask, Groq, Moondream). |

---

## ðŸ› ï¸ Technical Implementation Details

### RAG (Retrieval Augmented Generation)
Knowledge is divided into namespaces in Pinecone:
1. `medication_knowledge`: Pharmacological data, dosages, contraindications.
2. `diagnosis_knowledge`: Disease symptoms, clinical presentation, differential diagnosis.
3. `geo_directory`: Location-based specialist clinics.

### Agentic Loop
The system uses a `StateGraph`:
1. **Decision**: LLM evaluates user input and decides if a tool is needed.
2. **Action**: `ToolNode` executes the tool (Search, Vector Store, Vision).
3. **Synthesis**: LLM takes tool output and reformulates a patient-friendly response.
4. **Stream**: The final response is streamed via SSE for a modern, interactive feel.

