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
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
moondream_key = os.getenv("MOONDREAM_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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

def get_medication_store():
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index_name="psychiatrist-specialist",
        embedding=get_embeddings(),
        namespace="medication_knowledge"
    )

def get_diagnosis_store():
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index_name="psychiatrist-specialist",
        embedding=get_embeddings(),
        namespace="diagnosis_knowledge"
    )

def get_geo_directory_store():
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index_name="psychiatrist-specialist",
        embedding=get_embeddings(),
        namespace="psychiatrist_geo_directory"
    )

class ChatbotState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0,
    streaming=True,
    api_key=GROQ_API_KEY
)

# # Lazy loading for Moondream
_image_model = None
def get_image_model():
    global _image_model
    if _image_model is None:
        _image_model = md.vl(api_key=moondream_key)
    return _image_model
# # Initialize Gemini LLM
# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash", # or "gemini-1.5-pro"
#     temperature=0,
#     streaming=True,
#     google_api_key=GOOGLE_API_KEY
# )


CLINICAL_PROMPT_TEMPLATE = """
You are a Senior Psychiatric Assistant. Your goal is to extract and summarize medical information 
from the provided context to answer a doctor's query accurately.

### CONTEXT FROM VECTOR STORE:
{context}

### DOCTOR'S QUERY:
{query}

### INSTRUCTIONS:
- If the context contains the answer, provide it clearly.
- Use **Bold** for drug names and *Italics* for dosages.
- Include "First-line", "Second-line", and "Contraindications" if available.
- Structure the response with clear headings or a table.

### CLINICAL SUMMARY:
"""

def process_clinical_search(query, docs):
    prompt = ChatPromptTemplate.from_template(CLINICAL_PROMPT_TEMPLATE)
    context_text = "\n\n".join([doc.page_content for doc in docs])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context_text, "query": query})

@tool
def diagnosis_retrieval_tool(query: str) -> str:
    """
    Retrieves comprehensive diagnostic information from the psychiatric diagnosis vector store.
    Use for: Unconfirmed mental health conditions, symptom identification, and differential diagnosis.
    """
    retriever = get_diagnosis_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    return process_clinical_search(query, docs)

@tool
def medication_retrieval_tool(query: str) -> str:
    """
    Retrieves pharmacological treatments, psychotherapy protocols, and dosages from the medication store.
    Use for: Confirmed psychiatric conditions, drug names (antidepressants, anxiolytics, etc.), and treatment safety.
    """
    retriever = get_medication_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    return process_clinical_search(query, docs)

@tool
def search_tool(query: str) -> str:
    """
    CRITICAL: Use this tool in three specific scenarios:
    1. If the internal 'diagnosis_retrieval_tool' or 'medication_retrieval_tool' contain no information.
    2. To check for the latest 2024-2026 FDA psychiatric drug approvals or emerging clinical guidelines.
       PRIORITY: Always search "https://dailymed.nlm.nih.gov/dailymed/index.cfm" first for medication details.
    3. FINDING LOCAL DOCTORS: To find psychiatric clinics, therapy centers, and contact details for patient referrals.
    """
   
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    # Prepend site filter if it looks like a drug search
    is_drug_search = any(term in query.lower() for term in ["drug", "medication", "dose", "tablet", "capsule", "fda", "antidepressant", "anxiolytic"])
    search_query = f"site:dailymed.nlm.nih.gov {query}" if is_drug_search else query
    
    raw_response = client.search(query=search_query, search_depth="advanced", max_results=5)
        
    prompt = ChatPromptTemplate.from_template("""
        You are a Medical Data Refiner for Psychiatry. Your job is to take raw search results and make them professional and clean.
        
        QUERY: {query}
        RAW DATA: {raw_data}
        
        INSTRUCTIONS:
        1. If searching for medications, prioritize data from DailyMed (nlm.nih.gov).
        2. If the query is about DOCTORS/CLINICS: Extract Names, Phone Numbers, and Addresses into a clean list.
        3. If the query is about MEDICAL INFO/DRUGS: Summarize the latest 2024-2026 clinical data, FDA status, and key dosages.
        4. Remove all HTML tags, broken links, and advertisements.
        5. If information is missing, simply state 'Information not found in current search'.
        
        CLEAN SUMMARY:
        """)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"query": query, "raw_data": raw_response})

@tool
def doctor_search_tool(location: str) -> str:
    """
    Search for and locate psychiatrists and medical clinics near the patient.
    Use this tool when the patient provides a location (city, zip code, or address).
    
    Args:
        location: A string containing the user's location (e.g., 'Buner' or '90210').
    """
    final_query = f"psychiatrists and mental health clinics in {location}"
    retriever = get_geo_directory_store().as_retriever(
        search_type="similarity", 
        search_kwargs={"k": 3}
    )
    results = retriever.invoke(final_query)
    return results

@tool
def analyze_medical_report_image(image_path: str) -> str:
    """
    Use this tool when a patient provides a photo of a medical report or a psychological assessment.
    
    CRITICAL: 
    - You MUST use the EXACT file path provided in the "[System Alert: User uploaded an image. Local Path: ...]" message.
    - Copy the path character-for-character.
    - DO NOT make up, guess, or hallucinate a path (like 'D:\\tmp\\...'). If you don't see a [System Alert] with a path, do not use this tool.
    """
    
    # Fallback Logic for Hallucinated Paths
    if not os.path.exists(image_path):
        # Try to find the most recent image in static/uploads
        # Assuming the app structure is relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(base_dir, 'static', 'psychiatrist_upload')
        
        if os.path.exists(uploads_dir):
            # Get list of files with full paths
            files = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir) 
                     if os.path.isfile(os.path.join(uploads_dir, f))]
            
            if files:
                # Sort by modification time, newest first
                files.sort(key=os.path.getmtime, reverse=True)
                most_recent_file = files[0]
                image_path = most_recent_file
            else:
                 return f"Error: Image path '{image_path}' not found and no images found in uploads directory."
        else:
             return f"Error: Image path '{image_path}' not found and uploads directory does not exist."

    analysis_prompt = (
        "Check if this image is a medical report or a clinical document. "
        "IF A REPORT: Transcribe all text, dates, findings, and diagnostic codes exactly. "
        "Focus on psychiatric or mental health-related content."
    )
    try:
        image = Image.open(image_path)
        result = get_image_model().query(image, analysis_prompt)
        return result["answer"]
    except Exception as e:
        return f"Error analyzing image: {str(e)}"
@tool
def generate_medical_report(
    name: str, 
    age: str, 
    gender: str, 
    patient_id: str,
    location: str,
    complaints: str,
    notes: str,
    diagnosis: str, 
    medications: Any = None, 
    instructions: Any = None,
    treatment_steps: Any = None
) -> str:
    """
    Generates a formal, professional psychiatric consultation report in HTML/Tailwind format.
    
    Args:
        name: Patient's name.
        age: Patient's age.
        gender: Patient's gender.
        patient_id: Unique patient identifier.
        location: Patient's location.
        complaints: Primary medical complaints.
        notes: Clinical notes and observations.
        diagnosis: Final clinical diagnosis.
        medications: List of objects with 'name', 'dosage', 'frequency', and 'duration'. Example: [{"name": "Drug", "dosage": "10mg", "frequency": "Daily", "duration": "30 days"}]
        instructions: List of strings for care instructions.
        treatment_steps: List of strings for the treatment plan.
    """
    from datetime import datetime
    current_date_obj = datetime.now()
    report_date = current_date_obj.strftime("%B %d, %Y")
    report_id = f"report_{current_date_obj.strftime('%Y%m%d_%H%M%S')}"
    
    # Robust input handling
    if medications is None: medications = []
    if instructions is None: instructions = []
    if treatment_steps is None: treatment_steps = []

    # Updated table row logic for 4 columns
    med_rows = ""
    for m in medications:
        if isinstance(m, str):
            m_name = m
            m_dosage = "As directed"
            m_freq = "N/A"
            m_duration = "As specified"
        elif isinstance(m, dict):
            # Resilient key lookup
            m_name = m.get('name') or m.get('medicine') or m.get('drug') or 'N/A'
            m_dosage = m.get('dosage') or m.get('dose') or 'N/A'
            m_freq = m.get('frequency') or m.get('freq') or 'N/A'
            m_duration = m.get('duration') or m.get('time') or 'N/A'
        else:
            continue
        
        med_rows += f"""
        <tr class="group transition-colors hover:bg-sky-50/30">
            <td class="px-3 py-2">
                <span class="block text-[10px] font-bold text-slate-800 dark:text-white uppercase leading-tight tracking-tight">{m_name}</span>
                <span class="text-[7px] text-slate-400 uppercase font-medium italic">Prescribed Medicine</span>
            </td>
            <td class="px-3 py-2 text-[10px] text-slate-600 dark:text-gray-300">
                {m_dosage}
            </td>
            <td class="px-3 py-2">
                <span class="rounded bg-sky-100 px-1.5 py-0.5 text-[9px] font-black text-sky-700 dark:bg-sky-900/40 dark:text-sky-300">
                    {m_freq}
                </span>
            </td>
            <td class="px-3 py-2 text-right text-[10px] font-black text-slate-700 dark:text-gray-300">
                {m_duration}
            </td>
        </tr>"""

    # Format instructions as a numbered list
    formatted_instructions = "".join([
        f'<div class="flex items-start mb-1 text-[10px] leading-snug">'
        f'<div class="mr-1.5 font-black text-[#0ea5e9]">{i+1}.</div>'
        f'<div>{step}</div></div>' 
        for i, step in enumerate(instructions)
    ])

    # Format treatment steps as a bulleted list
    tx_list_items = "".join([
        f'<div class="flex items-start mb-1 text-[10px] leading-snug">'
        f'<div class="mr-1.5 text-slate-400">•</div>'
        f'<div>{step}</div></div>' 
        for step in treatment_steps
    ])

    return f"""
<div id="{report_id}" class="medical-report relative mx-auto flex min-h-[297mm] w-full max-w-[210mm] flex-col overflow-hidden bg-white font-sans text-slate-800 shadow-2xl sm:rounded-sm dark:bg-gray-950 dark:text-gray-200">
  <!-- Background Watermark -->
  <div class="pointer-events-none absolute inset-0 z-0 flex items-center justify-center opacity-[0.03]">
    <img src="/static/Watermark.png" class="w-[70%]" />
  </div>
  
  <div class="relative w-full flex-shrink-0 bg-teal-600 py-8 sm:py-10">
    <div class="relative z-10 flex flex-col items-center justify-between gap-6 px-6 sm:flex-row sm:items-start sm:px-10">
      <div class="flex flex-col items-center gap-3 text-center sm:flex-row sm:text-left">
        <div class="flex h-16 w-16 items-center justify-center rounded-full border-4 border-white/30 bg-white shadow-lg">
          <img src="/static/images/phys.gif" alt="Clinic Logo" class="h-11 w-11 rounded-full object-contain" />
        </div>
        <div class="text-white">
          <h1 class="text-xl font-black leading-none tracking-tight uppercase sm:text-2xl">Psychiatric &<br/><span class="text-teal-100">Wellbeing</span></h1>
          <p class="mt-1 text-[8px] font-bold tracking-[0.2em] text-teal-100 uppercase opacity-90">Consultation Report</p>
        </div>
      </div>
      <div class="text-center sm:text-right">
        <h2 class="text-xl font-bold leading-tight text-white sm:text-2xl uppercase tracking-tight">Dr. Aria</h2>
        <p class="text-xs font-extrabold text-teal-100">Consultant Psychiatrist</p>
        <p class="text-[9px] font-bold tracking-wide text-white/90">MBBS, FCPS (Psychiatry)</p>
        <div class="mt-2 h-0.5 w-20 rounded-full bg-white/30 mx-auto sm:ml-auto sm:mr-0 sm:w-24"></div>
      </div>
    </div>
  </div>

  <div class="relative z-10 -mt-6 px-4 sm:px-10">
    <div class="grid grid-cols-2 gap-y-3 gap-x-2 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-lg dark:border-gray-800 dark:bg-gray-900 sm:grid-cols-5 sm:gap-3 sm:px-6">
      <div class="col-span-2 sm:col-span-1">
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Patient Name</span>
        <span class="text-[11px] font-bold text-slate-800 uppercase dark:text-gray-100 truncate block">{name}</span>
      </div>
      <div>
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Age/Sex</span>
        <span class="text-[11px] font-bold text-slate-800 dark:text-gray-200">{age} / {gender}</span>
      </div>
      <div>
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Location</span>
        <span class="text-[11px] font-bold text-slate-800 dark:text-gray-200">{location}</span>
      </div>
      <div>
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Date</span>
        <span class="text-[11px] font-bold text-slate-800 dark:text-gray-200">{report_date}</span>
      </div>
      <div class="col-span-2 sm:col-span-1 sm:text-right">
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Patient ID</span>
        <span class="font-mono text-[11px] font-bold text-teal-600">{patient_id}</span>
      </div>
    </div>
  </div>

  <div class="relative z-10 flex flex-1 flex-col gap-6 px-6 pt-8 sm:flex-row sm:gap-8 sm:px-10">
    <div class="w-full space-y-6 sm:w-[35%] sm:border-r sm:border-slate-100 sm:pr-6 sm:dark:border-gray-800">
      <section>
        <h3 class="mb-2 text-[9px] font-black tracking-[0.15em] text-teal-600 uppercase">Complaints</h3>
        <div class="rounded-lg bg-slate-50 p-3 text-[10px] leading-snug text-slate-600 italic dark:bg-gray-900 dark:text-gray-400">"{complaints}"</div>
      </section>
      <section>
        <h3 class="mb-2 text-[9px] font-black tracking-[0.15em] text-teal-600 uppercase">Clinical Notes</h3>
        <div class="text-[10px] leading-snug text-slate-600 dark:text-gray-400">{notes}</div>
      </section>
      <section class="rounded-xl bg-red-50 p-4 dark:bg-red-950/30">
        <h3 class="mb-1 text-[8px] font-black tracking-widest text-red-600 uppercase">Diagnosis</h3>
        <div class="text-[11px] font-extrabold text-slate-900 uppercase dark:text-gray-100 leading-tight">{diagnosis}</div>
      </section>
    </div>

    <div class="w-full sm:w-[65%]">
      <div class="mb-4 flex items-baseline gap-3">
        <span class="font-serif text-4xl text-slate-900 italic dark:text-gray-100 sm:text-5xl">R<sub class="-ml-1 text-2xl sm:text-3xl">x</sub></span>
        <div class="h-[1.5px] flex-1 rounded-full bg-slate-100 dark:bg-gray-800"></div>
      </div>

      <div class="mb-6 overflow-hidden rounded-xl border border-slate-200 shadow-sm dark:border-gray-800">
        <table class="w-full table-fixed border-collapse text-left">
          <thead>
            <tr class="bg-slate-900 text-[8px] font-black tracking-widest text-white uppercase dark:bg-teal-900">
              <th class="w-[35%] px-3 py-2.5">Medicine</th>
              <th class="w-[20%] px-3 py-2.5">Dosage</th>
              <th class="w-[25%] px-3 py-2.5">Frequency</th>
              <th class="w-[20%] px-3 py-2.5 text-right">Duration</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-gray-800">
            {med_rows}
          </tbody>
        </table>
        <div class="bg-slate-50 px-4 py-1.5 text-[7px] font-bold text-slate-400 uppercase tracking-widest dark:bg-gray-900 text-center border-t border-slate-100">Digital Prescription Verified</div>
      </div>

      <div class="grid gap-3">
        <div class="rounded-xl border border-amber-100 bg-amber-50/40 p-3 dark:border-amber-900/30 dark:bg-amber-900/10">
          <h3 class="mb-1 text-[8px] font-black text-amber-700 uppercase dark:text-amber-500">Instructions</h3>
          <div class="text-slate-600 dark:text-gray-400">{formatted_instructions}</div>
        </div>
        <div class="rounded-xl border border-teal-100 bg-teal-50/40 p-3 dark:border-teal-900/30 dark:bg-teal-900/10">
          <h3 class="mb-1 text-[8px] font-black text-teal-700 uppercase dark:text-teal-500">Treatment Plan</h3>
          <div class="text-slate-600 dark:text-gray-400">{tx_list_items}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="relative z-10 mt-auto px-6 pb-10 sm:px-10">
    <div class="flex flex-col gap-8 border-t border-slate-100 pt-8 dark:border-gray-800 sm:flex-row sm:items-end sm:justify-between">
      <div class="max-w-xs space-y-0.5 text-[9px] text-slate-400">
        <p>Digitally signed on {current_date_obj.strftime("%b %d, %Y | %H:%M")}</p>
        <div class="mt-3 flex items-center gap-1.5">
           <div class="h-3.5 w-3.5 rounded bg-green-100 flex items-center justify-center text-green-600 font-bold text-[8px]">✓</div>
           <span class="italic text-[8px]">Verified Electronic Signature</span>
        </div>
      </div>
      <div class="relative w-full text-center sm:w-56">
        <div class="absolute -top-10 left-1/2 -translate-x-1/2 -rotate-12 pointer-events-none opacity-50">
          <div class="h-20 w-20 rounded-full border-4 border-double border-red-600/50 flex flex-col items-center justify-center text-[6px] font-black text-red-600 uppercase">
            <span>Verified</span>
            <span class="text-[8px]">Dr. Aria</span>
            <span>Clinic</span>
          </div>
        </div>
        <div class="border-t border-slate-800 pt-2">
          <p class="text-xs font-black text-slate-800 uppercase dark:text-gray-100">Dr. Aria</p>
          <p class="text-[8px] font-bold tracking-[0.2em] text-teal-600 uppercase">Consultant Specialist</p>
        </div>
      </div>
    </div>
  </div>

  <div class="relative w-full bg-teal-600 py-3">
    <div class="flex flex-col items-center justify-center gap-1.5 px-10 text-[7px] font-black text-white uppercase sm:flex-row sm:justify-between">
      <span>Record ID: {report_id}</span>
      <span>Clinic: Mon - Fri (09:00 - 11:00)</span>
    </div>
  </div>
</div>

<div class="mx-auto mt-8 mb-12 flex max-w-[210mm] justify-center px-4 print:hidden">
  <button onclick="downloadReport('{report_id}')" class="group flex items-center gap-3 rounded-full bg-teal-600 px-8 py-3 text-xs font-black tracking-widest text-white shadow-lg transition-all hover:bg-teal-700 hover:shadow-xl active:scale-95">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="h-4 w-4">
      <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
    DOWNLOAD REPORT
  </button>
</div>

<style>
  .medical-report .clip-path-header {{ clip-path: ellipse(100% 65% at 15% 0%); }}
  .medical-report .clip-path-footer {{ clip-path: ellipse(100% 100% at 50% 100%); }}

  @media print {{
      body {{ background: white !important; padding: 0 !important; }}
      .medical-report {{ shadow: none !important; margin: 0 !important; width: 100% !important; border: none !important; }}
      .print\\:hidden {{ display: none !important; }}
  }}
</style>

<script>
async function downloadReport(reportId) {{
    const reportElement = document.getElementById(reportId);
    if (!reportElement) return;
    
    const wrapper = document.createElement('div');
    wrapper.style.position = 'absolute';
    wrapper.style.left = '-9999px';
    wrapper.style.top = '0';
    document.body.appendChild(wrapper);

    const clone = reportElement.cloneNode(true);
    clone.style.transform = 'none';
    wrapper.appendChild(clone);

    const btn = document.querySelector(`button[onclick="downloadReport('${{reportId}}')"]`);
    const originalContent = btn ? btn.innerHTML : '';
    if (btn) {{
        btn.innerHTML = '<i class="fa-light fa-spinner-third animate-spin"></i> Generating...';
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

        // Layout Settlement Delay: Give the browser time to render the off-screen clone
        await new Promise(r => setTimeout(r, 800));

        const canvas = await html2canvas(clone, {{
            scale: 2, 
            useCORS: true,
            logging: true,
            backgroundColor: document.documentElement.classList.contains('dark') ? '#0b0f1a' : '#ffffff',
            windowWidth: 1200,
            onclone: (clonedDoc) => {{
                const element = clonedDoc.getElementById(reportId);
                if (element) {{
                    element.style.transform = 'none';
                    element.style.width = '1200px';
                    element.style.display = 'flex';
                    element.style.visibility = 'visible';
                    // Remove animations which often cause 'createPattern' errors in html2canvas
                    const animated = element.querySelectorAll('.animate-spin-slow, .animate-spin');
                    animated.forEach(el => {{
                        el.classList.remove('animate-spin-slow', 'animate-spin');
                        el.style.animation = 'none';
                    }});
                }}
            }}
        }});

        const link = document.createElement('a');
        link.download = `Psychiatry_Report_Dr_Aria_${{new Date().toISOString().split('T')[0]}}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();

    }} catch (error) {{
        console.error("Report generation failed:", error);
        alert("Failed to generate report image.");
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


# Bind tools
tools = [diagnosis_retrieval_tool, medication_retrieval_tool, search_tool, generate_medical_report, doctor_search_tool, analyze_medical_report_image]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

# Filter messages to save tokens
def filter_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
    # 1. Always keep the System Message (usually the first one)
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
        if isinstance(msg, ToolMessage) and msg.name == "generate_medical_report":
            # Create a copy or new message with summary content
            # valid_artifact is not a standard ToolMessage field, but we can just change content
            # We construct a new ToolMessage to avoid mutating the original object in the graph state if it's shared
            new_msg = ToolMessage(
                content="[Medical Report Generated Successfully - Full HTML content hidden to save tokens]",
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
    "ROLE: You are Dr. Aria, an expert Psychiatrist. "
    "STYLE: Short, WhatsApp-style (1-2 sentences). Direct and empathetic. "

    "\n--- MANDATORY TOOL PROTOCOL (INTERNAL LOGIC) ---"
    "\n1. PHASE 1: BASIC INFO: Collect Name, Age, Location, and Gender. Ask ONE BY ONE."
    "\n2. PHASE 2: THOROUGH INVESTIGATION: You are FORBIDDEN from calling tools after only 3-4 questions. "
    "You must perform a deep psychiatric evaluation. Ask about: duration of symptoms, impact on daily life, "
    "mood fluctuations, sleep patterns, appetite, triggers, and any previous mental health history/treatments."
    "\n3. PHASE 3: TOOL CALL: Only after you have a full and detailed history, call 'diagnosis_retrieval_tool'."
    "\n4. PHASE 4: MEDICATION/THERAPY CALL: After the diagnosis tool, you MUST immediately call 'medication_retrieval_tool' "
    "passing the exact results from the diagnosis tool to get the exact treatment/therapy plan. Do not suggest protocols from memory."
    "\n5. FALLBACK: Use internal knowledge ONLY if tools return 'No results found'."

    "\n\nPATIENT-FRIENDLY LANGUAGE: When explaining conditions or giving a diagnosis, "
    "NEVER use complex medical jargon or clinical terms. Use simple, everyday English "
    "that a person with no education can easily understand."

    "\n\nCRITICAL RULES FOR RESPONSE FORMAT:"
    "\n1. NEVER provide multiple versions, variations, or options for a response."
    "\n2. NEVER use long sequences of dots (....) or placeholders."
    "\n3. Generate only ONE response. Stop immediately after the first complete thought/question."
    "\n4. STABILITY RULE: Never generate repetitive or random strings. If you find yourself repeating, STOP immediately."
    "\n5. MANDATORY: Never ask two things at once. If you need 4 pieces of info, ask 4 times. Wait for user response before asking the next."

    "\n\nEMPATHY EXAMPLE:"
    "\nPatient: 'I feel so overwhelmed lately.'"
    "\nDr. Aria: 'That’s completely understandable. Life can be very difficult at times, but you are not alone in feeling this way. Let me help you work through this. Tell me...'"

    "\n\nFEW-SHOT STYLE:"
    "\nPatient: 'I can't sleep and I feel anxious all the time.'"
    "\nDr. Aria: 'I'm sorry to hear you're going through that. It sounds exhausting, but I'm glad you reached out. We are here for you.'"

    "\n\nCLINICAL RIGOR & REASONING: Medical accuracy is critical. NEVER make assumptions. "
    "Perform step-by-step clinical reasoning for every case. Ask clarifying questions "
    "until you have sufficient evidence to provide a safe and accurate diagnosis/assessment."

    "\n\n--- REPORT INTEGRITY & GENERATION (CRITICAL) ---"
    "\n1. MANDATORY: You are strictly FORBIDDEN from typing a medical report, summary, or diagnosis as text in the chat. Even if the user asks for a 'summary' or 'report', you MUST call the 'generate_medical_report' tool."
    "\n2. FORBIDDEN FORMAT: Never type a response like this: 'Psychiatric Consultation Report... Patient Information... Complaints... Clinical Notes... Diagnosis... Medications...'. This type of plain-text reporting is a CRITICAL FAILURE."
    "\n3. ZERO TOLERANCE FOR MISSING DATA: You are strictly FORBIDDEN from passing 'N/A', 'N/N', or empty strings to the report tool. "
    "\n3. RE-VERIFICATION RULE: If demographics (Name, Age, Location, Gender) were collected long ago and are missing from your current memory window, you MUST re-ask the patient for them before calling the tool."
    "\n4. PATIENT ID: Always generate a unique 8-digit alphanumeric ID (e.g., PSY-445566) for the 'patient_id' field."
    "\n5. FIELD REQUIREMENTS & MAPPING: "
    "\n   - 'Complaints' & 'Clinical Notes': Must be professional, highly detailed, and elaborate on the full history gathered in Phase 2."
    "\n   - 'medications': This must be a LIST of dictionaries. Each dictionary MUST use these exact keys: {'name': '...', 'dosage': '...', 'frequency': '...', 'duration': '...'}. Populate this using data from 'medication_retrieval_tool'."
    "\n   - 'Instructions': Must be a numbered list of at least 5-6 distinct, actionable care steps."
    "\n6. POST-GENERATION: Just say 'I have generated your detailed medical report. You can download it below.' and STOP."

    "\n\nCORE RULES FOR TOOLS (STRICT PROHIBITION):"
    "\n1. NEVER show raw tool output, JSON, clinical text snippets, or technical logs directly to the patient in the chat."
    "\n2. DOCTOR SEARCH: Present names and locations in a clean, professional list."
    "\n3. IMAGE ANALYSIS: Use 'analyze_medical_report_image'. Extract the Local Path from [System Alert] but keep it hidden."
    "\n4. CONVERSION RULE: Always take the information from the tools and rephrase it into your own clinical voice (Dr. Aria)."
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
DB_NAME = "psychiatrist.db"
conn = sqlite3.connect(database=DB_NAME, check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)
chatbot_compiled = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)
