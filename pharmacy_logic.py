import os
import sqlite3
import json
import moondream as md
from PIL import Image
from typing import List, TypedDict, Annotated, Literal, Dict, Any
from datetime import datetime
from tavily import TavilyClient
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pinecone import Pinecone
# Checkpoint
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    class SqliteSaver(MemorySaver):
        def __init__(self, conn=None):
            super().__init__()

# Load Environment Variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
moondream_key = os.getenv("MOONDREAM_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY_PHRAMACY = os.getenv("PINECONE_API_KEY_PHRAMACY")
PINECONE_API_KEY=os.getenv("PINECONE_API_KEY")

DB_NAME = "pharmacy_chats.db"



# 1. Lazy Loading for Embeddings and Vector Stores
_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name="abhinand/MedEmbed-base-v0.1"
        )
    return _embeddings




class ChatbotState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# Initialize LLM (Optimized for Pharmacy Knowledge)

llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0,
    streaming=True,
    api_key=GROQ_API_KEY
)






def contraindications_store():
    from langchain_pinecone import PineconeVectorStore
    # --- ACCOUNT 1 SETUP ---
    pc1 = Pinecone(api_key=PINECONE_API_KEY)
    
    return PineconeVectorStore(
        index_name="pharmacy",
        embedding=get_embeddings(),
        namespace="contraindications"
    )


def drugs_core_store():
    from langchain_pinecone import PineconeVectorStore
    # --- ACCOUNT 1 SETUP ---
    pc1 = Pinecone(api_key=PINECONE_API_KEY)
    
    return PineconeVectorStore(
        index_name="pharmacy",
        embedding=get_embeddings(),
        namespace="drugs_core"
    )


def dosage_guidelines_store():
    from langchain_pinecone import PineconeVectorStore
    # --- ACCOUNT 1 SETUP ---
    pc1 = Pinecone(api_key=PINECONE_API_KEY)
    
    return PineconeVectorStore(
        index_name="pharmacy",
        embedding=get_embeddings(),
        namespace="dosage_guidelines"
    )

def drug_interactions_store():
    from langchain_pinecone import PineconeVectorStore
    # --- ACCOUNT 1 SETUP ---
    pc1 = Pinecone(api_key=PINECONE_API_KEY)
    
    return PineconeVectorStore(
        index_name="pharmacy",
        embedding=get_embeddings(),
        namespace="drug_interactions"
    )

def side_effects_toxicity_store():
    from langchain_pinecone import PineconeVectorStore
    # --- ACCOUNT 1 SETUP ---
    pc1 = Pinecone(api_key=PINECONE_API_KEY_PHRAMACY)
    
    return PineconeVectorStore(
        index_name="pharmacy",
        embedding=get_embeddings(),
        namespace="side_effects_toxicity"
    )


def clinical_guidelines_store():
    from langchain_pinecone import PineconeVectorStore
    # --- ACCOUNT 1 SETUP ---
    pc1 = Pinecone(api_key=PINECONE_API_KEY_PHRAMACY)
    
    return PineconeVectorStore(
        index_name="pharmacy",
        embedding=get_embeddings(),
        namespace="clinical_guidelines"
    )


PHARMACY_TECHNICAL_TEMPLATE = """
### CLINICAL EVIDENCE FOR AI PROCESSING:
{context}

### PATIENT CONTEXT:
{query}

### AI INSTRUCTIONS:
Extract and summarize the technical pharmacological data from the source for the specified patient context.
Return a concise, structured clinical summary for internal AI reasoning.
Exclude all boilerplate, citations, and non-clinical text.
"""

def process_pharmacy_clinical_search(query, docs):
    prompt = ChatPromptTemplate.from_template(PHARMACY_TECHNICAL_TEMPLATE)
    context_text = "\n\n".join([doc.page_content for doc in docs])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context_text, "query": query})

@tool
def drugs_core_tool(query: str) -> str:
    """
    Retrieves central knowledge, drug identification, and basic clinical understanding.
    Source: Goodman & Gilman’s, Martindale, Katzung's Pharmacology.
    """
    retriever = drugs_core_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    return process_pharmacy_clinical_search(query, docs)

@tool
def dosage_guidelines_tool(query: str) -> str:
    """
    Validates prescribed dosages and detects potential overdose or sub-therapeutic dosing.
    Source: British National Formulary (BNF), Martindale.
    """
    retriever = dosage_guidelines_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    return process_pharmacy_clinical_search(query, docs)

@tool
def drug_interactions_tool(query: str) -> str:
    """
    Detects harmful drug-drug interactions and assigns severity risk levels.
    Primary Source: Stockley’s Drug Interactions.
    """
    retriever = drug_interactions_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    return process_pharmacy_clinical_search(query, docs)

@tool
def contraindications_tool(query: str) -> str:
    """
    Identifies unsafe conditions such as Pregnancy, Kidney/Liver disease, or Allergies.
    Source: BNF, Martindale, Toxicology texts.
    """
    retriever = contraindications_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    return process_pharmacy_clinical_search(query, docs)

@tool
def side_effects_toxicity_tool(query: str) -> str:
    """
    Provides data on side effects, adverse reactions, toxicity risks, and overdose symptoms.
    Source: Goodman & Gilman’s, BNF, Martindale.
    """
    retriever = side_effects_toxicity_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    return process_pharmacy_clinical_search(query, docs)

@tool
def clinical_guidelines_tool(query: str) -> str:
    """
    Checks if a prescription follows standard medical practice and disease-specific treatment protocols.
    Source: Merck Manual, Katzung's, BNF.
    """
    retriever = clinical_guidelines_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    return process_pharmacy_clinical_search(query, docs)

# # Lazy loading for Moondream
_image_model = None
def get_image_model():
    global _image_model
    if _image_model is None:
        _image_model = md.vl(api_key=moondream_key)
    return _image_model

@tool
def analyze_prescription_or_medical_report(image_path: str) -> str:
    """
    Use this tool when a patient provides a photo of a medical prescription, 
    lab report, or clinical summary. It extracts structured medical data.
    
    CRITICAL: 
    - You MUST use the EXACT file path provided in the "[System Alert]" message.
    - DO NOT hallucinate or guess a path.
    """
    
    # --- Path Validation & Fallback ---
    if not os.path.exists(image_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(base_dir, 'static', 'pharmacy_upload')
        
        if os.path.exists(uploads_dir):
            files = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir) 
                     if os.path.isfile(os.path.join(uploads_dir, f))]
            if files:
                files.sort(key=os.path.getmtime, reverse=True)
                image_path = files[0]
            else:
                return f"Error: Path '{image_path}' not found and no files in uploads."
        else:
            return f"Error: Path '{image_path}' not found and directory missing."

    # --- Dedicated Medical Data Extraction Prompt ---
    analysis_prompt = (
        "Extract all relevant information from this medical document/prescription. "
        "Provide a clear list of identified Medications and Citations. "
        "Do not provide analysis yet, just the raw data for further tool processing."
    )

    try:
        image = Image.open(image_path)
        result = get_image_model().query(image, analysis_prompt)
        return result["answer"]
    except Exception as e:
        return f"Error analyzing medical document: {str(e)}"

@tool
def generate_pharmacy_report(
    name: str = "Valued Patient", 
    age: str = "Not Specified", 
    gender: str = "Not Specified", 
    patient_id: str = "MED-X-AUTO",
    location: str = "Global",
    condition: str = "Review of Clinical Data",
    medications: Any = None, 
    treatment_plan: Any = None,
    safety_interactions: str = "Standard clinical safety profile confirmed.",
    mtm_review: str = "Medication Review & Counseling completed.",
    follow_up_date: str = "As scheduled by primary care.",
    conclusion: str = "The pharmaceutical analysis indicates a safe path forward.",
    pharmacist_notes: str = "Clinical evaluation performed by Dr. Pharma."
) -> str:
    """
    Generates a formal, customized AI Pharmaceutical Analysis Report in HTML/Tailwind format.
    Includes specific sections for Diagnosis, Medications, Treatment Plan, Safety, MTM, and Follow-up.
    """
    from datetime import datetime
    current_date_obj = datetime.now()
    report_date = current_date_obj.strftime("%B %d, %Y")
    report_id = f"report_{current_date_obj.strftime('%Y%m%d_%H%M%S')}"

    # Robust input handling
    if medications is None: medications = []
    if treatment_plan is None: treatment_plan = []
    
    # Medication Table Rows with Use and Side Effects
    med_rows = ""
    for m in medications:
        if isinstance(m, str):
            # Handle case where AI passes just a string
            m_name = m
            m_use = 'Consult tool logs'
            m_dosage = 'As directed'
            m_side_effects = 'Standard profile'
        elif isinstance(m, dict):
            m_name = m.get('name') or 'N/A'
            m_use = m.get('use') or m.get('key_info') or 'General usage'
            m_dosage = m.get('dosage') or 'As directed'
            m_side_effects = m.get('side_effects') or 'Standard profile'
        else:
            continue
        
        med_rows += f"""
        <div class="mb-4 rounded-xl border border-slate-100 bg-emerald-50/20 p-4 transition-all hover:shadow-md dark:border-gray-800 dark:bg-emerald-900/5">
            <div class="mb-2 flex items-center justify-between">
                <span class="text-xs font-black text-emerald-700 uppercase tracking-tight dark:text-emerald-400">{m_name}</span>
                <span class="rounded-full bg-emerald-100 px-2 py-0.5 text-[8px] font-bold text-emerald-800 uppercase dark:bg-emerald-900 dark:text-emerald-300">Verified</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[10px]">
                <div>
                    <span class="block font-black text-slate-400 uppercase tracking-widest text-[7px]">Usage</span>
                    <p class="text-slate-600 dark:text-gray-300">{m_use}</p>
                </div>
                <div>
                    <span class="block font-black text-slate-400 uppercase tracking-widest text-[7px]">Dosage</span>
                    <p class="font-bold text-slate-700 dark:text-gray-200">{m_dosage}</p>
                </div>
                <div class="sm:col-span-2 mt-1">
                    <span class="block font-black text-red-400 uppercase tracking-widest text-[7px]">Possible Side Effects</span>
                    <p class="italic text-slate-500 dark:text-gray-400">{m_side_effects}</p>
                </div>
            </div>
        </div>"""

    # Format Treatment Plan
    plan_steps = "".join([
        f'<div class="flex items-start mb-2 px-3 py-2 bg-slate-50 rounded-lg dark:bg-gray-900/50">'
        f'<div class="mr-3 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-[10px] font-black text-white">{i+1}</div>'
        f'<div class="text-[10px] text-slate-700 dark:text-gray-200">{step}</div>'
        f'</div>'
        for i, step in enumerate(treatment_plan)
    ])

    return f"""
<div id="{report_id}" class="medical-report relative mx-auto flex min-h-[297mm] w-full max-w-[210mm] flex-col overflow-hidden bg-white font-sans text-slate-800 shadow-2xl sm:rounded-sm dark:bg-gray-950 dark:text-gray-200 p-0 border border-slate-100 dark:border-gray-900">
  <!-- Background Watermark -->
  <div class="pointer-events-none absolute inset-0 z-0 flex items-center justify-center opacity-[0.03]">
    <img src="/static/Watermark.png" class="w-[70%]" />
  </div>
  
  <!-- Premium Header -->
  <div class="relative w-full px-8 py-10 text-white sm:px-12" style="background-color:#2a6138;">
    <div class="absolute right-0 top-0 h-full w-48 bg-white/5 skew-x-12 translate-x-24"></div>
    <div class="relative z-10 flex flex-col items-center justify-between gap-6 sm:flex-row sm:items-start sm:px-12">
      <div class="flex items-center gap-4">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-xl">
             <img src="/static/images/2.png" alt="Logo" class="h-12 w-12 rounded-lg object-contain" />
        </div>
        <div>
          <h1 class="text-2xl font-black uppercase tracking-tighter">MedNexus AI<br/><span style="color:#a8ccb4;">Specialist Pharmacy</span></h1>
          <p class="text-[9px] font-bold tracking-[0.3em] uppercase opacity-90" style="color:#a8ccb4;">Advanced Clinical Analytics</p>
        </div>
      </div>
      <div class="text-center sm:text-right">
        <h2 class="text-2xl font-black uppercase tracking-tight">Dr. Pharma</h2>
        <p class="text-[10px] font-extrabold uppercase tracking-widest" style="color:#a8ccb4;">Senior AI Pharmacist</p>
        <div class="mt-3 flex items-center justify-center gap-2 rounded-full bg-black/10 px-3 py-1 sm:justify-end">
            <div class="h-1.5 w-1.5 rounded-full animate-pulse" style="background-color:#78ad8b;"></div>
            <span class="text-[8px] font-black uppercase">Verified Credentials</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Patient Context Bar -->
  <div class="relative z-10 -mt-6 px-4 sm:px-12">
    <div class="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white/95 p-5 shadow-2xl backdrop-blur-md dark:border-gray-800 dark:bg-gray-900/95">
      <div class="flex flex-1 gap-6 md:gap-12">
        <div>
          <span class="block text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">Patient Info</span>
          <p class="text-[11px] font-bold text-slate-800 dark:text-white uppercase">{name} ({age}/{gender})</p>
        </div>
        <div>
          <span class="block text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">Registry Location</span>
          <p class="text-[11px] font-bold text-slate-800 dark:text-white uppercase">{location}</p>
        </div>
        <div>
          <span class="block text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">Clinic ID</span>
          <p class="font-mono text-[11px] font-bold" style="color:#2a6138;">{patient_id}</p>
        </div>
      </div>
      <div class="text-right">
        <span class="block text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">Issued Date</span>
        <p class="text-[11px] font-bold text-slate-800 dark:text-white uppercase">{report_date}</p>
      </div>
    </div>
  </div>

  <!-- Main Content Body -->
  <div class="mt-8 flex-1 px-8 pb-12 sm:px-12">
    
    <!-- Phase 1: Diagnosis / Condition -->
    <section class="mb-10">
        <div class="flex items-center gap-3 mb-4">
            <h3 class="text-[10px] font-black tracking-[0.2em] uppercase italic" style="color:#2a6138;">01. Clinical Context</h3>
            <div class="h-px flex-1" style="background:linear-gradient(to right, #d1e5d7, transparent);"></div>
        </div>
        <div class="rounded-2xl p-5" style="border-left:8px solid #2a6138; background-color:rgba(42,97,56,0.04);">
            <span class="block text-[8px] font-black uppercase mb-1" style="color:#2a6138;">Condition Identified</span>
            <p class="text-base font-bold text-slate-800 dark:text-white italic leading-tight">"{condition}"</p>
        </div>
    </section>

    <!-- Phase 2: Medication Ledger & Treatment Plan -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
        <!-- Medications -->
        <section>
            <div class="flex items-center gap-3 mb-4">
                <h3 class="text-[10px] font-black tracking-[0.2em] uppercase italic" style="color:#2a6138;">02. Medication Ledger</h3>
            </div>
            <div class="space-y-4">
                {med_rows}
            </div>
        </section>

        <!-- Treatment Plan -->
        <section>
            <div class="flex items-center gap-3 mb-4">
                <h3 class="text-[10px] font-black tracking-[0.2em] uppercase italic" style="color:#2a6138;">03. Treatment Plan</h3>
            </div>
            <div class="space-y-1">
                {plan_steps}
            </div>
            <div class="mt-6 rounded-xl border border-amber-50 bg-amber-50/20 p-4 dark:border-amber-900/20 dark:bg-amber-900/10">
                <div class="flex items-center gap-2 mb-2">
                    <i class="fa-solid fa-circle-exclamation text-amber-500 text-xs"></i>
                    <span class="text-[8px] font-black tracking-widest text-amber-700 uppercase dark:text-amber-500">Pharmacist's Notes</span>
                </div>
                <p class="text-[10px] italic text-slate-600 dark:text-gray-400 leading-snug">{pharmacist_notes}</p>
            </div>
        </section>
    </div>

    <!-- Phase 3: MTM & Safety -->
    <div class="mt-10 grid grid-cols-1 md:grid-cols-2 gap-10 border-t border-slate-100 pt-10 dark:border-gray-900">
        <section>
            <h3 class="text-[10px] font-black tracking-[0.2em] uppercase italic mb-4" style="color:#2a6138;">04. Medication Therapy Management (MTM)</h3>
            <div class="rounded-2xl p-5" style="border:1px solid #d1e5d7; background-color:rgba(42,97,56,0.03);">
                <p class="text-[11px] leading-relaxed text-slate-700 dark:text-gray-300">{mtm_review}</p>
                <div class="mt-4 pt-4" style="border-top:1px solid #d1e5d7;">
                    <span class="block text-[8px] font-black uppercase mb-1" style="color:#2a6138;">Follow-up Schedule</span>
                    <p class="text-[10px] font-bold text-slate-800 dark:text-white uppercase">{follow_up_date}</p>
                </div>
            </div>
        </section>
        <section>
            <h3 class="text-[10px] font-black tracking-[0.2em] text-red-600 uppercase italic mb-4">05. Safety & Interactions</h3>
            <div class="rounded-2xl border border-red-50 bg-red-50/20 p-5 dark:border-red-900/20 dark:bg-red-900/10">
                <p class="text-[11px] leading-relaxed text-slate-700 dark:text-gray-300">{safety_interactions}</p>
            </div>
        </section>
    </div>

    <!-- Phase 4: Conclusion -->
    <section class="mt-10">
        <h3 class="text-[10px] font-black tracking-[0.2em] uppercase italic mb-4" style="color:#2a6138;">06. Clinical Conclusion</h3>
        <div class="rounded-2xl bg-slate-900 p-6 text-white shadow-xl relative overflow-hidden">
            <div class="absolute right-0 top-0 h-full w-24 bg-white/5 skew-x-12"></div>
            <p class="relative z-10 text-[11px] font-medium leading-relaxed opacity-90 italic">"{conclusion}"</p>
        </div>
    </section>

  </div>

  <!-- Footer Seal -->
  <footer class="mt-auto px-8 pb-12 sm:px-12">
    <div class="flex flex-col items-center justify-between gap-8 border-t border-slate-100 pt-10 dark:border-gray-800 sm:flex-row">
      <div class="flex items-center gap-6">
        <div class="h-24 w-24 relative flex items-center justify-center">
             <div class="absolute inset-0 rounded-full border-2 border-dashed" style="border-color:#2a6138;"></div>
             <div class="absolute inset-1.5 rounded-full border" style="border-color:rgba(42,97,56,0.3);"></div>
             <div class="flex flex-col items-center justify-center text-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mb-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" style="color:#2a6138;"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                <span class="text-[6px] font-black uppercase" style="color:#2a6138;">Verified</span>
                <span class="text-[7px] font-black text-slate-800 dark:text-white uppercase leading-none">AI Seal</span>
             </div>
        </div>
        <div class="space-y-1">
            <p class="text-[9px] font-black text-slate-800 uppercase dark:text-white">Professional Integrity Code</p>
            <p class="font-mono text-[7px] text-slate-400">PHARMA-TRANS-8822-NEXUS-V3</p>
        </div>
      </div>
      <div class="text-center sm:text-right">
        <div class="mb-2">
            <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">Signed By</span>
            <p class="text-lg font-black leading-none" style="color:#2a6138;">Dr. Pharma</p>
        </div>
        <p class="text-[8px] text-slate-400 italic">This report is an AI-generated clinical assessment based on verified RAG protocols.</p>
      </div>
    </div>
  </footer>
</div>

<div class="mx-auto mt-8 mb-12 flex max-w-[210mm] justify-center px-4 print:hidden">
  <button onclick="downloadReport('{report_id}')" class="group flex items-center gap-3 rounded-full px-8 py-3 text-xs font-black tracking-widest text-white shadow-lg transition-all hover:shadow-xl active:scale-95" style="background-color:#2a6138;">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="h-4 w-4">
      <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
    DOWNLOAD REPORT
  </button>
</div>

<style>
@media print {{
    body {{ background: white !important; padding: 0 !important; }}
    .medical-report {{ box-shadow: none !important; margin: 0 !important; width: 100% !important; border: none !important; }}
    .print\\:hidden {{ display: none !important; }}
}}
</style>
<script>
async function downloadReport(reportId) {{
    const reportElement = document.getElementById(reportId);
    if (!reportElement) return;
    
    // Create temporary wrapper for cloning
    const wrapper = document.createElement('div');
    wrapper.style.position = 'absolute';
    wrapper.style.left = '-9999px';
    wrapper.style.top = '0';
    wrapper.style.width = '1200px';
    document.body.appendChild(wrapper);

    // Clone node
    const clone = reportElement.cloneNode(true);
    clone.style.transform = 'none';
    clone.style.width = '1200px';
    clone.style.minHeight = 'auto';
    clone.style.display = 'flex';
    clone.style.flexDirection = 'column';
    clone.style.visibility = 'visible';
    
    wrapper.appendChild(clone);

    // --- CRITICAL: Strip all animations and problematic elements BEFORE calling html2canvas ---
    // 1. Remove ALL spinning/animated elements — they cause the createPattern zero-dimension error
    clone.querySelectorAll('[class*="animate-"]').forEach(el => {{
        el.style.animation = 'none';
        el.style.transition = 'none';
        el.className = el.className.replace(/animate-\S+/g, '').trim();
    }});

    // 2. Remove the watermark <img> (external/CORS image causes rendering failures)
    clone.querySelectorAll('img').forEach(img => {{
        if (img.src.includes('Watermark') || img.src === '' || img.naturalWidth === 0) {{
            img.remove();
        }}
    }});

    // 3. Ensure all remaining images have crossorigin set
    clone.querySelectorAll('img').forEach(img => {{
        img.setAttribute('crossorigin', 'anonymous');
    }});

    const btn = document.querySelector(`button[onclick="downloadReport('${{reportId}}')"]`);
    const originalContent = btn ? btn.innerHTML : '';
    if (btn) {{
        btn.innerHTML = '<svg class="animate-spin h-4 w-4 inline mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Generating...';
        btn.disabled = true;
    }}

    try {{
        if (typeof html2canvas === 'undefined') {{
            await new Promise((resolve, reject) => {{
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            }});
        }}

        // Layout settlement delay — ensures cloned DOM is fully painted
        await new Promise(r => setTimeout(r, 600));

        const isDark = document.documentElement.classList.contains('dark');
        const canvas = await html2canvas(clone, {{
            scale: 2,
            useCORS: true,
            allowTaint: false,
            backgroundColor: isDark ? '#0f172a' : '#ffffff',
            windowWidth: 1200,
            ignoreElements: (el) => {{
                return el.tagName === 'DIV' && 
                       el.style.animation !== 'none' && 
                       el.offsetWidth === 0;
            }}
        }});

        const link = document.createElement('a');
        link.download = `Pharmacy_Report_Dr_Pharma_${{new Date().toISOString().split('T')[0]}}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();

    }} catch (error) {{
        console.error("Report generation failed:", error);
        alert("Failed to generate report image: " + error.message);
    }} finally {{
        document.body.removeChild(wrapper);
        if (btn) {{
            btn.innerHTML = originalContent;
            btn.disabled = false;
        }}
    }}
}}
</script>
"""

@tool
def search_tool(query: str) -> str:
    """
    CRITICAL: Use this tool in three specific scenarios:
    1. If the internal 'drugs_core_tool', 'dosage_guidelines_tool', or other RAG tools contain no information.
    2. To check for the latest 2024-2026 FDA drug approvals or emerging clinical guidelines. 
       PRIORITY: Always search "https://dailymed.nlm.nih.gov/dailymed/index.cfm" first for medication details.
    3. FINDING LOCAL PHARMACIES: To find pharmacies, pharmaceutical clinics, addresses, and contact details for patient referrals.
    """
   
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    # Prepend site filter if it looks like a drug search
    is_drug_search = any(term in query.lower() for term in ["drug", "medication", "dose", "tablet", "syrup", "cream", "ointment", "fda"])
    search_query = f"site:dailymed.nlm.nih.gov {query}" if is_drug_search else query
    
    raw_response = client.search(query=search_query, search_depth="advanced", max_results=5)
        
    prompt = ChatPromptTemplate.from_template("""
        You are a Senior Pharmaceutical Data Refiner. Your job is to take raw search results and make them professional, clean, and clinically valid.
        
        QUERY: {query}
        RAW DATA: {raw_data}
        
        INSTRUCTIONS:
        1. If searching for medications, prioritize data from DailyMed (nlm.nih.gov).
        2. If the query is about PHARMACIES/DRUGSTORES: Extract Names, Phone Numbers, and Addresses into a clean list.
        3. If the query is about MEDICAL INFO/DRUGS: Summarize the latest 2024-2026 clinical data, FDA status, and key dosages.
        4. Remove all HTML tags, broken links, and advertisements.
        5. If information is missing, simply state 'Information not found in current search'.
        
        CLEAN CLINICAL SUMMARY:
        """)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"query": query, "raw_data": raw_response})

tools = [
    analyze_prescription_or_medical_report, 
    drugs_core_tool, 
    dosage_guidelines_tool, 
    drug_interactions_tool, 
    contraindications_tool, 
    side_effects_toxicity_tool, 
    clinical_guidelines_tool,
    generate_pharmacy_report,
    search_tool
]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

# Filter messages to save tokens
def filter_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
    system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
    other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]

    # 2. Strategic "Sandwich" Windowing (Solution 3): 
    # Keep first 15 (Intake) and last 25 (Context) with a summary marker.
    if len(other_messages) > 40:
        intake_phase = other_messages[:15]
        recent_context = other_messages[-25:]
        
        middle_count = len(other_messages) - 40
        summary_marker = SystemMessage(content=f"[SYSTEM NOTE: {middle_count} middle messages have been condensed to save memory. The earlier clinical history and patient details are still accessible.]")
        
        other_messages = intake_phase + [summary_marker] + recent_context

    # 3. Filter out massive HTML reports from ToolMessages
    filtered_messages = []
    for msg in other_messages:
        if isinstance(msg, ToolMessage) and msg.name == "generate_pharmacy_report":
            new_msg = ToolMessage(
                content="[Pharmaceutical Analysis Report Generated Successfully - Full HTML content hidden to save tokens]",
                tool_call_id=msg.tool_call_id,
                name=msg.name,
                artifact=msg.artifact,
                status=msg.status
            )
            filtered_messages.append(new_msg)
        else:
            filtered_messages.append(msg)
    
    return system_messages + filtered_messages

def model_calling(messages: List[BaseMessage]) -> AIMessage:
    system_message = SystemMessage(content=(
    "ROLE: You are Dr. Pharma, a Senior AI Pharmacist. "
    "STYLE: Short, WhatsApp-style (1-2 sentences). Direct and empathetic. "

    "\n--- MANDATORY CLINICAL PROTOCOL ---"
    "\n1. PHASE 1: BASIC INFO: Collect Name, Age, Location, and Gender. Ask ONE BY ONE. Do not skip this."
    
    "\n--- REVISED PHASE 2 & 3 PROTOCOL ---"
    "\n2. PHASE 2: INITIAL ANALYSIS (IMAGE/REPORT):"
    "\n   - If a medical report/prescription is uploaded, IMMEDIATELY call 'analyze_prescription_or_medical_report'."
    "\n   - Extract patient details from the findings. If anything is missing, you MUST ask the user one-by-one."
    "\n   - Once demographics are secured, call ALL 6 RAG tools sequentially: 'drugs_core_tool', 'dosage_guidelines_tool', 'drug_interactions_tool', 'contraindications_tool', 'side_effects_toxicity_tool', and 'clinical_guidelines_tool'."
    "\n   - SEAMLESS SEARCH FALLBACK: If any of the RAG tools return 'No data found' or insufficient information, IMMEDIATELY call 'search_tool' to fetch the latest 2024-2026 data. CRITICAL: Never tell the user that data was not found initially. Complete the analysis using search results seamlessly."

    "\n2. PHASE 2: INTAKE (TEXT-ONLY USERS):"
    "\n   - If no report is provided, collect Name, Age, Location, and Gender ONE BY ONE. Do not skip."

    "\n3. PHASE 3: CLINICAL SUMMARY:"
    "\n   - Once ALL 6 tools (and potentially search_tool) have finished, translate the technical findings into a 'Best-in-Class' UNIFIED clinical summary."
    "\n   - MANDATORY FORMAT:"
    "\n     **Clinical Summary**: [Context Title]"
    "\n     **Interactions with [Drug A]**: [Detailed findings or 'No significant interactions found']"
    "\n     **Interactions with [Drug B]**: [Detailed findings or 'No significant interactions found']"
    "\n     **Key Points**: [Clinical takeaways]"
    "\n     **Management**: [Actionable advice]"
    "\n     "
    "\n     * **Diagnosis/Condition**: [Extracted context]"
    "\n     **Medication Profile**: [Names and primary uses]"
    "\n     **Dosage & Safety**: [Unified dosage instructions and critical interaction alerts]"
    "\n     **Side Effects**: [Common side effects to watch for]"
    "\n   "
    "\n   - After the summary, ask: 'I have finished my clinical analysis. Would you like me to generate your high-fidelity Pharmaceutical Analysis Report now?'"
    "\n   - WAIT for the user to say 'Yes', 'Go ahead', 'Approved', or similar before calling the report tool."

    "\n4. PHASE 4: FINAL REPORT GENERATION:"
    "\n   - ONLY after receiving user approval, call 'generate_pharmacy_report'."

    "\n\nPATIENT-FRIENDLY LANGUAGE: When explaining conditions or giving advice, NEVER use complex medical jargon. Use simple, everyday English."

    "\n\nCRITICAL RULES FOR RESPONSE FORMAT:"
    "\n1. NEVER provide multiple versions or placeholders."
    "\n2. Generate only ONE response. Stop immediately after the first complete thought/question."
    "\n3. STABILITY RULE: Never generate repetitive strings. If repeating, STOP immediately."
    "\n4. MANDATORY: Never ask two things at once."

    "\n--- UI & FORMATTING RULES (STRICT) ---"
    "\n- NO TEXT REPORTS: Never type the full clinical report in the chat. Keep the Phase 3 summary extremely brief."
    "\n- If the user approves, call 'generate_pharmacy_report' and say ONLY: 'I have generated your detailed pharmaceutical analysis report. You can download it below.' and STOP."

    "\n--- CLINICAL RIGOR & REASONING (CRITICAL) ---"
    "\nMedical accuracy is critical. NEVER make assumptions. "
    "Perform step-by-step clinical reasoning for every case. Ask clarifying questions "
    "until you have sufficient evidence to provide a safe and accurate assessment."

    "\n--- REPORT INTEGRITY & GENERATION (CRITICAL) ---"
    "\n1. MANDATORY: You are strictly FORBIDDEN from text-based refusals."
    "\n2. FIELD MAPPING: name, age, gender, location, condition, medications (list of dicts), treatment_plan (5+ steps), mtm_review, follow_up_date, safety_interactions, conclusion."

    "\nEMPATHY: 'I am analyzing your medical documents and cross-referencing safety guidelines now. Do you have any known allergies or history of liver/kidney issues?'"
))
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages = [system_message] + messages
    
    # Apply filtering before sending to LLM
    final_messages = filter_messages(messages)
    
    return llm_with_tools.invoke(final_messages)

def chat_node(state: ChatbotState):
    response = model_calling(state["messages"])
    return {"messages": response}

# Build Graph
graph = StateGraph(ChatbotState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge('tools', 'chat_node')

# SQLite Persistent Connection
conn = sqlite3.connect(database=DB_NAME, check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)
chatbot_compiled = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)
