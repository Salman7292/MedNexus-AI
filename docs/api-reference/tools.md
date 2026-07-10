# Agent Tools Reference

This section details the custom tools decorated with `@tool` that the specialist agents can invoke.

---

## Retrieval & Search Tools

### `diagnosis_retrieval_tool(query: str) -> str`
Retrieves symptom-disease mappings, diagnostic parameters, and clinical presentations from Pinecone.
*   **Args**:
    *   `query` (`str`): Factual symptom description or differential query.
*   **Returns**: Concordant vector chunks summarized by the LLM as a concise internal summary.

### `medication_retrieval_tool(query: str) -> str`
Retrieves treatment procedures, first-line medications, contraindications, and dosage margins from Pinecone.
*   **Args**:
    *   `query` (`str`): Factual drug or treatment query.
*   **Returns**: Dosage instructions and warnings summarized by the LLM.

### `search_tool(query: str) -> str`
Queries the web using the Tavily API. Filters results and summarizes findings.
*   **Args**:
    *   `query` (`str`): Factual search query.
*   **Returns**: Cleaned search output focusing on 2024–2026 data.

### `doctor_search_tool(location: str) -> str`
Queries local directories based on patient location (zip code or city) and maps them to proximal specialty clinics.
*   **Args**:
    *   `location` (`str`): Zip code or city string.
*   **Returns**: Clinic names, addresses, and phone numbers.

---

## Vision Processing Tools

### `analyze_skin_or_report_image(image_path: str) -> str`
Analyzes dermatology lesion uploads or text-based clinical reports using Moondream.
*   **Args**:
    *   `image_path` (`str`): Absolute server path to the file.
*   **Returns**: Transcribed report text or morphological skin descriptions.

### `analyze_ear_or_report_image(image_path: str) -> str`
Analyzes throat/ear photographs using Moondream.
*   **Args**:
    *   `image_path` (`str`): Absolute server path.
*   **Returns**: Ear drum descriptions, swelling assessments, or report transcriptions.

### `analyze_prescription_or_medical_report(image_path: str) -> str`
Extracts structured lists of drug names, dosages, and dosing intervals from prescription photos.
*   **Args**:
    *   `image_path` (`str`): Absolute server path.
*   **Returns**: Extracted text content listing medications and parameters.

---

## Report Generators

### `generate_medical_report(...)`
Compiles clinical parameters into an HTML report styled with Tailwind CSS.
*   **Key Args**:
    *   `name` (`str`), `age` (`str`), `gender` (`str`), `patient_id` (`str`), `location` (`str`): Demographic metadata.
    *   `complaints` (`str`), `notes` (`str`): Clinical intake parameters.
    *   `diagnosis` (`str`): suspected or confirmed condition.
    *   `medications` (`list[dict]`): Verified treatments. Example: `[{"name": "Drug A", "dosage": "10mg", "duration": "7 days"}]`
    *   `treatment_steps` (`list[str]`): Sequential care guidelines.
*   **Returns**: Complete HTML string rendered in the browser.

### `generate_pharmacy_report(...)`
Compiles drug interaction, MTM, and safety parameters into an HTML report styled with Tailwind CSS.
*   **Key Args**:
    *   `name` (`str`), `age` (`str`), `gender` (`str`), `patient_id` (`str`), `location` (`str`): Demographic metadata.
    *   `condition` (`str`): Evaluated condition.
    *   `medications` (`list[dict]`): Active medication profile.
    *   `treatment_plan` (`list[str]`): Sequential pharmacist instructions.
    *   `safety_interactions` (`str`): Drug-drug hazards found.
    *   `mtm_review` (`str`): Review notes.
*   **Returns**: HTML string.
