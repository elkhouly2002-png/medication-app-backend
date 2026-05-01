"""
Flask API for Medication Reminder Chatbot
COMPLETE replica of main.py with handle_dose_confirmation and database deletes
Updated: Added Symptom Triage System
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, time
import uuid
import re

from database_manager import DatabaseManager
from adherence_analyzer import AdherenceAnalyzer
from chatbot_engine import ChatbotEngine
from context_manager import ContextManager
from medication import Medication
from dose_log import DoseLog
from user import User
from triage_engine import TriageEngine  # NEW

app = Flask(__name__)
CORS(app)

db = DatabaseManager()
adherence_analyzer = AdherenceAnalyzer(db)
context_manager = ContextManager()
chatbot_engine = ChatbotEngine(context_manager)
triage_engine = TriageEngine()  # NEW

user_sessions = {}


class ChatbotSession:
    """COMPLETE replica of main.py with proper database operations"""

    def __init__(self, user_name):
        self.user_name = user_name
        self.user = User(user_id=str(uuid.uuid4())[:8], name=user_name)
        self.reload_data()
        self.context_manager = context_manager
        self.chatbot_engine = chatbot_engine
        self.adherence_analyzer = adherence_analyzer
        self.db = db
        self.last_user_message = ""
        self.no_dose_to_skip = False

    def reload_data(self):
        self.medications = db.load_medications(self.user_name)
        self.dose_logs = db.load_dose_logs(self.user_name, days=30)

    def parse_time(self, time_str):
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
        match = re.match(r'(\d{1,2}):(\d{2})', time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            return time(hour, minute)
        return time(8, 0)

    def get_next_dose(self):
        current_time = datetime.now().time()
        next_doses = []

        for med_id, med in self.medications.items():
            for scheduled_time in med.scheduled_times:
                already_completed = False
                for log in self.dose_logs:
                    if log.med_id == med_id and log.status in ['taken', 'skipped']:
                        if log.scheduled_time.time() == scheduled_time:
                            already_completed = True
                            break

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

    def handle_dose_confirmation(self, user_message):
        """EXACT copy from main.py - handles dose confirmation with proper medication detection"""
        if not self.medications:
            return

        target_med_id = None
        target_medication = None
        message_lower = user_message.lower()

        sorted_meds = sorted(self.medications.items(), key=lambda x: len(x[1].name), reverse=True)

        med_mentioned = False
        for med_id, med in sorted_meds:
            if med.name.lower() in message_lower:
                target_med_id = med_id
                target_medication = med
                med_mentioned = True
                break

        if not target_med_id:
            generic_phrases = ['took it', 'taken it', 'had it', 'done it', 'finished it',
                               'completed it', 'have taken it', 'have had it', 'just took it',
                               'just had it', 'already took it', 'already had it']

            is_generic = any(phrase in message_lower for phrase in generic_phrases)

            if is_generic and len(self.medications) > 0:
                self.chatbot_engine.set_conversation_state("waiting_for_med_name_confirm", "confirm_dose")
                return

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

        if not user_specified_time and len(target_medication.scheduled_times) > 1:
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

            if len(available_times) > 1:
                times_str = ', '.join([t.strftime('%I:%M %p') for t in sorted(available_times)])
                self.chatbot_engine.set_conversation_state("waiting_for_dose_time", "confirm_dose")
                self.chatbot_engine.save_to_context('pending_med_id', target_med_id)
                self.chatbot_engine.save_to_context('ask_dose_time', times_str)
                self.chatbot_engine.save_to_context('ask_med_name', target_medication.name)
                return
            elif len(available_times) == 1:
                user_specified_time = available_times[0]

        actual_time = datetime.now()
        current_time = actual_time.time()

        if user_specified_time:
            closest_scheduled = None
            for scheduled_time in target_medication.scheduled_times:
                if scheduled_time == user_specified_time:
                    closest_scheduled = scheduled_time
                    break

            if not closest_scheduled:
                closest_scheduled = min(
                    target_medication.scheduled_times,
                    key=lambda t: abs((datetime.combine(datetime.today(), t) -
                                       datetime.combine(datetime.today(), user_specified_time)).total_seconds())
                )
        else:
            candidate_times = []

            for scheduled_time in target_medication.scheduled_times:
                scheduled_today = datetime.combine(datetime.today(), scheduled_time)
                diff_seconds = (actual_time - scheduled_today).total_seconds()

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

        for log in self.dose_logs:
            if (log.med_id == target_med_id and
                    log.status == 'taken' and
                    log.scheduled_time.date() == scheduled_datetime.date() and
                    log.scheduled_time.time() == scheduled_datetime.time()):
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
        self.db.save_dose_log(self.user_name, dose_log)
        self.context_manager.update_last_dose(target_med_id, actual_time)

    def prepare_context_info(self, intent):
        context_info = {}
        msg = self.last_user_message

        if intent == 'query_history':
            if self.medications:
                today_logs = []
                for log in self.dose_logs:
                    if log.status == 'taken' and log.actual_time:
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
                taken = sum(1 for log in self.dose_logs if log.status == 'taken')
                skipped = sum(1 for log in self.dose_logs if log.status == 'skipped')
                total = taken + skipped
                context_info['taken'] = taken
                context_info['total'] = total if total > 0 else 1
                context_info['skipped'] = skipped

        elif intent == 'check_schedule':
            current_datetime = datetime.now()
            current_time = current_datetime.time()
            schedule = []

            for med_id, med in self.medications.items():
                for scheduled_time in med.scheduled_times:
                    if scheduled_time.hour <= 3 and current_time.hour >= 22:
                        is_past = False
                    elif scheduled_time.hour >= 22 and current_time.hour <= 3:
                        is_past = True
                    else:
                        is_past = scheduled_time <= current_time

                    status = None
                    for log in self.dose_logs:
                        if log.med_id == med_id:
                            if log.scheduled_time.time() == scheduled_time:
                                if log.status == 'taken':
                                    status = 'taken'
                                    is_past = True
                                    break
                                elif log.status == 'skipped':
                                    status = 'skipped'
                                    is_past = True
                                    break

                    if is_past and status not in ['taken', 'skipped']:
                        status = 'missed'

                    schedule.append({
                        'name': med.name,
                        'time': scheduled_time.strftime('%I:%M %p'),
                        'time_obj': scheduled_time,
                        'is_past': is_past,
                        'status': status
                    })

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
            if self.no_dose_to_skip:
                context_info['no_dose_to_skip'] = True
            elif self.dose_logs:
                last_log = self.dose_logs[-1]
                if last_log.status == 'skipped':
                    med = self.medications.get(last_log.med_id)
                    if med:
                        context_info['skipped_med'] = med.name
                        context_info['skipped_time'] = last_log.scheduled_time.strftime('%I:%M %p')

        return context_info

    def execute_intent_action(self, intent_data, user_message):
        intent = intent_data['intent']
        entities = intent_data.get('entities', {})

        if intent == 'confirm_dose':
            self.handle_dose_confirmation(user_message)

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

    def execute_completed_action(self, followup_result):
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
            medication.is_active = True  # Explicitly set to True!

            self.medications[med_id] = medication
            db.save_medication(self.user_name, medication)

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

    def process_message(self, user_message):
        self.reload_data()

        if not user_message:
            return {'success': False, 'message': ''}

        self.last_user_message = user_message.lower()

        # ── NEW: Run triage check BEFORE intent classification ──
        # Only run triage if not already in a medication conversation
        if not self.chatbot_engine.is_in_conversation():
            triage_result = triage_engine.assess(user_message)
            if triage_result:
                chat_response = triage_engine.format_chat_response(triage_result)
                return {
                    'success': True,
                    'message': chat_response,
                    'in_conversation': False,
                    'triage': triage_result  # Send triage data to frontend
                }
        # ── END triage check ──

        if self.chatbot_engine.is_in_conversation():
            followup_result = self.chatbot_engine.process_followup_response(user_message)

            if followup_result['action'] == 'ask_next':
                return {'success': True, 'message': followup_result['response'], 'in_conversation': True}

            elif followup_result['action'] == 'complete':
                self.execute_completed_action(followup_result)
                self.reload_data()

                if self.chatbot_engine.conversation_state not in ["waiting_for_dose_time", "waiting_for_skip_dose", "waiting_for_old_time"]:
                    self.chatbot_engine.clear_conversation_state()

                return {'success': True, 'message': followup_result['response'], 'in_conversation': False}

            elif followup_result['action'] == 'clarify':
                return {'success': True, 'message': followup_result['response'], 'in_conversation': True}

            else:
                return {'success': True, 'message': followup_result['response'], 'in_conversation': True}

        else:
            intent_data = self.chatbot_engine.process_message(user_message)

            if not self.chatbot_engine.is_in_conversation():
                self.execute_intent_action(intent_data, user_message)

            self.reload_data()
            context_info = self.prepare_context_info(intent_data['intent'])
            response = self.chatbot_engine.generate_response(intent_data, context_info, user_message)
            self.context_manager.add_conversation(user_message, response, intent_data['intent'])

            return {'success': True, 'message': response, 'in_conversation': self.chatbot_engine.is_in_conversation()}


@app.route('/api/user/register', methods=['POST'])
def register_user():
    data = request.json
    user_name = data.get('name') or data.get('user_name')
    password = data.get('password', '')

    if not user_name:
        return jsonify({'error': 'Username is required'}), 400

    # If password provided, use new auth system
    if password:
        result = db.register_user(user_name, password)
        if not result['success']:
            return jsonify({'success': False, 'error': result['error']}), 400

        if user_name not in user_sessions:
            user_sessions[user_name] = ChatbotSession(user_name)

        session = user_sessions[user_name]
        session.reload_data()
        return jsonify({'success': True, 'user_name': user_name, 'medication_count': 0})

    # Legacy: no password (backward compatibility)
    if user_name not in user_sessions:
        user_sessions[user_name] = ChatbotSession(user_name)

    session = user_sessions[user_name]
    session.reload_data()
    medications = session.medications

    return jsonify({'success': True, 'user_name': user_name, 'medication_count': len(medications)})


@app.route('/api/user/login', methods=['POST'])
def login_user():
    """Login with username and password"""
    try:
        data = request.json
        user_name = data.get('user_name') or data.get('name')
        password = data.get('password', '')

        if not user_name or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400

        result = db.login_user(user_name, password)

        if not result['success']:
            return jsonify({'success': False, 'error': result['error']}), 401

        if user_name not in user_sessions:
            user_sessions[user_name] = ChatbotSession(user_name)

        session = user_sessions[user_name]
        session.reload_data()

        return jsonify({
            'success': True,
            'user_name': user_name,
            'medication_count': len(session.medications)
        })

    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_name = data.get('user_name')
    message = data.get('message')

    if not all([user_name, message]):
        return jsonify({'error': 'Missing required fields'}), 400

    if user_name not in user_sessions:
        user_sessions[user_name] = ChatbotSession(user_name)

    session = user_sessions[user_name]
    result = session.process_message(message)

    return jsonify({
        'success': result['success'],
        'message': result['message'],
        'in_conversation': result.get('in_conversation', False),
        'triage': result.get('triage', None)  # NEW: pass triage data to frontend
    })


# NEW: Standalone triage endpoint
@app.route('/api/triage', methods=['POST'])
def triage():
    try:
        data = request.json
        message = data.get('message', '')

        if not message:
            return jsonify({'success': False, 'error': 'message is required'}), 400

        result = triage_engine.assess(message)

        if result:
            return jsonify({'success': True, 'triage': result})
        else:
            return jsonify({'success': True, 'triage': None, 'message': 'No symptoms detected'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dose/skip', methods=['POST'])
def skip_dose():
    """Directly skip/miss a dose without going through chat"""
    try:
        data = request.json
        user_name = data.get('user_name')
        med_name = data.get('med_name')

        if not user_name or not med_name:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        if user_name not in user_sessions:
            user_sessions[user_name] = ChatbotSession(user_name)

        session = user_sessions[user_name]
        session.reload_data()

        # Find medication by name
        target_med_id = None
        for med_id, med in session.medications.items():
            if med.name.lower() == med_name.lower():
                target_med_id = med_id
                break

        if not target_med_id:
            return jsonify({'success': False, 'error': 'Medication not found'}), 404

        # Log as skipped
        from datetime import datetime
        import uuid as uuid_module
        now = datetime.now()
        log_id = str(uuid_module.uuid4())[:8]
        dose_log = DoseLog(
            log_id=log_id,
            med_id=target_med_id,
            scheduled_time=now,
            status="skipped",
            actual_time=now
        )
        db.save_dose_log(user_name, dose_log)
        session.reload_data()

        return jsonify({'success': True, 'message': f'{med_name} marked as skipped'})

    except Exception as e:
        print(f"❌ Error skipping dose: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



def get_medications():
    user_name = request.args.get('user_name')
    if not user_name:
        return jsonify({'error': 'user_name required'}), 400

    if user_name not in user_sessions:
        user_sessions[user_name] = ChatbotSession(user_name)

    session = user_sessions[user_name]
    session.reload_data()
    medications = session.medications

    meds_list = [{
        'med_id': med.med_id,
        'name': med.name,
        'dosage': med.dosage,
        'times_per_day': med.times_per_day,
        'scheduled_times': [t.strftime('%H:%M') for t in med.scheduled_times],
        'is_active': med.is_active
    } for med in medications.values()]

    return jsonify({'success': True, 'medications': meds_list})


@app.route('/api/medication/toggle', methods=['POST'])
def toggle_medication():
    """Toggle medication active/paused status"""
    try:
        data = request.json
        user_name = data.get('user_name')
        med_id = data.get('med_id')
        is_active = data.get('is_active')

        if not all([user_name, med_id, is_active is not None]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        session = user_sessions.get(user_name)
        if session:
            med = session.medications.get(med_id)
            if med:
                med.is_active = is_active
                db.save_medication(user_name, med)
                status = "resumed" if is_active else "paused"
                return jsonify({'success': True, 'message': f'Medication {status}'})

        return jsonify({'success': False, 'error': 'Medication not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/profile', methods=['POST'])
def save_user_profile():
    """Save user profile (onboarding) - timezone, age_group, allergies"""
    try:
        data = request.json
        user_name = data.get('user_name')
        timezone = data.get('timezone', 'UTC')
        age_group = data.get('age_group', 'adult')
        allergies = data.get('allergies', '')

        if not user_name:
            return jsonify({'success': False, 'error': 'user_name required'}), 400

        # Create user profile in database
        success = db.create_user(user_name, timezone, age_group, allergies)

        if success:
            return jsonify({
                'success': True,
                'message': 'Profile saved successfully',
                'user_name': user_name,
                'timezone': timezone,
                'age_group': age_group,
                'allergies': allergies
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to save profile'}), 500

    except Exception as e:
        print(f"❌ Error saving profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """Get user profile information"""
    try:
        user_name = request.args.get('user_name')

        if not user_name:
            return jsonify({'success': False, 'error': 'user_name required'}), 400

        profile = db.get_user_profile(user_name)

        if profile:
            return jsonify({
                'success': True,
                'profile': profile
            })
        else:
            # Return default profile if not created yet
            return jsonify({
                'success': True,
                'profile': {
                    'user_name': user_name,
                    'timezone': 'UTC',
                    'age_group': 'adult',
                    'allergies': ''
                }
            })

    except Exception as e:
        print(f"❌ Error getting profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """Update user profile"""
    try:
        data = request.json
        user_name = data.get('user_name')
        timezone = data.get('timezone')
        age_group = data.get('age_group')
        allergies = data.get('allergies')

        if not user_name:
            return jsonify({'success': False, 'error': 'user_name required'}), 400

        success = db.update_user_profile(user_name, timezone, age_group, allergies)

        if success:
            profile = db.get_user_profile(user_name)
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully',
                'profile': profile
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update profile'}), 500

    except Exception as e:
        print(f"❌ Error updating profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'success': True, 'status': 'healthy', 'message': 'API running'})


if __name__ == '__main__':
    print("🚀 Starting Medication Reminder API...")
    print("📱 WITH proper database deletes for medications")
    print("🩺 Symptom Triage System loaded")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)