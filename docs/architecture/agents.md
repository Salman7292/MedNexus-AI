# Specialist Personas

MedNexus AI implements specialized clinical agents, each configured with specific medical instructions, system prompts, and toolsets.

---

## Agent Summary Table

| Specialist | Role | LLM Engine | Database File | Active Pinecone Namespace |
| :--- | :--- | :--- | :--- | :--- |
| **Dr. Zavian** | Dermatology | Llama-4-Scout-17b | `dermatologist.db` | `diagnosis_knowledge`, `medication_knowledge`, `dermatologists_geo_directory` |
| **Dr. Anees** | ENT | Llama-4-Scout-17b | `ent.db` | `diagnosis_knowledge`, `medication_knowledge`, `ent_geo_directory` |
| **Dr. Aria** | Psychiatry | Llama-4-Scout-17b | `psychiatrist.db` | `diagnosis_knowledge`, `medication_knowledge`, `psychiatrist_geo_directory` |
| **Dr. Pharma** | Pharmacy | Llama-4-Scout-17b | `pharmacy_chats.db` | `contraindications`, `drugs_core`, `dosage_guidelines`, `drug_interactions`, `side_effects_toxicity`, `clinical_guidelines` |
| **Dr. Alara** | General GP | OpenAI GPT-OSS-120b | `general.db` | *None (Provides triage referrals, currently under development)* |

---

## Detailed Personas

### 1. Dr. Zavian (AI Dermatologist)
*   **Module**: [dermatologist_logic.py](file:///d:/archive/mednexai_3rd_version/mednexai_3rd_version/dermatologist_logic.py)
*   **System Prompt Location**: Defined as the `system_message` string inside `model_calling` (lines 615–667).
*   **Bound Tools**:
    *   `analyze_skin_or_report_image`: Submits client photos to Moondream VLM for lesion assessment (scaling, crusting, erythema, margins).
    *   `diagnosis_retrieval_tool`: RAG query searching symptoms in `diagnosis_knowledge` namespace.
    *   `medication_retrieval_tool`: RAG query searching protocols in `medication_knowledge` namespace.
    *   `doctor_search_tool`: Pinecone similarity check on local dermatology clinics using patient location.
    *   `search_tool`: Tavily web query fallback for recent FDA drug parameters.
    *   `generate_medical_report`: Builds a download-ready HTML/Tailwind dermatology clinical report.
*   **Rigor Prompt Constraints**: Demands step-by-step reasoning. Must collect demographics (Name, Age, Location, Gender) one by one. Forbidden from suggesting medications without calling the RAG medication search tool.

### 2. Dr. Anees (AI ENT Specialist)
*   **Module**: [ent_logic.py](file:///d:/archive/mednexai_3rd_version/mednexai_3rd_version/ent_logic.py)
*   **System Prompt Location**: Defined as the `system_message` string inside `model_calling` (lines 631–683).
*   **Bound Tools**:
    *   `analyze_ear_or_report_image`: Moondream VLM script looking for signs of infection (erythema, swelling, discharge) in throat/ear canals.
    *   `diagnosis_retrieval_tool`: RAG search in ENT diagnosis namespace.
    *   `medication_retrieval_tool`: RAG search in ENT drug protocol namespace.
    *   `ent_doctor_search_tool`: Pinecone query locating Otolaryngologists in patient area.
    *   `search_tool`: Tavily search.
    *   `generate_ent_report`: Compiles an official HTML ENT consultation summary.

### 3. Dr. Aria (AI Psychiatrist)
*   **Module**: [psych_logic.py](file:///d:/archive/mednexai_3rd_version/mednexai_3rd_version/psych_logic.py)
*   **System Prompt Location**: Defined as the `system_message` string inside `model_calling` (lines 618–670).
*   **Bound Tools**:
    *   `analyze_medical_report_image`: Moondream VLM script to extract values and comments from printed clinical reports.
    *   `diagnosis_retrieval_tool`: RAG search in Psychiatrist diagnosis namespace.
    *   `medication_retrieval_tool`: RAG search in Psychiatrist drug namespace.
    *   `psychiatrist_doctor_search_tool`: Pinecone similarity query mapping zip codes to local psychiatric clinics.
    *   `search_tool`: Tavily web search.
    *   `generate_psych_report`: Builds an HTML psychiatric care report.

### 4. Dr. Pharma (AI Pharmacist)
*   **Module**: [pharmacy_logic.py](file:///d:/archive/mednexai_3rd_version/mednexai_3rd_version/pharmacy_logic.py)
*   **System Prompt Location**: Defined as the `system_message` string inside `model_calling` (lines 707–766).
*   **Bound Tools**:
    *   Runs the multi-stage RAG evaluation check (6 distinct tools). See [Dr. Pharma Pipeline](pharma-pipeline.md) for full descriptions.
