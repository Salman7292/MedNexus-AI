import unittest
import os
import json
import re
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

import dermatologist_logic as dl

class TestDermatologyWorkflowAudit(unittest.TestCase):
    """
    Comprehensive verification suite for the MedNexus AI Dermatology Specialist Workflow (Dr. Zavian).
    Validates all 15 scenarios specified in Section 15 of the audit specification.
    """

    def test_case_01_patient_greeting_and_initial_concern(self):
        """Case 1: A new patient receives a polite greeting and is asked about the main concern without immediate demographic interrogation."""
        # When a patient starts with a greeting like "Hello", "hello" must NOT be captured as chief complaint
        conversation = [HumanMessage(content="Hello.")]
        profile = dl.extract_patient_profile(conversation)
        self.assertIsNone(profile["complaint"], "Pure greeting 'Hello.' must not be stored as the chief complaint")

        # System message prompt must guide Dr. Zavian to introduce himself and ask for the skin concern
        sys_msg = dl.build_system_message(profile)
        self.assertIn("FIRST CONTACT / GREETING", sys_msg.content)
        self.assertIn("what skin concern or problem has brought them in today", sys_msg.content)

        # Unasked question fallback must ask for main skin concern first, not demographics
        next_q = dl._get_next_unasked_question(profile)
        self.assertIn("skin concern or problem", next_q.lower())

    def test_case_02_progressive_history_no_redundant_questions(self):
        """Case 2: History is collected progressively without repeatedly asking answered questions."""
        conversation = [
            HumanMessage(content="I have a red rash on my arm."),
            AIMessage(content="Hello! I am Dr. Zavian. How long has this rash been on your arm?"),
            HumanMessage(content="About five days."),
        ]
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["lesion_location"], "arm")
        self.assertIn("five days", p["duration"])
        self.assertIn("duration", p["answered_topics"])

        # Sanitizer must not ask about duration or body part again
        draft = "Can you tell me how long the rash has been present, and which body part it is on?"
        sanitized = dl.validate_and_sanitize_response(draft, p)
        self.assertNotIn("how long", sanitized.lower())
        self.assertNotIn("which body part", sanitized.lower())

    def test_case_03_photo_upload_during_history(self):
        """Case 3: A patient uploads a skin photograph during history collection, and visible findings are extracted."""
        conversation = [
            HumanMessage(content="I have had this bump on my cheek for two weeks."),
            AIMessage(content="On a scale of 0 to 10, how would you rate any pain in that area?"),
        ]
        # Upload photo in turn 2
        photo_analysis = dl.create_image_analysis_json(
            "test_cheek.jpg",
            raw_body_part="cheek",
            raw_findings="A discrete 6mm erythematous papule on the right cheek with central follicular plugging."
        )
        conversation.append(HumanMessage(content="[System Alert: User uploaded an image. Local Path: static/dermatalogist_upload/test_cheek.jpg] Here is a picture."))
        conversation.append(SystemMessage(content=f"[Active Image Analysis - img_001]:\n{json.dumps(photo_analysis)}"))

        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["image_inferred_region"], "cheek")
        self.assertEqual(p["duration"], "two weeks")
        self.assertEqual(p["lesion_location"], "cheek")

        # Prior history is preserved, and image observations are active
        sys_msg = dl.build_system_message(p)
        self.assertIn("• Duration: two weeks", sys_msg.content)
        self.assertIn("Visual Anatomical Region: cheek", sys_msg.content)
        self.assertIn("MANDATORY WORKFLOW FOR THIS RESPONSE - NEW IMAGE UPLOAD", sys_msg.content)

    def test_case_04_medical_report_upload_after_initial_assessment(self):
        """Case 4: A patient uploads a medical report after initial assessment, extracting dates, tests, and findings neutrally."""
        report_analysis = dl.create_image_analysis_json(
            "biopsy_report.jpg",
            raw_body_part="medical document",
            raw_findings="Medical Document. Skin Biopsy Report. Patient Name: Jane Doe. Date: 2026-03-15. Microscopic Diagnosis: Atopic dermatitis with focal spongiosis."
        )
        conversation = [
            HumanMessage(content="My name is Jane. I have itchy patches."),
            HumanMessage(content="[System Alert: User uploaded an image. Local Path: static/dermatalogist_upload/biopsy_report.jpg] Here is my lab report."),
            SystemMessage(content=f"[Active Image Analysis - img_doc]:\n{json.dumps(report_analysis)}")
        ]
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["image_type"], "medical_report")
        self.assertEqual(p["document_data"]["name"], "Jane Doe")
        self.assertIn("2026-03-15", p["document_data"]["dates"])
        self.assertIn("Atopic dermatitis", p["document_data"]["findings"])

        sys_msg = dl.build_system_message(p)
        self.assertIn("2026-03-15", sys_msg.content)
        self.assertIn("Atopic dermatitis", sys_msg.content)

    def test_case_05_uploaded_findings_persist_after_tool_calls_and_turns(self):
        """Case 5: Uploaded findings remain available after tool calls and subsequent questions."""
        photo_analysis = dl.create_image_analysis_json(
            "nose_bump.jpg",
            raw_body_part="nose",
            raw_findings="Multiple comedones with a tender erythematous papule on the nasal tip."
        )
        conversation = [
            HumanMessage(content="[System Alert: User uploaded an image. Local Path: static/dermatalogist_upload/nose_bump.jpg] Look at this."),
            SystemMessage(content=f"[Active Image Analysis - img_002]:\n{json.dumps(photo_analysis)}"),
            AIMessage(content="The photograph shows your nose with blackheads and a tender red bump. How long have you had this?"),
            HumanMessage(content="Three weeks."),
            # Simulated tool call to diagnosis retrieval
            AIMessage(
                content="",
                tool_calls=[{"id": "call_123", "name": "diagnosis_retrieval_tool", "args": {"query": "nose papule comedones 3 weeks"}}]
            ),
            ToolMessage(
                content="[Retrieved Knowledge]: Likely acne vulgaris or folliculitis.",
                tool_call_id="call_123",
                name="diagnosis_retrieval_tool"
            ),
            AIMessage(content="Based on your symptoms and the image, this could suggest acne or localized folliculitis. Does it itch?"),
            HumanMessage(content="No, not really.")
        ]
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["image_inferred_region"], "nose")
        self.assertIn("three weeks", p["duration"])
        self.assertEqual(p["itching"], "0/10 (denied)")

        # In context filter, image analysis output is preserved
        filtered = dl.filter_messages(conversation)
        self.assertTrue(any("nose papule" in str(getattr(m, "args", {})) or "diagnosis_retrieval_tool" in (getattr(m, "name", "") or "") for m in filtered))

    def test_case_06_differential_diagnosis_multiple_possibilities(self):
        """Case 6: System presents a differential diagnosis with multiple plausible options rather than declaring a definitive single disease."""
        p = {
            "name": "Tariq",
            "age": "28",
            "location": "Lahore",
            "gender": "Male",
            "complaint": "Itchy red bumps on chest",
            "duration": "10 days",
            "pain": "2/10",
            "itching": "6/10",
            "triggers": "Exercise and sweating",
            "previous_treatments": "None",
            "spread": "None",
            "firmness": "Soft",
            "redness": "Red",
            "associated_symptoms": "None"
        }
        sys_msg = dl.build_system_message(p)
        self.assertIn("[PHASE 4 TRANSITION - MANDATORY ACTION]", sys_msg.content)
        self.assertIn("Present 2 to 3 differential diagnosis possibilities", sys_msg.content)
        self.assertIn("NEVER claim a single disease is confirmed from chat/photo alone", sys_msg.content)

        # Sanitizer replaces definitive claims with differential possibilities
        definitive_draft = "You have confirmed herpes simplex virus infection."
        sanitized = dl.validate_and_sanitize_response(definitive_draft, p)
        self.assertNotIn("confirmed herpes", sanitized.lower())
        self.assertIn("possibilities", sanitized.lower())

    def test_case_07_differential_updates_with_new_evidence(self):
        """Case 7: Differential diagnosis updates when the patient provides new evidence (e.g. pus, crust, spreading)."""
        conversation = [
            HumanMessage(content="I have a red spot on my forehead for one week."),
            AIMessage(content="Do you see any visible pus or crusting on that spot?"),
            HumanMessage(content="Yes, there is pus and yellow crusting.")
        ]
        p = dl.extract_patient_profile(conversation)
        self.assertIsNotNone(p["associated_symptoms"])
        self.assertIn("Present (pus, crust, or scaling reported by patient)", p["associated_symptoms"])

        sys_msg = dl.build_system_message(p)
        self.assertIn("• Associated Findings (Pus / Crust): Present", sys_msg.content)

    def test_case_08_acknowledges_uncertainty(self):
        """Case 8: System explicitly acknowledges diagnostic uncertainty and recommends in-person physical clinical examination."""
        p = {"name": "Sara", "complaint": "Mild scaling on arm"}
        sys_msg = dl.build_system_message(p)
        self.assertIn("DO NOT issue legally binding prescriptions or declare definitive diagnoses without physical examination", sys_msg.content)
        self.assertIn("Explain uncertainty clearly and recommend physical clinical examination", sys_msg.content)

    def test_case_09_medication_safety_intake(self):
        """Case 9: Medication guidance requires safety checks (allergies, medical conditions, current medications)."""
        conversation = [
            HumanMessage(content="Can you prescribe me medication for this rash?"),
            AIMessage(content="Do you have any known drug or food allergies?"),
            HumanMessage(content="I am allergic to penicillin."),
            AIMessage(content="Do you have any chronic medical conditions?"),
            HumanMessage(content="I have asthma and diabetes."),
            AIMessage(content="Are you currently taking any medications?"),
            HumanMessage(content="I take metformin daily.")
        ]
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["allergies"], "I am allergic to penicillin.")
        self.assertIn("asthma", p["medical_conditions"].lower())
        self.assertIn("metformin", p["current_medications"].lower())

        sys_msg = dl.build_system_message(p)
        self.assertIn("• Known Allergies (Drug/Food): I am allergic to penicillin.", sys_msg.content)
        self.assertIn("• Existing Medical Conditions: I have asthma and diabetes.", sys_msg.content)
        self.assertIn("• Current Medications / Supplements: I take metformin daily.", sys_msg.content)

    def test_case_10_essential_report_fields_validation(self):
        """Case 10: Essential missing report fields (Name, Location, History) are validated before report finalization."""
        # When name or location is missing, instructions mandate collecting them before generating the report
        with open("prompts/zavian/system_prompt.txt", "r", encoding="utf-8") as f:
            prompt_txt = f.read()
        self.assertIn("Validate required fields beforehand (Name, Age, Location, Gender, Complaint, Assessment)", prompt_txt)
        self.assertIn("If essential fields like name or location are missing, ask for them before generating the report", prompt_txt)

    def test_case_11_final_report_incorporates_complete_consultation(self):
        """Case 11: The generated medical report incorporates full consultation details, clinical notes, and care steps."""
        report_html = dl.generate_medical_report.invoke({
            "name": "Farhan Khan",
            "age": "34",
            "gender": "Male",
            "patient_id": "ZAV-12345678",
            "location": "Peshawar",
            "complaints": "Erythematous itchy patch on forearm for 3 weeks with fine scaling.",
            "notes": "Patient-reported history: duration 3 weeks, pain 1/10, itch 6/10. Visual findings: superficial scaling without ulceration. Allergies: NKDA.",
            "diagnosis": "Differential Assessment: 1. Tinea Corporis; 2. Nummular Eczema. Requires clinical dermoscopy.",
            "medications": [{"name": "Topical Antifungal / Hydrocortisone Reference", "dosage": "Twice daily as advised", "duration": "14 days"}],
            "instructions": ["Keep the area clean and dry.", "Avoid harsh soaps or scrubbing.", "Do not scratch the lesion."],
            "treatment_steps": ["Schedule an in-person dermatology evaluation for fungal scraping.", "Seek urgent care if erythema spreads rapidly."]
        })

        self.assertIn("Farhan Khan", report_html)
        self.assertIn("34 / Male", report_html)
        self.assertIn("Peshawar", report_html)
        self.assertIn("Tinea Corporis", report_html)
        self.assertIn("Keep the area clean and dry", report_html)
        self.assertIn("DOWNLOAD REPORT", report_html)
        self.assertIn("CRITICAL HEALTHCARE DISCLAIMER", report_html)

    def test_case_12_doctor_search_uses_location_gracefully(self):
        """Case 12: Doctor search uses the patient's confirmed location and provides verifiable options or clear hospital referral steps."""
        # Empty location
        empty_res = dl.doctor_search_tool.invoke({"location": "   "})
        self.assertIn("Please provide a specific city or region", empty_res)

        # Non-empty location — may return live results (API key present) or fallback.
        # Either path must: (a) mention the location, (b) include dermatology/clinic
        # guidance or a hospital referral, (c) include the privacy assurance note.
        loc_res = dl.doctor_search_tool.invoke({"location": "Swat"})
        self.assertIn("Swat", loc_res)
        # At least one of: live clinic result OR fallback hospital guidance present
        has_guidance = (
            "district hospital" in loc_res.lower()        # fallback path
            or "dermatol" in loc_res.lower()              # live API result
            or "clinic" in loc_res.lower()                # live API result
            or "skin specialist" in loc_res.lower()       # live API result
            or "contact" in loc_res.lower()               # either path
        )
        self.assertTrue(has_guidance, "Expected dermatology guidance or clinic info in result")
        # Privacy note: either the fallback "Privacy Assurance" label or the live
        # API path "patient consent" / "patient records" note must be present.
        has_privacy_note = (
            "Privacy Assurance" in loc_res           # fallback path label
            or "patient consent" in loc_res.lower()  # live API path note
            or "patient records" in loc_res.lower()  # live API path note
        )
        self.assertTrue(has_privacy_note, "Expected privacy assurance note in result")

    def test_case_13_report_sharing_instructions_accurate(self):
        """Case 13: Report sharing instructions accurately reflect that report must be downloaded by user, not sent automatically."""
        with open("prompts/zavian/system_prompt.txt", "r", encoding="utf-8") as f:
            prompt_txt = f.read()
        self.assertIn("download it using the 'DOWNLOAD REPORT' button", prompt_txt)
        self.assertIn("Do NOT claim the report has been emailed or transmitted automatically — it has not.", prompt_txt)

    def test_case_14_persistence_and_conversation_state(self):
        """Case 14: SQLite conversation checkpointer preserves state across turns."""
        self.assertTrue(os.path.exists(dl.DB_NAME))
        self.assertIsNotNone(dl.checkpointer)
        threads = dl.retrieve_all_threads()
        self.assertIsInstance(threads, list)

    def test_case_15_graceful_handling_of_tool_failures_and_blurry_uploads(self):
        """Case 15: System handles unreadable uploads, corrupt images, and tool failures gracefully."""
        # Corrupt / unreadable file
        corrupt_analysis = dl.create_image_analysis_json("non_existent_file.png", error_msg="The attached photograph could not be accessed.")
        self.assertEqual(corrupt_analysis["classification_status"], "failed")
        self.assertEqual(corrupt_analysis["anatomical_region"]["status"], "not_assessable")

        # Blurry image
        blurry_analysis = dl.create_image_analysis_json("blurry.jpg", raw_body_part="uncertain", raw_findings="Very blurry and dark photograph.")
        self.assertEqual(blurry_analysis["image_type"], "unknown")
        self.assertEqual(blurry_analysis["classification_status"], "uncertain")

        # System message for failed image notes failure honestly
        profile = {"image_analysis": json.dumps(corrupt_analysis), "image_explained": False}
        sys_msg = dl.build_system_message(profile)
        self.assertIn("failed", sys_msg.content)

    def test_case_16_medication_or_tablet_image_upload(self):
        """Case 16: Image tool accurately identifies tablet / medication packaging uploads without fabricating skin lesions."""
        raw_bp = "medication or tablet"
        raw_find = "A blister pack of white round tablets labeled Doxycycline 100mg. Manufacturer: Generic Pharma."
        raw_cond = "Antibacterial / Tetracycline antibiotic for acne and skin infections"

        analysis = dl.create_image_analysis_json(
            "doxy_tablets.jpg",
            raw_body_part=raw_bp,
            raw_findings=raw_find,
            raw_condition=raw_cond
        )

        self.assertEqual(analysis["image_type"], "medication_photo")
        self.assertEqual(analysis["classification_status"], "identified")
        self.assertEqual(analysis["anatomical_region"]["status"], "not_applicable")
        self.assertFalse(analysis["clinical_skin_photo"]["lesion_identified"]["value"])
        self.assertIn("medication", analysis["clinical_skin_photo"]["lesion_description"].lower())

        # Check extracted medication details
        med_det = analysis.get("medication_details", {})
        self.assertTrue(med_det.get("is_medication"))
        self.assertIn("100mg", med_det.get("dosage_strength", ""))
        self.assertIn("tablet", med_det.get("formulation", "").lower())

        # Verify state extraction and system message guidance
        conversation = [
            HumanMessage(content="[System Alert: User uploaded an image. Local Path: static/dermatalogist_upload/doxy_tablets.jpg] This is what I took."),
            SystemMessage(content=f"[Active Image Analysis - img_med_01]:\n{json.dumps(analysis)}")
        ]
        profile = dl.extract_patient_profile(conversation)
        self.assertEqual(profile["image_type"], "medication_photo")
        self.assertIn("Uploaded Medication Image", profile["document_data"]["findings"])

        sys_msg = dl.build_system_message(profile)
        self.assertIn("ACTIVE IMAGE VISUAL OBSERVATIONS (MEDICATION / PHARMACEUTICAL IMAGE)", sys_msg.content)
        self.assertIn("MANDATORY WORKFLOW FOR THIS RESPONSE - MEDICATION / TABLET IMAGE UPLOAD", sys_msg.content)
        self.assertIn("The patient uploaded a photograph of a medication or tablet", sys_msg.content)

if __name__ == "__main__":
    unittest.main()
