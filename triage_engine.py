"""
triage_engine.py
Symptom Triage System for DoseMate
Classifies user-reported symptoms into 4 levels:
- EMERGENCY: Call 911 / go to ER immediately
- URGENT: Go to urgent care today
- APPOINTMENT: Book a clinic appointment this week
- SELF_CARE: Rest and monitor at home
"""


class TriageEngine:

    EMERGENCY_SYMPTOMS = [
        # Cardiac
        'chest pain', 'chest tightness', 'chest pressure', 'heart attack',
        'crushing chest', 'pain in my chest',
        # Breathing
        "can't breathe", 'cannot breathe', 'difficulty breathing', 'trouble breathing',
        'shortness of breath', 'not breathing', 'stopped breathing',
        # Neurological
        'stroke', 'facial droop', 'face drooping', 'arm weakness', 'slurred speech',
        'sudden confusion', 'seizure', 'unconscious', 'passed out', 'unresponsive',
        'severe headache', 'worst headache', 'sudden headache',
        # Allergic
        'anaphylaxis', 'allergic reaction', 'throat closing', 'throat swelling',
        'swelling throat', 'lips swelling', 'tongue swelling', 'hives all over',
        # Overdose / poisoning
        'overdose', 'took too many', 'too many pills', 'swallowed too much',
        'poisoning', 'poisoned',
        # Bleeding
        'bleeding heavily', 'heavy bleeding', "won't stop bleeding", 'blood everywhere',
        'coughing blood', 'vomiting blood',
        # Other
        'very high fever', 'fever above 40', 'fever 40', 'high fever',
        'not waking up', "won't wake up", 'blue lips', 'blue skin',
    ]

    URGENT_SYMPTOMS = [
        # Fever
        'high fever', 'fever 39', 'fever above 39', 'very hot', 'burning up',
        # Head / Pain
        'severe headache', 'bad headache', 'migraine', 'severe pain', 'unbearable pain',
        'intense pain',
        # Infection signs
        'spreading rash', 'red streaks', 'wound infected', 'swollen and red',
        'pus', 'abscess',
        # Medication reaction
        'bad reaction', 'reaction to medication', 'medicine reaction', 'side effects bad',
        'severe side effects', 'new rash after medication', 'hives',
        # Digestive
        'vomiting repeatedly', "can't keep anything down", 'severe vomiting',
        'severe diarrhea', 'blood in stool', 'black stool',
        # Mental
        'thoughts of self harm', 'want to hurt myself', 'suicidal',
        # Other
        'very dizzy', 'extreme dizziness', "can't walk", 'fell down',
        'broken bone', 'deep cut', 'bad cut',
    ]

    APPOINTMENT_SYMPTOMS = [
        # Persistent symptoms
        'persistent cough', 'cough for weeks', 'cough for days', 'ongoing cough',
        "cough won't go away",
        # Mild infection
        'sore throat', 'ear pain', 'ear ache', 'runny nose for days',
        'eye infection', 'pink eye',
        # Mild pain
        'mild pain', 'back pain', 'knee pain', 'joint pain', 'mild headache',
        # Skin
        'mild rash', 'skin irritation', 'itchy skin',
        # Medication related
        'missed several doses', 'not sure about medication', 'need refill',
        'prescription expired', 'side effects',
        # Digestive
        'stomach ache', 'nausea', 'constipation', 'bloating',
        # Other
        'fatigue', 'tired all the time', 'sleeping too much', 'weight loss',
        'weight gain', 'feeling off', 'not feeling well',
    ]

    SELF_CARE_SYMPTOMS = [
        # Cold / flu
        'common cold', 'mild cold', 'runny nose', 'stuffy nose', 'sneezing',
        'mild cough', 'sore throat mild',
        # Minor pain
        'minor headache', 'headache', 'light headache', 'mild fever', 'low fever',
        'slight fever', 'minor pain', 'muscle ache', 'body ache',
        # Tiredness
        'a bit tired', 'slightly tired', 'mild fatigue',
        # Digestive
        'mild nausea', 'slightly nauseous', 'upset stomach', 'indigestion',
        'mild stomach pain',
        # Minor skin
        'minor cut', 'small cut', 'scratch', 'bruise', 'minor bruise',
        # Other
        'feeling a bit off', 'not 100%', 'slightly unwell',
    ]

    TRIAGE_RESPONSES = {
        'EMERGENCY': {
            'level': 'EMERGENCY',
            'emoji': '🚨',
            'title': 'Emergency - Act Now',
            'action': 'Call 911 or go to the nearest Emergency Room immediately.',
            'color': '#FF3B30',
            'advice': (
                'Do not wait. Call emergency services (911) right now or have someone '
                'take you to the ER immediately. Do not drive yourself.'
            ),
            'disclaimer': (
                'This is not a diagnosis. This triage guidance is for informational '
                'purposes only. Always follow the advice of emergency services.'
            )
        },
        'URGENT': {
            'level': 'URGENT',
            'emoji': '⚠️',
            'title': 'Urgent Care Needed Today',
            'action': 'Visit an urgent care clinic or your doctor today.',
            'color': '#FF9500',
            'advice': (
                'Your symptoms need medical attention today. If you cannot reach a '
                'doctor or urgent care, and your symptoms worsen, go to the ER.'
            ),
            'disclaimer': (
                'This is not a diagnosis. Please consult a healthcare professional.'
            )
        },
        'APPOINTMENT': {
            'level': 'APPOINTMENT',
            'emoji': '📅',
            'title': 'Book a Clinic Appointment',
            'action': 'Schedule an appointment with your doctor this week.',
            'color': '#007AFF',
            'advice': (
                'Your symptoms are not immediately dangerous but should be evaluated '
                'by a doctor soon. Book an appointment within the next few days.'
            ),
            'disclaimer': (
                'This is not a diagnosis. If symptoms worsen, seek care sooner.'
            )
        },
        'SELF_CARE': {
            'level': 'SELF_CARE',
            'emoji': '🏠',
            'title': 'Self-Care at Home',
            'action': 'Rest, stay hydrated, and monitor your symptoms.',
            'color': '#34C759',
            'advice': (
                'Your symptoms appear mild. Rest well, drink plenty of fluids, and '
                'monitor how you feel. If symptoms persist beyond 3 days or worsen, '
                'contact a doctor.'
            ),
            'disclaimer': (
                'This is not a diagnosis. Always consult a professional if you are unsure.'
            )
        }
    }

    def assess(self, user_message: str) -> dict:
        """
        Assess the triage level from a user message.
        Returns a dict with level, title, action, advice, color, emoji, disclaimer.
        """
        message_lower = user_message.lower()

        # Check from most severe to least severe
        for symptom in self.EMERGENCY_SYMPTOMS:
            if symptom in message_lower:
                return self._build_response('EMERGENCY', symptom)

        for symptom in self.URGENT_SYMPTOMS:
            if symptom in message_lower:
                return self._build_response('URGENT', symptom)

        for symptom in self.APPOINTMENT_SYMPTOMS:
            if symptom in message_lower:
                return self._build_response('APPOINTMENT', symptom)

        for symptom in self.SELF_CARE_SYMPTOMS:
            if symptom in message_lower:
                return self._build_response('SELF_CARE', symptom)

        # If symptoms mentioned but no match - default to appointment (safe)
        symptom_indicators = [
            'i feel', 'i am feeling', "i'm feeling", 'i have', "i've been",
            'pain', 'ache', 'hurt', 'sick', 'unwell', 'symptom', 'feel bad',
            'not feeling', 'feeling', 'my head', 'my chest', 'my stomach',
        ]
        if any(indicator in message_lower for indicator in symptom_indicators):
            return self._build_response('APPOINTMENT', None)

        return None  # Not a symptom message

    def _build_response(self, level: str, matched_symptom) -> dict:
        template = self.TRIAGE_RESPONSES[level]
        response = dict(template)
        if matched_symptom:
            response['matched_symptom'] = matched_symptom
        return response

    def format_chat_response(self, triage_result: dict) -> str:
        """Format triage result as a chat message string"""
        emoji = triage_result['emoji']
        title = triage_result['title']
        action = triage_result['action']
        advice = triage_result['advice']
        disclaimer = triage_result['disclaimer']

        return (
            f"{emoji} {title}\n\n"
            f"{action}\n\n"
            f"{advice}\n\n"
            f"{disclaimer}"
        )