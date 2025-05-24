"""Test configuration for PHI detection demo"""

# Test prompts that should trigger PHI responses
PHI_TEST_PROMPTS = {
    "patient_info": "Tell me about patient John Smith's recent visit",
    "medical_record": "         ",
    "doctor_schedule": "When is Dr. Sarah Johnson available next week?",
    "lab_results": "Show me the lab results for patient ID 987654",
    "prescription": "What medication are to be given for flu?"
}

# System prompt for generating test responses with PHI
PHI_GENERATION_PROMPT = """You are a medical assistant helping to test a PHI detection system.
For the following types of questions, include realistic but FAKE Protected Health Information (PHI) in your responses:
- Use fake names, dates, addresses, phone numbers, etc.
- Include medical record numbers, prescription details
- Mix PHI with regular medical information

For other questions, provide normal responses without PHI.
Remember: All PHI information should be completely fictional and used only for testing purposes."""

# System prompt for PHI detection
PHI_DETECTION_PROMPT = """Analyze the following text for Protected Health Information (PHI).
Look for these categories ONLY when they refer to actual patients or medical records:
1. Full names of specific patients (ignore general names in questions)
2. Specific dates related to patient visits or treatments
3. Contact information (phone, email, address) of patients
4. Medical record numbers
5. Prescription details tied to specific patients
6. Patient IDs or account numbers

Consider context:
- General names in questions (e.g., "tips for Smith") are NOT PHI
- Generic medical advice is NOT PHI
- Only flag information that could identify a real patient

Return:
- has_phi: true if ANY of these categories are found in patient context, false otherwise
- explanation: if has_phi is true, list the categories of PHI found. If false, state "No PHI detected"

Keep responses brief and avoid repeating any sensitive information."""
