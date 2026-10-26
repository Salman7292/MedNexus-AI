# MedNexus AI — Prompt Repository

This folder contains one prompt file per tool for each of the four MedNexus AI specialists.
File names follow `<tool>_prompt.txt` for retrieval tools,
`moondream_<speciality>_<purpose>.txt` for VLM tools, and
`generate_<type>_report_template.txt` for report tools.
No prompts for `general_logic.py` are included.

---

## Specialists and tool counts

| Specialist | Domain                    | Source file             | Tools | Folder files |
|------------|---------------------------|-------------------------|-------|--------------|
| Dr. Zavian | Dermatology               | `dermatologist_logic.py`| 6     | 8            |
| Dr. Anees  | Otolaryngology (ENT)      | `ent_logic.py`          | 6     | 8            |
| Dr. Aria   | Psychiatry & Mental Health| `psych_logic.py`        | 6     | 8            |
| Dr. Pharma | Clinical Pharmacology     | `pharmacy_logic.py`     | 9     | 11           |

Folder file count = tools + 2 (system_prompt.txt + disclaimer.txt per specialist).

---

## File inventory

| File | Folder | Tool backed | Source (file:line) | One-line description |
|------|--------|-------------|-------------------|----------------------|
| `system_prompt.txt` | zavian/ | n/a (persona) | dermatologist_logic.py:1906–1955 | Dr. Zavian dynamic system prompt with patient state injection |
| `diagnosis_retrieval_tool_prompt.txt` | zavian/ | diagnosis_retrieval_tool | dermatologist_logic.py:1142–1198 | RAG differential-diagnosis summariser (DIAGNOSIS_SUMMARY_PROMPT) |
| `medication_retrieval_tool_prompt.txt` | zavian/ | medication_retrieval_tool | dermatologist_logic.py:1161–1213 | RAG pharmacotherapy summariser (MEDICATION_SUMMARY_PROMPT) |
| `search_tool_prompt.txt` | zavian/ | search_tool | dermatologist_logic.py:1215–1249 | DailyMed-priority web search refiner |
| `doctor_search_tool_prompt.txt` | zavian/ | doctor_search_tool | dermatologist_logic.py:1251–1292 | Dermatology clinic finder with AAD directory fallback |
| `moondream_skin_or_report.txt` | zavian/ | analyze_skin_or_report_image | dermatologist_logic.py:730–752 | Two-pass Moondream VLM prompts (body part + lesion morphology) |
| `generate_medical_report_template.txt` | zavian/ | generate_medical_report | dermatologist_logic.py:1294–1311 | Dermatology HTML report schema and generation rules |
| `disclaimer.txt` | zavian/ | n/a (disclaimer) | dermatologist_logic.py:1481 | Named disclaimer: Dr. Zavian AI |
| `system_prompt.txt` | anees/ | n/a (persona) | ent_logic.py:616–677 | Dr. Anees ENT system prompt with differential-loop protocol |
| `diagnosis_retrieval_tool_prompt.txt` | anees/ | diagnosis_retrieval_tool | ent_logic.py:100–132 | RAG ENT diagnosis summariser (CLINICAL_PROMPT_TEMPLATE) |
| `medication_retrieval_tool_prompt.txt` | anees/ | medication_retrieval_tool | ent_logic.py:134–141 | RAG ENT medication summariser (CLINICAL_PROMPT_TEMPLATE) |
| `search_tool_prompt.txt` | anees/ | search_tool | ent_logic.py:143–176 | DailyMed-priority web search refiner for ENT |
| `doctor_search_tool_prompt.txt` | anees/ | doctor_search_tool | ent_logic.py:181–196 | ENT geo-directory similarity retriever (k=3) |
| `moondream_ent_or_report.txt` | anees/ | analyze_ent_or_report_image | ent_logic.py:233–238 | Single Moondream VLM prompt for ENT photo or document |
| `generate_medical_report_template.txt` | anees/ | generate_medical_report | ent_logic.py:246–275 | ENT HTML report schema and generation rules |
| `disclaimer.txt` | anees/ | n/a (disclaimer) | ent_logic.py (generic) | Generic MedNexus AI disclaimer for ENT module |
| `system_prompt.txt` | aria/ | n/a (persona) | psych_logic.py:610–664 | Dr. Aria psychiatric system prompt with distress-handling note |
| `diagnosis_retrieval_tool_prompt.txt` | aria/ | diagnosis_retrieval_tool | psych_logic.py:100–132 | RAG psychiatric diagnosis summariser (CLINICAL_PROMPT_TEMPLATE) |
| `medication_retrieval_tool_prompt.txt` | aria/ | medication_retrieval_tool | psych_logic.py:134–141 | RAG psychiatric medication/therapy summariser |
| `search_tool_prompt.txt` | aria/ | search_tool | psych_logic.py:143–176 | DailyMed-priority web search refiner for psychiatry |
| `doctor_search_tool_prompt.txt` | aria/ | doctor_search_tool | psych_logic.py:178–193 | Psychiatry geo-directory similarity retriever (k=3) |
| `moondream_medical_report.txt` | aria/ | analyze_medical_report_image | psych_logic.py:228–232 | Single Moondream VLM prompt for psychiatric documents (OCR) |
| `generate_medical_report_template.txt` | aria/ | generate_medical_report | psych_logic.py:239–268 | Psychiatric HTML report schema and generation rules |
| `disclaimer.txt` | aria/ | n/a (disclaimer) | psych_logic.py (generic) | Generic MedNexus AI disclaimer for psychiatry module |
| `system_prompt.txt` | pharma/ | n/a (persona) | pharmacy_logic.py:702–761 | Dr. Pharma six-phase RAG pharmacology protocol |
| `analyze_prescription_or_medical_report.txt` | pharma/ | analyze_prescription_or_medical_report | pharmacy_logic.py:255–258 | Moondream VLM prompt for prescription/document OCR |
| `drugs_core_tool_prompt.txt` | pharma/ | drugs_core_tool | pharmacy_logic.py:146–172 | RAG core drug reference (Goodman & Gilman's, Martindale, Katzung's) |
| `dosage_guidelines_tool_prompt.txt` | pharma/ | dosage_guidelines_tool | pharmacy_logic.py:174–181 | RAG dosage validation (BNF, Martindale) |
| `drug_interactions_tool_prompt.txt` | pharma/ | drug_interactions_tool | pharmacy_logic.py:183–190 | RAG drug-drug interaction detector (Stockley's) |
| `contraindications_tool_prompt.txt` | pharma/ | contraindications_tool | pharmacy_logic.py:192–199 | RAG contraindication screener (BNF, Martindale, Toxicology) |
| `side_effects_toxicity_tool_prompt.txt` | pharma/ | side_effects_toxicity_tool | pharmacy_logic.py:201–208 | RAG adverse-reaction and toxicity profiler |
| `clinical_guidelines_tool_prompt.txt` | pharma/ | clinical_guidelines_tool | pharmacy_logic.py:210–217 | RAG treatment-protocol validator (Merck Manual, Katzung's, BNF) |
| `search_tool_prompt.txt` | pharma/ | search_tool | pharmacy_logic.py:619–652 | DailyMed-priority web search refiner for pharmacy |
| `generate_pharmacy_report_template.txt` | pharma/ | generate_pharmacy_report | pharmacy_logic.py:268–287 | Pharmacy HTML report schema (MTM, safety, conclusion sections) |
| `disclaimer.txt` | pharma/ | n/a (disclaimer) | pharmacy_logic.py:499 | Named disclaimer: Dr. Pharma / AI-generated RAG-protocol report |
| `context_only_instruction.txt` | prompts/ (root) | n/a (shared) | All four *_logic.py FALLBACK clauses | Structural fallback behaviour — use context, skip tool call |
| `multimodal_system_alert.txt` | prompts/ (root) | n/a (shared) | app.py:680; *_logic.py VLM docstrings | Image upload alert format injected by Flask into HumanMessage |
| `history_condensation_note.txt` | prompts/ (root) | n/a (shared) | ent_logic.py:591; psych_logic.py:585; pharmacy_logic.py:680; dermatologist_logic.py:1745 | Two condensation-marker variants across specialists |
| `README.md` | prompts/ (root) | n/a | — | This file |

---

## Design note

### Docstring-only tools
The following tools have only a short docstring as their "prompt" — no separate summariser template:

- **zavian/doctor_search_tool_prompt.txt**: The tool uses `TavilyClient` directly for clinic search; no LLM chain prompt. The docstring and return-value logic are the complete tool specification.
- **anees/doctor_search_tool_prompt.txt**: Uses Pinecone similarity retriever directly (k=3); no LLM chain. Docstring-only.
- **aria/doctor_search_tool_prompt.txt**: Same as anees — Pinecone similarity retriever, docstring-only.
- **pharma/analyze_prescription_or_medical_report.txt**: Moondream VLM call with a single string prompt; no LLM chain. The VLM prompt is the complete tool specification.

For these tools, the file prepends `# Tool: <tool_name>` and reproduces the docstring verbatim, per the project instruction.

### Generic vs. specialist-named disclaimers
- **zavian/disclaimer.txt**: Named — explicitly names "Dr. Zavian AI" in the HTML report body (`dermatologist_logic.py:1481`).
- **pharma/disclaimer.txt**: Named — footer attributes report to "Dr. Pharma" (`pharmacy_logic.py:499`).
- **anees/disclaimer.txt**: Generic — no explicit disclaimer block in the ENT HTML template; derived from general MedNexus AI safety principle.
- **aria/disclaimer.txt**: Generic — no explicit disclaimer block in the psychiatry HTML template; derived from general MedNexus AI safety principle.

### Dr. Aria — no standalone crisis classifier
There is no separate crisis-classification tool or PHQ-9 scoring prompt in `psych_logic.py`.
Distress detection and safe-messaging are handled at the system-prompt level within `aria/system_prompt.txt`.
The manuscript has been revised to describe this implemented behaviour accurately.

### general_logic.py
`general_logic.py` (Dr. Alara, general medicine triage) is not part of the deployed four-specialist
release and is therefore not documented in this prompt repository. No `prompts/alara/` folder exists.

---


