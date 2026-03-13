# reminder_manager.py
# This class handles scheduling and managing medication reminders

from datetime import datetime, timedelta
from typing import List, Dict


class ReminderManager:
    """
    Manages all medication reminders, scheduling, and rescheduling
    """

    def __init__(self):
        """
        Create a new reminder manager
        """
        self.active_reminders = {}  # Dict of reminder_id: reminder_data
        self.pending_reminders = []  # List of upcoming reminders
        self.reminder_counter = 0  # To generate unique reminder IDs

    def create_reminder(self, med_id, scheduled_time, reminder_type="standard"):
        """
        Create a new reminder for a medication

        med_id: which medication this reminder is for
        scheduled_time: when to send the reminder
        reminder_type: "standard", "followup", or "predictive"
        Returns: reminder_id
        """
        self.reminder_counter += 1
        reminder_id = f"REM_{self.reminder_counter}"

        reminder_data = {
            'reminder_id': reminder_id,
            'med_id': med_id,
            'scheduled_time': scheduled_time,
            'reminder_type': reminder_type,
            'status': 'pending',  # pending, sent, responded, expired
            'created_at': datetime.now(),
            'sent_at': None,
            'responded_at': None
        }

        self.active_reminders[reminder_id] = reminder_data
        self.pending_reminders.append(reminder_id)
        return reminder_id

    def send_reminder(self, reminder_id):
        """
        Mark reminder as sent
        Returns reminder data if found, None otherwise
        """
        if reminder_id not in self.active_reminders:
            return None

        self.active_reminders[reminder_id]['status'] = 'sent'
        self.active_reminders[reminder_id]['sent_at'] = datetime.now()
        return self.active_reminders[reminder_id]

    def respond_to_reminder(self, reminder_id, response_type):
        """
        Record user response to reminder

        response_type: "taken", "snooze", "skip"
        Returns: True if successful, False if reminder not found
        """
        if reminder_id not in self.active_reminders:
            return False

        self.active_reminders[reminder_id]['status'] = 'responded'
        self.active_reminders[reminder_id]['responded_at'] = datetime.now()
        self.active_reminders[reminder_id]['response_type'] = response_type

        # Remove from pending list
        if reminder_id in self.pending_reminders:
            self.pending_reminders.remove(reminder_id)

        return True

    def snooze_reminder(self, reminder_id, snooze_minutes):
        """
        Reschedule reminder for later

        reminder_id: the reminder to snooze
        snooze_minutes: how many minutes to wait
        Returns: new reminder_id
        """
        if reminder_id not in self.active_reminders:
            return None

        old_reminder = self.active_reminders[reminder_id]

        # Mark old reminder as responded
        self.respond_to_reminder(reminder_id, "snoozed")

        # Create new reminder at snoozed time
        new_time = datetime.now() + timedelta(minutes=snooze_minutes)
        new_reminder_id = self.create_reminder(
            med_id=old_reminder['med_id'],
            scheduled_time=new_time,
            reminder_type="snoozed"
        )

        return new_reminder_id

    def mark_as_missed(self, reminder_id):
        """
        Mark reminder as missed (no response after timeout)
        """
        if reminder_id not in self.active_reminders:
            return False

        self.active_reminders[reminder_id]['status'] = 'missed'

        # Remove from pending
        if reminder_id in self.pending_reminders:
            self.pending_reminders.remove(reminder_id)

        return True

    def get_pending_reminders(self):
        """
        Get list of all pending reminders
        Returns: list of reminder_ids
        """
        return self.pending_reminders.copy()

    def get_reminder_details(self, reminder_id):
        """
        Get full details of a specific reminder
        """
        return self.active_reminders.get(reminder_id, None)

    def check_expired_reminders(self, timeout_minutes=30):
        """
        Find reminders that were sent but got no response

        timeout_minutes: how long to wait before marking as missed
        Returns: list of expired reminder_ids
        """
        expired = []
        current_time = datetime.now()

        for reminder_id, data in self.active_reminders.items():
            if data['status'] == 'sent' and data['sent_at']:
                # Calculate time since sent
                time_passed = (current_time - data['sent_at']).total_seconds() / 60

                if time_passed >= timeout_minutes:
                    expired.append(reminder_id)

        return expired

    def get_reminders_for_medication(self, med_id):
        """
        Get all reminders for a specific medication
        """
        med_reminders = []
        for reminder_id, data in self.active_reminders.items():
            if data['med_id'] == med_id:
                med_reminders.append(reminder_id)
        return med_reminders

    def clear_old_reminders(self, days_old=7):
        """
        Remove reminders older than specified days
        Keeps the system from getting cluttered
        """
        cutoff_time = datetime.now() - timedelta(days=days_old)
        to_remove = []

        for reminder_id, data in self.active_reminders.items():
            if data['created_at'] < cutoff_time:
                to_remove.append(reminder_id)

        for reminder_id in to_remove:
            del self.active_reminders[reminder_id]
            if reminder_id in self.pending_reminders:
                self.pending_reminders.remove(reminder_id)

        return len(to_remove)