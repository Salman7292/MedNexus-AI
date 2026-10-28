import unittest
import os
import re
import json
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

import dermatologist_logic as dl

class TestDermatologistAgentRegression(unittest.TestCase):
    """
    Automated Regression Test Suite for Dr. Zavian Dermatology Agent (MedNexus AI).
    Validates Tests A through P covering image analysis, anatomical identification,
    consistency checks, state persistence, single-question enforcement, and tool isolation.
    """

    def test_a_face_photograph(self):
        """Test A: Face photo with visible concern identifies face region and describes findings without inventing diagnoses."""
        raw_bp = "face"
        raw_find = "A 5mm erythematous patch with mild fine scaling on the facial skin."
        result = dl.create_image_analysis_json("dummy_face.jpg", raw_body_part=raw_bp, raw_findings=raw_find)

        self.assertEqual(result["image_type"], "clinical_skin_photo")
        self.assertEqual(result["classification_status"], "identified")
        self.assertEqual(result["anatomical_region"]["value"], "face")
        self.assertEqual(result["anatomical_region"]["status"], "visually_identified")
        self.assertTrue(result["clinical_skin_photo"]["lesion_identified"]["value"])

        # Check visible findings
        features = {vf["feature"]: vf["status"] for vf in result["clinical_skin_photo"]["visible_findings"]}
        self.assertEqual(features.get("redness"), "present")
        self.assertEqual(features.get("scaling"), "present")

        # System message generation
        profile = {"name": "TestUser", "image_analysis": json.dumps(result), "image_explained": False}
        sys_msg = dl.build_system_message(profile)
        self.assertIn("Visual Anatomical Region: face (status: visually_identified)", sys_msg.content)
        self.assertIn("Visual observations alone cannot confirm a definitive diagnosis", sys_msg.content)

    def test_b_nose_photograph(self):
        """Test B: Nose photograph with visible bump mentions nose and describes bump only when visible."""
        raw_bp = "nose"
        raw_find = "A small raised bump with mild surrounding redness on the tip of the nose."
        result = dl.create_image_analysis_json("dummy_nose.jpg", raw_body_part=raw_bp, raw_findings=raw_find)

        self.assertEqual(result["anatomical_region"]["value"], "nose")
        self.assertEqual(result["anatomical_region"]["status"], "visually_identified")
        self.assertTrue(result["clinical_skin_photo"]["lesion_identified"]["value"])
        self.assertIn("tip of the nose", result["clinical_skin_photo"]["lesion_location"])

        # Patient-facing response test
        raw_response = "The photograph appears to show your nose with a small raised bump and mild surrounding redness. How long has the bump been present?"
        sanitized = dl.validate_and_sanitize_response(raw_response, {"lesion_location": "nose"})
        self.assertIn("nose", sanitized.lower())
        self.assertIn("bump", sanitized.lower())
        self.assertEqual(sanitized.count("?"), 1)

    def test_c_other_body_parts(self):
        """Test C: System accurately identifies cheek, forehead, arm, hand, and leg rather than defaulting to face or nose."""
        body_part_samples = [
            ("cheek", "A localized patch on the malar cheek with slight redness.", "cheek"),
            ("forehead", "Dry flaking on the central forehead.", "forehead"),
            ("forearm", "Red papules scattered across the forearm.", "forearm"),
            ("hand", "Erythematous swelling on the dorsal hand.", "hand"),
            ("leg", "Mild scaling along the lower leg.", "leg")
        ]

        for bp_raw, find_raw, expected_label in body_part_samples:
            analysis = dl.create_image_analysis_json(f"dummy_{expected_label}.jpg", raw_body_part=bp_raw, raw_findings=find_raw)
            self.assertEqual(analysis["anatomical_region"]["value"], expected_label, f"Failed for {expected_label}")
            self.assertEqual(analysis["anatomical_region"]["status"], "visually_identified")
            # Must NOT default to nose or face
            if expected_label not in ["nose", "face"]:
                self.assertNotIn(analysis["anatomical_region"]["value"], ["nose", "face"])

    def test_d_no_distinct_lesion(self):
        """Test D: Image with no distinct lesion acknowledges limitation without fabricating bumps or distribution."""
        raw_bp = "forehead"
        raw_find = "The skin appears unremarkable. No distinct lesion, bump, or visible abnormality is identifiable."
        analysis = dl.create_image_analysis_json("dummy_clear.jpg", raw_body_part=raw_bp, raw_findings=raw_find)

        self.assertFalse(analysis["clinical_skin_photo"]["lesion_identified"]["value"])
        self.assertEqual(analysis["clinical_skin_photo"]["lesion_identified"]["status"], "not_identified")
        self.assertIsNone(analysis["clinical_skin_photo"]["lesion_location"])
        self.assertEqual(analysis["clinical_skin_photo"]["distribution"], "not_assessable")
        self.assertIn("No distinct focal lesion", analysis["clinical_skin_photo"]["lesion_description"])

    def test_e_poor_image_quality(self):
        """Test E: Blurry or poorly lit photograph communicates uncertainty and notes image limitations."""
        raw_bp = "uncertain"
        raw_find = "The photograph is extremely blurry, out of focus, and poorly lit. Cannot assess skin textures."
        analysis = dl.create_image_analysis_json("dummy_blurry.jpg", raw_body_part=raw_bp, raw_findings=raw_find)

        self.assertEqual(analysis["image_type"], "unknown")
        self.assertEqual(analysis["classification_status"], "uncertain")
        self.assertEqual(analysis["anatomical_region"]["status"], "not_assessable")
        self.assertTrue(len(analysis["image_quality"]["limitations"]) > 0)
        self.assertIn("blurry", analysis["image_quality"]["limitations"][0].lower())

    def test_f_medical_report(self):
        """Test F: Uploaded medical report is classified as document, extracts data, and does not invent skin findings."""
        raw_bp = "medical document"
        raw_find = (
            "This is a medical document. Laboratory Diagnostic Report.\n"
            "Patient Name: John Anderson.\n"
            "Date of Test: 2026-04-10.\n"
            "Test: Complete Blood Count (CBC) and Skin Scraping.\n"
            "Impression: Tinea Corporis culture positive.\n"
            "Prescription: Terbinafine 1% cream."
        )
        analysis = dl.create_image_analysis_json("dummy_doc.jpg", raw_body_part=raw_bp, raw_findings=raw_find)

        self.assertEqual(analysis["image_type"], "medical_report")
        self.assertTrue(analysis["medical_report"]["is_report"])
        self.assertEqual(analysis["anatomical_region"]["status"], "not_applicable")
        self.assertFalse(analysis["clinical_skin_photo"]["lesion_identified"]["value"])
        self.assertEqual(analysis["clinical_skin_photo"]["lesion_identified"]["status"], "not_applicable")

        # Check extracted patient details
        extracted_names = [d["value"] for d in analysis["medical_report"]["extracted_patient_details"] if d.get("field") == "patient_name"]
        self.assertIn("John Anderson", extracted_names)
        self.assertTrue(len(analysis["medical_report"]["dates"]) > 0)

    def test_g_immediate_image_explanation(self):
        """Test G: Uploading a photograph triggers immediate visual explanation in system workflow prompt."""
        raw_bp = "nose"
        raw_find = "A small discrete erythematous papule on the tip of the nose."
        obs_struct = dl.create_image_analysis_json("dummy_upload.png", raw_body_part=raw_bp, raw_findings=raw_find)
        obs_json = json.dumps(obs_struct)

        # Profile with newly uploaded unaddressed image
        profile = {
            "name": "Sarah",
            "image_analysis": obs_json,
            "image_explained": False,
            "image_inferred_region": "nose",
            "image_inferred_region_status": "visually_identified"
        }
        sys_msg = dl.build_system_message(profile)

        self.assertIn("MANDATORY WORKFLOW FOR THIS RESPONSE - NEW IMAGE UPLOAD", sys_msg.content)
        self.assertIn("immediately acknowledge and describe the photograph", sys_msg.content)
        self.assertIn("tip of the nose", sys_msg.content)

    def test_h_body_part_visible(self):
        """Test H: When body part is already identified visually, assistant uses visual analysis and does not re-ask body part."""
        profile = {
            "name": "David",
            "image_inferred_region": "nose",
            "image_inferred_region_status": "visually_identified",
            "lesion_location": "nose",
            "duration": None
        }

        # Simulate LLM attempting to ask "Which body part is affected?"
        raw_ai_text = "I see your photo. Which body part or area of your body is affected by this bump?"
        sanitized = dl.validate_and_sanitize_response(raw_ai_text, profile)

        # The location question MUST be replaced with next unasked question (duration)
        self.assertNotIn("which body part", sanitized.lower())
        self.assertIn("how long", sanitized.lower())

    def test_i_repeat_image_question(self):
        """Test I: Asking 'What is in the image?' reuses stored analysis and maintains consistent description."""
        analysis = dl.create_image_analysis_json("nose_photo.jpg", raw_body_part="nose", raw_findings="A 4mm raised bump with mild surrounding redness.")
        profile = {
            "name": "Elena",
            "image_analysis": json.dumps(analysis),
            "image_explained": True,
            "image_inferred_region": "nose",
            "image_inferred_region_status": "visually_identified"
        }

        # System message embeds ACTIVE IMAGE VISUAL OBSERVATIONS permanently
        sys_msg = dl.build_system_message(profile)
        self.assertIn("ACTIVE IMAGE VISUAL OBSERVATIONS", sys_msg.content)
        self.assertIn("Visual Anatomical Region: nose", sys_msg.content)
        self.assertIn("4mm raised bump with mild surrounding redness", sys_msg.content)

    def test_j_patient_history_persistence(self):
        """Test J: Full demographic and clinical details (Name, Age, Location, Gender, Duration, Location) persist and are never re-asked."""
        user_message_content = (
            "Name: Salman. Age: 22. Location: Buner. Gender: Male. "
            "Lesion duration: Approximately two weeks. Lesion location: Nose."
        )
        messages = [
            AIMessage(content="Hello! I am Dr. Zavian. How can I help you?"),
            HumanMessage(content=user_message_content)
        ]

        profile = dl.extract_patient_profile(messages)

        # All 6 fields must be parsed reliably
        self.assertEqual(profile["name"], "Salman")
        self.assertEqual(profile["age"], "22")
        self.assertEqual(profile["location"], "Buner")
        self.assertEqual(profile["gender"], "Male")
        self.assertIn("two weeks", profile["duration"].lower())
        self.assertEqual(profile["lesion_location"], "nose")

        # System prompt lists all confirmed fields
        sys_msg = dl.build_system_message(profile)
        self.assertIn("• Name: Salman", sys_msg.content)
        self.assertIn("• Age: 22", sys_msg.content)
        self.assertIn("• Location: Buner", sys_msg.content)
        self.assertIn("• Gender: Male", sys_msg.content)
        self.assertIn("• Duration: Approximately two weeks", sys_msg.content)

        # Sanitizer guarantees assistant does not re-ask any known fields
        draft_redundant = "Thank you. What is your name? How old are you?"
        sanitized = dl.validate_and_sanitize_response(draft_redundant, profile)
        self.assertNotIn("your name", sanitized.lower())
        self.assertNotIn("how old", sanitized.lower())

    def test_k_conflicting_location_sources(self):
        """Test K: Patient-reported location and image-inferred region are kept strictly separate."""
        # Patient reports "cheek", while image analysis recognized "nose"
        analysis = dl.create_image_analysis_json("img.jpg", raw_body_part="nose", raw_findings="Small bump on nose.")
        messages = [
            AIMessage(content="Where is the lesion located?"),
            HumanMessage(content="The bump is on my cheek."),
            SystemMessage(content=f"[Active Image Analysis - img_001]:\n{json.dumps(analysis)}")
        ]
        profile = dl.extract_patient_profile(messages)

        self.assertEqual(profile["lesion_location"], "cheek")
        self.assertEqual(profile["image_inferred_region"], "nose")

        # In system prompt, both sources remain distinct
        sys_msg = dl.build_system_message(profile)
        self.assertIn("Patient-Reported Lesion Location: cheek", sys_msg.content)
        self.assertIn("Image-Inferred Anatomical Region (from photo): nose", sys_msg.content)

    def test_l_contradictory_observations(self):
        """Test L: Contradictory observations (e.g. no lesion but asserted bump, or redness present and not_evident) are resolved."""
        contradictory_data = {
            "image_id": "img_test_contra",
            "image_type": "clinical_skin_photo",
            "classification_status": "identified",
            "anatomical_region": {"value": "nose", "status": "visually_identified"},
            "clinical_skin_photo": {
                "lesion_identified": {"value": False, "status": "not_identified"},
                "lesion_location": "tip of the nose",
                "lesion_description": "A prominent raised bump is visible on the nose.",
                "visible_findings": [
                    {"feature": "redness", "status": "present"},
                    {"feature": "redness", "status": "not_evident"},
                    {"feature": "raised_surface", "status": "present"}
                ],
                "distribution": "discrete_isolated"
            },
            "medical_report": {"is_report": False},
            "image_quality": {"limitations": []},
            "diagnostic_limitations": []
        }

        validated = dl._validate_consistency(contradictory_data)
        photo = validated["clinical_skin_photo"]

        # Since lesion_identified is False:
        self.assertIsNone(photo["lesion_location"])
        self.assertEqual(photo["distribution"], "not_assessable")
        self.assertIn("No distinct focal lesion", photo["lesion_description"])

        # Conflicting redness present vs not_evident must be resolved to uncertain
        features = {vf["feature"]: vf["status"] for vf in photo["visible_findings"]}
        self.assertEqual(features.get("redness"), "uncertain")
        # Raised surface must be stripped because lesion_identified is False
        self.assertNotIn("raised_surface", features)

    def test_m_tool_failure(self):
        """Test M: Visual tool failure returns clear error structure and does not pretend analysis succeeded."""
        struct = dl.create_image_analysis_json("bad_file.png", error_msg="The image could not be loaded because the file is corrupted.")
        self.assertEqual(struct["classification_status"], "failed")
        self.assertEqual(struct["anatomical_region"]["status"], "not_assessable")
        self.assertIn("corrupted", struct["image_quality"]["limitations"][0])

        profile = {"image_analysis": json.dumps(struct), "image_explained": False}
        sys_msg = dl.build_system_message(profile)
        self.assertIn("failed", sys_msg.content)

    def test_n_groq_rate_limit(self):
        """Test N: Groq HTTP 429 rate limit triggers bounded retries with backoff and safe fallback response."""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Groq HTTP 429: rate limit exceeded, please try again in 0.5s")

        # Invoke retry helper with small delay for test speed
        res = dl.invoke_llm_with_retry(mock_llm, [HumanMessage(content="Hello")], max_retries=1, base_delay=0.1, max_delay=0.2)

        self.assertIsInstance(res, AIMessage)
        self.assertIn("high consultation volume", res.content.lower())
        self.assertIn("safely saved", res.content.lower())
        # Confirms invocation did not loop indefinitely
        self.assertEqual(mock_llm.invoke.call_count, 2)

    def test_o_internal_output_isolation(self):
        """Test O: Internal raw markdown tables (medicines or diagnostic lists) and system alert strings are stripped."""
        profile = {"name": "Alex", "lesion_location": "cheek"}
        raw_ai_message = (
            "[System Alert: User uploaded an image. Local Path: D:/MedNexus/static/dermatalogist_upload/123.jpg]\n"
            "Here is the retrieved differential table:\n"
            "| Condition | Possibility | Evidence |\n"
            "|---|---|---|\n"
            "| Folliculitis | High | Papules |\n"
            "| Herpes Simplex | Low | No clustering |\n"
            "How long has this been present?"
        )

        sanitized = dl.validate_and_sanitize_response(raw_ai_message, profile)
        self.assertNotIn("| Condition |", sanitized)
        self.assertNotIn("[System Alert", sanitized)
        self.assertNotIn("D:/MedNexus", sanitized)
        self.assertIn("How long has this been present?", sanitized)

    def test_p_end_to_end_replay(self):
        """Test P: Multi-turn end-to-end replay preserves demographics, explains image promptly, and strictly enforces single question."""
        conversation = []

        # Turn 1: Patient supplies demographics in structured format
        conversation.append(HumanMessage(content="Name: Salman. Age: 22. Location: Buner. Gender: Male."))
        p1 = dl.extract_patient_profile(conversation)
        self.assertEqual(p1["name"], "Salman")
        self.assertEqual(p1["age"], "22")
        self.assertEqual(p1["location"], "Buner")
        self.assertEqual(p1["gender"], "Male")

        # Turn 2: Patient uploads nose photograph
        analysis_nose = dl.create_image_analysis_json(
            "user_salman_nose.png",
            raw_body_part="nose",
            raw_findings="A small discrete raised bump with mild surrounding erythema on the tip of the nose."
        )
        conversation.append(AIMessage(content="Hello Salman. What symptoms are you noticing?"))
        conversation.append(HumanMessage(content="[System Alert: User uploaded an image. Local Path: static/dermatalogist_upload/user_salman_nose.png] Here is a picture of it."))
        conversation.append(SystemMessage(content=f"[Active Image Analysis - img_nose]:\n{json.dumps(analysis_nose)}"))

        p2 = dl.extract_patient_profile(conversation)
        self.assertEqual(p2["image_inferred_region"], "nose")
        self.assertFalse(p2["image_explained"])

        # System message mandates immediate photograph explanation
        sys2 = dl.build_system_message(p2)
        self.assertIn("MANDATORY WORKFLOW FOR THIS RESPONSE - NEW IMAGE UPLOAD", sys2.content)
        self.assertIn("tip of the nose", sys2.content)

        # AI responds explaining photograph
        ai_resp_t2 = "The photograph appears to show your nose with a small raised bump and mild surrounding redness. How long has the bump been present?"
        conversation.append(AIMessage(content=ai_resp_t2))

        # Turn 3: Patient says "You can see it in the image" and asks "What is in the image?"
        conversation.append(HumanMessage(content="What is in the image? You can see it."))
        p3 = dl.extract_patient_profile(conversation)
        self.assertTrue(p3["image_explained"])
        self.assertEqual(p3["image_inferred_region"], "nose")

        # Turn 4: Patient supplies duration and confirms location
        conversation.append(AIMessage(content="In the photograph, I can see a small raised bump with mild redness on the tip of your nose. How long has it been present?"))
        conversation.append(HumanMessage(content="It has been there for approximately two weeks on my nose. Pain is 3/10."))
        p4 = dl.extract_patient_profile(conversation)
        self.assertEqual(p4["duration"], "approximately two weeks")
        self.assertEqual(p4["lesion_location"], "nose")
        self.assertEqual(p4["pain"], "3/10")

        # System message retains all confirmed fields across the entire conversation
        sys4 = dl.build_system_message(p4)
        self.assertIn("• Name: Salman", sys4.content)
        self.assertIn("• Age: 22", sys4.content)
        self.assertIn("• Location: Buner", sys4.content)
        self.assertIn("• Gender: Male", sys4.content)
        self.assertIn("• Duration: approximately two weeks", sys4.content)
        self.assertIn("• Patient-Reported Lesion Location: nose", sys4.content)
        self.assertIn("• Image-Inferred Anatomical Region (from photo): nose", sys4.content)


if __name__ == "__main__":
    unittest.main()
