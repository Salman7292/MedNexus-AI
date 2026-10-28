import json
import unittest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import dermatologist_logic as dl

class TestSalmanConsultationReplay(unittest.TestCase):
    def test_salman_transcript_state_progression(self):
        """
        Replays Salman's consultation turn-by-turn to verify:
        1. Contextual interpretation of short replies ('No.', '5.', 'Not soft.', 'Red.').
        2. Detection of patient confusion and clarification needs.
        3. Contradiction resolution (initial denial vs 5/10 score).
        4. Elimination of infinite questioning loops.
        5. Proper transition to Phase 4 differential and medical report offering.
        """
        conversation = []

        # Phase A: Demographics
        conversation.append(HumanMessage(content="Hello."))
        conversation.append(AIMessage(content="Hello! I am Dr. Zavian, an AI dermatology specialist at MedNexus AI. May I have your name, please?"))
        conversation.append(HumanMessage(content="Salman."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["name"], "Salman")

        conversation.append(AIMessage(content="Salman, could you tell me your age, please?"))
        conversation.append(HumanMessage(content="22."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["age"], "22")

        conversation.append(AIMessage(content="Could you share your current location (city or region), please?"))
        conversation.append(HumanMessage(content="Buner."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["location"], "Buner")

        conversation.append(AIMessage(content="May I know your gender, please?"))
        conversation.append(HumanMessage(content="Male."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["gender"], "Male")

        # Phase B: Image upload & explanation
        analysis_nose = dl.create_image_analysis_json(
            "dummy_salman.jpg",
            raw_body_part="nose",
            raw_findings="Multiple dark pinpoint comedones (blackheads) on the nasal tip and bridge, with a focal 4mm firm erythematous area."
        )
        conversation.append(AIMessage(content="Where on your body are you noticing the skin concern?"))
        conversation.append(HumanMessage(content="[System Alert: User uploaded an image. Local Path: static/dermatalogist_upload/dummy_salman.jpg] This is my condition right now."))
        conversation.append(SystemMessage(content=f"[Active Image Analysis - img_salman]:\n{json.dumps(analysis_nose)}"))
        
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["image_inferred_region"], "nose")

        # User asks what is in the image
        conversation.append(AIMessage(content="The photograph shows your nose with multiple dark pinpoint comedones (blackheads) and a localized reddish area. How long have you noticed this condition?"))
        conversation.append(HumanMessage(content="Can you explain what is visible in the image?"))
        conversation.append(AIMessage(content="In the photograph, I observe blackheads on the nasal bridge along with a small red area. How long have you had these spots?"))
        conversation.append(HumanMessage(content="About three weeks."))
        p = dl.extract_patient_profile(conversation)
        self.assertIn("three weeks", p["duration"])

        # Phase C: Confusion handling and negative answers
        conversation.append(AIMessage(content="On a scale of 0 to 10, how would you rate any pain or tenderness you feel on your nose?"))
        conversation.append(HumanMessage(content="I don't understand what you mean."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["clarification_needed"], "pain")

        conversation.append(AIMessage(content="Tenderness means any soreness or pain when you touch the spot. Do you feel any pain there?"))
        conversation.append(HumanMessage(content="No."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["pain"], "0/10 (denied)")

        # Prior treatments inquiry
        conversation.append(AIMessage(content="Have you used any cleansers, creams, or other treatments on the blackheads so far?"))
        conversation.append(HumanMessage(content="No, I haven't used anything yet."))
        p = dl.extract_patient_profile(conversation)
        self.assertIn("None", p["previous_treatments"])

        # Triggers inquiry
        conversation.append(AIMessage(content="Have you noticed any factors—such as heat, sun exposure, or stress—that seem to make the spots on your nose worse?"))
        conversation.append(HumanMessage(content="No."))
        p = dl.extract_patient_profile(conversation)
        self.assertIn("None", p["triggers"])

        # Contradiction resolution: Patient clarifies pain rating as 5
        conversation.append(AIMessage(content="How would you describe any discomfort or soreness in that area on a scale of 1 to 10?"))
        conversation.append(HumanMessage(content="5."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["pain"], "5/10")

        # Itching and confusion
        conversation.append(AIMessage(content="On a scale of 0 to 10, how would you rate any itching you feel on your nose?"))
        conversation.append(HumanMessage(content="What does itching mean?"))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["clarification_needed"], "itching")

        conversation.append(AIMessage(content="Itching is that uncomfortable, tickling sensation on the skin that makes you want to scratch it. Do you feel that?"))
        conversation.append(HumanMessage(content="No."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["itching"], "0/10 (denied)")

        # Spreading question
        conversation.append(AIMessage(content="Have you noticed any changes or spreading in that area recently?"))
        conversation.append(HumanMessage(content="No."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["spread"], "None (stable, not spreading)")

        # Appearance details: firmness and color
        conversation.append(AIMessage(content="What does the skin on your nose feel like when touched?"))
        conversation.append(HumanMessage(content="Not soft."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["firmness"], "Firm (not soft)")

        conversation.append(AIMessage(content="Is the spot red or pink in color?"))
        conversation.append(HumanMessage(content="Red."))
        p = dl.extract_patient_profile(conversation)
        self.assertEqual(p["redness"], "Red")

        # Associated pus/crust
        conversation.append(AIMessage(content="Do you see any visible pus or crust on the area?"))
        conversation.append(HumanMessage(content="Yes."))
        p = dl.extract_patient_profile(conversation)
        self.assertIn("Present", p["associated_symptoms"])

        # Check completed state
        sys_msg = dl.build_system_message(p)
        self.assertIn("• Name: Salman", sys_msg.content)
        self.assertIn("• Age: 22", sys_msg.content)
        self.assertIn("• Location: Buner", sys_msg.content)
        self.assertIn("• Gender: Male", sys_msg.content)
        self.assertIn("• Duration: about three weeks", sys_msg.content)
        self.assertIn("• Pain Level: 5/10", sys_msg.content)
        self.assertIn("• Itching Level: 0/10 (denied)", sys_msg.content)
        self.assertIn("• Spreading / Progression: None (stable, not spreading)", sys_msg.content)
        self.assertIn("• Surface Texture / Firmness: Firm (not soft)", sys_msg.content)
        self.assertIn("• Color / Redness: Red", sys_msg.content)
        
        # Check Phase 4 mandatory transition trigger in prompt
        self.assertIn("[PHASE 4 TRANSITION - MANDATORY ACTION]", sys_msg.content)
        self.assertIn("YOU ARE FORBIDDEN FROM ASKING MORE HISTORY QUESTIONS", sys_msg.content)

        # Sanitizer guarantees assistant does not re-ask spreading or triggers
        draft_redundant = "Based on this, have you noticed any changes or spreading in that area recently? Have you noticed any triggers?"
        sanitized = dl.validate_and_sanitize_response(draft_redundant, p)
        self.assertNotIn("spreading", sanitized.lower())
        self.assertNotIn("triggers", sanitized.lower())
        self.assertIn("medical summary report", sanitized.lower())

if __name__ == "__main__":
    unittest.main()
