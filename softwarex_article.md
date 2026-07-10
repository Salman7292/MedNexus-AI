# Title (Name of your software: MedNexus AI: A Multi-Agent System for Specialized Clinical Diagnostics)

Names of authors / main developers (incl. affiliations, addresses, email)
[Insert Author Name(s)]
[Insert Affiliation, Addresses]
[Insert Email]

## Abstract
The rapid evolution of Large Language Models (LLMs) has advanced digital health, yet general-purpose AI commonly lacks the clinical rigor required for specialized medical fields, leading to potentially dangerous hallucinations. We present MedNexus AI, a specialized software ecosystem utilizing a multi-agent orchestrated architecture to provide expert-level consultation across multiple clinical domains, including **Otorhinolaryngology, Dermatology, Psychiatry, Pharmacy, and General Medicine**. By integrating Agentic AI workflows (LangGraph), domain-specific Retrieval-Augmented Generation (RAG) across clinical medical datasets, and multi-modal computer vision (Moondream), MedNexus AI enables automated symptom evaluation, visual lesion diagnosis, and the generation of structured clinical reports. Confining agents to strict clinical personas and real-time medical data retrieval ensures high diagnostic accuracy and presents a reproducible framework for clinical AI research. The software is released under the MIT License and available for research and development purposes.

## Keywords
Medical AI, Multi-Agent System, Retrieval-Augmented Generation, LangGraph, Clinical Diagnostics, Telemedicine

## Metadata

| Nr | Code metadata description | Metadata |
|---|---|---|
| C1 | Current code version | v1.0 |
| C2 | Permanent link to code/repository used for this code version | [Insert GitHub repository URL] |
| C3 | Permanent link to reproducible capsule | [Insert Code Ocean or similar capsule URL] |
| C4 | Legal code license | MIT License |
| C5 | Code versioning system used | git |
| C6 | Software code languages, tools and services used | Python, JavaScript, HTML5, CSS (Tailwind CSS), Flask, LangGraph, Groq, Moondream, Pinecone, SQLite, HuggingFace |
| C7 | Compilation requirements, operating environments and dependencies | Python 3.9+, Node.js (for Tailwind), modern web browser with Web Speech API support |
| C8 | If available, link to developer documentation/manual | [Insert Documentation URL] |
| C9 | Support email for questions | [Insert Email] |

## 1. Motivation and significance

Modern healthcare systems face profound challenges in accessibility, equitable care distribution, and the efficient allocation of specialized medical resources. While digital health assistants have been widely proposed to alleviate this burden, their practical utility has been severely stunted by a lack of specialized knowledge, unverified clinical assumptions, and the tendency of general-purpose Large Language Models (LLMs) to generate confident yet erroneous "hallucinations."

MedNexus AI directly addresses these critical limitations by introducing a highly specialized, reliable digital consultation ecosystem. It partitions broad medical expertise into dedicated, tool-augmented software agents designed to replicate the rigorous consultation workflows of human specialists—specifically in **Dermatology, Otorhinolaryngology (ENT), Psychiatry, Pharmacy, and General Medicine**. The software serves the need for a precise "Clinical Sandbox" where conversational AI is continuously constrained by validated medical vectors and given the explicit capability to autonomously query real-world clinical databases.

MedNexus AI significantly contributes to the advancement of clinical informatics and diagnostic AI. It offers a structured and highly reproducible framework for researchers aiming to isolate, execute, and evaluate multi-stage autonomous medical agent interactions. It provides a means to systematically experiment with specialized Retrieval-Augmented Generation (RAG) optimization, multi-modal clinical image parsing, and state-based conversational memory structures in high-stakes healthcare contexts.

In a standard deployment or experimental setting, a user interfaces with the software via text, voice dictation, or clinical image uploads. The system then orchestrates cyclic reasoning loops to visually evaluate patient lesions, query specific pharmacological databases for guidelines, fetch geographical data for human referrals, and eventually synthesize the full conversation path into a formal HTML consultation report structure. Previous work in healthcare conversational AI heavily relies on static prompt engineering or linear LangChain pipelines. MedNexus AI significantly extends these foundations by utilizing LangGraph for complex directed acyclic graph (DAG) execution, integrating multi-modal capabilities like Moondream, and segmenting its knowledge base into rigorously targeted Pinecone vector namespaces.

## 2. Software description

MedNexus AI is a multi-agent web platform tailored for domain-specific medical consultations, shifting the digital architectural paradigm from broad, generalized chatbots to precise, memory-persistent clinical agents.

### 2.1. Software architecture

The architecture of MedNexus AI consists of an interactive frontend layer, a core backend orchestration server, and an autonomous tool integration node. The frontend is built using responsive HTML5, Tailwind CSS, and JavaScript.

The backend execution layer employs an "Agentic Loop" orchestrated by LangGraph using a `StateGraph`, enabling non-linear reasoning cycles. State persistence and conversational memory are maintained across sessions via `SqliteSaver` checkpointing into per-specialist SQLite databases, continuously routed through the primary LLM engine. The four specialist agents (Dermatology, ENT, Psychiatry, Pharmacy) run on `meta-llama/llama-4-scout-17b-16e-instruct` via Groq. The General Physician triage agent (Dr. Alara) runs on `openai/gpt-oss-120b`.

Crucially, the system features a dedicated Tool Node that the LLM queries whenever it encounters a lack of native confidence. This node acts as an interface to several external and internal data sources. The knowledge backbone relies on a Pinecone vector database populated with domain-specific text mapped through `abhinand/MedEmbed-base-v0.1` (HuggingFace). It features distinct namespaces for differential diagnosis mappings, safe medication protocols, and geographically based clinician directories. The deployed retrieval pipeline performs a direct top-5 similarity search (k=5); retrieved chunks are passed directly to the LLM for synthesis without an intermediate reranking step, optimizing for real-time streaming latency. Additionally, the tool layer bridges visual inputs through the Moondream Vision Language Model API and integrates dynamic real-time medical updates via the Tavily live web search API.

### 2.2. Software functionalities

The MedNexus AI system provides an array of integrated clinical functionalities:
*   **Dynamic Multi-Agent Conversation:** Hosts individualized conversational specialist models (e.g., an ENT agent and a Dermatologist agent) governed by strict clinical rigor system prompts demanding step-by-step reasoning rather than spontaneous generation.
*   **Visual Medical Analysis:** Automates the examination of uploaded clinical photography (such as suspicious skin lesions or inflamed sinus tracts) or printed lab results by employing an external vision language model to determine relevant medical morphology and clinical presentation.
*   **Domain-Specific RAG Navigation:** Autonomously triggers vector database searches focused independently on diagnoses (symptom-to-disease logic), pharmaceutical rules (contraindications and dosages), and proximity-based local human doctor recommendations based on the patient's area/zip code.
*   **Live Clinical Web Override:** Employs an intelligent web search fallback to bypass the static LLM knowledge cutoff, autonomously pulling emerging clinical guidelines or sudden FDA drug approval changes as they occur.
*   **Automated Clinical Reporting:** Transcribes the entirety of the triage phase into a structured, downloadable HTML and Tailwind CSS medical report, complete with physical signatures, session notes, and formalized prescription tables.
*   **Inclusive Accessibility Tools:** Integrates the browser-native Web Speech API, generating real-time Server-Sent Events (SSE) token streaming via text-to-speech output and accurate speech-to-text dictation to emulate a highly accessible consultation room.

## 3. Illustrative examples

To best illustrate the MedNexus AI agent workflow, consider a scenario where a patient accesses the system to evaluate a persistently inflamed facial rash.

The patient initiates the session via the `Dermatologist (Dr. Zavian)` interface, utilizing the built-in speech-to-text functionality to verbally describe the physical discomfort, before uploading a localized photograph of the rash. The user interface converts and binds the file path to the backend. The software's LangGraph orchestrator pauses the language response, mapping the image into the tool node and firing the `analyze_skin_or_report_image` tool via Moondream. The Moondream API parses the morphological elements of the photo, returning visual symptoms suggesting contact dermatitis to the LLM. 

Recognizing a clinical diagnosis, the agent queries the `diagnosis_retrieval_tool` to confirm the relationship between the visual and verbal symptoms within the Pinecone vector database. The agent subsequently calls the `medication_retrieval_tool` to fetch approved first-line mitigation strategies (e.g., topical corticosteroids) and checks against generalized contraindications. Noting the facial presence of the rash, the agent queries the `doctor_search_tool` using the patient's local zip code to refer them for an immediate physical biopsy if required. Once completed, the `generate_medical_report` tool activates, automatically compiling the diagnostic evaluation, the recommended medical protocols, and the nearby clinic’s address into an official HTML-based digital prescription that the patient can directly print or display to local healthcare providers. 

## 4. Impact

MedNexus AI provides a foundational, open-source template for effectively managing and deploying multi-stage autonomous clinical agents, generating meaningful impacts on both informatics research and digital healthcare product development:

*   **Pioneering New Research Questions:** By establishing a robust framework for agent tool utilization and StateGraph execution, medical software researchers can pursue intricate research questions surrounding the long-term mitigation of LLM hallucinations. It invites investigation into how multi-modal integration impacts the false-positive diagnostic rates in specialized healthcare software.
*   **Enhancing the Pursuit of Existing Research:** The software acts as an accessible testing environment for clinical embedding methodologies. Researchers working with healthcare vectors can effortlessly substitute or benchmark embedding models (such as testing the native HuggingFace MedEmbed against custom local models) within an active, scalable diagnostic pipeline.
*   **Changing Daily Practice:** For software developers and digital telehealth practitioners, MedNexus AI significantly lowers the barrier to entry for building memory-persistent acyclic graph applications. Its accessible feature set—offering both SSE token streams and integrated dictation out of the box—proposes a new technical standard for how empathy and responsiveness are designed within patient-facing software.
*   **Widespread Use:** The modular, Python-centric backend allows MedNexus to be highly adaptable by the broader academic community and technical open-source groups intent on replicating agentic behaviors in allied health fields (such as radiology or psychiatry).
*   **Commercial Potential:** The capacity of the agents to perform preliminary triage, cross-reference real-world pharmacy guidelines, and seamlessly generate legally formatted clinical report documentation opens immediate pathways for commercialization within enterprise telehealth solutions, E-clinic integrations, and automated Clinical Decision Support Systems (CDSS).

## 5. Conclusions

MedNexus AI represents a technical shift from monolithic, generalized medical chatbots directly toward rigorous, tool-augmented clinical agents. By harmonizing StateGraph memory checkpointing with multi-modal vision models and precise RAG vector namespaces, the software forms a highly accurate and replicable medical consultation environment. The architecture successfully minimizes dangerous assumptions by forcing the LLM to ground its outputs in queried facts while actively elevating patient accessibility through voice integration and the automated provision of structured medical documents. Future iterations of this architecture aim to scale the specialist agent catalog and safely explore the technical requirements for real-time synchronization with external Electronic Health Record (EHR) systems.

## Acknowledgements

The authors wish to acknowledge the expansive open-source developer communities maintaining LangGraph, Moondream, and Groq, whose foundational technical infrastructure facilitated the robust multi-agent orchestration crucial to this software design.

## References

[1] Langchain Foundation. (2024). LangGraph: Building Stateful, Multi-Actor Applications with LLMs. https://langchain.com
[2] Groq, Inc. (2024). Groq LPU™ Inference Engine configuration. https://groq.com
[3] Moondream. (2024). Moondream: A tiny vision language model. https://github.com/vikhyat/moondream
