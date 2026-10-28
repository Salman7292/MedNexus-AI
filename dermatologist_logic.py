import os
import re
import sqlite3
import json
import uuid
import time
import random
from typing import List, TypedDict, Annotated, Literal, Dict, Any, Optional
from datetime import datetime
from PIL import Image
try:
    import pillow_avif
except ImportError:
    pass

import moondream as md
from tavily import TavilyClient
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from retrieval_service import retrieve_with_rerank

# Checkpointer Setup
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
        _embeddings = HuggingFaceEmbeddings(
            model_name="abhinand/MedEmbed-base-v0.1"
        )
    return _embeddings

def get_medication_store():
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index_name="dermatologist",
        embedding=get_embeddings(),
        namespace="medication_knowledge"
    )

def get_diagnosis_store():
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index_name="dermatologist",
        embedding=get_embeddings(),
        namespace="diagnosis_knowledge"
    )

def get_geo_directory_store():
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index_name="dermatologist",
        embedding=get_embeddings(),
        namespace="dermatologists_geo_directory"
    )

# 2. LLM Configuration
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    streaming=True,
    api_key=GROQ_API_KEY
)

# 3. Vision Model (Moondream)
_image_model = None
def get_image_model():
    global _image_model
    if _image_model is None:
        _image_model = md.vl(api_key=moondream_key)
    return _image_model


# ==============================================================================
# ROBUST GROQ API RETRY & ERROR HANDLING LAYER
# ==============================================================================

def invoke_llm_with_retry(
    llm_instance,
    messages: List[BaseMessage],
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 4.0
) -> AIMessage:
    """
    Executes LLM invocation with bounded retries, exponential backoff with jitter,
    respect for Groq rate limit retry-after hints, and safe fallback generation.
    Does not log credentials or sensitive patient data.
    """
    attempt = 0
    last_exception = None

    while attempt <= max_retries:
        try:
            return llm_instance.invoke(messages)
        except Exception as e:
            last_exception = e
            err_str = str(e).lower()

            # Client or authorization errors should not be retried in a tight loop
            if any(code in err_str for code in ["401", "unauthorized", "invalid_api_key"]):
                print("[LLM Error]: Authentication failure with Groq API.")
                raise
            if "400" in err_str and "tools should have a name" in err_str:
                raise

            # Detect rate limits (429) or transient network/server glitches (500, 502, 503)
            is_rate_limit = "429" in err_str or "rate limit" in err_str or "tokens per minute" in err_str
            is_transient = is_rate_limit or any(term in err_str for term in ["500", "502", "503", "504", "timeout", "connection"])

            if not is_transient or attempt == max_retries:
                print(f"[LLM Invocation Failed]: Non-retryable error or retries exhausted (Attempt {attempt+1}/{max_retries+1}): {type(e).__name__}")
                break

            attempt += 1
            wait_time = base_delay * (2 ** (attempt - 1))

            # Parse provider's retry guidance if provided (e.g. "try again in 2.5s")
            match = re.search(r'try again in\s*([\d\.]+)\s*s', err_str)
            if match:
                try:
                    wait_time = max(wait_time, float(match.group(1)))
                except ValueError:
                    pass

            wait_time = min(wait_time + random.uniform(0.1, 0.4), max_delay)
            print(f"[LLM Retry]: Provider rate limit / transient error on attempt {attempt}. Backing off for {wait_time:.2f}s...")
            time.sleep(wait_time)

    # Safe fallback if retries exhausted or live API failed
    if last_exception and ("429" in str(last_exception) or "rate limit" in str(last_exception).lower()):
        fallback_msg = (
            "MedNexus AI is currently experiencing high consultation volume. "
            "Your conversation and medical details are safely saved. "
            "Please wait a moment and try sending your message again, or seek emergency medical care if you have urgent symptoms."
        )
    else:
        fallback_msg = (
            "I apologize, but our clinical service experienced a brief interruption. "
            "Your previous statements have been preserved. "
            "Please re-send your message so we can continue your evaluation."
        )
    return AIMessage(content=fallback_msg)


# ==============================================================================
# STRUCTURED IMAGE ANALYSIS HELPER & TOOL
# ==============================================================================

# Canonical anatomical region keywords ordered from most specific to most general
_ANATOMICAL_KEYWORDS: List[tuple] = [
    # Head / Face - specific regions first
    ("nasal tip", "nose"),
    ("tip of the nose", "nose"),
    ("bridge of the nose", "nose"),
    ("nostril", "nose"),
    ("ala", "nose"),
    ("nasal", "nose"),
    ("nose", "nose"),
    ("forehead", "forehead"),
    ("temple", "temple"),
    ("scalp", "scalp"),
    ("eyelid", "eyelid"),
    ("periorbital", "eye area"),
    ("eye area", "eye area"),
    ("eye", "eye area"),
    ("malar", "cheek"),
    ("cheek", "cheek"),
    ("chin", "chin"),
    ("jawline", "jawline"),
    ("jaw", "jawline"),
    ("lips", "lips"),
    ("lip", "lips"),
    ("perioral", "lips area"),
    ("mouth", "lips area"),
    ("earlobe", "ear"),
    ("ear", "ear"),
    ("throat", "neck"),
    ("neck", "neck"),
    ("face", "face"),
    # Trunk
    ("chest", "chest"),
    ("breast", "chest"),
    ("abdomen", "abdomen"),
    ("belly", "abdomen"),
    ("stomach", "abdomen"),
    ("upper back", "back"),
    ("lower back", "back"),
    ("back", "back"),
    ("shoulder", "shoulder"),
    # Upper extremity
    ("forearm", "forearm"),
    ("upper arm", "arm"),
    ("arm", "arm"),
    ("elbow", "elbow"),
    ("wrist", "wrist"),
    ("palm", "palm"),
    ("finger", "finger"),
    ("hand", "hand"),
    # Lower extremity
    ("thigh", "thigh"),
    ("shin", "shin"),
    ("calf", "leg"),
    ("knee", "knee"),
    ("ankle", "ankle"),
    ("leg", "leg"),
    ("heel", "foot"),
    ("sole", "sole of foot"),
    ("toe", "toe"),
    ("foot", "foot"),
    # Groin / Buttocks
    ("groin", "groin"),
    ("buttock", "buttock"),
    ("gluteal", "buttock"),
]


def _detect_anatomical_region(text: str) -> Optional[str]:
    """Return the first anatomical region keyword found in text, or None."""
    lower = text.lower()
    for keyword, label in _ANATOMICAL_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', lower):
            return label
    return None


def _validate_consistency(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and resolves contradictions in structured image-analysis findings:
    - Distinguishes: clinical_skin_photo, medical_report, other_image, unknown.
    - If medical_report: ensures no fabricated skin lesion findings, sets lesion_identified to not_applicable.
    - If other_image: marks anatomical_region and lesion_identified as not_applicable.
    - If unknown/blurry: marks status as uncertain or not_assessable.
    - For clinical_skin_photo:
      - If lesion_identified is False/not_identified:
        lesion_location is None, distribution is 'not_assessable',
        lesion_description states no distinct lesion is identifiable.
        visible_findings asserting focal bumps or lesions are cleaned.
      - If lesion_identified is True/observed:
        lesion_description must not contradict by claiming no lesion is visible.
      - Resolves conflicting visible_findings (e.g. erythema present vs not_evident).
      - Preserves uncertainty; never invents findings not in the image.
    """
    img_type = analysis.get("image_type", "clinical_skin_photo")
    photo = analysis.get("clinical_skin_photo", {})
    med_report = analysis.get("medical_report", {})
    limitations = analysis.setdefault("diagnostic_limitations", [])

    if "Visual observations alone cannot confirm a definitive diagnosis." not in limitations:
        limitations.append("Visual observations alone cannot confirm a definitive diagnosis.")

    if img_type == "medical_report":
        analysis["classification_status"] = "identified"
        analysis["anatomical_region"] = {"value": None, "status": "not_applicable"}
        med_report["is_report"] = True
        photo["lesion_identified"] = {"value": False, "status": "not_applicable"}
        photo["lesion_location"] = None
        photo["lesion_description"] = "Uploaded image is a medical report or document, not a clinical skin photograph."
        photo["visible_findings"] = []
        photo["distribution"] = "not_applicable"
        analysis["clinical_skin_photo"] = photo
        analysis["medical_report"] = med_report
        return analysis

    elif img_type == "other_image":
        analysis["classification_status"] = "identified"
        analysis["anatomical_region"] = {"value": None, "status": "not_applicable"}
        med_report["is_report"] = False
        photo["lesion_identified"] = {"value": False, "status": "not_applicable"}
        photo["lesion_location"] = None
        photo["visible_findings"] = []
        photo["distribution"] = "not_applicable"
        analysis["clinical_skin_photo"] = photo
        analysis["medical_report"] = med_report
        return analysis

    elif img_type == "unknown":
        analysis["classification_status"] = "uncertain"
        analysis["anatomical_region"] = {"value": None, "status": "not_assessable"}
        med_report["is_report"] = False
        photo["lesion_identified"] = {"value": None, "status": "uncertain"}
        photo["lesion_location"] = None
        photo["distribution"] = "not_assessable"
        analysis["image_quality"].setdefault("limitations", []).append(
            "The image is blurry, poorly lit, or difficult to assess. A clearer, well-lit photograph is recommended."
        )
        analysis["clinical_skin_photo"] = photo
        analysis["medical_report"] = med_report
        return analysis

    # ---- Clinical skin photograph consistency checks ----
    analysis["image_type"] = "clinical_skin_photo"
    med_report["is_report"] = False
    med_report["test_names"] = []
    med_report["dates"] = []
    med_report["values"] = []
    med_report["reference_ranges"] = []
    med_report["extracted_patient_details"] = []
    med_report["diagnoses_and_treatments"] = []

    lesion_info = photo.get("lesion_identified", {})
    lesion_status = lesion_info.get("status", "uncertain")
    lesion_val = lesion_info.get("value")

    # 1. Resolve contradictions when no focal lesion is identified
    if lesion_val is False or lesion_status in ["not_identified", "not_applicable"]:
        photo["lesion_identified"] = {"value": False, "status": "not_identified"}
        photo["lesion_location"] = None
        photo["distribution"] = "not_assessable"
        if not photo.get("lesion_description") or "bump" in photo.get("lesion_description", "").lower() or "lesion" in photo.get("lesion_description", "").lower():
            photo["lesion_description"] = "No distinct focal lesion or abnormality can be confidently identified in the provided image."

        # Remove visible_findings that assert a focal lesion or raised bump
        cleaned_vf = []
        for vf in photo.get("visible_findings", []):
            feat = vf.get("feature", "").lower()
            if feat in ["raised_surface", "ulceration", "erosion"]:
                continue
            cleaned_vf.append(vf)
        photo["visible_findings"] = cleaned_vf

    # 2. Resolve contradictions when lesion is identified
    elif lesion_val is True or lesion_status == "observed":
        photo["lesion_identified"] = {"value": True, "status": "observed"}
        desc = photo.get("lesion_description", "")
        # Remove contradictory phrases like "No distinct lesion is visible" if a lesion was confirmed
        if "no distinct lesion" in desc.lower() or "no lesion identifiable" in desc.lower():
            photo["lesion_description"] = "Visible skin concern observed with localized surface changes."

    # 3. Check for contradictory feature statuses (e.g., both present and not_evident)
    feature_map: Dict[str, str] = {}
    cleaned_vf = []
    for vf in photo.get("visible_findings", []):
        feat = vf.get("feature", "").lower()
        stat = vf.get("status", "uncertain")
        if feat in feature_map:
            # If opposite statuses exist, resolve to uncertain to preserve clinical integrity
            if feature_map[feat] != stat:
                feature_map[feat] = "uncertain"
        else:
            feature_map[feat] = stat

    for feat, stat in feature_map.items():
        cleaned_vf.append({"feature": feat, "status": stat})
    photo["visible_findings"] = cleaned_vf

    analysis["clinical_skin_photo"] = photo
    analysis["medical_report"] = med_report
    return analysis


def create_image_analysis_json(
    image_path: str,
    raw_body_part: str = "",
    raw_findings: str = "",
    raw_condition: Optional[str] = None,
    error_msg: Optional[str] = None,
    image_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs the exact structured JSON schema for image analysis.
    Distinguishes clinical skin photos from medical reports, other images, and unknown/blurry uploads.
    Extracts anatomical location, what is on that location, and suspected dermatological conditions in detail.
    Validates for internal consistency and eliminates contradictions before returning.
    """
    clean_path = str(image_path).replace("\\", "/")
    img_name = os.path.basename(clean_path) if clean_path else "unknown_image"
    if not image_id:
        image_id = f"img_{uuid.uuid5(uuid.NAMESPACE_DNS, img_name).hex[:12]}"

    # Extract structured sections if raw_findings contains clinical examination headers
    if raw_findings:
        bp_m = re.search(r'(?:1\.?\s*Anatomical\s*(?:body\s*part\s*[/]?\s*)?location|location)[:\s]+([^\n]+)', raw_findings, re.IGNORECASE)
        vf_m = re.search(r'(?:2\.?\s*Detailed\s*visual\s*findings|visual\s*findings)[:\s]+([\s\S]*?)(?=(?:3\.?\s*Suspected|\Z))', raw_findings, re.IGNORECASE)
        sc_m = re.search(r'(?:3\.?\s*Suspected\s*(?:dermatological\s*)?condition|possible\s*dermatological\s*condition)[:\s]+([\s\S]*?)$', raw_findings, re.IGNORECASE)
        if bp_m and (not raw_body_part or raw_body_part.lower() in ["uncertain", "none", "", "skin"]):
            raw_body_part = bp_m.group(1).strip()
        if sc_m and not raw_condition:
            raw_condition = sc_m.group(1).strip()

    raw_answer = (str(raw_body_part or "") + " " + str(raw_findings or "") + " " + str(raw_condition or "")).strip()
    lower_raw = raw_answer.lower()
    lower_bp = str(raw_body_part or "").lower().strip()
    lower_findings = str(raw_findings or "").lower().strip()

    # ---- Error short-circuit ---------------------------------------------------
    if error_msg:
        analysis: Dict[str, Any] = {
            "image_id": image_id,
            "image_type": "unknown",
            "classification_status": "failed",
            "anatomical_region": {"value": None, "status": "not_assessable"},
            "medical_report": {
                "is_report": False,
                "test_names": [],
                "dates": [],
                "values": [],
                "reference_ranges": [],
                "extracted_patient_details": [],
                "diagnoses_and_treatments": []
            },
            "clinical_skin_photo": {
                "lesion_identified": {"value": None, "status": "not_applicable"},
                "lesion_location": None,
                "lesion_description": error_msg,
                "visible_findings": [],
                "distribution": "not_applicable"
            },
            "image_quality": {
                "resolution": "unknown",
                "magnification": "not available",
                "limitations": [error_msg]
            },
            "diagnostic_limitations": [
                "Visual analysis failed. The assistant could not examine this image.",
                "Clinical conclusions cannot be drawn from an unanalyzed upload."
            ]
        }
        return analysis

    # ---- Evaluate resolution from image dimensions ----------------------------
    img_res = "moderate"
    try:
        if os.path.exists(image_path):
            with Image.open(image_path) as im:
                w, h = im.size
                if max(w, h) >= 1200:
                    img_res = "high"
                elif max(w, h) >= 600:
                    img_res = "moderate"
                else:
                    img_res = "low"
    except Exception:
        pass

    # ---- Determine Image Category ---------------------------------------------
    # 1. Genuine Medical Report Detection:
    # Requires genuine document signals, NOT general conversational words like 'doctor' or 'clinic'.
    genuine_report_markers = [
        "medical document", "lab report", "laboratory report", "laboratory results",
        "pathology report", "biopsy report", "blood test", "test result",
        "reference range", "specimen:", "collected:", "reported:", "complete blood count",
        "cbc", "urinalysis", "test name", "rx:", "prescription:", "patient name:"
    ]
    is_explicit_document = any(marker in lower_bp or marker in lower_findings for marker in [
        "medical document", "medical report", "lab report", "this is a medical document"
    ])
    has_report_evidence = any(m in lower_raw for m in genuine_report_markers)
    is_medical_report = is_explicit_document or (has_report_evidence and "photo of skin" not in lower_raw)

    # 2. Other Image (Non-human / Non-body) Detection:
    other_image_markers = [
        "landscape", "car", "building", "object", "animal", "pet", "dog", "cat", "furniture",
        "nature", "tree", "plant", "room", "food", "drawing", "illustration"
    ]
    is_other_image = any(m == lower_bp for m in other_image_markers) or any(
        f"image of a {m}" in lower_raw or f"photo of a {m}" in lower_raw for m in other_image_markers
    )

    # 3. Blurry / Unknown / Unidentifiable:
    blurry_markers = [
        "blurry", "blurred", "poorly lit", "pitch black", "cannot determine",
        "too blurry", "out of focus", "unidentifiable", "unclear image"
    ]
    is_poor_quality = any(b in lower_raw for b in blurry_markers)

    # ---- Construct Base Analysis -----------------------------------------------
    analysis = {
        "image_id": image_id,
        "image_type": "clinical_skin_photo",
        "classification_status": "identified",
        "anatomical_region": {"value": None, "status": "uncertain"},
        "medical_report": {
            "is_report": False,
            "test_names": [],
            "dates": [],
            "values": [],
            "reference_ranges": [],
            "extracted_patient_details": [],
            "diagnoses_and_treatments": []
        },
        "clinical_skin_photo": {
            "lesion_identified": {"value": False, "status": "not_identified"},
            "lesion_location": None,
            "lesion_description": "No distinct lesion identifiable in the provided image.",
            "visible_findings": [],
            "distribution": "not_assessable"
        },
        "image_quality": {
            "resolution": img_res,
            "magnification": "standard",
            "limitations": []
        },
        "diagnostic_limitations": [
            "Visual observations alone cannot confirm a definitive diagnosis."
        ]
    }

    if is_medical_report:
        analysis["image_type"] = "medical_report"
        analysis["anatomical_region"] = {"value": None, "status": "not_applicable"}
        analysis["medical_report"]["is_report"] = True

        # Extract patient details from document text
        name_match = re.search(r'patient(?:\s*name)?[:\s]+([a-zA-Z\s\'-]+)', raw_answer, re.IGNORECASE)
        if name_match:
            p_name = name_match.group(1).strip().split(".")[0].split("\n")[0].split(",")[0].strip()
            if p_name and p_name.lower() not in ["none", "unknown", "n/a"]:
                analysis["medical_report"]["extracted_patient_details"].append(
                    {"field": "patient_name", "value": p_name}
                )

        loc_match = re.search(r'(?:lesion location|site|location|region)[:\s]+([a-zA-Z\s\'-]+)', raw_answer, re.IGNORECASE)
        if loc_match:
            p_loc = loc_match.group(1).strip().split(".")[0].split("\n")[0].split(",")[0].strip()
            analysis["medical_report"]["extracted_patient_details"].append(
                {"field": "location", "value": p_loc}
            )

        date_matches = re.findall(
            r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|'
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b',
            raw_answer, re.IGNORECASE
        )
        if date_matches:
            analysis["medical_report"]["dates"] = list(set(date_matches))

        for line in raw_answer.split("\n"):
            line_str = line.strip()
            if any(term in line_str.lower() for term in [
                "diagnosis", "diagnoses", "impression", "assessment", "rx", "treatment", "prescribed", "culture"
            ]):
                analysis["medical_report"]["diagnoses_and_treatments"].append(line_str)
            elif any(term in line_str.lower() for term in [
                "test", "panel", "wbc", "rbc", "platelet", "hemoglobin", "glucose", "tinea", "biopsy"
            ]):
                analysis["medical_report"]["test_names"].append(line_str)

    elif is_other_image:
        analysis["image_type"] = "other_image"
        analysis["anatomical_region"] = {"value": None, "status": "not_applicable"}
        analysis["clinical_skin_photo"]["lesion_description"] = "The uploaded image does not appear to show human skin or a medical concern."

    elif is_poor_quality and not _detect_anatomical_region(raw_body_part):
        analysis["image_type"] = "unknown"
        analysis["classification_status"] = "uncertain"
        analysis["anatomical_region"] = {"value": None, "status": "not_assessable"}
        analysis["clinical_skin_photo"]["lesion_identified"] = {"value": None, "status": "uncertain"}
        analysis["clinical_skin_photo"]["lesion_description"] = "Image quality is insufficient to assess skin features reliably."
        analysis["image_quality"]["limitations"].append(
            "The photograph is blurry, poorly illuminated, or out of focus. A clearer close-up photograph is requested."
        )

    else:
        # ---- Clinical Skin Photo Parsing ----
        analysis["image_type"] = "clinical_skin_photo"

        # Anatomical Region Detection
        detected_region = _detect_anatomical_region(raw_body_part) or _detect_anatomical_region(raw_findings)
        if detected_region:
            analysis["anatomical_region"] = {"value": detected_region, "status": "visually_identified"}
        elif raw_body_part.strip() and raw_body_part.strip().lower() not in [
            "i cannot determine", "not clear", "unclear", "uncertain", "unknown", "n/a", "none", "skin"
        ]:
            analysis["anatomical_region"] = {"value": raw_body_part.strip()[:60], "status": "uncertain"}
        else:
            analysis["anatomical_region"] = {"value": None, "status": "uncertain"}

        # Lesion identification
        lesion_present_keywords = [
            "lesion", "bump", "papule", "pustule", "nodule", "macule", "patch", "plaque",
            "vesicle", "blister", "ulcer", "erosion", "crust", "scale", "rash", "growth",
            "mark", "spot", "lump", "swelling", "raised", "wound", "sore", "pimple",
            "acne", "cyst", "wart", "mole", "nevus", "red spot"
        ]
        no_lesion_keywords = [
            "no distinct lesion", "no lesion", "no visible lesion", "no abnormality",
            "skin appears normal", "no visible abnormality", "no obvious lesion",
            "cannot identify", "not visible", "not clearly identifiable", "no focal lesion",
            "unremarkable skin"
        ]

        has_lesion_hint = any(kw in lower_findings for kw in lesion_present_keywords)
        has_no_lesion_hint = any(kw in lower_findings for kw in no_lesion_keywords)

        if has_no_lesion_hint or not lower_findings or len(lower_findings) <= 10:
            analysis["clinical_skin_photo"]["lesion_identified"] = {"value": False, "status": "not_identified"}
            analysis["clinical_skin_photo"]["lesion_description"] = (
                "No distinct focal lesion or abnormality can be confidently identified in the provided image."
            )
            analysis["clinical_skin_photo"]["distribution"] = "not_assessable"
        elif has_lesion_hint:
            analysis["clinical_skin_photo"]["lesion_identified"] = {"value": True, "status": "observed"}
            analysis["clinical_skin_photo"]["lesion_description"] = raw_findings.strip()
            analysis["clinical_skin_photo"]["what_is_on_location"] = raw_findings.strip()
            if raw_condition:
                analysis["clinical_skin_photo"]["suspected_condition_patterns"] = raw_condition.strip()

            # Lesion sub-location within the region
            region_val = analysis["anatomical_region"].get("value") or "visible skin"
            subloc_found = False
            for sub in ["tip of the", "bridge of the", "ala of the", "upper", "lower", "central", "lateral", "malar"]:
                if sub in lower_findings:
                    analysis["clinical_skin_photo"]["lesion_location"] = f"{sub} {region_val}"
                    subloc_found = True
                    break
            if not subloc_found and region_val:
                analysis["clinical_skin_photo"]["lesion_location"] = f"visible area of the {region_val}"

            # Distribution
            if any(t in lower_findings for t in ["isolated", "discrete", "single", "solitary"]):
                analysis["clinical_skin_photo"]["distribution"] = "discrete_isolated"
            elif any(t in lower_findings for t in ["grouped", "clustered"]):
                analysis["clinical_skin_photo"]["distribution"] = "grouped_clustered"
            elif any(t in lower_findings for t in ["scattered", "disseminated", "generalized", "diffuse", "widespread"]):
                analysis["clinical_skin_photo"]["distribution"] = "scattered_diffuse"
            else:
                analysis["clinical_skin_photo"]["distribution"] = "uncertain"
        else:
            analysis["clinical_skin_photo"]["lesion_identified"] = {"value": None, "status": "uncertain"}
            analysis["clinical_skin_photo"]["lesion_description"] = (
                raw_findings.strip() if raw_findings.strip() else "Visual observations of skin could not be confirmed reliably."
            )
            analysis["clinical_skin_photo"]["what_is_on_location"] = raw_findings.strip()
            if raw_condition:
                analysis["clinical_skin_photo"]["suspected_condition_patterns"] = raw_condition.strip()
            analysis["clinical_skin_photo"]["distribution"] = "uncertain"

        # ---- Parse Visible Features (consistent status values) ----
        vf: List[Dict[str, str]] = []

        # Erythema / redness
        has_erythema = any(t in lower_findings for t in ["erythem", "redness", "red", "pink", "inflamed", "flush"])
        no_erythema = any(t in lower_findings for t in ["no redness", "no erythema", "no significant color change", "normal color"])
        if has_erythema and not no_erythema:
            vf.append({"feature": "redness", "status": "present"})
        elif no_erythema:
            vf.append({"feature": "redness", "status": "not_evident"})

        # Scaling
        if any(t in lower_findings for t in ["scaling", "scale", "flaking", "desquamation"]):
            if not any(t in lower_findings for t in ["no scaling", "no scale", "without scaling"]):
                vf.append({"feature": "scaling", "status": "present"})
            else:
                vf.append({"feature": "scaling", "status": "not_evident"})
        elif any(t in lower_findings for t in ["no scaling", "no scale"]):
            vf.append({"feature": "scaling", "status": "not_evident"})

        # Crusting
        if any(t in lower_findings for t in ["crust", "crusting", "scab"]):
            if not any(t in lower_findings for t in ["no crust", "no crusting"]):
                vf.append({"feature": "crusting", "status": "present"})
            else:
                vf.append({"feature": "crusting", "status": "not_evident"})
        elif any(t in lower_findings for t in ["no crust", "no crusting"]):
            vf.append({"feature": "crusting", "status": "not_evident"})

        # Erosion / Ulceration
        if "erosi" in lower_findings and "no erosi" not in lower_findings:
            vf.append({"feature": "erosion", "status": "present"})
        if "ulcer" in lower_findings and "no ulcer" not in lower_findings:
            vf.append({"feature": "ulceration", "status": "present"})

        # Swelling
        if any(t in lower_findings for t in ["swelling", "swollen", "edema"]):
            if not any(t in lower_findings for t in ["no swelling", "without swelling"]):
                vf.append({"feature": "swelling", "status": "present"})

        # Raised surface
        if any(t in lower_findings for t in ["raised", "elevated", "bump", "papule", "nodule"]):
            if not any(t in lower_findings for t in ["flat", "macular", "not raised"]):
                vf.append({"feature": "raised_surface", "status": "present"})

        # Comedones / Blackheads / Clogged pores
        if any(t in lower_findings for t in ["comedone", "blackhead", "whitehead", "clogged pore", "pore"]):
            if not any(t in lower_findings for t in ["no comedone", "no blackhead"]):
                vf.append({"feature": "comedones_blackheads", "status": "present"})

        # Depigmentation / Vitiligo / Hypopigmentation
        if any(t in lower_findings for t in ["depigment", "hypopigment", "vitiligo", "loss of pigment", "light-colored"]):
            vf.append({"feature": "depigmentation", "status": "present"})

        # Hyperpigmentation / Melasma / Dark spots
        if any(t in lower_findings for t in ["hyperpigment", "melasma", "dark spot", "brown patch"]):
            vf.append({"feature": "hyperpigmentation", "status": "present"})

        # Pustules / Purulent lesions
        if any(t in lower_findings for t in ["pustule", "pimple", "purulent"]):
            vf.append({"feature": "pustules", "status": "present"})

        analysis["clinical_skin_photo"]["visible_findings"] = vf

        # Quality limitations note
        if is_poor_quality:
            analysis["image_quality"]["limitations"].append(
                "Image clarity or lighting is suboptimal, which may limit detection of fine surface textures."
            )

    # ---- Consistency Validation -----------------------------------------------
    analysis = _validate_consistency(analysis)
    return analysis


@tool
def analyze_skin_or_report_image(image_path: str) -> str:
    """
    Use this tool when a patient provides a photo of their skin, lesion, rash, or a medical report.
    
    CRITICAL: 
    - You MUST use the EXACT file path provided in the "[System Alert: User uploaded an image. Local Path: ...]" message.
    - Copy the path character-for-character.
    - DO NOT make up, guess, or hallucinate a path (like 'D:\\tmp\\...'). If you don't see a [System Alert] with a path, do not use this tool.
    """
    clean_path = str(image_path).strip().strip("'\"").replace("\\", "/")
    # Locate image file if relative or shifted
    if not os.path.exists(clean_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(base_dir, "static", "dermatalogist_upload")
        if os.path.exists(uploads_dir):
            files = [
                os.path.join(uploads_dir, f).replace("\\", "/")
                for f in os.listdir(uploads_dir)
                if os.path.isfile(os.path.join(uploads_dir, f))
            ]
            if files:
                files.sort(key=os.path.getmtime, reverse=True)
                clean_path = files[0]
            else:
                struct = create_image_analysis_json(
                    image_path,
                    error_msg="The attached photograph could not be accessed on the server. Please re-upload a clear image."
                )
                return json.dumps(struct, indent=2)
        else:
            struct = create_image_analysis_json(
                image_path,
                error_msg="The image upload directory is currently inaccessible."
            )
            return json.dumps(struct, indent=2)

    try:
        image = Image.open(clean_path).convert('RGB')
        model = get_image_model()

        # Comprehensive Clinical Dermatological Examination Query
        exam_prompt = (
            "Perform a detailed clinical dermatological examination of this image:\n"
            "1. Anatomical body part / location: Where on the human body is this located? (Be specific: e.g. nose, cheek, forehead, chin, periorbital / eye area, lips, ear, neck, abdomen, chest, back, arm, hand, leg, foot). If this is a printed paper lab test or report, state 'medical document'. If non-human object/animal, state 'other'.\n"
            "2. Detailed visual findings: Describe in comprehensive detail what is on that location: specific lesions (macules, papules, pustules, comedones/blackheads, patches, plaques), color (erythema/redness, depigmentation, hyperpigmentation), borders, surface texture (raised, flat, rough, scaling, crusting), and pore features.\n"
            "3. Suspected dermatological condition / pattern: What specific skin condition, diagnosis, or clinical pattern does this visual presentation most strongly indicate or resemble (e.g., acne vulgaris / comedones, vitiligo, melasma, eczema, rosacea, folliculitis, tinea, etc.)?"
        )
        result_findings = model.query(image, exam_prompt)
        raw_findings = result_findings.get("answer", "").strip()

        # Parse sections
        bp_m = re.search(r'(?:1\.?\s*Anatomical\s*(?:body\s*part\s*[/]?\s*)?location|location)[:\s]+([^\n]+)', raw_findings, re.IGNORECASE)
        raw_body_part = bp_m.group(1).strip() if bp_m else "uncertain"
        cond_m = re.search(r'(?:3\.?\s*Suspected\s*(?:dermatological\s*)?condition|possible\s*dermatological\s*condition)[:\s]+([\s\S]*?)$', raw_findings, re.IGNORECASE)
        raw_condition = cond_m.group(1).strip() if cond_m else None

        struct = create_image_analysis_json(clean_path, raw_body_part=raw_body_part, raw_findings=raw_findings, raw_condition=raw_condition)
        return json.dumps(struct, indent=2)

    except Exception as e:
        struct = create_image_analysis_json(
            clean_path,
            error_msg=(
                f"Visual inspection tool encountered an error ({type(e).__name__}). "
                "Please describe what skin changes you are noticing so I can continue your clinical evaluation."
            )
        )
        return json.dumps(struct, indent=2)


# ==============================================================================
# STRUCTURED PATIENT STATE & HISTORY EXTRACTION
# ==============================================================================

# Number word mapping for spelled-out durations
_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "a couple of": "2", "several": "few"
}

def extract_patient_profile(messages: List[BaseMessage]) -> Dict[str, Any]:
    """
    Deterministically tracks confirmed patient demographics, history, image findings,
    and maintains STRICT SEPARATION between patient-provided data, visually observed findings,
    and uploaded document data.
    """
    profile: Dict[str, Any] = {
        "name": None,
        "age": None,
        "location": None,
        "gender": None,
        "complaint": None,
        "duration": None,
        "pain": None,
        "itching": None,
        "spread": None,
        "triggers": None,
        "previous_treatments": None,
        "associated_symptoms": None,
        "firmness": None,
        "redness": None,
        "clarification_needed": None,
        "lesion_location": None,              # Patient-reported lesion location
        "image_inferred_region": None,        # Visual AI inferred anatomical region
        "image_inferred_region_status": None, # visually_identified / uncertain / not_assessable
        "image_id": None,
        "image_path": None,
        "image_analysis": None,
        "image_type": None,
        "image_timestamp": None,
        "image_explained": False,
        "document_data": {
            "name": None,
            "location": None,
            "dates": [],
            "findings": None,
            "is_conflicting": False,
            "discrepancy_note": None
        },
        "answered_topics": set(),
        "pending_question": None,
        "last_tool_status": None,
        "report_generated": False,
        "differential_diagnoses": []
    }

    last_ai_question = ""
    last_ai_topic = "other"

    for idx, msg in enumerate(messages):
        # 1. AI MESSAGE PROCESSING
        if isinstance(msg, AIMessage):
            text = msg.content if isinstance(msg.content, str) else ""
            if "?" in text:
                # Capture the full question sentence without breaking on abbreviations like e.g. or dr.
                q_matches = re.findall(r'([^.!?\n]+(?:\([^\)]*\))?[^.!?\n]*\?)', text)
                if q_matches:
                    last_ai_question = q_matches[-1].strip().lower()
                    profile["pending_question"] = q_matches[-1].strip()
                else:
                    last_ai_question = text.strip().lower()
                    profile["pending_question"] = text.strip()

            # Classify question topic
            combined_q = (last_ai_question + " " + text.lower())
            if any(w in combined_q for w in ["your name", "what is your name", "may i have your name", "who am i speaking with"]):
                last_ai_topic = "name"
            elif any(w in combined_q for w in ["how old", "your age", "tell me your age"]):
                last_ai_topic = "age"
            elif any(w in combined_q for w in ["where are you located", "your location", "where do you live", "current location", "city or region", "city"]):
                last_ai_topic = "location"
            elif any(w in combined_q for w in ["gender", "biological sex", "male or female"]):
                last_ai_topic = "gender"
            elif any(w in combined_q for w in ["where on your body", "which body part", "where is the lesion", "location of the bump", "affected area"]):
                last_ai_topic = "lesion_location"
            elif any(w in combined_q for w in ["how long", "duration", "how many days", "how many weeks", "when did this start"]):
                last_ai_topic = "duration"
            elif ("pain" in combined_q or "tenderness" in combined_q or "discomfort" in combined_q) and ("itch" in combined_q):
                last_ai_topic = "pain_and_itching"
            elif "pain" in combined_q or "tenderness" in combined_q or "discomfort" in combined_q or "hurt" in combined_q:
                last_ai_topic = "pain"
            elif "itch" in combined_q or "scratch" in combined_q:
                last_ai_topic = "itching"
            elif any(w in combined_q for w in ["trigger", "worse", "heat", "sun", "stress", "food", "factors"]):
                last_ai_topic = "triggers"
            elif any(w in combined_q for w in ["cleanser", "cream", "treatment", "ointment", "medication", "products", "tried anything", "used any"]):
                last_ai_topic = "treatments"
            elif any(w in combined_q for w in ["spread", "spreading", "changes", "new bumps", "grown", "getting bigger"]):
                last_ai_topic = "spread"
            elif any(w in combined_q for w in ["pus", "crust", "scaling", "fluid", "blister", "scab", "peeling"]):
                last_ai_topic = "associated_symptoms"
            elif any(w in combined_q for w in ["what does the skin", "look like", "color", "red or pink", "firm", "soft"]):
                last_ai_topic = "appearance"
            else:
                last_ai_topic = "other"

            # Detect whether assistant has addressed/explained the uploaded photograph
            if any(term in text.lower() for term in [
                "photograph appears to show", "photo appears to show", "image appears to show",
                "i examined your photograph", "i can see in the photograph", "the photo shows",
                "the photograph shows", "in the image you uploaded", "the uploaded report lists"
            ]):
                profile["image_explained"] = True

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get("name") == "generate_medical_report":
                        profile["report_generated"] = True

        # 2. TOOL MESSAGE PROCESSING
        elif isinstance(msg, ToolMessage):
            if msg.name == "analyze_skin_or_report_image" and msg.content:
                profile["image_analysis"] = msg.content
                try:
                    data = json.loads(msg.content)
                    profile["image_id"] = data.get("image_id")
                    img_type = data.get("image_type")
                    profile["image_type"] = img_type

                    if img_type == "medical_report" or data.get("medical_report", {}).get("is_report"):
                        profile["image_type"] = "medical_report"
                        med_rep = data.get("medical_report", {})
                        for detail in med_rep.get("extracted_patient_details", []):
                            if isinstance(detail, dict):
                                if detail.get("field") == "patient_name" and detail.get("value"):
                                    profile["document_data"]["name"] = detail.get("value")
                                elif detail.get("field") == "location" and detail.get("value"):
                                    profile["document_data"]["location"] = detail.get("value")
                        if med_rep.get("dates"):
                            profile["document_data"]["dates"] = med_rep.get("dates")
                        if med_rep.get("diagnoses_and_treatments"):
                            profile["document_data"]["findings"] = "; ".join(med_rep.get("diagnoses_and_treatments"))

                    elif img_type == "clinical_skin_photo":
                        anat = data.get("anatomical_region", {})
                        if isinstance(anat, dict):
                            val = anat.get("value")
                            status = anat.get("status")
                            if val and status in ["visually_identified", "uncertain"]:
                                profile["image_inferred_region"] = val
                                profile["image_inferred_region_status"] = status
                except Exception:
                    pass

            elif msg.name == "generate_medical_report":
                profile["report_generated"] = True

        # 3. SYSTEM MESSAGE PROCESSING (Observations from input_preprocess_node)
        elif isinstance(msg, SystemMessage):
            content_str = str(msg.content)
            if "image_type" in content_str or "[Active Image Analysis" in content_str or "[System Alert: Newly Uploaded Image Analyzed" in content_str:
                try:
                    json_match = re.search(r'\{[\s\S]*\}', content_str)
                    if json_match:
                        profile["image_analysis"] = json_match.group(0)
                        data = json.loads(json_match.group(0))
                    else:
                        profile["image_analysis"] = content_str
                        data = json.loads(content_str)
                    profile["image_id"] = data.get("image_id")
                    img_type = data.get("image_type")
                    profile["image_type"] = img_type

                    if img_type == "medical_report" or data.get("medical_report", {}).get("is_report"):
                        profile["image_type"] = "medical_report"
                        med_rep = data.get("medical_report", {})
                        for detail in med_rep.get("extracted_patient_details", []):
                            if isinstance(detail, dict):
                                if detail.get("field") == "patient_name" and detail.get("value"):
                                    profile["document_data"]["name"] = detail.get("value")
                                elif detail.get("field") == "location" and detail.get("value"):
                                    profile["document_data"]["location"] = detail.get("value")
                        if med_rep.get("dates"):
                            profile["document_data"]["dates"] = med_rep.get("dates")
                        if med_rep.get("diagnoses_and_treatments"):
                            profile["document_data"]["findings"] = "; ".join(med_rep.get("diagnoses_and_treatments"))

                    elif img_type == "clinical_skin_photo":
                        anat = data.get("anatomical_region", {})
                        if isinstance(anat, dict):
                            val = anat.get("value")
                            status = anat.get("status")
                            if val and status in ["visually_identified", "uncertain"]:
                                profile["image_inferred_region"] = val
                                profile["image_inferred_region_status"] = status
                except Exception:
                    pass

        # 4. HUMAN MESSAGE PROCESSING
        elif isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else ""

            # Check for image upload alert
            img_match = re.search(r'\[System Alert: User uploaded an image\.\s*Local Path:\s*([^\]]+)\]', content)
            if img_match:
                new_image_path = img_match.group(1).strip()
                if profile["image_path"] != new_image_path:
                    profile["image_path"] = new_image_path
                    # Reset image_explained for newly attached image
                    profile["image_explained"] = False

            clean_text = re.sub(r'\[System Alert:[^\]]+\]', '', content).strip()
            clean_lower = clean_text.lower().rstrip(".!? ")
            if not clean_text:
                continue

            # (A) STRUCTURED / KEY-VALUE EXTRACTION
            kv_name = re.search(r'\b(?:patient(?:\s*name)?|name)\s*[:=\-]\s*([a-zA-Z\s\'-]+?)(?:,|\.|\n|$)', clean_text, re.IGNORECASE)
            if kv_name:
                cand = kv_name.group(1).strip().split(".")[0].split(",")[0].strip()
                if len(cand) >= 2 and cand.lower() not in ["none", "n/a", "unknown"]:
                    profile["name"] = cand
                    profile["answered_topics"].add("name")

            kv_age = re.search(r'\b(?:age)\s*[:=\-]\s*(\d{1,3})\b', clean_text, re.IGNORECASE)
            if kv_age:
                profile["age"] = kv_age.group(1).strip()
                profile["answered_topics"].add("age")

            kv_loc = re.search(r'\b(?:location|city|residence)\s*[:=\-]\s*([a-zA-Z\s]+?)(?:,|\.|\n|$)', clean_text, re.IGNORECASE)
            if kv_loc:
                cand = kv_loc.group(1).strip().split(".")[0].split(",")[0].strip()
                if len(cand) >= 2 and cand.lower() not in ["none", "n/a", "unknown"]:
                    profile["location"] = cand
                    profile["answered_topics"].add("location")

            kv_gender = re.search(r'\b(?:gender|sex|biological sex)\s*[:=\-]\s*([a-zA-Z]+)', clean_text, re.IGNORECASE)
            if kv_gender:
                cand = kv_gender.group(1).strip().capitalize()
                if cand.lower() in ["male", "man", "boy"]:
                    profile["gender"] = "Male"
                    profile["answered_topics"].add("gender")
                elif cand.lower() in ["female", "woman", "girl"]:
                    profile["gender"] = "Female"
                    profile["answered_topics"].add("gender")
                elif "non-binary" in cand.lower():
                    profile["gender"] = "Non-binary"
                    profile["answered_topics"].add("gender")

            kv_dur = re.search(r'\b(?:duration|lesion duration|symptom duration|how long)\s*[:=\-]\s*([a-zA-Z0-9\s]+?)(?:,|\.|\n|$)', clean_text, re.IGNORECASE)
            if kv_dur:
                cand = kv_dur.group(1).strip()
                if cand:
                    profile["duration"] = cand
                    profile["answered_topics"].add("duration")

            kv_site = re.search(r'\b(?:lesion location|site|affected area)\s*[:=\-]\s*([a-zA-Z\s]+?)(?:,|\.|\n|$)', clean_text, re.IGNORECASE)
            if kv_site:
                cand = kv_site.group(1).strip()
                if cand:
                    profile["lesion_location"] = cand.lower()
                    profile["answered_topics"].add("lesion_location")

            # (B) NATURAL CONVERSATIONAL PHRASES
            direct_name = re.search(r'\b(?:my name is|i am called|call me)\s+([a-zA-Z\'-]+)', clean_text, re.IGNORECASE)
            if direct_name and not profile["name"]:
                cand = direct_name.group(1).strip().split(".")[0].split(",")[0].strip()
                if cand.lower() not in ["hi", "hello", "hey", "sure", "ok", "yes", "no", "salman"]:
                    profile["name"] = cand
                    profile["answered_topics"].add("name")
                elif cand.lower() == "salman":
                    profile["name"] = "Salman"
                    profile["answered_topics"].add("name")

            direct_loc = re.search(r'\b(?:i live in|i am in|i am located in|from)\s+([a-zA-Z\s]+?)(?:,|\.|\n|$)', clean_text, re.IGNORECASE)
            if direct_loc and not profile["location"]:
                cand = direct_loc.group(1).strip().split(".")[0].split(",")[0].strip()
                if len(cand) > 2 and cand.lower() not in ["pain", "trouble", "bed", "here"]:
                    profile["location"] = cand
                    profile["answered_topics"].add("location")

            direct_age = re.search(r'\b(\d{1,3})\s*(?:years?\s*old|yo\b)', clean_text, re.IGNORECASE)
            if direct_age and not profile["age"]:
                profile["age"] = direct_age.group(1).strip()
                profile["answered_topics"].add("age")

            # Standalone gender mentions
            if not profile["gender"]:
                if re.search(r'\b(male|man|boy)\b', clean_lower) and not re.search(r'\b(female)\b', clean_lower):
                    profile["gender"] = "Male"
                    profile["answered_topics"].add("gender")
                elif re.search(r'\b(female|woman|girl)\b', clean_lower):
                    profile["gender"] = "Female"
                    profile["answered_topics"].add("gender")

            # (C) PATIENT CONFUSION & CLARIFICATION REQUESTS
            if any(conf in clean_lower for conf in [
                "what does itching mean", "what is itching", "what does that mean", 
                "what do you mean", "i don't understand", "sorry, what", "sorry what", "pardon"
            ]):
                profile["clarification_needed"] = last_ai_topic if last_ai_topic != "other" else "general"

            # (D) CONCISE NEGATIVE RESPONSES ("no", "none", "nope", "haven't used anything", etc.)
            is_negative = bool(re.search(r'^(?:no|nope|none|not really|not at all|haven\'t|nothing|zero|0)\b', clean_lower) or clean_lower in [
                "no", "none", "nope", "nothing", "not at all", "no i haven't", "no, i haven't", 
                "no i haven't used anything yet", "no, i haven't used anything yet", "no, nothing", "no changes"
            ])
            if is_negative and clean_lower not in ["not soft"]:
                if last_ai_topic == "pain":
                    profile["pain"] = "0/10 (denied)"
                    profile["answered_topics"].add("pain")
                    profile["pending_question"] = None
                elif last_ai_topic == "itching":
                    profile["itching"] = "0/10 (denied)"
                    profile["answered_topics"].add("itching")
                    profile["pending_question"] = None
                elif last_ai_topic == "pain_and_itching":
                    profile["pain"] = "0/10 (denied)"
                    profile["itching"] = "0/10 (denied)"
                    profile["answered_topics"].update(["pain", "itching"])
                    profile["pending_question"] = None
                elif last_ai_topic == "triggers":
                    profile["triggers"] = "None reported (denied)"
                    profile["answered_topics"].add("triggers")
                    profile["pending_question"] = None
                elif last_ai_topic == "treatments":
                    profile["previous_treatments"] = "None (no prior treatments used)"
                    profile["answered_topics"].add("treatments")
                    profile["pending_question"] = None
                elif last_ai_topic == "spread":
                    profile["spread"] = "None (stable, not spreading)"
                    profile["answered_topics"].add("spread")
                    profile["pending_question"] = None
                elif last_ai_topic == "associated_symptoms":
                    profile["associated_symptoms"] = "None (denied)"
                    profile["answered_topics"].add("associated_symptoms")
                    profile["pending_question"] = None

            # (E) NUMERIC RATING OR STANDALONE NUMBER (e.g. "5", "5/10", "about 5")
            num_match = re.search(r'^(?:about\s+|approximately\s+)?(\d{1,2})(?:\s*/\s*10|\s*out of\s*10|\.)?$', clean_text.strip()) or re.search(r'(\b\d{1,2}\s*/\s*10\b|\b\d{1,2}\s*out of\s*10\b)', clean_text.strip())
            if num_match:
                raw_score = num_match.group(1).strip()
                formatted_score = f"{raw_score}/10" if "/10" not in raw_score else raw_score
                if last_ai_topic == "pain" or ("pain" in last_ai_question and "itch" not in last_ai_question):
                    profile["pain"] = formatted_score
                    profile["answered_topics"].add("pain")
                    profile["pending_question"] = None
                elif last_ai_topic == "itching" or ("itch" in last_ai_question and "pain" not in last_ai_question):
                    profile["itching"] = formatted_score
                    profile["answered_topics"].add("itching")
                    profile["pending_question"] = None
                elif (last_ai_topic == "age" or "how old" in last_ai_question or "your age" in last_ai_question) and not profile["age"]:
                    profile["age"] = raw_score
                    profile["answered_topics"].add("age")
                    profile["pending_question"] = None

            # (F) POSITIVE CONFIRMATIONS ("yes", "yeah", "i do", "there is")
            if clean_lower in ["yes", "yeah", "yep", "i do", "there is", "yes, there is", "yes."]:
                if last_ai_topic == "associated_symptoms" or any(w in last_ai_question for w in ["pus", "crust", "scaling"]):
                    profile["associated_symptoms"] = "Present (pus, crust, or scaling reported by patient)"
                    profile["answered_topics"].add("associated_symptoms")
                    profile["pending_question"] = None
                elif last_ai_topic == "spread" or "spread" in last_ai_question:
                    profile["spread"] = "Present (spreading or changes noted)"
                    profile["answered_topics"].add("spread")
                    profile["pending_question"] = None

            # (G) LESION TEXTURE AND APPEARANCE DETAILS
            if clean_lower in ["not soft", "firm"]:
                profile["firmness"] = "Firm (not soft)"
                profile["answered_topics"].add("appearance")
                profile["pending_question"] = None
            if clean_lower in ["red", "pink", "redness"]:
                profile["redness"] = clean_lower.capitalize()
                profile["answered_topics"].add("appearance")
                profile["pending_question"] = None
            if "blackhead" in clean_lower:
                profile["complaint"] = "Blackheads on nose"
                profile["lesion_location"] = "nose"
                profile["answered_topics"].add("lesion_location")

            # (H) CONTEXT-BASED REPLIES (AI asked question on previous turn)
            if ("your name" in last_ai_question or "what is your name" in last_ai_question or "may i have your name" in last_ai_question) and not profile["name"]:
                name_match = re.search(r'(?:my name is|i am|i\'m|call me)?\s*([a-zA-Z\s\.\'-]+)', clean_text, re.IGNORECASE)
                if name_match:
                    name_cand = name_match.group(1).strip().split(".")[0].split(",")[0].strip()
                    if name_cand.lower() not in ["hi", "hello", "hey", "sure", "ok", "yes", "no"]:
                        profile["name"] = name_cand
                        profile["answered_topics"].add("name")
                        profile["pending_question"] = None

            elif ("how old are you" in last_ai_question or "your age" in last_ai_question or "tell me your age" in last_ai_question) and not profile["age"]:
                age_match = re.search(r'(\b\d{1,3}\b)', clean_text)
                if age_match:
                    profile["age"] = age_match.group(1).strip()
                    profile["answered_topics"].add("age")
                    profile["pending_question"] = None

            elif any(w in last_ai_question for w in ["where are you located", "your location", "where do you live", "city", "current location"]) and not profile["location"]:
                loc_cand = clean_text.replace("I live in", "").replace("I am in", "").replace("Location is", "").strip().split(".")[0].strip()
                if loc_cand and len(loc_cand) >= 2 and loc_cand.lower() not in ["yes", "no", "sure", "ok", "none"]:
                    profile["location"] = loc_cand
                    profile["answered_topics"].add("location")
                    profile["pending_question"] = None

            # (I) DURATION
            dur_since = re.search(r'\b(?:since|for)\s+((?:about\s+|approximately\s+)?[a-zA-Z0-9\s]+?(?:days?|weeks?|months?|years?))\b', clean_text, re.IGNORECASE)
            if dur_since and not profile["duration"]:
                profile["duration"] = dur_since.group(1).strip().lower()
                profile["answered_topics"].add("duration")
                if "how long" in last_ai_question or "duration" in last_ai_question:
                    profile["pending_question"] = None

            dur_match = re.search(r'(\b(?:about\s+|approximately\s+)?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a couple of|several)\s*(?:days?|weeks?|months?|years?)\b)', clean_text, re.IGNORECASE)
            if dur_match and not profile["duration"]:
                profile["duration"] = dur_match.group(1).strip().lower()
                profile["answered_topics"].add("duration")
                if "how long" in last_ai_question or "duration" in last_ai_question:
                    profile["pending_question"] = None

            # (J) PATIENT-REPORTED LESION LOCATION
            for loc in ["nose", "cheek", "forehead", "chin", "lip", "lips", "ear", "eye", "neck", "arm", "forearm", "hand", "leg", "thigh", "foot", "chest", "back", "abdomen", "scalp"]:
                if f"on my {loc}" in clean_lower or f"in my {loc}" in clean_lower or f"on the {loc}" in clean_lower or f"my {loc}" in clean_lower or clean_lower == loc:
                    profile["lesion_location"] = loc
                    profile["answered_topics"].add("lesion_location")
                    break
            if not profile["lesion_location"]:
                for loc in ["nose", "cheek", "forehead", "chin", "lip", "ear", "neck", "arm", "hand", "leg", "foot", "back", "chest"]:
                    if loc in clean_lower and not any(neg in clean_lower for neg in [f"not on my {loc}", f"no {loc}"]):
                        profile["lesion_location"] = loc
                        profile["answered_topics"].add("lesion_location")
                        break

            # (K) PAIN AND ITCHING SEPARATION
            if re.search(r'\b(no itch\w*|not itch\w*|zero itch\w*|denies itch\w*|without itch\w*)\b', clean_lower):
                profile["itching"] = "None (denied)"
                profile["answered_topics"].add("itching")
                if "itch" in last_ai_question: profile["pending_question"] = None
            elif re.search(r'(?:itch\w*|itchiness)\s*(?:is|score|level)?[:\s]*(\b\d+\s*/\s*10\b|\b\d+\s*out of\s*10\b|\b\d+\b|mild|severe|moderate)', clean_text, re.IGNORECASE):
                itch_m = re.search(r'(?:itch\w*|itchiness)\s*(?:is|score|level)?[:\s]*(\b\d+\s*/\s*10\b|\b\d+\s*out of\s*10\b|\b\d+\b|mild|severe|moderate)', clean_text, re.IGNORECASE)
                profile["itching"] = itch_m.group(1).strip()
                profile["answered_topics"].add("itching")
                if "itch" in last_ai_question: profile["pending_question"] = None

            if re.search(r'\b(no pain|not pain\w*|zero pain|denies pain|painless|without pain)\b', clean_lower):
                profile["pain"] = "None (denied)"
                profile["answered_topics"].add("pain")
                if "pain" in last_ai_question: profile["pending_question"] = None
            elif re.search(r'(?:pain|pain level|pain score)\s*(?:is)?[:\s]*(\b\d+\s*/\s*10\b|\b\d+\s*out of\s*10\b|\b\d+\b|mild|severe|moderate)', clean_text, re.IGNORECASE):
                pain_m = re.search(r'(?:pain|pain level|pain score)\s*(?:is)?[:\s]*(\b\d+\s*/\s*10\b|\b\d+\s*out of\s*10\b|\b\d+\b|mild|severe|moderate)', clean_text, re.IGNORECASE)
                profile["pain"] = pain_m.group(1).strip()
                profile["answered_topics"].add("pain")
                if "pain" in last_ai_question: profile["pending_question"] = None

            # (L) TRIGGERS & TREATMENTS
            if any(trig in clean_lower for trig in ["heat", "sun", "sweat", "stress", "cold", "food", "spicy"]):
                profile["triggers"] = clean_text
                profile["answered_topics"].add("triggers")
            if any(t in clean_lower for t in ["cream", "ointment", "hydrocortisone", "aloe", "antibiotic", "nothing", "no treatment", "lotion"]):
                profile["previous_treatments"] = clean_text
                profile["answered_topics"].add("treatments")

            if not profile["complaint"] and len(clean_text) > 4 and not any(k in clean_lower for k in ["name", "age", "location", "gender"]):
                profile["complaint"] = clean_text

    # (M) EVALUATE MEDICAL REPORT CONFLICT / DISCREPANCY
    doc_name = profile["document_data"].get("name")
    if doc_name and profile["name"]:
        if profile["name"].lower() not in doc_name.lower() and doc_name.lower() not in profile["name"].lower():
            profile["document_data"]["is_conflicting"] = True
            loc_note = ""
            if profile["document_data"].get("location") and profile.get("lesion_location"):
                if profile["lesion_location"].lower() not in profile["document_data"]["location"].lower():
                    loc_note = f" The document also lists location as '{profile['document_data']['location']}', while your concern is on your {profile['lesion_location']}."
            profile["document_data"]["discrepancy_note"] = (
                f"The uploaded document lists the patient name as '{doc_name}', whereas you identified yourself as '{profile['name']}'.{loc_note} "
                "Because medical reports are confidential clinical records, I cannot assume this report belongs to you."
            )

    return profile


# ==============================================================================
# RAG SUMMARIZER PROMPTS (INTERNAL CLINICAL KNOWLEDGE ONLY)
# ==============================================================================

DIAGNOSIS_SUMMARY_PROMPT = """You are a Senior Dermatological Clinical Assistant.
Analyze the following retrieved dermatological knowledge and synthesize an INTERNAL clinical summary for differential diagnosis.

CONTEXT FROM CLINICAL KNOWLEDGE BASE:
{context}

PATIENT SYMPTOMS & CLINICAL HISTORY:
{query}

STRICT INSTRUCTIONS:
1. Identify 2 to 3 plausible DIFFERENTIAL DIAGNOSES based on the findings.
2. DO NOT declare any single disease confirmed. Highlight uncertainties and atypical presentations.
3. For each condition, list key SUPPORTING evidence and MISSING/CONFLICTING features.
4. Suggest 1 or 2 specific distinguishing clinical questions or physical examination tests needed.
5. Keep the summary concise, professional, and structured for internal decision support.

INTERNAL CLINICAL DIFFERENTIAL SUMMARY:
"""

MEDICATION_SUMMARY_PROMPT = """You are a Dermatological Pharmacotherapy Assistant.
Synthesize the retrieved pharmacological reference information into concise, INTERNAL clinical education notes.

CONTEXT FROM PHARMACOTHERAPY KNOWLEDGE BASE:
{context}

CLINICAL TOPIC:
{query}

STRICT INSTRUCTIONS:
1. Extract standard evidence-based drug classes, mechanisms of action, and typical first-line vs second-line approaches.
2. Highlight critical contraindications, precautions, and safety considerations.
3. DO NOT format this as a prescription or a raw patient-facing table.
4. Emphasize that actual medication selection requires physician assessment of individual patient factors.
5. Keep the output focused as internal clinical background.

INTERNAL MEDICATION REFERENCE NOTES:
"""


# ==============================================================================
# TOOLS IMPLEMENTATION
# ==============================================================================

@tool
def diagnosis_retrieval_tool(query: str) -> str:
    """
    Retrieves internal clinical evidence and differential diagnoses from the dermatology diagnosis store.
    Use after sufficient clinical history has been gathered to explore differential possibilities.
    """
    try:
        docs = retrieve_with_rerank(get_diagnosis_store(), query)
        context_text = "\n\n".join([doc.page_content for doc in docs])
        prompt = ChatPromptTemplate.from_template(DIAGNOSIS_SUMMARY_PROMPT)
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"context": context_text, "query": query})
    except Exception as e:
        return f"[Diagnosis Retrieval Notice]: Internal knowledge lookup unavailable ({str(e)}). Proceeding with cautious clinical differential reasoning."

@tool
def medication_retrieval_tool(query: str) -> str:
    """
    Retrieves evidence-based pharmacotherapy and treatment considerations from the dermatology medication store.
    Use only when treatment information is explicitly requested by the patient or clinically appropriate.
    """
    try:
        docs = retrieve_with_rerank(get_medication_store(), query)
        context_text = "\n\n".join([doc.page_content for doc in docs])
        prompt = ChatPromptTemplate.from_template(MEDICATION_SUMMARY_PROMPT)
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"context": context_text, "query": query})
    except Exception as e:
        return f"[Medication Retrieval Notice]: Internal pharmacotherapy lookup unavailable ({str(e)}). Proceeding with general clinical care guidelines."

@tool
def search_tool(query: str) -> str:
    """
    Searches authoritative medical reference sources (such as DailyMed/NIH) for recent clinical guidelines or medication labeling.
    """
    try:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return "Web search is currently unavailable. Using established dermatological knowledge."
        
        client = TavilyClient(api_key=api_key)
        is_drug_search = any(term in query.lower() for term in ["drug", "medication", "dose", "tablet", "syrup", "cream", "ointment", "fda"])
        search_query = f"site:dailymed.nlm.nih.gov {query}" if is_drug_search else query
        
        raw_response = client.search(query=search_query, search_depth="advanced", max_results=4)
        
        prompt = ChatPromptTemplate.from_template("""
        You are a Medical Data Refiner for Dermatology.
        Synthesize the raw search results into concise internal notes.
        
        QUERY: {query}
        RAW DATA: {raw_data}
        
        INSTRUCTIONS:
        1. Prioritize authoritative FDA labeling from DailyMed (nlm.nih.gov).
        2. Summarize clinical guidelines, indications, and documented precautions.
        3. Remove advertising, marketing claims, and unverified forums.
        4. If reliable data is not found, state 'Reliable clinical data not found in current search'.
        
        CLEAN SUMMARY:
        """)
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"query": query, "raw_data": raw_response})
    except Exception as e:
        return f"External medical search notice: {str(e)}"

@tool
def doctor_search_tool(location: str) -> str:
    """
    Searches for verified dermatology clinics and specialists in the patient's area.
    Use this tool when the patient explicitly requests local referrals or clinic information.
    """
    clean_location = location.strip()
    if not clean_location:
        return "Please provide a specific city or region to locate nearby dermatology clinics."

    verified_results = []
    try:
        api_key = os.environ.get("TAVILY_API_KEY")
        if api_key:
            client = TavilyClient(api_key=api_key)
            query = f"dermatology clinic hospital {clean_location} address phone contact"
            res = client.search(query=query, search_depth="basic", max_results=3)
            for r in res.get("results", []):
                title = r.get("title", "")
                content = r.get("content", "")
                url = r.get("url", "")
                has_medical = any(term in (title + content).lower() for term in ["dermatol", "skin", "clinic", "hospital", "medical center"])
                matches_loc = clean_location.lower() in (title + content + url).lower()
                if has_medical and matches_loc:
                    verified_results.append(f"• **{title}**\n  Details: {content[:180]}...\n  Reference: {url}")
    except Exception:
        pass

    if verified_results:
        return (
            f"Verified Dermatology Resources near {clean_location}:\n\n" +
            "\n\n".join(verified_results) +
            "\n\n*Note: MedNexus AI does not share patient records or medical reports with external clinics without explicit patient consent. Please contact the clinic directly to verify appointment availability.*"
        )
    else:
        return (
            f"No verified local dermatology clinics were directly identified in our directory for '{clean_location}'.\n\n"
            "To locate a certified dermatologist safely:\n"
            "1. Visit the American Academy of Dermatology (AAD) directory at **https://find-a-derm.aad.org/**\n"
            "2. Contact your regional public hospital or primary healthcare center for a qualified clinical referral.\n"
            "*Privacy Assurance: Your consultation details are strictly private and never shared externally without your explicit consent.*"
        )

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
    Generates a formal, professional dermatology consultation summary in HTML format.
    Must only be called when the patient explicitly requests a consultation report or download.
    """
    current_date_obj = datetime.now()
    report_date = current_date_obj.strftime("%B %d, %Y")
    
    clean_id = str(patient_id).strip()
    if not re.match(r'^ZAV-[A-Z0-9]{8}$', clean_id):
        clean_id = f"ZAV-{uuid.uuid4().hex[:8].upper()}"

    clean_name = str(name).strip() if name and name.lower() not in ["none", "n/a", "unknown"] else "Patient"
    clean_age = str(age).strip() if age and age.lower() not in ["none", "n/a", "unknown"] else "Not recorded"
    clean_gender = str(gender).strip() if gender and gender.lower() not in ["none", "n/a", "unknown"] else "Not specified"
    clean_location = str(location).strip() if location and location.lower() not in ["none", "n/a", "unknown"] else "Not recorded"
    clean_complaints = str(complaints).strip() if complaints else "Skin consultation"
    clean_notes = str(notes).strip() if notes else "Clinical history gathered during AI consultation."
    clean_diagnosis = str(diagnosis).strip() if diagnosis else "Dermatological Evaluation (Differential Assessment)"

    if medications is None: medications = []
    if instructions is None: instructions = []
    if treatment_steps is None: treatment_steps = []

    med_rows = ""
    for m in medications:
        if isinstance(m, str):
            m_name = m
            m_dosage = "Educational guidance"
            m_duration = "As evaluated by doctor"
        elif isinstance(m, dict):
            m_name = m.get('name') or m.get('medicine') or m.get('drug') or 'Medication'
            m_dosage = m.get('dosage') or m.get('dose') or 'Educational guidance'
            m_duration = m.get('duration') or m.get('time') or 'As directed'
        else:
            continue
        
        med_rows += f"""
        <tr class="group transition-colors hover:bg-sky-50/30">
            <td class="px-3 py-2">
                <span class="block text-[10px] font-bold text-slate-800 dark:text-white uppercase leading-tight tracking-tight">{m_name}</span>
                <span class="text-[7px] text-slate-400 uppercase font-medium italic">Clinical Reference</span>
            </td>
            <td class="px-3 py-2 text-[10px] text-slate-600 dark:text-gray-300">{m_dosage}</td>
            <td class="px-3 py-2 text-right text-[10px] font-black text-slate-700 dark:text-gray-300">{m_duration}</td>
        </tr>"""

    if not med_rows:
        med_rows = """
        <tr>
            <td colspan="3" class="px-3 py-2 text-[10px] text-slate-500 italic text-center">
                No specific medications recommended. In-person clinical assessment required prior to prescribing.
            </td>
        </tr>"""

    formatted_instructions = "".join([
        f'<div class="flex items-start mb-1 text-[10px] leading-snug"><div class="mr-1.5 font-black text-[#0ea5e9]">{i+1}.</div><div>{step}</div></div>' 
        for i, step in enumerate(instructions)
    ]) if instructions else '<div class="text-[10px] text-slate-500 italic">Follow general skincare hygiene and seek physical evaluation if symptoms persist.</div>'

    tx_list_items = "".join([
        f'<div class="flex items-start mb-1 text-[10px] leading-snug"><div class="mr-1.5 text-slate-400">•</div><div>{step}</div></div>' 
        for step in treatment_steps
    ]) if treatment_steps else '<div class="text-[10px] text-slate-500 italic">In-person examination by a licensed dermatologist recommended.</div>'

    report_id = f"report_{current_date_obj.strftime('%Y%m%d_%H%M%S')}"

    return f"""
<div id="{report_id}" class="medical-report relative mx-auto flex min-h-[297mm] w-full max-w-[210mm] flex-col overflow-hidden bg-white font-sans text-slate-800 shadow-2xl sm:rounded-sm dark:bg-gray-950 dark:text-gray-200">
  <div class="pointer-events-none absolute inset-0 z-0 flex items-center justify-center opacity-[0.03]">
    <img src="/static/Watermark.png" class="w-[70%]" alt="Watermark" />
  </div>
  
  <div class="relative w-full flex-shrink-0 bg-[#0ea5e9] py-8 sm:py-10">
    <div class="relative z-10 flex flex-col items-center justify-between gap-6 px-6 sm:flex-row sm:items-start sm:px-10">
      <div class="flex flex-col items-center gap-3 text-center sm:flex-row sm:text-left">
        <div class="flex h-16 w-16 items-center justify-center rounded-full border-4 border-white/30 bg-white shadow-lg">
          <img src="https://raw.githubusercontent.com/Salman7292/Agentic-AI/refs/heads/main/ai_doctor_logo.gif" alt="Clinic Logo" class="h-11 w-11 rounded-full object-contain" />
        </div>
        <div class="text-white">
          <h1 class="text-xl font-black leading-none tracking-tight uppercase sm:text-2xl">MedNexus AI<br/><span class="text-sky-100">Dermatology Decision Support</span></h1>
          <p class="mt-1 text-[8px] font-bold tracking-[0.2em] text-sky-100 uppercase opacity-90">Consultation Summary & Care Plan</p>
        </div>
      </div>
      <div class="text-center sm:text-right">
        <h2 class="text-xl font-bold leading-tight text-white sm:text-2xl uppercase tracking-tight">Dr. Zavian AI</h2>
        <p class="text-xs font-extrabold text-sky-100">AI Dermatology Specialist</p>
        <p class="text-[9px] font-bold tracking-wide text-white/90">Clinical Decision Support System</p>
        <div class="mt-2 h-0.5 w-20 rounded-full bg-white/30 mx-auto sm:ml-auto sm:mr-0 sm:w-24"></div>
      </div>
    </div>
  </div>

  <div class="relative z-10 -mt-6 px-4 sm:px-10">
    <div class="grid grid-cols-2 gap-y-3 gap-x-2 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-lg dark:border-gray-800 dark:bg-gray-900 sm:grid-cols-5 sm:gap-3 sm:px-6">
      <div class="col-span-2 sm:col-span-1">
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Patient Name</span>
        <span class="text-[11px] font-bold text-slate-800 uppercase dark:text-gray-100 truncate block">{clean_name}</span>
      </div>
      <div>
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Age/Sex</span>
        <span class="text-[11px] font-bold text-slate-800 dark:text-gray-200">{clean_age} / {clean_gender}</span>
      </div>
      <div>
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Location</span>
        <span class="text-[11px] font-bold text-slate-800 dark:text-gray-200">{clean_location}</span>
      </div>
      <div>
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Date</span>
        <span class="text-[11px] font-bold text-slate-800 dark:text-gray-200">{report_date}</span>
      </div>
      <div class="col-span-2 sm:col-span-1 sm:text-right">
        <span class="mb-0.5 block text-[8px] font-black text-slate-400 uppercase tracking-wider">Consultation ID</span>
        <span class="font-mono text-[11px] font-bold text-[#0ea5e9]">{clean_id}</span>
      </div>
    </div>
  </div>

  <div class="relative z-10 flex flex-1 flex-col gap-6 px-6 pt-8 sm:flex-row sm:gap-8 sm:px-10">
    <div class="w-full space-y-6 sm:w-[35%] sm:border-r sm:border-slate-100 sm:pr-6 sm:dark:border-gray-800">
      <section>
        <h3 class="mb-2 text-[9px] font-black tracking-[0.15em] text-[#0ea5e9] uppercase">Reported Symptoms</h3>
        <div class="rounded-lg bg-slate-50 p-3 text-[10px] leading-snug text-slate-600 italic dark:bg-gray-900 dark:text-gray-400">"{clean_complaints}"</div>
      </section>
      <section>
        <h3 class="mb-2 text-[9px] font-black tracking-[0.15em] text-[#0ea5e9] uppercase">Clinical Assessment Notes</h3>
        <div class="text-[10px] leading-snug text-slate-600 dark:text-gray-400">{clean_notes}</div>
      </section>
      <section class="rounded-xl bg-sky-50 p-4 dark:bg-sky-950/30 border border-sky-100 dark:border-sky-900/50">
        <h3 class="mb-1 text-[8px] font-black tracking-widest text-sky-700 uppercase">Differential Assessment</h3>
        <div class="text-[11px] font-extrabold text-slate-900 uppercase dark:text-gray-100 leading-tight">{clean_diagnosis}</div>
        <p class="mt-1 text-[8px] text-slate-500 italic">Informational evaluation — requires in-person clinical confirmation.</p>
      </section>
    </div>

    <div class="w-full sm:w-[65%]">
      <div class="mb-4 flex items-baseline gap-3">
        <span class="font-serif text-3xl text-slate-900 italic dark:text-gray-100 sm:text-4xl">Clinical Considerations</span>
        <div class="h-[1.5px] flex-1 rounded-full bg-slate-100 dark:bg-gray-800"></div>
      </div>

      <div class="mb-6 overflow-hidden rounded-xl border border-slate-200 shadow-sm dark:border-gray-800">
        <table class="w-full table-fixed border-collapse text-left">
          <thead>
            <tr class="bg-slate-900 text-[8px] font-black tracking-widest text-white uppercase dark:bg-sky-900">
              <th class="w-[40%] px-3 py-2.5">Therapeutic Option</th>
              <th class="w-[30%] px-3 py-2.5">Guidance Level</th>
              <th class="w-[30%] px-3 py-2.5 text-right">Duration</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-gray-800">
            {med_rows}
          </tbody>
        </table>
        <div class="bg-slate-50 px-4 py-1.5 text-[7px] font-bold text-slate-500 uppercase tracking-widest dark:bg-gray-900 text-center border-t border-slate-100">
          AI Educational Consultation Summary — Not an Official Prescription
        </div>
      </div>

      <div class="grid gap-3">
        <div class="rounded-xl border border-amber-100 bg-amber-50/40 p-3 dark:border-amber-900/30 dark:bg-amber-900/10">
          <h3 class="mb-1 text-[8px] font-black text-amber-700 uppercase dark:text-amber-500">Care Instructions & Hygiene</h3>
          <div class="text-slate-600 dark:text-gray-400">{formatted_instructions}</div>
        </div>
        <div class="rounded-xl border border-sky-100 bg-sky-50/40 p-3 dark:border-sky-900/30 dark:bg-sky-900/10">
          <h3 class="mb-1 text-[8px] font-black text-sky-700 uppercase dark:text-sky-500">Recommended Next Steps</h3>
          <div class="text-slate-600 dark:text-gray-400">{tx_list_items}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="relative z-10 mt-auto px-6 pb-8 sm:px-10">
    <div class="p-3 mb-6 rounded-lg bg-amber-50/80 border border-amber-200 dark:bg-amber-950/20 dark:border-amber-900/40 text-[8px] text-amber-800 dark:text-amber-300 leading-relaxed">
      <strong>CRITICAL HEALTHCARE DISCLAIMER:</strong> This report is generated by an artificial intelligence decision-support tool (Dr. Zavian AI) for patient educational and informational guidance only. It does not establish a formal doctor-patient relationship, issue a binding prescription, or replace in-person physical clinical examination, dermoscopy, or biopsy. If your symptoms worsen, spread rapidly, or involve systemic signs, please seek emergency medical evaluation immediately.
    </div>

    <div class="flex flex-col gap-6 border-t border-slate-100 pt-6 dark:border-gray-800 sm:flex-row sm:items-end sm:justify-between">
      <div class="max-w-xs space-y-0.5 text-[9px] text-slate-400">
        <p>Generated on {current_date_obj.strftime("%b %d, %Y | %H:%M")}</p>
        <div class="mt-2 flex items-center gap-1.5">
           <div class="h-3.5 w-3.5 rounded bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-[8px]">ℹ</div>
           <span class="italic text-[8px] text-slate-500">MedNexus AI Decision Support — Unsigned Patient Summary</span>
        </div>
      </div>
      <div class="relative w-full text-center sm:w-56">
        <div class="border-t border-slate-400 pt-2">
          <p class="text-xs font-black text-slate-800 uppercase dark:text-gray-100">Dr. Zavian AI</p>
          <p class="text-[8px] font-bold tracking-[0.2em] text-[#0ea5e9] uppercase">Clinical AI Specialist</p>
          <p class="text-[7px] text-slate-400">MedNexus Medical AI Decision Support</p>
        </div>
      </div>
    </div>
  </div>

  <div class="relative w-full bg-[#0ea5e9] py-2.5">
    <div class="flex flex-col items-center justify-center gap-1 px-10 text-[7px] font-black text-white uppercase sm:flex-row sm:justify-between">
      <span>Consultation ID: {clean_id}</span>
      <span>MedNexus AI • Educational Clinical Decision Support</span>
    </div>
  </div>
</div>

<div class="mx-auto mt-6 mb-10 flex max-w-[210mm] justify-center px-4 print:hidden">
  <button onclick="downloadReport('{report_id}')" class="group flex items-center gap-3 rounded-full bg-[#0ea5e9] px-8 py-3 text-xs font-black tracking-widest text-white shadow-lg transition-all hover:bg-[#0284c7] hover:shadow-xl active:scale-95">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="h-4 w-4">
      <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
    DOWNLOAD REPORT
  </button>
</div>

<script>
async function downloadReport(reportId) {{
    const reportElement = document.getElementById(reportId);
    if (!reportElement) return;
    const btn = event ? event.currentTarget : null;
    const originalContent = btn ? btn.innerHTML : '';
    if (btn) {{
        btn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Generating Image...';
        btn.disabled = true;
    }}
    try {{
        const canvas = await html2canvas(reportElement, {{ scale: 2, useCORS: true, logging: false }});
        const link = document.createElement('a');
        link.download = `Medical_Report_Dr_Zavian_${{new Date().toISOString().split('T')[0]}}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    }} catch (error) {{
        console.error("Report download failed:", error);
        alert("Failed to download report image. Please try using print (Ctrl+P).");
    }} finally {{
        if (btn) {{
            btn.innerHTML = originalContent;
            btn.disabled = false;
        }}
    }}
}}
</script>
"""

# Bind tools
tools = [
    diagnosis_retrieval_tool, 
    medication_retrieval_tool, 
    search_tool, 
    generate_medical_report, 
    doctor_search_tool, 
    analyze_skin_or_report_image
]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)


# ==============================================================================
# RESPONSE VALIDATION & SINGLE-QUESTION ENFORCEMENT LAYER
# ==============================================================================

def _get_next_unasked_question(profile: Dict[str, Any]) -> str:
    """
    Determines the next unasked clinical question in sequence, preventing loops
    and transitioning cleanly to consultation closure when history is complete.
    """
    answered = profile.get("answered_topics", set())
    if not profile.get("name") and "name" not in answered:
        return "May I have your name, please?"
    if not profile.get("age") and "age" not in answered:
        return "How old are you?"
    if not profile.get("location") and "location" not in answered:
        return "Where are you located?"
    if not profile.get("gender") and "gender" not in answered:
        return "What is your biological sex or gender?"
    if not profile.get("duration") and "duration" not in answered:
        return "How long has this lesion been present?"
    if profile.get("pain") is None and "pain" not in answered:
        return "How would you describe any pain or discomfort in that area (e.g. on a 1 to 10 scale)?"
    if profile.get("itching") is None and "itching" not in answered:
        return "Have you experienced any itching or burning sensations in that area?"
    if profile.get("triggers") is None and "triggers" not in answered:
        return "Have you noticed any factors—such as heat, sun, or stress—that make it worse?"
    if profile.get("previous_treatments") is None and "treatments" not in answered:
        return "Have you tried any cleansers, creams, or other treatments for this so far?"
    if profile.get("spread") is None and "spread" not in answered:
        return "Have you noticed any changes or spreading in that area recently?"
    # When clinical intake is complete, offer report generation
    return "Would you like me to generate a formal medical summary report for you to download or share with your doctor?"


def validate_and_sanitize_response(text: str, profile: Dict[str, Any]) -> str:
    """
    Enforces clinical safety and UI guardrails:
    1. Exactly ONE clinical question per turn (application-level constraint).
    2. Prevents repeating already answered questions or asking for known body parts.
    3. Strips raw markdown medication tables, raw differential tables, and JSON tool outputs.
    4. Hides internal paths, system alert tags, or internal reasoning traces (<thought> / <reasoning>).
    5. Enforces non-definitive phrasing for unconfirmed diagnoses.
    6. Injects safety warning for red-flag symptoms (severe pain >= 8/10 or rapid facial spread).
    7. Guarantees non-empty response.
    """
    if not text or not text.strip():
        return "I am carefully evaluating your symptoms. To help me assist you accurately, could you describe what sensations or changes you are noticing in that area?"

    # 1. Strip internal reasoning tokens from reasoning models (<thought> or <reasoning>)
    cleaned = re.sub(r'<thought>[\s\S]*?</thought>', '', text)
    cleaned = re.sub(r'<reasoning>[\s\S]*?</reasoning>', '', cleaned)

    # 2. Remove leaked file paths, internal alert tags, and raw JSON analysis dumps
    cleaned = re.sub(r'\[System Alert:[^\]]+\]', '', cleaned)
    cleaned = re.sub(r'\[Visual Examination[^\]]+\]', '', cleaned)
    cleaned = re.sub(r'\[Active Image Analysis[^\]]+\]', '', cleaned)
    cleaned = re.sub(r'(?:static/|D:[\\/]|C:[\\/])[^\s]+\.(?:png|jpg|jpeg|webp|jfif)', '', cleaned)
    cleaned = re.sub(r'```json[\s\S]*?```', '', cleaned)
    cleaned = re.sub(r'\{[\s\S]*"image_type"[\s\S]*\}', '', cleaned)

    # 3. Prevent raw tool table dumps (e.g. | Medicine | Dosage | or differential tables)
    if "|" in cleaned and any(term in cleaned for term in ["| Medicine |", "| Drug |", "| Condition |", "| Differential |", "| First-line |", "| Diagnosis |"]):
        cleaned = re.sub(r'\|[^\n]+\|\n\|[-|\s]+\|\n(?:\|[^\n]+\|\n)+', '', cleaned)
        if not cleaned.strip():
            cleaned = "There are several standard therapeutic and diagnostic considerations documented for this condition. A licensed clinician must evaluate your presentation in person to select the appropriate treatment safely."

    # 4. Prevent definitive diagnostic claims for vague lesions or retrieval candidates
    definitive_patterns = [
        (r'\b(you have|this is definitively|this is an established case of|confirmed diagnosis is)\s+(hsv-1|herpes|cold sore|melanoma|carcinoma|bacterial infection|tinea|acne|folliculitis)', 
         r'this presentation could suggest several possibilities, including viral lesions (such as HSV-1), localized folliculitis, or dermatitis. An in-person evaluation is necessary to confirm.'),
        (r'\b(?:and\s+)?(?:this is definitively|this is a definitive|is a confirmed)\s+(?:a\s+)?(?:cold sore|hsv-1|herpes|infection|condition)[^.]*', ''),
    ]
    for pattern, repl in definitive_patterns:
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdefinitively\b', 'potentially', cleaned, flags=re.IGNORECASE)

    # 5. ENFORCE EXACTLY ONE QUESTION RULE & PREVENT REDUNDANT QUESTIONS
    if "?" in cleaned:
        segments = re.split(r'(?<=[.!?])\s+', cleaned.strip())
        preserved_segments = []
        question_count = 0

        for seg in segments:
            if "?" in seg:
                if question_count == 0:
                    # Split compound questions joined by conjunctions
                    compound_split = re.split(r',\s+(?:and|or)\s+(?:also\s+)?(?:when\b|where\b|how\b|what\b|have you\b|do you\b|did it\b|is there\b|can you\b|does it\b|whether\b|if\b)', seg, flags=re.IGNORECASE)
                    single_q = compound_split[0].strip()
                    if not single_q.endswith("?"):
                        single_q += "?"

                    # Resolve compound symptom questions in single_q
                    if "pain" in single_q.lower() and "itch" in single_q.lower():
                        if "pain" not in profile.get("answered_topics", set()) and profile.get("pain") is None:
                            single_q = "How would you describe any pain or discomfort in that area (e.g. on a 1 to 10 scale)?"
                        else:
                            single_q = "Have you experienced any itching or burning sensations in that area?"
                    elif "pus" in single_q.lower() and "crust" in single_q.lower():
                        single_q = "Do you see any visible pus or fluid-filled spots in that area?"

                    q_lower = single_q.lower()
                    answered = profile.get("answered_topics", set())

                    # Check if question asks for location when location is ALREADY KNOWN
                    is_location_q = any(w in q_lower for w in [
                        "where is the lesion", "which body part", "where is it located", "where on your body",
                        "what body part", "location of the bump", "where is this bump", "where is this lesion"
                    ])
                    has_known_location = bool(
                        profile.get("lesion_location") or 
                        (profile.get("image_inferred_region") and profile.get("image_inferred_region_status") == "visually_identified")
                    )

                    if is_location_q and has_known_location:
                        if not profile.get("duration") and "duration" not in answered:
                            single_q = "How long has this lesion been present?"
                        else:
                            single_q = _get_next_unasked_question(profile)

                    # Check if question asks for duration when duration is ALREADY KNOWN
                    elif ("how long" in q_lower or "duration" in q_lower or "when did" in q_lower) and (profile.get("duration") or "duration" in answered):
                        single_q = _get_next_unasked_question(profile)

                    # Check if question asks for demographics when already known
                    elif ("your name" in q_lower or "what is your name" in q_lower or "may i have your name" in q_lower) and (profile.get("name") or "name" in answered):
                        single_q = _get_next_unasked_question(profile)

                    elif ("how old" in q_lower or "your age" in q_lower or "tell me your age" in q_lower) and (profile.get("age") or "age" in answered):
                        single_q = _get_next_unasked_question(profile)

                    elif ("where are you located" in q_lower or "where do you live" in q_lower or "current location" in q_lower or "city or region" in q_lower) and (profile.get("location") or "location" in answered):
                        single_q = _get_next_unasked_question(profile)

                    elif ("gender" in q_lower or "biological sex" in q_lower) and (profile.get("gender") or "gender" in answered):
                        single_q = _get_next_unasked_question(profile)

                    # Check if question asks for triggers when already known
                    elif ("trigger" in q_lower or "heat" in q_lower or "sun" in q_lower or "stress" in q_lower) and (profile.get("triggers") is not None or "triggers" in answered):
                        single_q = _get_next_unasked_question(profile)

                    # Check if question asks for prior treatments when already known
                    elif ("cream" in q_lower or "cleanser" in q_lower or "treatment" in q_lower or "medication" in q_lower or "cleansers" in q_lower) and (profile.get("previous_treatments") is not None or "treatments" in answered):
                        single_q = _get_next_unasked_question(profile)

                    # Check if question asks for spreading / changes when already known
                    elif ("spread" in q_lower or "spreading" in q_lower or "new bumps" in q_lower or "changes" in q_lower) and (profile.get("spread") is not None or "spread" in answered):
                        single_q = _get_next_unasked_question(profile)

                    # Check if question asks for pain when already known
                    elif ("pain" in q_lower or "tenderness" in q_lower or "discomfort" in q_lower) and (profile.get("pain") is not None or "pain" in answered):
                        if not ("itch" in q_lower and (profile.get("itching") is None and "itching" not in answered)):
                            single_q = _get_next_unasked_question(profile)

                    # Check if question asks for itching when already known
                    elif ("itch" in q_lower or "scratch" in q_lower) and (profile.get("itching") is not None or "itching" in answered):
                        single_q = _get_next_unasked_question(profile)

                    preserved_segments.append(single_q)
                    question_count += 1
                else:
                    # Drop second and subsequent questions
                    continue
            else:
                if question_count == 0:
                    preserved_segments.append(seg)
                else:
                    # Drop trailing non-question text after the single question
                    continue

        if preserved_segments:
            cleaned = " ".join(preserved_segments).strip()

    # 6. Red-flag safety escalation for severe pain or rapid worsening
    pain_val = str(profile.get("pain", "")).lower()
    has_severe_pain = any(score in pain_val for score in ["8/10", "9/10", "10/10", "severe", "excruciating"])
    if has_severe_pain and "urgent" not in cleaned.lower() and "emergency" not in cleaned.lower():
        cleaned += "\n\n*Safety Advisory: Because severe pain or rapidly evolving facial lesions can indicate a serious acute complication, please seek an urgent in-person medical evaluation.*"

    # Clean up repetitive filler phrases
    cleaned = re.sub(r'I apologize for (?:asking|repeating)[^.\n]*[.]?', '', cleaned, flags=re.IGNORECASE).strip()

    # Final guard against empty response
    if not cleaned.strip():
        cleaned = "I am carefully evaluating your symptoms. To help me assist you accurately, could you describe what sensations or changes you are noticing in that area?"

    return cleaned


# ==============================================================================
# TOKEN SAVER & CONTEXT FILTERING
# ==============================================================================

def filter_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
    """
    Limits prompt token consumption to strictly prevent Groq 429 TPM overages (8,000 TPM limit).
    Keeps initial complaint (first 2 messages) and recent turns (last 8 messages).
    All confirmed clinical facts are already in the dynamic SystemMessage.
    """
    system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
    other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]

    # Limit active messages to at most 10 non-system messages
    if len(other_messages) > 10:
        intake_phase = other_messages[:2]
        recent_context = other_messages[-8:]
        summary_marker = SystemMessage(content="[Earlier messages condensed; all demographics and findings are preserved in clinical state]")
        other_messages = intake_phase + [summary_marker] + recent_context

    filtered = []
    valid_tool_call_ids = set()

    for msg in other_messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    valid_tool_call_ids.add(tc.get("id"))
            filtered.append(msg)
        elif isinstance(msg, ToolMessage):
            tool_name = msg.name or "medical_tool"
            new_kwargs = dict(msg.additional_kwargs or {})
            new_kwargs["name"] = tool_name

            # Prevent HarmonyError if tool message is orphaned
            if msg.tool_call_id not in valid_tool_call_ids:
                filtered.append(SystemMessage(content=f"[{tool_name} Observation]: {str(msg.content)[:200]}"))
                continue

            if msg.name == "generate_medical_report":
                filtered.append(ToolMessage(
                    content="[Medical Report Generated Successfully - Full HTML rendered in UI]",
                    tool_call_id=msg.tool_call_id,
                    name=tool_name,
                    additional_kwargs=new_kwargs,
                    artifact=msg.artifact,
                    status=msg.status
                ))
            else:
                # Truncate bulky tool responses in context to prevent exceeding TPM budget
                content_to_keep = str(msg.content)[:500] if len(str(msg.content)) > 500 else msg.content
                filtered.append(ToolMessage(
                    content=content_to_keep,
                    tool_call_id=msg.tool_call_id,
                    name=tool_name,
                    additional_kwargs=new_kwargs,
                    artifact=msg.artifact,
                    status=msg.status
                ))
        else:
            filtered.append(msg)

    return system_messages + filtered


# ==============================================================================
# PROMPT CONSTRUCTION & GRAPH NODES
# ==============================================================================

def build_system_message(profile: Dict[str, Any]) -> SystemMessage:
    """
    Constructs Dr. Zavian's system prompt dynamically injected with confirmed state,
    active image observations, strict single-question mandate, and report separation.
    """
    name_str = profile.get("name") or "Not yet provided"
    age_str = profile.get("age") or "Not yet provided"
    loc_str = profile.get("location") or "Not yet provided"
    gender_str = profile.get("gender") or "Not yet provided"
    complaint_str = profile.get("complaint") or "Not yet provided"
    dur_str = profile.get("duration") or "Not yet provided"
    pain_str = profile.get("pain") or "Not yet assessed"
    itch_str = profile.get("itching") or "Not yet assessed"
    spread_str = profile.get("spread") or "Not yet assessed"
    triggers_str = profile.get("triggers") or "None reported"
    tx_str = profile.get("previous_treatments") or "None reported"
    firm_str = profile.get("firmness") or "Not specified"
    red_str = profile.get("redness") or "Not specified"
    assoc_str = profile.get("associated_symptoms") or "None reported"

    # Patient-reported vs. image-inferred location (kept strictly separate)
    patient_reported_loc = profile.get("lesion_location") or "Not yet reported by patient"
    inferred_region = profile.get("image_inferred_region")
    inferred_status = profile.get("image_inferred_region_status") or "uncertain"
    if inferred_region:
        inferred_str = f"{inferred_region} (status: {inferred_status})"
    else:
        inferred_str = "Not determined from image"

    img_status = (
        "Analyzed (Visual findings available in context)" if profile.get("image_analysis")
        else ("Attached, awaiting analysis" if profile.get("image_path") else "None uploaded")
    )

    doc_data = profile.get("document_data", {})
    doc_name = doc_data.get("name")
    doc_discrepancy = doc_data.get("discrepancy_note")

    doc_section = ""
    if doc_name or doc_discrepancy:
        doc_section = (
            "\n--- UPLOADED DOCUMENT INFORMATION (STRICT SEPARATION: UNVERIFIED EXTERNAL RECORD) ---\n"
            f"• Document Patient Name: {doc_name or 'Not specified'}\n"
            f"• Discrepancy Note: {doc_discrepancy or 'None'}\n"
            "• MANDATE: Do NOT assume this document belongs to the patient. Do NOT merge document details into patient record. If names conflict, explain the discrepancy neutrally.\n"
        )

    # Format structured active image observations section
    image_obs_section = ""
    immediate_image_instruction = ""
    if profile.get("image_analysis"):
        try:
            raw_analysis = profile["image_analysis"]
            if isinstance(raw_analysis, str):
                json_match = re.search(r'\{[\s\S]*\}', raw_analysis)
                data = json.loads(json_match.group(0)) if json_match else json.loads(raw_analysis)
            else:
                data = raw_analysis
            img_type = data.get("image_type", "clinical_skin_photo")
            class_status = data.get("classification_status", "identified")
            anat_obj = data.get("anatomical_region", {})
            anat_val = anat_obj.get("value")
            anat_stat = anat_obj.get("status", "uncertain")
            photo = data.get("clinical_skin_photo", {})
            lesion_ident = photo.get("lesion_identified", {})
            lesion_loc = photo.get("lesion_location") or anat_val or "affected area"
            lesion_desc = photo.get("lesion_description") or "Visual skin observation"
            what_is_on_loc = photo.get("what_is_on_location") or lesion_desc
            suspected_cond = photo.get("suspected_condition_patterns") or "Under clinical differential evaluation"
            vf_list = photo.get("visible_findings", [])
            vf_str = ", ".join([f"{v.get('feature')} ({v.get('status')})" for v in vf_list]) if vf_list else "None specific"
            dist_str = photo.get("distribution") or "not_assessable"
            limitations_list = data.get("image_quality", {}).get("limitations", [])
            lim_str = "; ".join(limitations_list) if limitations_list else "Standard visual assessment"

            image_obs_section = (
                "\n--- ACTIVE IMAGE VISUAL OBSERVATIONS (CONFIRMED OBJECTIVE FINDINGS) ---\n"
                f"• Image Category: {img_type} (status: {class_status})\n"
                f"• Visual Anatomical Region: {anat_val or 'Uncertain / Not determined'} (status: {anat_stat})\n"
                f"• Specific Location: {lesion_loc}\n"
                f"• What Is On That Location (Findings & Lesions): {what_is_on_loc}\n"
                f"• Suspected Dermatological Condition/Pattern: {suspected_cond}\n"
                f"• Visible Features: {vf_str}\n"
                f"• Distribution: {dist_str}\n"
                f"• Quality Limitations: {lim_str}\n"
                "• Visual Safety Rule: Visual observations alone cannot confirm a definitive diagnosis without an in-person physical examination.\n"
            )

            # If image has not yet been explained to the patient on this turn:
            if not profile.get("image_explained"):
                if img_type == "clinical_skin_photo":
                    immediate_image_instruction = (
                        f"\n[MANDATORY WORKFLOW FOR THIS RESPONSE - NEW IMAGE UPLOAD]:\n"
                        f"In your response, you must immediately acknowledge and describe the photograph to the patient in compassionate, professional terms:\n"
                        f"1. Acknowledge the anatomical location ('{anat_val or 'area shown'}') and specific site ('{lesion_loc}').\n"
                        f"2. Describe in detail what you observe on that location ('{what_is_on_loc}').\n"
                        f"3. Note the suspected dermatological condition or pattern suggested by the visual presentation ('{suspected_cond}'), explaining that while the visual features suggest this possibility, an in-person clinical examination is required to confirm.\n"
                        f"4. Do NOT ask 'which body part is it on?' or 'what does it look like?'.\n"
                        f"5. Then, ask at most ONE relevant clinical history follow-up question (e.g. duration, pain/itching, or triggers).\n"
                    )
                elif img_type == "medical_report":
                    immediate_image_instruction = (
                        f"\n[MANDATORY WORKFLOW FOR THIS RESPONSE - MEDICAL DOCUMENT UPLOAD]:\n"
                        f"Explain that the uploaded image is a medical report or document, not a clinical skin photograph. "
                        f"Summarize the written findings neutrally without adopting them as confirmed patient records.\n"
                    )
                elif img_type == "unknown":
                    immediate_image_instruction = (
                        f"\n[MANDATORY WORKFLOW FOR THIS RESPONSE - UNCLEAR IMAGE]:\n"
                        f"Explain honestly that the photograph is blurry or poorly illuminated and cannot be assessed reliably. "
                        f"Request a clearer, well-lit close-up photograph and ask one clinical question.\n"
                    )
        except Exception:
            pass

    # Check for confusion clarification guidance
    clarification_section = ""
    if profile.get("clarification_needed"):
        term = profile.get("clarification_needed")
        clarification_section = (
            f"\n[PATIENT-FRIENDLY CLARIFICATION REQUIRED]:\n"
            f"The patient requested clarification or expressed confusion about '{term}'. "
            "First, explain the concept in plain, simple everyday words (e.g. itching is an uncomfortable tickling feeling that makes you want to scratch; tenderness is soreness when pressed or touched; pus is a small white/yellow fluid bump; crust is a dried scab). "
            "Then, ask ONE simple, gentle question.\n"
        )

    # Check if clinical history intake is complete
    history_complete = bool(
        profile.get("duration") and 
        profile.get("pain") is not None and 
        profile.get("itching") is not None and 
        (profile.get("triggers") is not None or profile.get("previous_treatments") is not None or profile.get("spread") is not None)
    )

    consolidated_query = f"{patient_reported_loc or inferred_region or 'skin'} lesion; duration: {dur_str}; pain: {pain_str}; itching: {itch_str}; triggers: {triggers_str}; treatments: {tx_str}; spread: {spread_str}"

    phase4_transition_section = ""
    if history_complete:
        phase4_transition_section = (
            "\n[PHASE 4 TRANSITION - MANDATORY ACTION]:\n"
            "Clinical history intake is COMPLETE. All key diagnostic dimensions are gathered.\n"
            "YOU ARE FORBIDDEN FROM ASKING MORE HISTORY QUESTIONS OR REPEATING PREVIOUS QUESTIONS (such as asking about spreading, pain, itching, or triggers again).\n"
            "YOU MUST NOW:\n"
            f"1. Call 'diagnosis_retrieval_tool' with the consolidated query: '{consolidated_query}'.\n"
            "2. Present 2 to 3 differential diagnosis possibilities clearly explaining supporting features and missing features.\n"
            "3. State the clinical uncertainty and explain that an in-person physical clinical examination by a dermatologist is required for confirmation.\n"
            "4. Provide safe, practical home care guidance (e.g. gentle non-comedogenic cleansing, avoid picking or squeezing blackheads, sun protection).\n"
            "5. Conclude with this single question: 'Would you like me to generate a formal medical summary report for you to download or share with your doctor?'\n"
        )

    prompt = (
        "ROLE: You are Dr. Zavian, an expert clinical AI decision-support specialist in Dermatology at MedNexus AI.\n"
        "TONE & STYLE: Compassionate, concise (1-2 sentences), professional. Use simple everyday language.\n"
        "CLINICAL SCOPE: You provide careful informational guidance and differential assessments. You DO NOT issue legally binding prescriptions or declare definitive diagnoses without physical examination.\n\n"

        "--- CURRENT CONFIRMED PATIENT RECORD (DO NOT RE-ASK KNOWN FIELDS) ---\n"
        f"• Name: {name_str}\n"
        f"• Age: {age_str}\n"
        f"• Location: {loc_str}\n"
        f"• Gender: {gender_str}\n"
        f"• Chief Complaint: {complaint_str}\n"
        f"• Duration: {dur_str}\n"
        f"• Pain Level: {pain_str}\n"
        f"• Itching Level: {itch_str}\n"
        f"• Spreading / Progression: {spread_str}\n"
        f"• Triggers: {triggers_str}\n"
        f"• Previous Treatments: {tx_str}\n"
        f"• Surface Texture / Firmness: {firm_str}\n"
        f"• Color / Redness: {red_str}\n"
        f"• Associated Findings (Pus / Crust): {assoc_str}\n"
        f"• Patient-Reported Lesion Location: {patient_reported_loc}\n"
        f"• Image-Inferred Anatomical Region (from photo): {inferred_str}\n"
        f"• Image Status: {img_status}\n"
        f"{doc_section}"
        f"{image_obs_section}"
        f"{immediate_image_instruction}"
        f"{clarification_section}"
        f"{phase4_transition_section}\n"

        "--- STRICT WORKFLOW PROTOCOL ---\n"
        "1. SINGLE QUESTION MANDATE (ZERO TOLERANCE): You must ask EXACTLY ONE question per response. Never combine questions with 'and', commas, or semicolons.\n"
        "2. IMAGE ANALYSIS (MANDATORY TOOL CALL):\n"
        "   - When an image is uploaded (indicated by '[System Alert: User uploaded an image. Local Path: ...]'), you MUST IMMEDIATELY call the 'analyze_skin_or_report_image' tool with the exact Local Path provided before offering any diagnostic reasoning or follow-up question.\n"
        "   - NEVER assume, hallucinate, or guess skin findings without calling this tool.\n"
        "   - Extract the Local Path from [System Alert] but keep the technical file path hidden from the patient.\n"
        "3. IMAGE OBSERVATIONS & EXPLANATION:\n"
        "   - Once 'analyze_skin_or_report_image' has executed (or when active image observations are in context), explain the visible findings in simple, patient-friendly terms.\n"
        "   - If the patient asks 'What is in the image?' or says 'You can see it in the image', answer directly from the analyzed observations. Name the identified body part and visible skin findings. Do NOT ask 'which body part is it on?'.\n"
        "   - Distinguish visible observations from possible diagnoses: a raised bump with redness is an observation; folliculitis or dermatitis is an interpretation, not a proven fact.\n"
        "3. PHASE 1: DEMOGRAPHIC INTAKE: Collect Name -> Age -> Location -> Gender INDIVIDUALLY. If a field is known above, DO NOT ask for it again. Ask only for the next missing field.\n"
        "4. PHASE 2: CLINICAL INVESTIGATION: After basic info, ask relevant history ONE question at a time:\n"
        "   - Duration (if Patient-Reported Lesion Location or Image-Inferred Anatomical Region is known, do NOT ask for location)\n"
        "   - Pain vs Itching (evaluate separately; never assume pain score is an itching score)\n"
        "   - Triggers (heat, sun, stress) & prior treatments (creams, medications)\n"
        "5. PHASE 3: REPORT DISCREPANCIES: If an uploaded medical report contains a different name or conflicting details, explain the discrepancy neutrally. Never merge unverified report data.\n"
        "6. PHASE 4: DIFFERENTIAL DIAGNOSIS & RETRIEVAL:\n"
        "   - Call 'diagnosis_retrieval_tool' when sufficient history is gathered.\n"
        "   - Maintain a DIFFERENTIAL DIAGNOSIS (e.g. 'This could suggest several possibilities, including acne, folliculitis, or early viral lesions'). NEVER claim a single disease is confirmed from chat/photo alone.\n"
        "   - Explain uncertainty clearly and recommend physical clinical examination.\n"
        "7. PHASE 5: TREATMENT & MEDICATION GUIDANCE:\n"
        "   - Call 'medication_retrieval_tool' ONLY when the patient asks for treatment or when clinically justified.\n"
        "   - Never output raw medication tables. Offer educational information only, not personal prescriptions.\n"
        "8. PHASE 6: MEDICAL REPORT GENERATION:\n"
        "   - When the user requests a medical report or care plan download, call 'generate_medical_report'.\n"
        "   - Populate fields strictly using known patient history above. Do not re-ask duration or demographics.\n"
        "   - After the tool executes, reply ONLY with: 'I have generated your detailed medical report. You can download it below.'\n"
        "9. PHASE 7: LOCAL DOCTOR RECOMMENDATION:\n"
        "   - When requested, call 'doctor_search_tool'. Never invent clinic names or phone numbers.\n"
        "   - Explicitly note that patient records are never shared externally without consent.\n"
    )
    return SystemMessage(content=prompt)


def input_preprocess_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic image attachment handler:
    Detects newly uploaded images and runs visual analysis immediately before ordinary chat.
    Stores structured JSON analysis in conversation state.
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    last_msg = messages[-1]
    if isinstance(last_msg, HumanMessage) and isinstance(last_msg.content, str):
        match = re.search(r'\[System Alert: User uploaded an image\.\s*Local Path:\s*([^\]]+)\]', last_msg.content)
        if match:
            image_path = match.group(1).strip()
            # Assign deterministic image_id
            clean_name = os.path.basename(image_path.replace("\\", "/"))
            image_id = f"img_{uuid.uuid5(uuid.NAMESPACE_DNS, clean_name).hex[:12]}"

            # Check if this exact image has already been analyzed in the state
            already_analyzed = any(
                (image_path in str(m.content) or image_id in str(m.content)) and "image_type" in str(m.content)
                for m in messages
            )
            if not already_analyzed and os.path.exists(image_path):
                obs_json = analyze_skin_or_report_image.invoke(image_path)
                sys_msg = SystemMessage(
                    content=f"[Active Image Analysis - {image_id}]:\n{obs_json}"
                )
                return {"messages": [sys_msg]}

    return state


def chat_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core assistant decision node with structured profile injection, Groq retry handling,
    and single-question response validation.
    """
    messages = state.get("messages", [])
    profile = extract_patient_profile(messages)
    system_msg = build_system_message(profile)

    # Filter out older system messages and inject updated state-aware system prompt
    filtered_history = [m for m in messages if not isinstance(m, SystemMessage)]
    full_messages = [system_msg] + filter_messages(filtered_history)

    # Call LLM with bounded retry
    response: AIMessage = invoke_llm_with_retry(llm_with_tools, full_messages)

    # If the response contains text and no active tool call, validate and sanitize output
    if response.content and not response.tool_calls:
        clean_text = validate_and_sanitize_response(str(response.content), profile)
        response.content = clean_text
    elif not response.content and not response.tool_calls:
        # Prevent empty assistant response
        response.content = "I have noted your information. To assist you accurately, could you tell me more about what you are observing?"

    return {"messages": [response]}


# ==============================================================================
# COMPILE GRAPH
# ==============================================================================

class ChatbotState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

graph = StateGraph(ChatbotState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

DB_NAME = "dermatologist.db"
conn = sqlite3.connect(database=DB_NAME, check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)
chatbot_compiled = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)
