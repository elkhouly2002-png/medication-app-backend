# main.py
# Interactive chatbot application with full conversational support
# Includes conversation state management for multi-turn dialogues
# FIXED: Medication name matching uses word boundaries to prevent partial matches

from datetime import datetime, time, timedelta
from medication import Medication
from dose_log import DoseLog
from user import User
from reminder_manager import ReminderManager
from context_manager import ContextManager
from chatbot_engine import ChatbotEngine
from adherence_predictor import AdherencePredictor
from database_manager import DatabaseManager
from adherence_analyzer import AdherenceAnalyzer
import uuid
import re


class MedicationChatbotApp:
    """
    Main application that runs the medication chatbot
    """

    def __init__(self):
        """Initialize the chatbot application"""
        self.user = None
        self.medications = {}
        self.dose_logs = []
        self.context_manager = ContextManager()
        self.reminder_manager = ReminderManager()
        self.chatbot_engine = ChatbotEngine(self.context_manager)
        self.adherence_predictor = AdherencePredictor(self.context_manager)

        # NEW: Database and adherence analyzer
        self.db = DatabaseManager()
        self.adherence_analyzer = AdherenceAnalyzer(self.db)

        self.is_running = True
        self.last_user_message = ""
        self.no_dose_to_skip = False  # Flag for skip validation

    def start(self):
        """Start the chatbot application"""
        print("\n" + "=" * 50)
        print("  MEDICATION REMINDER CHATBOT")
        print("=" * 50)
        print("\nWelcome! I'm here to help you manage your medications.\n")

        self.setup_user()

        print("\nYou can now chat with me naturally!")
        print("Try saying things like:")
        print("  • 'Add paracetamol 500mg twice daily'")
        print("  • 'When is my next dose?'")
        print("  • 'Show my medications'")
        print("  • 'I took my medication'")
        print("\nType 'exit' to quit.\n")

        self.conversational_mode()

    def setup_user(self):
        """Setup user profile and load existing data"""
        print("Let me get to know you first.\n")
        name = input("What's your name? ").strip()

        user_id = str(uuid.uuid4())[:8]
        self.user = User(user_id=user_id, name=name)

        print(f"\nGreat! Nice to meet you, {name}! 👋\n")

        # Load existing medications and dose logs from database
        self.medications = self.db.load_medications(name)
        self.dose_logs = self.db.load_dose_logs(name, days=30)

        if self.medications:
            print(f"📋 Loaded {len(self.medications)} medication(s) from your history.\n")

    def conversational_mode(self):
        """Main conversational loop with state management"""
        while self.is_running:
            user_message = input("You: ").strip()

            if not user_message:
                continue

            if user_message.lower() in ['exit', 'quit', 'bye']:
                self.exit_app()
                break

            self.last_user_message = user_message.lower()

            if self.chatbot_engine.is_in_conversation():
                followup_result = self.chatbot_engine.process_followup_response(user_message)

                if followup_result['action'] == 'ask_next':
                    print(f"Bot: {followup_result['response']}\n")

                elif followup_result['action'] == 'complete':
                    # Check if this is a dose confirmation followup
                    if self.chatbot_engine.last_intent == 'confirm_dose' and 'confirmation' in followup_result.get(
                            'data', {}):
                        # Check if it's a dose time specification
                        if 'specified_time' in followup_result.get('data', {}):
                            # User specified which dose time - record it
                            med_id = self.chatbot_engine.get_from_context('pending_med_id')
                            if med_id:
                                # Reconstruct the message with the time
                                med = self.medications.get(med_id)
                                if med:
                                    time_str = followup_result['data']['specified_time']
                                    reconstructed_msg = f"i took my {time_str} {med.name} dosage"
                                    self.handle_dose_confirmation(reconstructed_msg)
                                    context_info = self.prepare_context_info('confirm_dose')
                                    response = f"Great! I've recorded your {time_str} {med.name} dosage."
                                    if context_info and 'next_time' in context_info:
                                        response += f" Your next dose is at {context_info['next_time']}."
                                    print(f"Bot: {response}\n")
                                    self.chatbot_engine.clear_conversation_state()  # Clear state after recording
                        elif 'need_recheck' in followup_result.get('data', {}):
                            # User specified med name - re-call handle_dose_confirmation to check for multiple doses
                            med_name = followup_result['data']['med_name']
                            reconstructed_msg = f"i took {med_name}"
                            self.chatbot_engine.clear_conversation_state()  # Clear first
                            self.handle_dose_confirmation(reconstructed_msg)

                            # Check if we're now waiting for dose time
                            if self.chatbot_engine.conversation_state == "waiting_for_dose_time":
                                # Ask which dose
                                med_name_ctx = self.chatbot_engine.get_from_context('ask_med_name') or ''
                                times_str = self.chatbot_engine.get_from_context('ask_dose_time') or ''
                                print(f"Bot: Which {med_name_ctx} dose did you take? ({times_str})\n")
                            else:
                                # Only one dose, already recorded
                                context_info = self.prepare_context_info('confirm_dose')
                                response = f"Great! I've recorded that you took {med_name}."
                                if context_info and 'next_time' in context_info:
                                    response += f" Your next dose is at {context_info['next_time']}."
                                print(f"Bot: {response}\n")
                                self.chatbot_engine.clear_conversation_state()
                        else:
                            # Old flow
                            self.handle_dose_confirmation(user_message)
                            context_info = self.prepare_context_info('confirm_dose')
                            response = f"Great! I've recorded that you took {followup_result['data']['med_name']}."
                            if context_info and 'next_time' in context_info:
                                response = f"Great! I've recorded that. Your next dose is at {context_info['next_time']}."
                            print(f"Bot: {response}\n")
                    elif self.chatbot_engine.last_intent == 'skip_dose' and 'skip_dose_info' in followup_result.get(
                            'data', {}):
                        # User selected which dose to skip
                        dose_info = followup_result['data']['skip_dose_info']
                        # Create the skip log
                        scheduled_datetime = datetime.now().replace(
                            hour=dose_info['time'].hour,
                            minute=dose_info['time'].minute,
                            second=0,
                            microsecond=0
                        )
                        log_id = str(uuid.uuid4())[:8]
                        dose_log = DoseLog(
                            log_id=log_id,
                            med_id=dose_info['med_id'],
                            scheduled_time=scheduled_datetime,
                            status="skipped",
                            actual_time=None
                        )
                        self.dose_logs.append(dose_log)
                        print(f"Bot: {followup_result['response']}\n")
                        self.chatbot_engine.clear_conversation_state()  # Clear state immediately
                    elif self.chatbot_engine.last_intent == 'change_schedule' and 'old_time' in followup_result.get(
                            'data', {}):
                        # User selected which dose time to change
                        old_time = followup_result['data']['old_time']
                        med_name = self.chatbot_engine.get_from_context('change_med_name')
                        new_time = self.chatbot_engine.get_from_context('change_new_time')

                        # Execute the change
                        self.execute_completed_action({
                            'action': 'complete',
                            'data': {
                                'med_name': med_name,
                                'new_time': new_time,
                                'old_time': old_time
                            }
                        })
                        print(f"Bot: Got it! I've changed your {old_time} {med_name} dose to {new_time}.\n")
                        self.chatbot_engine.clear_conversation_state()  # Clear state immediately
                    else:
                        self.execute_completed_action(followup_result)
                        print(f"Bot: {followup_result['response']}\n")

                    # Only clear state if not waiting for dose time, skip dose, or old time
                    if self.chatbot_engine.conversation_state not in ["waiting_for_dose_time", "waiting_for_skip_dose",
                                                                      "waiting_for_old_time"]:
                        self.chatbot_engine.clear_conversation_state()

                elif followup_result['action'] == 'clarify':
                    print(f"Bot: {followup_result['response']}\n")

                else:
                    print(f"Bot: {followup_result['response']}\n")

            else:
                intent_data = self.chatbot_engine.process_message(user_message)

                # Execute actions FIRST (before preparing context)
                if not self.chatbot_engine.is_in_conversation():
                    self.execute_intent_action(intent_data, user_message)

                # Prepare context info based on intent (AFTER action is executed)
                context_info = self.prepare_context_info(intent_data['intent'])

                # Generate response
                response = self.chatbot_engine.generate_response(intent_data, context_info, user_message)

                # Save conversation
                self.context_manager.add_conversation(user_message, response, intent_data['intent'])

                print(f"Bot: {response}\n")

    def execute_completed_action(self, followup_result):
        """Execute action when multi-turn conversation is complete"""
        data = followup_result.get('data', {})
        intent = self.chatbot_engine.last_intent

        if intent == 'add_medication':
            med_name = data.get('med_name')
            dosage = data.get('dosage')
            times = data.get('times')
            times_per_day = data.get('times_per_day')

            med_id = str(uuid.uuid4())[:8]

            scheduled_times = []
            if times:
                for time_str in times:
                    parsed_time = self.parse_time(time_str)
                    if parsed_time:
                        scheduled_times.append(parsed_time)
                if not times_per_day:
                    times_per_day = len(scheduled_times)
            else:
                if not times_per_day:
                    times_per_day = 2
                if times_per_day == 1:
                    scheduled_times = [time(8, 0)]
                elif times_per_day == 2:
                    scheduled_times = [time(8, 0), time(20, 0)]
                elif times_per_day == 3:
                    scheduled_times = [time(8, 0), time(14, 0), time(20, 0)]

            if not scheduled_times:
                scheduled_times = [time(8, 0), time(20, 0)]
                times_per_day = 2

            medication = Medication(
                med_id=med_id,
                name=med_name,
                dosage=dosage,
                times_per_day=times_per_day,
                scheduled_times=scheduled_times,
                reminder_pref="on_time"
            )

            self.medications[med_id] = medication

            # Save to database
            self.db.save_medication(self.user.name, medication)

        elif intent == 'change_schedule':
            med_name = data.get('med_name')
            new_time = data.get('new_time')
            old_time = data.get('old_time')  # Which dose to change

            for med_id, med in self.medications.items():
                if med.name.lower() == med_name.lower():
                    new_time_obj = self.parse_time(new_time)
                    if new_time_obj:
                        if old_time:
                            # Change specific dose time
                            old_time_obj = self.parse_time(old_time)
                            if old_time_obj and old_time_obj in med.scheduled_times:
                                # Replace the specific time
                                med.scheduled_times = [new_time_obj if t == old_time_obj else t for t in
                                                       med.scheduled_times]
                        else:
                            # No old time specified (single dose medication) - replace all
                            med.scheduled_times = [new_time_obj]
                            med.times_per_day = 1
                    break

        elif intent == 'delete_medication':
            med_name = data.get('med_name')
            if med_name:
                if med_name.lower() == 'all':
                    for med_id in list(self.medications.keys()):
                        self.db.delete_medication(med_id)
                    self.medications.clear()
                    self.dose_logs.clear()
                else:
                    for med_id, med in list(self.medications.items()):
                        if med.name.lower() == med_name.lower():
                            self.db.delete_medication(med_id)
                            del self.medications[med_id]
                            break

        elif intent == 'update_medication':
            med_name = data.get('med_name')
            dosage = data.get('dosage')
            times = data.get('times')

            for med_id, med in self.medications.items():
                if med.name.lower() == med_name.lower():
                    if dosage:
                        med.dosage = dosage
                    if times:
                        scheduled_times = [self.parse_time(t) for t in times]
                        med.scheduled_times = scheduled_times
                    break

    def parse_time(self, time_str):
        """Parse time string to time object"""
        if not time_str:
            return time(8, 0)

        time_str = time_str.lower().strip()

        match = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)', time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3)
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            return time(hour, minute)

        match = re.match(r'(\d{1,2})\s*(am|pm)', time_str)
        if match:
            hour = int(match.group(1))
            period = match.group(2)
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            return time(hour, 0)

        return time(8, 0)

    def prepare_context_info(self, intent):
        """Prepare context information for different intents"""
        context_info = {}
        msg = self.last_user_message

        if intent == 'query_history':
            if self.medications:
                # Get all doses taken today
                today_logs = []
                for log in self.dose_logs:
                    if log.status == 'taken' and log.actual_time:
                        # Check if taken today
                        if log.actual_time.date() == datetime.now().date():
                            med = self.medications.get(log.med_id)
                            if med:
                                today_logs.append({
                                    'med_name': med.name,
                                    'scheduled_time': log.scheduled_time.strftime('%I:%M %p'),
                                    'actual_time': log.actual_time.strftime('%I:%M %p')
                                })

                if today_logs:
                    context_info['today_doses'] = today_logs
                else:
                    context_info['today_doses'] = []

        elif intent == 'adherence_summary':
            if self.medications:
                # Count doses from ALL medications
                taken = sum(1 for log in self.dose_logs if log.status == 'taken')
                skipped = sum(1 for log in self.dose_logs if log.status == 'skipped')

                # Total = taken + skipped
                total = taken + skipped

                context_info['taken'] = taken
                context_info['total'] = total if total > 0 else 1  # Avoid division by zero
                context_info['skipped'] = skipped

                # Add adherence pattern insights
                insights = self.analyze_and_show_adherence_patterns()
                context_info['adherence_insights'] = insights

        elif intent == 'check_schedule':
            current_datetime = datetime.now()
            current_time = current_datetime.time()

            schedule = []
            for med_id, med in self.medications.items():
                for scheduled_time in med.scheduled_times:
                    scheduled_datetime = datetime.combine(datetime.today(), scheduled_time)

                    # Handle midnight crossing
                    if scheduled_time.hour <= 3 and current_time.hour >= 22:
                        is_past = False
                    elif scheduled_time.hour >= 22 and current_time.hour <= 3:
                        is_past = True
                    else:
                        is_past = scheduled_time <= current_time

                    status = None

                    # Check dose logs for both taken and skipped
                    for log in self.dose_logs:
                        if log.med_id == med_id:
                            if log.scheduled_time.time() == scheduled_time:
                                if log.status == 'taken':
                                    status = 'taken'
                                    # If taken, treat as past even if it was early
                                    is_past = True
                                    break
                                elif log.status == 'skipped':
                                    status = 'skipped'
                                    is_past = True
                                    break

                    # Only mark as missed if it's actually past and not taken/skipped
                    if is_past and status not in ['taken', 'skipped']:
                        status = 'missed'

                    schedule.append({
                        'name': med.name,
                        'time': scheduled_time.strftime('%I:%M %p'),
                        'time_obj': scheduled_time,
                        'is_past': is_past,
                        'status': status
                    })

            # Filter by time of day
            if any(word in msg for word in ['tonight', 'evening', 'night']):
                schedule = [s for s in schedule if s['time_obj'].hour >= 17 or s['time_obj'].hour <= 2]
            elif any(word in msg for word in ['morning']):
                schedule = [s for s in schedule if s['time_obj'].hour < 12]
            elif any(word in msg for word in ['afternoon']):
                schedule = [s for s in schedule if 12 <= s['time_obj'].hour < 17]

            context_info['schedule'] = [{
                'name': s['name'],
                'time': s['time'],
                'is_past': s['is_past'],
                'status': s['status']
            } for s in schedule]

        elif intent == 'medication_info':
            meds = []
            for med_id, med in self.medications.items():
                meds.append({
                    'name': med.name,
                    'dosage': med.dosage,
                    'times_per_day': med.times_per_day
                })
            context_info['medications'] = meds

        elif intent == 'check_next_dose':
            next_dose = self.get_next_dose()
            if next_dose:
                context_info['next_dose'] = next_dose

        elif intent == 'confirm_dose':
            next_dose = self.get_next_dose()
            if next_dose:
                context_info['next_time'] = next_dose['time']

            # Add info about what was just confirmed
            if self.dose_logs:
                last_log = self.dose_logs[-1]
                if last_log.status == 'taken':
                    med = self.medications.get(last_log.med_id)
                    if med:
                        context_info['confirmed_med'] = med.name
                        context_info['confirmed_time'] = last_log.scheduled_time.strftime('%I:%M %p')
                        if last_log.actual_time:
                            context_info['confirmed_actual_time'] = last_log.actual_time.strftime('%I:%M %p')

        elif intent == 'skip_dose':
            # Check if there was no dose to skip
            if self.no_dose_to_skip:
                context_info['no_dose_to_skip'] = True
            # Add info about what was just skipped
            elif self.dose_logs:
                last_log = self.dose_logs[-1]
                if last_log.status == 'skipped':
                    med = self.medications.get(last_log.med_id)
                    if med:
                        context_info['skipped_med'] = med.name
                        context_info['skipped_time'] = last_log.scheduled_time.strftime('%I:%M %p')

        return context_info

    def get_next_dose(self):
        """Find the next scheduled dose (excluding taken and skipped doses)"""
        current_time = datetime.now().time()
        next_doses = []

        for med_id, med in self.medications.items():
            for scheduled_time in med.scheduled_times:
                # Check if this dose has already been taken or skipped
                already_completed = False
                for log in self.dose_logs:
                    if log.med_id == med_id and log.status in ['taken', 'skipped']:
                        if log.scheduled_time.time() == scheduled_time:
                            already_completed = True
                            break

                # Only include if not completed and is in the future
                if not already_completed and scheduled_time >= current_time:
                    next_doses.append({
                        'name': med.name,
                        'time': scheduled_time.strftime('%I:%M %p'),
                        'time_obj': scheduled_time
                    })

        if next_doses:
            next_doses.sort(key=lambda x: x['time_obj'])
            return next_doses[0]
        return None

    def execute_intent_action(self, intent_data, user_message):
        """Execute actions based on detected intent"""
        intent = intent_data['intent']
        entities = intent_data.get('entities', {})

        if intent == 'confirm_dose':
            self.handle_dose_confirmation(user_message)

        elif intent == 'skip_dose':
            self.handle_skip_dose(user_message)

        elif intent == 'delete_all_medications':
            self.delete_all_medications()

        elif intent == 'add_medication':
            med_name = entities.get('med_name')
            dosage = entities.get('dosage')
            times = entities.get('times')

            if med_name and dosage and times:
                followup_result = {
                    'action': 'complete',
                    'data': {
                        'med_name': med_name,
                        'dosage': dosage,
                        'times': times,
                        'times_per_day': len(times) if times else 2
                    }
                }
                self.chatbot_engine.last_intent = 'add_medication'
                self.execute_completed_action(followup_result)

        elif intent == 'change_schedule':
            med_name = entities.get('med_name')
            new_time = entities.get('new_time')

            if med_name and new_time:
                # Find the medication
                target_med = None
                for med_id, med in self.medications.items():
                    if med.name.lower() == med_name.lower():
                        target_med = med
                        break

                # If medication has multiple doses, ask which one to change
                if target_med and len(target_med.scheduled_times) > 1:
                    times_str = ', '.join([t.strftime('%I:%M %p') for t in sorted(target_med.scheduled_times)])
                    self.chatbot_engine.set_conversation_state("waiting_for_old_time", "change_schedule")
                    self.chatbot_engine.save_to_context('change_med_name', med_name)
                    self.chatbot_engine.save_to_context('change_new_time', new_time)
                    self.chatbot_engine.save_to_context('change_dose_options', times_str)
                    # Don't execute yet - wait for user to specify which dose
                    return

                # Single dose - execute immediately
                followup_result = {
                    'action': 'complete',
                    'data': {
                        'med_name': med_name,
                        'new_time': new_time
                    }
                }
                self.chatbot_engine.last_intent = 'change_schedule'
                self.execute_completed_action(followup_result)

        elif intent == 'update_medication':
            # Extract entities from message
            med_name = entities.get('med_name')
            dosage = entities.get('dosage')
            times = entities.get('times')

            if med_name and (dosage or times):
                # Execute immediately if we have medication name and something to update
                followup_result = {
                    'action': 'complete',
                    'data': {
                        'med_name': med_name,
                        'dosage': dosage,
                        'times': times
                    }
                }
                self.chatbot_engine.last_intent = 'update_medication'
                self.execute_completed_action(followup_result)
            # If missing info, the response generator will ask for it

    def handle_dose_confirmation(self, user_message):
        """Handle when user confirms taking a dose"""
        if not self.medications:
            return

        target_med_id = None
        target_medication = None
        message_lower = user_message.lower()

        # Check if user mentioned a specific medication name
        # Sort medications by name length (longest first) to match "Aspirin Extra Strength" before "Aspirin"
        sorted_meds = sorted(self.medications.items(), key=lambda x: len(x[1].name), reverse=True)

        med_mentioned = False
        for med_id, med in sorted_meds:
            # FIXED: Use word boundaries to match exact medication names
            # This prevents "tamalol" from matching "paramol"
            med_pattern = r'\b' + re.escape(med.name.lower()) + r'\b'
            if re.search(med_pattern, message_lower):
                target_med_id = med_id
                target_medication = med
                med_mentioned = True
                break

        # If no specific medication mentioned and user just said "i took it" / "taken it"
        # Ask them to specify which medication
        if not target_med_id:
            # Check if message is too generic (just "took it", "taken it", "had it", etc.)
            generic_phrases = ['took it', 'taken it', 'had it', 'done it', 'finished it',
                               'completed it', 'have taken it', 'have had it', 'just took it',
                               'just had it', 'already took it', 'already had it']

            is_generic = any(phrase in message_lower for phrase in generic_phrases)

            # If generic and we have medications, we need to know which one
            if is_generic and len(self.medications) > 0:
                # Don't record anything, just return - the chatbot will ask for clarification
                # Set a flag that we're waiting for medication name
                self.chatbot_engine.set_conversation_state("waiting_for_med_name_confirm", "confirm_dose")
                return

            # Otherwise, use closest scheduled time (fallback for other phrasings)
            current_time = datetime.now().time()
            closest_diff = float('inf')
            for med_id, med in self.medications.items():
                for scheduled_time in med.scheduled_times:
                    diff = abs((datetime.combine(datetime.today(), scheduled_time) -
                                datetime.combine(datetime.today(), current_time)).total_seconds())
                    if diff < closest_diff:
                        closest_diff = diff
                        target_med_id = med_id
                        target_medication = med

        if not target_medication:
            return

        # Check if user specified a time in their message (e.g., "i took my 2pm dose")
        user_specified_time = None
        time_pattern = r'(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)'
        time_match = re.search(time_pattern, message_lower)
        if time_match:
            hour = int(time_match.group(1))
            period = time_match.group(2).replace('.', '').replace(' ', '')
            if period in ['pm', 'pm'] and hour != 12:
                hour += 12
            elif period in ['am', 'am'] and hour == 12:
                hour = 0
            user_specified_time = time(hour, 0)

        # If medication has multiple doses and user didn't specify which one, ask
        if not user_specified_time and len(target_medication.scheduled_times) > 1:
            # Filter out already taken/skipped doses
            available_times = []
            today = datetime.now().date()

            for scheduled_time in target_medication.scheduled_times:
                already_done = False
                for log in self.dose_logs:
                    if (log.med_id == target_med_id and
                            log.scheduled_time.date() == today and
                            log.scheduled_time.time() == scheduled_time and
                            log.status in ['taken', 'skipped']):
                        already_done = True
                        break

                if not already_done:
                    available_times.append(scheduled_time)

            # If multiple available times, ask which one
            if len(available_times) > 1:
                times_str = ', '.join([t.strftime('%I:%M %p') for t in sorted(available_times)])
                # Set conversation state to wait for time specification
                self.chatbot_engine.set_conversation_state("waiting_for_dose_time", "confirm_dose")
                self.chatbot_engine.save_to_context('pending_med_id', target_med_id)
                # Store a flag so the response generator knows to ask
                self.chatbot_engine.save_to_context('ask_dose_time', times_str)
                self.chatbot_engine.save_to_context('ask_med_name', target_medication.name)
                return
            elif len(available_times) == 1:
                # Only one available time, use it
                user_specified_time = available_times[0]
            # else: all times already taken/skipped, will proceed to find closest

        actual_time = datetime.now()
        current_time = actual_time.time()

        # Find the scheduled time to use
        if user_specified_time:
            # User specified a time - find the matching scheduled time
            closest_scheduled = None
            for scheduled_time in target_medication.scheduled_times:
                if scheduled_time == user_specified_time:
                    closest_scheduled = scheduled_time
                    break

            # If exact match not found, use closest to user specified time
            if not closest_scheduled:
                closest_scheduled = min(
                    target_medication.scheduled_times,
                    key=lambda t: abs((datetime.combine(datetime.today(), t) -
                                       datetime.combine(datetime.today(), user_specified_time)).total_seconds())
                )
        else:
            # No time specified - find closest dose time (recently passed or coming up soon)
            candidate_times = []

            for scheduled_time in target_medication.scheduled_times:
                scheduled_today = datetime.combine(datetime.today(), scheduled_time)
                diff_seconds = (actual_time - scheduled_today).total_seconds()

                # Recently passed (within last 3 hours) OR coming up soon (within next 30 min)
                if 0 <= diff_seconds <= 10800:
                    candidate_times.append((scheduled_time, abs(diff_seconds)))
                elif -1800 <= diff_seconds < 0:
                    candidate_times.append((scheduled_time, abs(diff_seconds)))

            if candidate_times:
                candidate_times.sort(key=lambda x: x[1])
                closest_scheduled = candidate_times[0][0]
            else:
                closest_scheduled = min(
                    target_medication.scheduled_times,
                    key=lambda t: abs((datetime.combine(datetime.today(), t) -
                                       datetime.combine(datetime.today(), current_time)).total_seconds())
                )

        scheduled_datetime = datetime.now().replace(
            hour=closest_scheduled.hour,
            minute=closest_scheduled.minute,
            second=0,
            microsecond=0
        )

        # Check if this exact dose was already taken today
        for log in self.dose_logs:
            if (log.med_id == target_med_id and
                    log.status == 'taken' and
                    log.scheduled_time.date() == scheduled_datetime.date() and
                    log.scheduled_time.time() == scheduled_datetime.time()):
                # Already taken - don't log again
                return

        log_id = str(uuid.uuid4())[:8]
        dose_log = DoseLog(
            log_id=log_id,
            med_id=target_med_id,
            scheduled_time=scheduled_datetime,
            status="taken",
            actual_time=actual_time
        )

        self.dose_logs.append(dose_log)

        # Save to database
        self.db.save_dose_log(self.user.name, dose_log)

        self.context_manager.update_last_dose(target_med_id, actual_time)

        delay = dose_log.get_delay_minutes()
        if delay and delay > 0:
            self.context_manager.record_delay(target_med_id, delay)

    def handle_skip_dose(self, user_message=""):
        """Handle skipping a dose"""
        if not self.medications:
            # No medications at all - can't skip
            self.no_dose_to_skip = True
            return

        # Check if user said generic "skip it" or "skip my next dose" without specifying which medication
        message_lower = user_message.lower()
        generic_skip = message_lower in ['skip it', 'skip']
        skip_next_dose = 'next dose' in message_lower or 'next medication' in message_lower

        # Try to extract medication name from message
        specified_med_name = None
        for med_id, med in self.medications.items():
            if med.name.lower() in message_lower:
                specified_med_name = med.name
                break

        # Get all doses that haven't been taken or skipped yet (both past and future)
        upcoming_doses = []
        current_time = datetime.now().time()
        today = datetime.now().date()

        for med_id, med in self.medications.items():
            # If user specified a medication, only include that one
            if specified_med_name and med.name.lower() != specified_med_name.lower():
                continue

            for scheduled_time in med.scheduled_times:
                # Check if not already skipped or taken today
                already_done = False
                for log in self.dose_logs:
                    if (log.med_id == med_id and
                            log.scheduled_time.date() == today and
                            log.scheduled_time.time() == scheduled_time and
                            log.status in ['taken', 'skipped']):
                        already_done = True
                        break

                if not already_done:
                    upcoming_doses.append({
                        'med_id': med_id,
                        'med_name': med.name,
                        'time': scheduled_time,
                        'time_str': scheduled_time.strftime('%I:%M %p')
                    })

        # If no upcoming doses for specified medication
        if specified_med_name and len(upcoming_doses) == 0:
            self.no_dose_to_skip = True
            return

        # If no upcoming doses at all
        if len(upcoming_doses) == 0:
            self.no_dose_to_skip = True
            return

        # If user said "skip my next dose", skip the first upcoming one without asking
        if skip_next_dose and len(upcoming_doses) >= 1:
            # Filter to only FUTURE doses (not past/missed ones)
            current_time = datetime.now().time()
            future_doses = [d for d in upcoming_doses if d['time'] >= current_time]

            if len(future_doses) == 0:
                # No future doses, fall back to all doses
                self.no_dose_to_skip = True
                return

            # Sort by time and skip the first future one
            future_doses.sort(key=lambda x: x['time'])
            dose_to_skip = future_doses[0]

            scheduled_datetime = datetime.now().replace(
                hour=dose_to_skip['time'].hour,
                minute=dose_to_skip['time'].minute,
                second=0,
                microsecond=0
            )

            log_id = str(uuid.uuid4())[:8]
            dose_log = DoseLog(
                log_id=log_id,
                med_id=dose_to_skip['med_id'],
                scheduled_time=scheduled_datetime,
                status="skipped",
                actual_time=None
            )

            self.dose_logs.append(dose_log)
            self.no_dose_to_skip = False
            return

        # If generic "skip it" and multiple upcoming doses, ask which one
        if generic_skip and len(upcoming_doses) > 1:
            # Ask which dose to skip
            dose_options = [f"{d['med_name']} at {d['time_str']}" for d in upcoming_doses]
            self.chatbot_engine.set_conversation_state("waiting_for_skip_dose", "skip_dose")
            self.chatbot_engine.save_to_context('upcoming_doses', upcoming_doses)
            self.chatbot_engine.save_to_context('skip_dose_options', ', '.join(dose_options))
            return

        # If user specified medication and it has multiple doses, ask which time
        if specified_med_name and len(upcoming_doses) > 1:
            dose_options = [f"{d['med_name']} at {d['time_str']}" for d in upcoming_doses]
            self.chatbot_engine.set_conversation_state("waiting_for_skip_dose", "skip_dose")
            self.chatbot_engine.save_to_context('upcoming_doses', upcoming_doses)
            self.chatbot_engine.save_to_context('skip_dose_options', ', '.join(dose_options))
            return

        # Single dose to skip (or user specified exact dose)
        if len(upcoming_doses) == 1:
            dose_to_skip = upcoming_doses[0]
            scheduled_datetime = datetime.now().replace(
                hour=dose_to_skip['time'].hour,
                minute=dose_to_skip['time'].minute,
                second=0,
                microsecond=0
            )

            log_id = str(uuid.uuid4())[:8]
            dose_log = DoseLog(
                log_id=log_id,
                med_id=dose_to_skip['med_id'],
                scheduled_time=scheduled_datetime,
                status="skipped",
                actual_time=None
            )

            self.dose_logs.append(dose_log)
            self.no_dose_to_skip = False
            return

        # No upcoming doses at all
        self.no_dose_to_skip = True
        return

    def save_dose_log_to_db(self, dose_log):
        """Helper method to save dose log to database"""
        self.db.save_dose_log(self.user.name, dose_log)

    def analyze_and_show_adherence_patterns(self):
        """Analyze adherence patterns and show insights"""
        insights = self.adherence_analyzer.generate_adherence_insights(
            self.user.name, self.medications
        )
        return insights

    def get_adjusted_reminder_times(self):
        """Get all adjusted reminder times based on adherence patterns"""
        adjusted_times = {}
        for med_id, med in self.medications.items():
            for scheduled_time in med.scheduled_times:
                adjusted_time, adjustment = self.adherence_analyzer.get_adjusted_reminder_time(
                    self.user.name, med_id, scheduled_time
                )
                if adjustment > 0:
                    adjusted_times[f"{med.name} at {scheduled_time.strftime('%I:%M %p')}"] = {
                        'original': scheduled_time,
                        'adjusted': adjusted_time,
                        'adjustment_minutes': adjustment
                    }
        return adjusted_times

    def delete_all_medications(self):
        """Delete all medications for the user"""
        if not self.medications:
            return

        # Delete from database FIRST (before clearing)
        for med_id in list(self.medications.keys()):
            self.db.delete_medication(med_id)

        # Then clear from memory
        self.medications.clear()
        self.dose_logs.clear()

    def exit_app(self):
        """Exit the application"""
        # Show adherence insights before exiting
        if self.medications:
            print("\n📊 Analyzing your adherence patterns...\n")
            insights = self.analyze_and_show_adherence_patterns()
            if insights:
                print(insights)

        # Close database connection
        self.db.close()

        print("\n" + "=" * 50)
        print("Thanks for using Medication Reminder Chatbot!")
        print("Stay healthy! 👋")
        print("=" * 50 + "\n")
        self.is_running = False


def main():
    """Main entry point"""
    app = MedicationChatbotApp()
    app.start()


if __name__ == "__main__":
    main()