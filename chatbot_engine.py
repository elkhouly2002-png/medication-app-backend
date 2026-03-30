# chatbot_engine.py
# This class handles conversation flow and user intent detection using ML
# Includes conversation state management for multi-turn dialogues
# Updated: Added symptom_report and emergency_symptom intent handling

from datetime import datetime, timedelta
import pickle
import re


class ChatbotEngine:
    """
    Handles natural language understanding and chatbot responses using ML
    With conversation state tracking for multi-turn interactions
    """

    def __init__(self, context_manager, model_path='intent_model.pkl', vectorizer_path='vectorizer.pkl'):
        """
        Create a new chatbot engine

        context_manager: reference to ContextManager for memory
        model_path: path to trained ML model
        vectorizer_path: path to trained vectorizer
        """
        self.context_manager = context_manager
        self.current_intent = None

        # Conversation state tracking (STEP 1)
        self.conversation_state = None  # Current state (e.g., "waiting_for_med_name")
        self.conversation_context = {}  # Stores data collected during conversation
        self.last_intent = None  # What was the last detected intent
        self.awaiting_response = False  # Are we waiting for user to answer a question

        # Load the trained ML model and vectorizer
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.use_ml = True
            print("✅ ML model loaded successfully")
        except FileNotFoundError:
            print("⚠️ ML model not found. Using keyword matching as fallback.")
            self.use_ml = False
            self.model = None
            self.vectorizer = None

    # STEP 1: Conversation state management methods
    def is_in_conversation(self):
        """Check if we're currently in middle of a conversation"""
        return self.conversation_state is not None

    def set_conversation_state(self, state, intent=None):
        """
        Set the current conversation state

        state: the state to set (e.g., "waiting_for_med_name")
        intent: the intent associated with this conversation
        """
        self.conversation_state = state
        if intent:
            self.last_intent = intent
        self.awaiting_response = True

    def clear_conversation_state(self):
        """Clear conversation state when conversation is complete"""
        self.conversation_state = None
        self.conversation_context = {}
        self.last_intent = None
        self.awaiting_response = False

    def save_to_context(self, key, value):
        """Save data collected during conversation"""
        self.conversation_context[key] = value

    def get_from_context(self, key):
        """Retrieve data from conversation context"""
        return self.conversation_context.get(key, None)

    # STEP 2: State machine for multi-turn dialogues
    def process_followup_response(self, user_message):
        """
        Process user's response when in middle of a conversation

        user_message: what the user said
        Returns: dict with extracted information and next action
        """
        message_lower = user_message.lower().strip()

        # Handle based on current state
        if self.conversation_state == "waiting_for_med_name":
            # When user is answering "what's the medication name?", take their full input
            # Don't try to extract - they're directly telling us the name
            med_name = user_message.strip().title()  # "panadol extra" → "Panadol Extra"

            self.save_to_context('med_name', med_name)

            # Check what we already have
            already_have_dosage = self.get_from_context('dosage')
            already_have_times = self.get_from_context('times')

            if already_have_dosage and already_have_times:
                # We have everything
                return {
                    'action': 'complete',
                    'response': f"Perfect! I've added {med_name} ({already_have_dosage}) to your medications.",
                    'data': {
                        'med_name': med_name,
                        'dosage': already_have_dosage,
                        'times': already_have_times,
                        'times_per_day': len(already_have_times)
                    }
                }
            elif already_have_dosage:
                # Have dosage, need times
                self.set_conversation_state("waiting_for_times", self.last_intent)
                return {
                    'action': 'ask_next',
                    'response': f"What time(s) do you take {med_name}? (e.g., 8am and 8pm)"
                }
            else:
                # Need dosage next
                self.set_conversation_state("waiting_for_dosage", self.last_intent)
                return {
                    'action': 'ask_next',
                    'response': f"What's the dosage for {med_name}? (e.g., 500mg, 2 tablets)"
                }

        elif self.conversation_state == "waiting_for_med_name_confirm":
            # User is confirming which medication they took
            med_name = self._extract_medication_name(message_lower)
            if not med_name:
                # Try taking full input as medication name
                med_name = user_message.strip().title()

            if med_name:
                # Return with med_name so main.py can re-call handle_dose_confirmation
                return {
                    'action': 'complete',
                    'response': f"Great! I've recorded that you took {med_name}.",
                    'data': {
                        'med_name': med_name,
                        'confirmation': True,
                        'need_recheck': True  # Flag to re-call handle_dose_confirmation
                    }
                }
            else:
                return {
                    'action': 'clarify',
                    'response': "Which medication did you take?"
                }

        elif self.conversation_state == "waiting_for_dose_time":
            # User is specifying which dose time they took
            # Extract the time from their response
            extracted_time = self._extract_time(message_lower)

            if extracted_time:
                return {
                    'action': 'complete',
                    'response': f"Got it! Recording {extracted_time} dose.",
                    'data': {
                        'specified_time': extracted_time,
                        'confirmation': True
                    }
                }
            else:
                return {
                    'action': 'clarify',
                    'response': "Which dose time? Please specify (e.g., 9am, 2pm, 9pm)"
                }

        elif self.conversation_state == "waiting_for_skip_dose":
            # User is specifying which dose to skip
            # Try to extract medication name and time
            upcoming_doses = self.get_from_context('upcoming_doses') or []

            # Extract time or medication name from message
            extracted_time = self._extract_time(message_lower)
            med_name = self._extract_medication_name(message_lower)

            # Find matching dose
            for dose in upcoming_doses:
                # Normalize time strings for comparison - remove :00, spaces, and leading zeros
                dose_time_normalized = dose['time_str'].lower().replace(':00', '').replace(' ', '').lstrip('0')
                extracted_normalized = extracted_time.lower().replace(':00', '').replace(' ', '').replace('.',
                                                                                                          '').lstrip(
                    '0') if extracted_time else ''

                time_match = extracted_time and dose_time_normalized == extracted_normalized
                # Exact name match, not substring
                name_match = med_name and dose['med_name'].lower() == med_name.lower()

                # Also check if both time and name match for phrases like "metformin at 8pm"
                both_match = time_match and name_match

                if both_match:
                    # Perfect match - both time and medication name
                    return {
                        'action': 'complete',
                        'response': f"Okay, I've marked {dose['med_name']} at {dose['time_str']} as skipped.",
                        'data': {
                            'skip_dose_info': dose
                        }
                    }

            # If no exact match, try time-only or name-only match
            for dose in upcoming_doses:
                dose_time_normalized = dose['time_str'].lower().replace(':00', '').replace(' ', '').lstrip('0')
                extracted_normalized = extracted_time.lower().replace(':00', '').replace(' ', '').replace('.',
                                                                                                          '').lstrip(
                    '0') if extracted_time else ''

                time_match = extracted_time and dose_time_normalized == extracted_normalized
                name_match = med_name and dose['med_name'].lower() == med_name.lower()

                if time_match or name_match:
                    return {
                        'action': 'complete',
                        'response': f"Okay, I've marked {dose['med_name']} at {dose['time_str']} as skipped.",
                        'data': {
                            'skip_dose_info': dose
                        }
                    }

            return {
                'action': 'clarify',
                'response': "Which dose? Please specify the medication and/or time."
            }

        elif self.conversation_state == "waiting_for_old_time":
            # User is specifying which dose time to change
            extracted_time = self._extract_time(message_lower)

            if extracted_time:
                return {
                    'action': 'complete',
                    'response': f"Got it! Changing that dose.",
                    'data': {
                        'old_time': extracted_time
                    }
                }
            else:
                return {
                    'action': 'clarify',
                    'response': "Which dose time? Please specify (e.g., 8am, 2pm)"
                }

        elif self.conversation_state == "waiting_for_dosage":
            dosage = self._extract_dosage(message_lower)
            if not dosage:
                dosage = user_message.strip()

            self.save_to_context('dosage', dosage)
            med_name = self.get_from_context('med_name')

            # Check if times were already saved from the original message
            already_have_times = self.get_from_context('times')

            if already_have_times:
                # We have everything - skip asking for times
                # DON'T clear conversation state yet - main.py needs last_intent
                return {
                    'action': 'complete',
                    'response': f"Perfect! I've added {med_name} ({dosage}) to your medications.",
                    'data': {
                        'med_name': med_name,
                        'dosage': dosage,
                        'times': already_have_times,
                        'times_per_day': len(already_have_times)
                    }
                }
            else:
                # Still need times
                self.set_conversation_state("waiting_for_times", self.last_intent)
                return {
                    'action': 'ask_next',
                    'response': f"What time(s) do you take {med_name}? (e.g., 8am and 8pm, or twice daily)"
                }

        elif self.conversation_state == "waiting_for_times":
            times = self._extract_times(message_lower)

            times_per_day = None
            if 'twice' in message_lower or '2' in message_lower:
                times_per_day = 2
            elif 'once' in message_lower or '1' in message_lower:
                times_per_day = 1
            elif 'three' in message_lower or '3' in message_lower:
                times_per_day = 3

            self.save_to_context('times', times)
            self.save_to_context('times_per_day', times_per_day)

            med_name = self.get_from_context('med_name')
            dosage = self.get_from_context('dosage')

            # DON'T clear conversation state yet - main.py needs last_intent
            return {
                'action': 'complete',
                'response': f"Perfect! I've added {med_name} ({dosage}) to your medications.",
                'data': {
                    'med_name': med_name,
                    'dosage': dosage,
                    'times': times,
                    'times_per_day': times_per_day
                }
            }

        elif self.conversation_state == "waiting_for_schedule_details":
            new_time = self._extract_time(message_lower)
            med_name = self._extract_medication_name(message_lower)

            if med_name and new_time:
                return {
                    'action': 'complete',
                    'response': f"Got it! I'll update {med_name} to {new_time}.",
                    'data': {
                        'med_name': med_name,
                        'new_time': new_time
                    }
                }
            else:
                return {
                    'action': 'clarify',
                    'response': "Please tell me the medication name and new time (e.g., 'Paracetamol at 9pm')"
                }

        elif self.conversation_state == "waiting_for_delete_confirmation":
            # Check if user is confirming with yes/no
            if 'yes' in message_lower or 'confirm' in message_lower or 'sure' in message_lower:
                # User confirmed - get medication from context
                med_name = self.get_from_context('med_name')
                if med_name:
                    return {
                        'action': 'complete',
                        'response': f"Okay, I've removed {med_name} from your medications.",
                        'data': {'med_name': med_name}
                    }
                else:
                    return {
                        'action': 'clarify',
                        'response': "Which medication would you like to remove?"
                    }
            elif 'no' in message_lower or 'cancel' in message_lower or 'nevermind' in message_lower:
                # User cancelled
                return {
                    'action': 'complete',
                    'response': "Okay, I won't remove any medications.",
                    'data': {}
                }

            # Otherwise, extract medication name from message
            med_name = self._extract_medication_name(message_lower)

            if not med_name:
                # Take first meaningful word as medication name
                skip_words = ['please', 'remove', 'delete', 'stop', 'cancel',
                              'the', 'my', 'a', 'an', 'yes', 'no']
                words = user_message.lower().split()
                for word in words:
                    if word not in skip_words and len(word) > 2:
                        med_name = word.capitalize()
                        break

            if med_name:
                return {
                    'action': 'complete',
                    'response': f"Okay, I've removed {med_name} from your medications.",
                    'data': {'med_name': med_name}
                }
            else:
                return {
                    'action': 'clarify',
                    'response': "Which medication would you like to remove?"
                }

        elif self.conversation_state == "waiting_for_update_details":
            med_name = self._extract_medication_name(message_lower)
            dosage = self._extract_dosage(message_lower)
            times = self._extract_times(message_lower)

            if med_name:
                return {
                    'action': 'complete',
                    'response': f"I've updated {med_name}.",
                    'data': {
                        'med_name': med_name,
                        'dosage': dosage,
                        'times': times
                    }
                }
            else:
                return {
                    'action': 'clarify',
                    'response': "Please specify which medication to update and what to change."
                }

        elif self.conversation_state == "waiting_for_reminder_time":
            new_time = self._extract_time(message_lower)

            if new_time:
                return {
                    'action': 'complete',
                    'response': f"Got it! I'll set reminders for {new_time}.",
                    'data': {
                        'reminder_time': new_time
                    }
                }
            else:
                return {
                    'action': 'clarify',
                    'response': "What time would you like? (e.g., 8am, 9:30pm)"
                }

        # Default fallback
        return {
            'action': 'error',
            'response': "I didn't understand that. Let's start over."
        }

    def process_message(self, user_message):
        """
        Process user message and determine intent using ML

        user_message: what the user typed
        Returns: dict with intent and extracted info
        """
        message_lower = user_message.lower().strip()

        # Check if we're in middle of a conversation
        if self.is_in_conversation():
            intent_data = {
                'intent': self.last_intent,
                'entities': {},
                'confidence': 1.0,
                'is_followup': True
            }
            return intent_data

        # Normal intent prediction
        intent_data = {
            'intent': None,
            'entities': {},
            'confidence': 0.0,
            'is_followup': False
        }

        if self.use_ml and self.model is not None:
            intent_data = self._predict_intent_ml(message_lower)
        else:
            intent_data = self._predict_intent_keywords(message_lower)

        intent_data['is_followup'] = False

        # Extract additional entities based on intent
        if intent_data['intent'] == 'confirm_dose':
            intent_data['entities']['time'] = self._extract_time(message_lower)

        elif intent_data['intent'] == 'snooze_reminder':
            intent_data['entities']['duration'] = self._extract_duration(message_lower)

        elif intent_data['intent'] == 'add_medication':
            intent_data['entities']['med_name'] = self._extract_medication_name(message_lower)
            intent_data['entities']['dosage'] = self._extract_dosage(message_lower)
            intent_data['entities']['times'] = self._extract_times(message_lower)

        elif intent_data['intent'] == 'delete_medication':
            intent_data['entities']['med_name'] = self._extract_medication_name(message_lower)

        elif intent_data['intent'] == 'change_schedule':
            intent_data['entities']['med_name'] = self._extract_medication_name(message_lower)
            intent_data['entities']['new_time'] = self._extract_time(message_lower)
            # Store message for later use
            self._last_message = message_lower

        self.current_intent = intent_data['intent']
        return intent_data

    def _predict_intent_ml(self, message):
        """Use ML model to predict intent"""
        cleaned_message = self._preprocess_text(message)
        message_vector = self.vectorizer.transform([cleaned_message])
        predicted_intent = self.model.predict(message_vector)[0]
        probabilities = self.model.predict_proba(message_vector)[0]
        confidence = max(probabilities)

        return {
            'intent': predicted_intent,
            'entities': {},
            'confidence': confidence
        }

    def _preprocess_text(self, text):
        """Clean text for ML model"""
        text = text.lower()
        text = ' '.join(text.split())
        return text

    def _predict_intent_keywords(self, message):
        """Fallback keyword-based intent detection"""
        intent_data = {'intent': None, 'entities': {}, 'confidence': 0.0}

        if self._check_dose_taken(message):
            intent_data['intent'] = 'confirm_dose'
            intent_data['confidence'] = 0.9
        elif self._check_snooze_request(message):
            intent_data['intent'] = 'snooze_reminder'
            intent_data['confidence'] = 0.85
        elif self._check_skip_request(message):
            intent_data['intent'] = 'skip_dose'
            intent_data['confidence'] = 0.9
        elif self._check_history_query(message):
            intent_data['intent'] = 'query_history'
            intent_data['confidence'] = 0.8
        elif self._check_adherence_query(message):
            intent_data['intent'] = 'adherence_summary'
            intent_data['confidence'] = 0.85
        elif self._check_schedule_change(message):
            intent_data['intent'] = 'change_schedule'
            intent_data['confidence'] = 0.75
        elif self._check_add_medication(message):
            intent_data['intent'] = 'add_medication'
            intent_data['confidence'] = 0.8
        else:
            intent_data['intent'] = 'general'
            intent_data['confidence'] = 0.5

        return intent_data

    def generate_response(self, intent_data, context_info=None, user_message=None):
        """Generate appropriate response based on intent"""
        intent = intent_data['intent']

        if intent == 'confirm_dose':
            return self._response_dose_confirmed(context_info)
        elif intent == 'snooze_reminder':
            duration = intent_data['entities'].get('duration', 20)
            return self._response_snoozed(duration)
        elif intent == 'skip_dose':
            return self._response_skipped(context_info)
        elif intent == 'query_history':
            return self._response_history(context_info)
        elif intent == 'adherence_summary':
            return self._response_adherence(context_info)
        elif intent == 'change_schedule':
            return self._response_schedule_change(intent_data['entities'])
        elif intent == 'add_medication':
            return self._response_add_medication(intent_data['entities'])
        elif intent == 'check_schedule':
            return self._response_check_schedule(context_info)
        elif intent == 'medication_info':
            return self._response_medication_info(context_info)
        elif intent == 'update_medication':
            return self._response_update_medication()
        elif intent == 'delete_medication':
            return self._response_delete_medication(intent_data.get('entities', {}))
        elif intent == 'check_next_dose':
            return self._response_next_dose(context_info)
        elif intent == 'set_reminder_preference':
            return self._response_set_reminder(user_message)
        # Triage intents (fallback if triage_engine didn't catch it first)
        elif intent == 'symptom_report':
            return "I've noted your symptoms. Please describe them in more detail so I can help guide you."
        elif intent == 'emergency_symptom':
            return "🚨 This sounds serious. Please call emergency services (123) or go to the nearest ER immediately. Do not wait."
        # NEW: Treatment information intents
        elif intent == 'ask_side_effects':
            return self._response_side_effects(user_message)
        elif intent == 'ask_missed_dose':
            return self._response_missed_dose(user_message)
        elif intent == 'ask_interactions':
            return self._response_interactions(user_message)
        elif intent == 'ask_how_to_take':
            return self._response_how_to_take(user_message)
        else:
            return self._response_general()

    # Entity extraction methods
    def _extract_medication_name(self, message):
        """Extract medication name from message"""
        # Check for multi-word medication names FIRST (before single words)
        multi_word_meds = [
            'vitamin d', 'vitamin c', 'vitamin b', 'vitamin e', 'vitamin a',
            'fish oil', 'omega 3', 'omega-3', 'cod liver oil',
            'blood pressure', 'birth control'
        ]
        for med in multi_word_meds:
            if med in message:
                return med.title()  # "vitamin d" → "Vitamin D"

        # Words that are NOT medication names
        skip_words = ['a', 'an', 'the', 'my', 'new', 'some', 'medication', 'med',
                      'pill', 'tablet', 'capsule', 'drug', 'prescription', 'dose',
                      'daily', 'want', 'need', 'please', 'called', 'named', 'another',
                      'i', 'to', 'and', 'or', 'is', 'it', 'this', 'that', 'with',
                      'add', 'take', 'have', 'get', 'for', 'about', 'remove', 'delete',
                      'stop', 'cancel', 'update', 'change', 'schedule', 'reminder',
                      'vitamin']  # Add 'vitamin' to skip list since we check multi-word first

        # Look for word after specific trigger words (BEFORE checking keywords)
        # Match 1-2 words but exclude common prepositions
        patterns = [
            r'called\s+(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
            r'named\s+(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
            r'add\s+(?:a\s+)?(?:medication\s+)?(?:called\s+)?(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
            r'register\s+(?:a\s+)?(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
            r'track\s+(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
            r'remove\s+(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
            r'delete\s+(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
            r'move\s+(?:my\s+)?(\w+(?:\s+(?!to|for|from|at|the|in|on)\w+)?)(?:\s|$)',
            r'change\s+(?:my\s+)?(\w+(?:\s+(?!to|for|from|at|the|in|on)\w+)?)(?:\s|$)',
            r'shift\s+(?:my\s+)?(\w+(?:\s+(?!to|for|from|at|the|in|on)\w+)?)(?:\s|$)',
            r'update\s+(?:my\s+)?(\w+(?:\s+(?!to|for|from|at|the|in|on)\w+)?)(?:\s|$)',
            r'discontinue\s+(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
            r'stop\s+tracking\s+(\w+(?:\s+(?!to|for|from|at|my|the|in|on)\w+)?)(?:\s|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                candidate = match.group(1).strip().lower()
                # Check if it's a known multi-word med
                if candidate in multi_word_meds:
                    return candidate.title()
                # Clean up and return all meaningful words
                words = candidate.split()
                # Filter out skip words, dosage numbers (like "10mg", "500mg"), and keep meaningful ones
                meaningful_words = []
                for w in words:
                    # Skip if it's a skip word
                    if w in skip_words:
                        continue
                    # Skip if it's a dosage (number + mg/iu/tablet/etc)
                    if re.match(r'^\d+(?:mg|iu|mcg|ml|tablets?|pills?|capsules?)?$', w, re.IGNORECASE):
                        continue
                    # Skip very short words
                    if len(w) <= 1:
                        continue
                    meaningful_words.append(w)

                if meaningful_words:
                    return ' '.join(meaningful_words).title()

        # THEN check for single-word medication keywords (as fallback)
        med_keywords = ['paracetamol', 'aspirin', 'ibuprofen', 'metformin',
                        'antibiotic', 'panadol', 'advil', 'tylenol', 'amoxicillin',
                        'atorvastatin', 'lisinopril', 'omeprazole', 'metoprolol',
                        'warfarin', 'insulin', 'levothyroxine', 'gabapentin',
                        'lipitor', 'prozac', 'zoloft', 'crestor', 'nexium',
                        'synthroid', 'lexapro', 'cymbalta', 'abilify', 'wellbutrin',
                        'prednisone', 'tramadol', 'hydrocodone', 'oxycodone',
                        'simvastatin', 'amlodipine', 'losartan', 'albuterol']
        for keyword in med_keywords:
            if keyword in message:
                return keyword.capitalize()

        # Return None if no medication name found - don't guess!
        return None

    def _extract_dosage(self, message):
        """Extract dosage from message (e.g., 500mg, 2 tablets)"""
        dosage_pattern = r'(\d+)\s*(mg|tablets?|pills?|capsules?|ml)'
        match = re.search(dosage_pattern, message, re.IGNORECASE)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return None

    def _extract_times(self, message):
        """Extract time mentions from message"""
        times = []
        time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)'
        matches = re.finditer(time_pattern, message, re.IGNORECASE)
        for match in matches:
            times.append(match.group(0))
        return times if times else None

    def _check_dose_taken(self, message):
        """Check if message indicates dose was taken"""
        keywords = ['took', 'taken', 'took it', 'yes', 'done', 'finished', 'had', 'swallowed']
        return any(keyword in message for keyword in keywords)

    def _check_snooze_request(self, message):
        """Check if message requests to delay reminder"""
        keywords = ['later', 'remind me', 'snooze', 'in 20', 'in 30', 'delay', 'postpone']
        return any(keyword in message for keyword in keywords)

    def _check_skip_request(self, message):
        """Check if user wants to skip dose"""
        keywords = ['skip', 'not taking', "won't take", 'cancel', 'ignore']
        return any(keyword in message for keyword in keywords)

    def _check_history_query(self, message):
        """Check if asking about medication history"""
        keywords = ['did i take', 'when did i', 'last dose', 'history', 'when was']
        return any(keyword in message for keyword in keywords)

    def _check_adherence_query(self, message):
        """Check if asking about adherence stats"""
        keywords = ['how am i doing', 'missed', 'adherence', 'this week', 'summary', 'stats']
        return any(keyword in message for keyword in keywords)

    def _check_schedule_change(self, message):
        """Check if requesting schedule change"""
        keywords = ['change time', 'update schedule', 'different time', 'move reminder', 'reschedule']
        return any(keyword in message for keyword in keywords)

    def _check_add_medication(self, message):
        """Check if adding new medication"""
        keywords = ['add medication', 'new medication', 'add med', 'another medication', 'register']
        return any(keyword in message for keyword in keywords)

    def _extract_time(self, message):
        """Extract time from message"""
        time_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)?'
        match = re.search(time_pattern, message)
        if match:
            return match.group(0)
        return None

    def _extract_duration(self, message):
        """Extract duration in minutes from message"""
        if '20' in message or 'twenty' in message:
            return 20
        elif '30' in message or 'thirty' in message:
            return 30
        elif '15' in message or 'fifteen' in message:
            return 15
        elif '60' in message or 'hour' in message:
            return 60
        elif '45' in message or 'forty' in message:
            return 45
        elif '10' in message or 'ten' in message:
            return 10
        else:
            return 20

    # Response generation methods
    def _response_dose_confirmed(self, context_info):
        """Generate response for confirmed dose"""
        # Check if we're waiting for medication name clarification
        if self.conversation_state == "waiting_for_med_name_confirm":
            return "Which medication did you take?"

        # Check if we need to ask which dose time
        if self.conversation_state == "waiting_for_dose_time":
            med_name = self.get_from_context('ask_med_name') or ''
            times_str = self.get_from_context('ask_dose_time') or ''
            return f"Which {med_name} dose did you take? ({times_str})"

        # Include medication name and time in confirmation
        if context_info and 'confirmed_med' in context_info:
            med_name = context_info.get('confirmed_med')
            scheduled_time = context_info.get('confirmed_time')
            actual_time = context_info.get('confirmed_actual_time')

            if med_name and scheduled_time:
                # Format as "3pm" instead of "03:00 PM"
                time_simple = scheduled_time.lower().replace(':00 ', '').replace(' ', '')

                # Check if taken early/late
                if actual_time and actual_time != scheduled_time:
                    actual_simple = actual_time.lower().replace(':00 ', '').replace(' ', '')
                    response = f"Great! I've recorded that you took your {time_simple} {med_name} dosage (actually taken at {actual_simple})."
                else:
                    response = f"Perfect! I've recorded that you took your {time_simple} {med_name} dosage."

                # Add next dose info if available
                if 'next_time' in context_info:
                    response += f" Your next dose is at {context_info['next_time']}."

                return response

        if context_info and 'next_time' in context_info:
            return f"Great! I've recorded that. Your next dose is at {context_info['next_time']}."
        return "Perfect! I've recorded that you took your medication."

    def _response_snoozed(self, duration):
        """Generate response for snoozed reminder"""
        return f"No problem! I'll remind you again in {duration} minutes."

    def _response_skipped(self, context_info=None):
        """Generate response for skipped dose"""
        # Check if we're waiting for dose selection
        if self.conversation_state == "waiting_for_skip_dose":
            options = self.get_from_context('skip_dose_options') or ''
            return f"Which dose do you want to skip? ({options})"

        # Check if there was no dose to skip
        if context_info and context_info.get('no_dose_to_skip'):
            return "You don't have any upcoming doses to skip."

        if context_info and 'skipped_med' in context_info:
            med_name = context_info.get('skipped_med')
            med_time = context_info.get('skipped_time')
            if med_name and med_time:
                return f"Okay, I've marked {med_name} at {med_time} as skipped."
        return "Okay, I've marked this dose as skipped."

    def _response_history(self, context_info):
        """Generate response for history query"""
        if context_info and 'today_doses' in context_info:
            doses = context_info['today_doses']
            if not doses:
                return "I don't have any record of medication taken today."

            if len(doses) == 1:
                dose = doses[0]
                if dose['actual_time'] != dose['scheduled_time']:
                    return f"You took {dose['med_name']} at {dose['scheduled_time']} (actually taken at {dose['actual_time']})."
                else:
                    return f"You took {dose['med_name']} at {dose['scheduled_time']}."
            else:
                # Multiple doses taken
                response = "Today you took:\n"
                for dose in doses:
                    if dose['actual_time'] != dose['scheduled_time']:
                        response += f"• {dose['med_name']} at {dose['scheduled_time']} (actually taken at {dose['actual_time']})\n"
                    else:
                        response += f"• {dose['med_name']} at {dose['scheduled_time']}\n"
                return response.rstrip()

        return "I don't have any record of medication taken yet."

    def _response_adherence(self, context_info):
        """Generate response for adherence summary"""
        if context_info:
            taken = context_info.get('taken', 0)
            total = context_info.get('total', 0)
            skipped = context_info.get('skipped', 0)

            if total > 0:
                percentage = (taken / total) * 100
                response = f"This week you took {taken} out of {total} doses ({percentage:.0f}% adherence)."
                if skipped > 0:
                    response += f" You skipped {skipped} dose{'s' if skipped > 1 else ''}."

                # Add pattern insights if available
                insights = context_info.get('adherence_insights', '')
                if insights:
                    response += f"\n\n{insights}"

                return response
        return "I don't have enough data yet to give you a summary."

    def _response_schedule_change(self, entities):
        """Generate response for schedule change request"""
        # Check if we're waiting for old time selection
        if self.conversation_state == "waiting_for_old_time":
            med_name = self.get_from_context('change_med_name') or ''
            times_str = self.get_from_context('change_dose_options') or ''
            new_time = self.get_from_context('change_new_time') or ''
            return f"Which {med_name} dose do you want to change to {new_time}? ({times_str})"

        # Try to extract medication name and time from the message
        med_name = entities.get('med_name')
        # For change_schedule, we need to extract time differently
        # Check if there's a message to extract from
        if hasattr(self, '_last_message'):
            message = self._last_message.lower()
            new_time = self._extract_time(message)
        else:
            new_time = None

        # Save whatever we have
        if med_name:
            self.save_to_context('med_name', med_name)
        if new_time:
            self.save_to_context('new_time', new_time)

        # If we have both, complete immediately (will be handled by main.py)
        if med_name and new_time:
            return f"Got it! I'll update {med_name} to {new_time}."

        # Otherwise ask for details
        self.set_conversation_state("waiting_for_schedule_details", "change_schedule")
        return "Sure! Which medication do you want to reschedule, and what's the new time?"

    def _response_add_medication(self, entities):
        """Generate response for adding medication"""
        med_name = entities.get('med_name')
        dosage = entities.get('dosage')
        times = entities.get('times')

        # If starting fresh (no conversation state), clear any stale context
        if not self.conversation_state or self.conversation_state not in ['waiting_for_med_name', 'waiting_for_dosage',
                                                                          'waiting_for_times']:
            # Clear previous medication context to avoid contamination
            self.save_to_context('med_name', None)
            self.save_to_context('dosage', None)
            self.save_to_context('times', None)

        # Save everything we already have
        if med_name:
            self.save_to_context('med_name', med_name)
        if dosage:
            self.save_to_context('dosage', dosage)
        if times:
            self.save_to_context('times', times)

        # Ask for what's missing in order
        if not med_name:
            self.set_conversation_state("waiting_for_med_name", "add_medication")
            return "Sure! What's the name of the medication you want to add?"
        elif not dosage:
            self.set_conversation_state("waiting_for_dosage", "add_medication")
            return f"What's the dosage for {med_name}? (e.g., 500mg, 2 tablets)"
        elif not times:
            self.set_conversation_state("waiting_for_times", "add_medication")
            return f"What time(s) do you take {med_name}? (e.g., 8am and 8pm)"
        else:
            # We have everything - one line add
            return f"Got it! Adding {med_name} {dosage} at {', '.join(times)}."

    def _response_check_schedule(self, context_info):
        """Generate response for checking today's schedule"""
        if context_info and 'schedule' in context_info:
            schedule = context_info['schedule']
            if not schedule:
                return "You don't have any medications scheduled for that time."

            past = [s for s in schedule if s.get('is_past')]
            upcoming = [s for s in schedule if not s.get('is_past')]

            response = ""

            if past:
                response += "Past doses:\n"
                for s in past:
                    if s['status'] == 'taken':
                        response += f"• ✅ {s['name']} at {s['time']} - taken\n"
                    elif s['status'] == 'skipped':
                        response += f"• ⏭️ {s['name']} at {s['time']} - skipped\n"
                    else:
                        response += f"• ❌ {s['name']} at {s['time']} - missed\n"

            if upcoming:
                if past:
                    response += "\nUpcoming doses:\n"
                else:
                    response += "Upcoming doses:\n"
                for s in upcoming:
                    response += f"• 🕐 {s['name']} at {s['time']}\n"

            return response
        return "You don't have any medications registered yet."

    def _response_medication_info(self, context_info):
        """Generate response for medication information query"""
        if context_info and 'medications' in context_info:
            meds = context_info['medications']
            if not meds:
                return "You don't have any medications registered yet."
            response = "Here are your current medications:\n"
            for med in meds:
                response += f"• {med['name']} - {med['dosage']}, {med['times_per_day']}x daily\n"
            return response
        return "You don't have any medications registered yet."

    def _response_update_medication(self):
        """Generate response for updating medication"""
        self.set_conversation_state("waiting_for_update_details", "update_medication")
        return "Which medication would you like to update, and what changes do you want to make?"

    def _response_delete_medication(self, entities):
        """Generate response for deleting medication"""
        # Check if medication name already mentioned in original message
        med_name = entities.get('med_name') if entities else None
        if med_name:
            self.save_to_context('med_name', med_name)
            self.set_conversation_state("waiting_for_delete_confirmation", "delete_medication")
            return f"Are you sure you want to remove {med_name}? Just say yes to confirm."
        else:
            self.set_conversation_state("waiting_for_delete_confirmation", "delete_medication")
            return "Which medication would you like to remove?"

    def _response_next_dose(self, context_info):
        """Generate response for next dose query"""
        if context_info and 'next_dose' in context_info:
            next_dose = context_info['next_dose']
            return f"Your next dose is {next_dose['name']} at {next_dose['time']}."
        return "You don't have any upcoming doses scheduled."

    def _response_set_reminder(self, message=None):
        """Generate response for setting reminder preference"""
        # Check if user specified "X minutes early/before"
        if message:
            early_pattern = r'(\d+)\s*min(?:ute)?s?\s*(?:early|earlier|before)'
            match = re.search(early_pattern, message.lower())
            if match:
                minutes = int(match.group(1))
                return f"Got it! I'll remind you {minutes} minutes before your scheduled doses."

        self.set_conversation_state("waiting_for_reminder_time", "set_reminder_preference")
        return "What time would you like to set your reminders for?"

    def _response_side_effects(self, user_message=None):
        """Generate response for side effects questions"""
        med_name = None
        if user_message:
            med_name = self._extract_medication_name(user_message.lower())

        if med_name:
            return (
                f"Common side effects vary by medication. For {med_name}, common side effects may include "
                f"nausea, dizziness, headache, or stomach upset. "
                f"If you experience severe side effects like difficulty breathing, chest pain, or severe allergic reaction, "
                f"call 123 immediately or go to the nearest ER. "
                f"Always consult your doctor or pharmacist for specific side effect information about {med_name}."
            )
        return (
            "Common side effects of most medications may include nausea, dizziness, headache, or stomach upset. "
            "Serious side effects like difficulty breathing, severe rash, or chest pain require immediate medical attention — call 123. "
            "Always consult your doctor or pharmacist for specific information about your medication's side effects."
        )

    def _response_missed_dose(self, user_message=None):
        """Generate response for missed dose questions"""
        return (
            "If you missed a dose:\n\n"
            "• Take it as soon as you remember — unless it's almost time for your next dose.\n"
            "• If it's almost time for your next dose, skip the missed one and continue your normal schedule.\n"
            "• Never double up doses to make up for a missed one.\n"
            "• If you're unsure, contact your doctor or pharmacist.\n\n"
            "⚠️ For critical medications like blood thinners or insulin, contact your doctor immediately if you miss a dose."
        )

    def _response_interactions(self, user_message=None):
        """Generate response for food/drug interactions questions"""
        med_name = None
        if user_message:
            med_name = self._extract_medication_name(user_message.lower())

        if med_name:
            return (
                f"Regarding {med_name} and food interactions:\n\n"
                f"• Some medications should be taken with food to reduce stomach upset.\n"
                f"• Others should be taken on an empty stomach for better absorption.\n"
                f"• Avoid alcohol with most medications as it can increase side effects.\n"
                f"• Grapefruit juice can interact with certain medications.\n\n"
                f"Please check the instructions on your {med_name} packaging or ask your pharmacist for specific guidance."
            )
        return (
            "Regarding food and medication interactions:\n\n"
            "• Some medications should be taken with food to reduce stomach upset.\n"
            "• Others should be taken on an empty stomach for better absorption.\n"
            "• Avoid alcohol with most medications as it can increase side effects.\n"
            "• Grapefruit juice can interact with certain medications.\n\n"
            "Always check your medication label or ask your pharmacist for specific guidance."
        )

    def _response_how_to_take(self, user_message=None):
        """Generate response for how to take medication questions"""
        med_name = None
        if user_message:
            med_name = self._extract_medication_name(user_message.lower())

        if med_name:
            return (
                f"General guidance for taking {med_name}:\n\n"
                f"• Follow the dosage exactly as prescribed by your doctor.\n"
                f"• Take it at the same time each day to maintain consistent levels.\n"
                f"• Swallow tablets whole with a full glass of water unless instructed otherwise.\n"
                f"• Check if it should be taken with or without food.\n"
                f"• Do not stop taking {med_name} without consulting your doctor first.\n\n"
                f"For specific instructions about {med_name}, always refer to the medication leaflet or ask your pharmacist."
            )
        return (
            "General guidance for taking medication:\n\n"
            "• Follow the dosage exactly as prescribed by your doctor.\n"
            "• Take it at the same time each day to maintain consistent levels.\n"
            "• Swallow tablets whole with a full glass of water unless instructed otherwise.\n"
            "• Do not stop taking medication without consulting your doctor first.\n\n"
            "Always refer to your medication leaflet or ask your pharmacist for specific instructions."
        )

    def _response_general(self):
        """Generate response for general conversation"""
        return "Hello! I'm your medication assistant. You can ask me about your medications, schedule, or adherence."