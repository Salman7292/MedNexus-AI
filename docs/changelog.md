# Changelog

All notable changes to the MedNexus AI platform are documented in this file.

---

## [v3.0.0] - 2026-07-10
### Added
*   **Dr. Pharma Pipeline**: Expanded the AI Pharmacist with a six-stage validation check (drugs core, dosage guidelines, interactions, contraindications, toxicity, and clinical guidelines).
*   **Documentation Site**: Set up full MkDocs + Material theme documentation with `mkdocstrings` and Read the Docs configurations.
*   **RAG evaluation notebook metrics**: Detailed retrieval (NDCG, Precision@k) and generation (RAGAS faithfulness, correctness) scores inside the `evaluation_script_and_datasets/` directory.

### Changed
*   **Context Window Management**: Switched agent history processing to a "Sandwich Windowing" mechanism. The system preserves the initial 15 intake messages and the latest 25 conversation messages, dropping intermediate messages to manage token usage.
*   **Report Token Reduction**: Configured filter logic to hide generated PDF/HTML reports from downstream LLM calls, substituting them with lightweight completion metadata placeholders.

---

## [v2.0.0] - 2026-03-12
### Added
*   **Multi-Modal Image Evaluation**: Added image upload capabilities using the Moondream VLM API to inspect ear canal pictures, rashes, and transcribing medical reports.
*   **Speech Integration**: Integrated browser-native Web Speech API for TTS and STT dictation within the chat bubbles.
*   **Google OAuth**: Configured authlib integration to allow logging in using Google Accounts.
