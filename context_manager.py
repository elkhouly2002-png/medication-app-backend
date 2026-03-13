# context_manager.py
# This class manages conversation memory and user behavior patterns

from datetime import datetime, timedelta
from typing import List, Dict


class ContextManager:
    """
    Stores and manages conversation context and user patterns
    """

    def __init__(self):
        """
        Create a new context manager
        """
        self.conversation_history = []  # List of recent interactions
        self.last_dose_times = {}  # med_id: last dose datetime
        self.user_patterns = {}  # med_id: pattern data
        self.delay_history = {}  # med_id: list of delay times
        self.missed_history = {}  # med_id: list of missed dates

    def add_conversation(self, user_message, bot_response, intent=None):
        """
        Add a conversation exchange to history

        user_message: what the user said
        bot_response: what the bot replied
        intent: detected intent (optional)
        """
        conversation_entry = {
            'timestamp': datetime.now(),
            'user_message': user_message,
            'bot_response': bot_response,
            'intent': intent
        }
        self.conversation_history.append(conversation_entry)

        # Keep only last 50 conversations to save memory
        if len(self.conversation_history) > 50:
            self.conversation_history.pop(0)

    def update_last_dose(self, med_id, dose_time):
        """
        Update the last time a medication was taken
        """
        self.last_dose_times[med_id] = dose_time

    def get_last_dose(self, med_id):
        """
        Get the last time a medication was taken
        Returns None if never taken
        """
        return self.last_dose_times.get(med_id, None)

    def record_delay(self, med_id, delay_minutes):
        """
        Record how many minutes late a dose was taken
        """
        if med_id not in self.delay_history:
            self.delay_history[med_id] = []

        self.delay_history[med_id].append({
            'timestamp': datetime.now(),
            'delay_minutes': delay_minutes
        })

    def record_missed_dose(self, med_id, missed_date):
        """
        Record when a dose was missed
        """
        if med_id not in self.missed_history:
            self.missed_history[med_id] = []

        self.missed_history[med_id].append(missed_date)

    def get_average_delay(self, med_id, days=7):
        """
        Calculate average delay for a medication over last N days
        Returns None if no data
        """
        if med_id not in self.delay_history:
            return None

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_delays = [
            entry['delay_minutes']
            for entry in self.delay_history[med_id]
            if entry['timestamp'] >= cutoff_date
        ]

        if not recent_delays:
            return None

        return sum(recent_delays) / len(recent_delays)

    def get_missed_count(self, med_id, days=7):
        """
        Count how many doses were missed in last N days
        """
        if med_id not in self.missed_history:
            return 0

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_missed = [
            date for date in self.missed_history[med_id]
            if date >= cutoff_date
        ]

        return len(recent_missed)

    def detect_pattern(self, med_id):
        """
        Detect patterns in medication taking behavior
        Returns dict with pattern information
        """
        pattern = {
            'frequently_delayed': False,
            'frequently_missed': False,
            'weekend_issues': False,
            'morning_issues': False,
            'evening_issues': False
        }

        # Check if frequently delayed (average delay > 20 mins)
        avg_delay = self.get_average_delay(med_id, days=14)
        if avg_delay and avg_delay > 20:
            pattern['frequently_delayed'] = True

        # Check if frequently missed (more than 2 in last week)
        missed_count = self.get_missed_count(med_id, days=7)
        if missed_count > 2:
            pattern['frequently_missed'] = True

        # Check for weekend pattern
        if self.check_weekend_pattern(med_id):
            pattern['weekend_issues'] = True

        # Store pattern for this medication
        self.user_patterns[med_id] = pattern
        return pattern

    def check_weekend_pattern(self, med_id):
        """
        Check if user tends to miss doses on weekends
        """
        if med_id not in self.missed_history:
            return False

        # Get recent missed doses
        cutoff_date = datetime.now() - timedelta(days=14)
        recent_missed = [
            date for date in self.missed_history[med_id]
            if date >= cutoff_date
        ]

        # Count weekend vs weekday misses
        weekend_misses = sum(1 for date in recent_missed if date.weekday() >= 5)
        weekday_misses = len(recent_missed) - weekend_misses

        # If more than 60% of misses are on weekends, it's a pattern
        if len(recent_missed) >= 3:
            weekend_ratio = weekend_misses / len(recent_missed)
            return weekend_ratio > 0.6

        return False

    def get_recent_conversations(self, count=10):
        """
        Get the last N conversations
        """
        return self.conversation_history[-count:]

    def search_conversation_history(self, keyword):
        """
        Search for conversations containing a keyword
        """
        results = []
        for entry in self.conversation_history:
            if keyword.lower() in entry['user_message'].lower():
                results.append(entry)
        return results

    def clear_old_data(self, days=30):
        """
        Remove data older than specified days
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Clear old conversations
        self.conversation_history = [
            entry for entry in self.conversation_history
            if entry['timestamp'] >= cutoff_date
        ]

        # Clear old delay history
        for med_id in self.delay_history:
            self.delay_history[med_id] = [
                entry for entry in self.delay_history[med_id]
                if entry['timestamp'] >= cutoff_date
            ]

        # Clear old missed history
        for med_id in self.missed_history:
            self.missed_history[med_id] = [
                date for date in self.missed_history[med_id]
                if date >= cutoff_date
            ]