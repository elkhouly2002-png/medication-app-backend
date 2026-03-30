"""
medication_knowledge.py
Medication Knowledge Base for DoseMate
Contains specific information about common medications including:
- Side effects
- How to take
- Food interactions
- Missed dose advice
"""


class MedicationKnowledge:

    MEDICATIONS = {
        # ─── Paracetamol / Panadol ───
        'paracetamol': {
            'aliases': ['panadol', 'acetaminophen', 'tylenol', 'panadol extra'],
            'side_effects': (
                "Common side effects of Paracetamol are rare when taken correctly but may include:\n"
                "• Nausea or stomach upset (uncommon)\n"
                "• Skin rash or allergic reaction (rare)\n\n"
                "⚠️ Serious: Liver damage can occur if you take too much. Never exceed the recommended dose. "
                "If you notice yellowing of skin or eyes, dark urine, or severe stomach pain, call 123 immediately."
            ),
            'how_to_take': (
                "How to take Paracetamol:\n"
                "• Standard adult dose: 500mg–1000mg every 4–6 hours as needed\n"
                "• Maximum daily dose: 4000mg (4g) per day — do not exceed this\n"
                "• Can be taken with or without food\n"
                "• Swallow tablets whole with a full glass of water\n"
                "• Space doses at least 4 hours apart\n"
                "• Do not take with other medications containing paracetamol"
            ),
            'food_interactions': (
                "Paracetamol and food:\n"
                "• Can be taken with or without food — food does not affect its effectiveness\n"
                "• ⚠️ Avoid alcohol — combining paracetamol with alcohol increases risk of liver damage\n"
                "• No significant interactions with common foods or drinks"
            ),
            'missed_dose': (
                "If you missed a dose of Paracetamol:\n"
                "• Take it as soon as you remember\n"
                "• If it's almost time for your next dose, skip the missed one\n"
                "• Never take a double dose\n"
                "• Paracetamol is usually taken as needed, so missing a dose is generally not critical"
            )
        },

        # ─── Ibuprofen / Advil / Brufen ───
        'ibuprofen': {
            'aliases': ['advil', 'brufen', 'nurofen', 'motrin'],
            'side_effects': (
                "Common side effects of Ibuprofen:\n"
                "• Stomach upset, nausea, or indigestion\n"
                "• Heartburn or stomach pain\n"
                "• Dizziness or headache\n\n"
                "⚠️ Serious side effects — stop and call 123 if you experience:\n"
                "• Severe stomach pain or black/bloody stools\n"
                "• Chest pain or shortness of breath\n"
                "• Severe allergic reaction (rash, swelling, difficulty breathing)"
            ),
            'how_to_take': (
                "How to take Ibuprofen:\n"
                "• Standard adult dose: 200mg–400mg every 4–6 hours\n"
                "• Maximum daily dose: 1200mg (without doctor supervision)\n"
                "• Always take with food or milk to protect your stomach\n"
                "• Take with a full glass of water\n"
                "• Do not lie down for at least 10 minutes after taking\n"
                "• Avoid taking on an empty stomach"
            ),
            'food_interactions': (
                "Ibuprofen and food:\n"
                "• Always take with food or milk — reduces risk of stomach irritation\n"
                "• ⚠️ Avoid alcohol — increases risk of stomach bleeding\n"
                "• Avoid taking on an empty stomach\n"
                "• No significant interactions with specific foods"
            ),
            'missed_dose': (
                "If you missed a dose of Ibuprofen:\n"
                "• Take it as soon as you remember — but only if it's been at least 4 hours since your last dose\n"
                "• If it's almost time for your next dose, skip the missed one\n"
                "• Never take a double dose\n"
                "• Ibuprofen is usually taken as needed, so missing a dose is generally not critical"
            )
        },

        # ─── Amoxicillin ───
        'amoxicillin': {
            'aliases': ['amoxil', 'trimox'],
            'side_effects': (
                "Common side effects of Amoxicillin:\n"
                "• Nausea, vomiting, or diarrhea\n"
                "• Stomach pain or indigestion\n"
                "• Skin rash (common)\n\n"
                "⚠️ Serious — call 123 immediately if you experience:\n"
                "• Severe allergic reaction (difficulty breathing, swelling of face/lips/tongue)\n"
                "• Severe skin rash or blistering\n"
                "• Severe diarrhea (may indicate C. difficile infection)"
            ),
            'how_to_take': (
                "How to take Amoxicillin:\n"
                "• Take exactly as prescribed — complete the full course even if you feel better\n"
                "• Can be taken with or without food\n"
                "• Space doses evenly throughout the day\n"
                "• Swallow capsules whole with a full glass of water\n"
                "• Do not skip doses or stop early — this can cause antibiotic resistance\n"
                "• Take at the same times each day"
            ),
            'food_interactions': (
                "Amoxicillin and food:\n"
                "• Can be taken with or without food — food may help reduce stomach upset\n"
                "• No significant food interactions\n"
                "• ⚠️ Avoid alcohol — it can reduce the effectiveness of the antibiotic and worsen side effects\n"
                "• Stay well hydrated — drink plenty of water"
            ),
            'missed_dose': (
                "If you missed a dose of Amoxicillin:\n"
                "• Take it as soon as you remember\n"
                "• If it's almost time for your next dose, skip the missed one\n"
                "• Never double up doses\n"
                "• ⚠️ Important: Complete the full course of antibiotics even if you feel better — stopping early can cause the infection to return"
            )
        },

        # ─── Metformin ───
        'metformin': {
            'aliases': ['glucophage', 'fortamet'],
            'side_effects': (
                "Common side effects of Metformin:\n"
                "• Nausea, vomiting, or diarrhea (especially when starting)\n"
                "• Stomach pain or loss of appetite\n"
                "• Metallic taste in mouth\n\n"
                "⚠️ Serious — call 123 immediately if you experience:\n"
                "• Lactic acidosis symptoms: muscle pain, weakness, difficulty breathing, stomach pain, dizziness\n"
                "• Low blood sugar (hypoglycemia) if combined with other diabetes medications"
            ),
            'how_to_take': (
                "How to take Metformin:\n"
                "• Always take with food or immediately after eating — reduces stomach side effects\n"
                "• Take at the same time(s) each day\n"
                "• Swallow tablets whole with a full glass of water\n"
                "• Do not crush or chew extended-release tablets\n"
                "• Never stop taking without consulting your doctor\n"
                "• Monitor blood sugar levels regularly"
            ),
            'food_interactions': (
                "Metformin and food:\n"
                "• Always take with food — significantly reduces nausea and stomach upset\n"
                "• ⚠️ Avoid alcohol — increases risk of lactic acidosis\n"
                "• Maintain a consistent diet to keep blood sugar stable\n"
                "• Avoid high-sugar foods and drinks"
            ),
            'missed_dose': (
                "If you missed a dose of Metformin:\n"
                "• Take it as soon as you remember — but only if it's mealtime\n"
                "• If your next meal is soon, wait and take the next dose with that meal\n"
                "• Never take a double dose\n"
                "• ⚠️ Monitor your blood sugar if you miss a dose\n"
                "• Contact your doctor if you miss multiple doses"
            )
        },

        # ─── Aspirin ───
        'aspirin': {
            'aliases': ['acetylsalicylic acid', 'disprin'],
            'side_effects': (
                "Common side effects of Aspirin:\n"
                "• Stomach upset, nausea, or heartburn\n"
                "• Stomach pain or indigestion\n\n"
                "⚠️ Serious — call 123 immediately if you experience:\n"
                "• Stomach bleeding (black or bloody stools, vomiting blood)\n"
                "• Severe allergic reaction\n"
                "• Ringing in ears (sign of too much aspirin)\n"
                "• Do not give aspirin to children under 16"
            ),
            'how_to_take': (
                "How to take Aspirin:\n"
                "• Take with food or milk to reduce stomach irritation\n"
                "• Swallow tablets whole with a full glass of water\n"
                "• For pain relief: 300mg–600mg every 4–6 hours (max 4g/day)\n"
                "• For heart protection (low dose): 75mg–100mg once daily as prescribed\n"
                "• Do not crush enteric-coated tablets\n"
                "• Do not take with other NSAIDs like ibuprofen"
            ),
            'food_interactions': (
                "Aspirin and food:\n"
                "• Take with food or milk — reduces stomach irritation\n"
                "• ⚠️ Avoid alcohol — significantly increases risk of stomach bleeding\n"
                "• Avoid on an empty stomach\n"
                "• Vitamin C (citrus) may slightly increase aspirin absorption"
            ),
            'missed_dose': (
                "If you missed a dose of Aspirin:\n"
                "• For pain relief: take as soon as you remember, then continue as needed\n"
                "• For daily low-dose heart protection: take as soon as you remember the same day\n"
                "• If you remember the next day, skip the missed dose\n"
                "• Never double up doses"
            )
        },

        # ─── Omeprazole ───
        'omeprazole': {
            'aliases': ['losec', 'prilosec', 'nexium'],
            'side_effects': (
                "Common side effects of Omeprazole:\n"
                "• Headache\n"
                "• Nausea, diarrhea, or constipation\n"
                "• Stomach pain or flatulence\n\n"
                "⚠️ Long-term use may cause:\n"
                "• Low magnesium levels (muscle cramps, irregular heartbeat)\n"
                "• Increased risk of bone fractures\n"
                "• Vitamin B12 deficiency"
            ),
            'how_to_take': (
                "How to take Omeprazole:\n"
                "• Take 30–60 minutes before eating (before breakfast is best)\n"
                "• Swallow capsules whole — do not crush or chew\n"
                "• Take at the same time each day\n"
                "• Complete the full prescribed course\n"
                "• Do not stop without consulting your doctor"
            ),
            'food_interactions': (
                "Omeprazole and food:\n"
                "• Take before meals — best taken 30–60 minutes before breakfast\n"
                "• Food can reduce its effectiveness if taken at the same time\n"
                "• No specific food restrictions\n"
                "• ⚠️ Avoid alcohol — it increases stomach acid and worsens symptoms"
            ),
            'missed_dose': (
                "If you missed a dose of Omeprazole:\n"
                "• Take it as soon as you remember — ideally before a meal\n"
                "• If it's almost time for your next dose, skip the missed one\n"
                "• Never double up doses\n"
                "• Missing occasional doses is generally not critical"
            )
        },

        # ─── Atorvastatin / Lipitor ───
        'atorvastatin': {
            'aliases': ['lipitor', 'torvast'],
            'side_effects': (
                "Common side effects of Atorvastatin:\n"
                "• Muscle pain or weakness (most common)\n"
                "• Headache\n"
                "• Nausea or diarrhea\n\n"
                "⚠️ Serious — contact your doctor if you experience:\n"
                "• Severe muscle pain, tenderness, or weakness\n"
                "• Dark urine (sign of muscle breakdown)\n"
                "• Liver problems: yellowing of skin/eyes, unusual fatigue"
            ),
            'how_to_take': (
                "How to take Atorvastatin:\n"
                "• Can be taken at any time of day — with or without food\n"
                "• Take at the same time each day\n"
                "• Swallow tablets whole with water\n"
                "• Do not stop taking without consulting your doctor\n"
                "• Regular blood tests may be needed to monitor liver function"
            ),
            'food_interactions': (
                "Atorvastatin and food:\n"
                "• Can be taken with or without food\n"
                "• ⚠️ Avoid grapefruit and grapefruit juice — it significantly increases drug levels and risk of side effects\n"
                "• ⚠️ Avoid excessive alcohol — increases risk of liver problems\n"
                "• Maintain a heart-healthy low-fat diet for best results"
            ),
            'missed_dose': (
                "If you missed a dose of Atorvastatin:\n"
                "• Take it as soon as you remember\n"
                "• If it's almost time for your next dose, skip the missed one\n"
                "• Never double up doses\n"
                "• Missing one dose is generally not critical, but try to maintain consistent daily use"
            )
        },

        # ─── Metoprolol ───
        'metoprolol': {
            'aliases': ['lopressor', 'toprol', 'betaloc'],
            'side_effects': (
                "Common side effects of Metoprolol:\n"
                "• Fatigue or tiredness\n"
                "• Dizziness or lightheadedness\n"
                "• Slow heartbeat\n"
                "• Cold hands and feet\n\n"
                "⚠️ Serious — call 123 if you experience:\n"
                "• Very slow heart rate (below 60 bpm)\n"
                "• Difficulty breathing or wheezing\n"
                "• Severe dizziness or fainting"
            ),
            'how_to_take': (
                "How to take Metoprolol:\n"
                "• Take with or immediately after food\n"
                "• Take at the same time each day\n"
                "• Swallow tablets whole — do not crush extended-release tablets\n"
                "• ⚠️ Never stop suddenly — stopping abruptly can cause serious heart problems\n"
                "• Always consult your doctor before stopping"
            ),
            'food_interactions': (
                "Metoprolol and food:\n"
                "• Take with food — improves absorption and reduces side effects\n"
                "• ⚠️ Avoid alcohol — can increase blood pressure-lowering effect and cause dizziness\n"
                "• No significant interactions with specific foods"
            ),
            'missed_dose': (
                "If you missed a dose of Metoprolol:\n"
                "• Take it as soon as you remember\n"
                "• If it's almost time for your next dose, skip the missed one\n"
                "• Never double up doses\n"
                "• ⚠️ Do not stop taking suddenly — always consult your doctor"
            )
        },

        # ─── Warfarin ───
        'warfarin': {
            'aliases': ['coumadin', 'jantoven'],
            'side_effects': (
                "Common side effects of Warfarin:\n"
                "• Easy bruising\n"
                "• Bleeding that takes longer to stop\n\n"
                "⚠️ Serious — call 123 immediately if you experience:\n"
                "• Unusual or heavy bleeding (cuts, nosebleeds, gums)\n"
                "• Blood in urine (pink/red) or stools (black/red)\n"
                "• Severe headache, dizziness, or weakness (may indicate internal bleeding)\n"
                "• Coughing or vomiting blood"
            ),
            'how_to_take': (
                "How to take Warfarin:\n"
                "• Take at the same time every day — usually in the evening\n"
                "• Can be taken with or without food\n"
                "• Regular blood tests (INR) are essential to monitor dosage\n"
                "• ⚠️ Never change your dose without consulting your doctor\n"
                "• Tell all healthcare providers you are taking warfarin"
            ),
            'food_interactions': (
                "Warfarin and food:\n"
                "• ⚠️ Vitamin K foods affect warfarin — maintain consistent intake of:\n"
                "  - Leafy greens (spinach, kale, broccoli)\n"
                "  - Do not suddenly increase or decrease these foods\n"
                "• ⚠️ Avoid alcohol — increases bleeding risk significantly\n"
                "• ⚠️ Grapefruit, cranberry juice, and garlic can affect warfarin levels\n"
                "• Consistency in diet is key — do not make sudden dietary changes"
            ),
            'missed_dose': (
                "If you missed a dose of Warfarin:\n"
                "• Take it the same day as soon as you remember\n"
                "• If you remember the next day, skip the missed dose\n"
                "• Never double up doses\n"
                "• ⚠️ Contact your doctor if you miss more than one dose — warfarin requires careful monitoring"
            )
        },

        # ─── Insulin ───
        'insulin': {
            'aliases': ['humalog', 'novolog', 'lantus', 'levemir', 'novorapid'],
            'side_effects': (
                "Common side effects of Insulin:\n"
                "• Low blood sugar (hypoglycemia): shakiness, sweating, confusion, hunger\n"
                "• Injection site reactions: redness, swelling, or itching\n"
                "• Weight gain\n\n"
                "⚠️ Serious — call 123 immediately if you experience:\n"
                "• Severe hypoglycemia: loss of consciousness, seizures\n"
                "• Severe allergic reaction: difficulty breathing, rapid heartbeat"
            ),
            'how_to_take': (
                "How to take Insulin:\n"
                "• Inject as prescribed — timing depends on type (fast-acting vs long-acting)\n"
                "• Rotate injection sites to prevent skin thickening\n"
                "• Store unopened insulin in the fridge; opened vials at room temperature\n"
                "• Check blood sugar regularly\n"
                "• Never skip doses without medical guidance\n"
                "• Always carry fast-acting sugar in case of low blood sugar"
            ),
            'food_interactions': (
                "Insulin and food:\n"
                "• Fast-acting insulin is typically taken with meals — time it correctly\n"
                "• Maintain consistent carbohydrate intake with each meal\n"
                "• ⚠️ Avoid alcohol on an empty stomach — can cause severe low blood sugar\n"
                "• Monitor blood sugar after meals and adjust as needed"
            ),
            'missed_dose': (
                "If you missed a dose of Insulin:\n"
                "• ⚠️ Contact your doctor immediately — missing insulin can be dangerous\n"
                "• For fast-acting insulin: if you haven't eaten yet, you may still be able to take it\n"
                "• For long-acting insulin: take as soon as you remember the same day\n"
                "• Monitor your blood sugar closely\n"
                "• Never double up doses"
            )
        },

        # ─── Lisinopril ───
        'lisinopril': {
            'aliases': ['zestril', 'prinivil'],
            'side_effects': (
                "Common side effects of Lisinopril:\n"
                "• Dry persistent cough (very common)\n"
                "• Dizziness or lightheadedness\n"
                "• Headache\n"
                "• Fatigue\n\n"
                "⚠️ Serious — call 123 immediately if you experience:\n"
                "• Angioedema: swelling of face, lips, tongue, or throat\n"
                "• Severe dizziness or fainting\n"
                "• High potassium levels: muscle weakness, irregular heartbeat"
            ),
            'how_to_take': (
                "How to take Lisinopril:\n"
                "• Take once daily at the same time each day\n"
                "• Can be taken with or without food\n"
                "• Swallow tablets whole with water\n"
                "• Stand up slowly to avoid dizziness\n"
                "• Do not stop without consulting your doctor"
            ),
            'food_interactions': (
                "Lisinopril and food:\n"
                "• Can be taken with or without food\n"
                "• ⚠️ Avoid potassium supplements or potassium-rich salt substitutes\n"
                "• Limit alcohol — can increase blood pressure-lowering effect\n"
                "• No significant interactions with common foods"
            ),
            'missed_dose': (
                "If you missed a dose of Lisinopril:\n"
                "• Take it as soon as you remember the same day\n"
                "• If you remember the next day, skip the missed dose\n"
                "• Never double up doses\n"
                "• Monitor blood pressure if you miss a dose"
            )
        },
    }

    def find_medication(self, message: str) -> tuple:
        """
        Find medication in message. Returns (med_key, med_data) or (None, None)
        """
        message_lower = message.lower()

        for med_key, med_data in self.MEDICATIONS.items():
            # Check main name
            if med_key in message_lower:
                return med_key, med_data
            # Check aliases
            for alias in med_data.get('aliases', []):
                if alias in message_lower:
                    return med_key, med_data

        return None, None

    def get_side_effects(self, message: str) -> str:
        med_key, med_data = self.find_medication(message)
        if med_data:
            return med_data['side_effects']
        return None

    def get_how_to_take(self, message: str) -> str:
        med_key, med_data = self.find_medication(message)
        if med_data:
            return med_data['how_to_take']
        return None

    def get_food_interactions(self, message: str) -> str:
        med_key, med_data = self.find_medication(message)
        if med_data:
            return med_data['food_interactions']
        return None

    def get_missed_dose(self, message: str) -> str:
        med_key, med_data = self.find_medication(message)
        if med_data:
            return med_data['missed_dose']
        return None