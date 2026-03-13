# user.py
# This class stores user preferences and settings

from datetime import datetime


class User:
    """
    Stores user profile and preferences for the chatbot
    """

    def __init__(self, user_id, name, timezone="UTC"):
        """
        Create a new user profile

        user_id: unique ID for this user
        name: user's name
        timezone: user's timezone (default UTC)
        """
        self.user_id = user_id
        self.name = name
        self.timezone = timezone
        self.created_at = datetime.now()

        # Reminder preferences
        self.default_reminder_pref = "on_time"  # or "grace_period"
        self.grace_period_minutes = 15  # how many minutes of delay is acceptable
        self.snooze_duration_minutes = 20  # default snooze time

        # Notification preferences
        self.notifications_enabled = True
        self.sound_enabled = True
        self.vibration_enabled = True

        # Adherence tracking preferences
        self.track_adherence = True
        self.weekly_summary_enabled = True

    def update_reminder_preference(self, pref):
        """
        Change default reminder preference
        pref: "on_time" or "grace_period"
        """
        if pref in ["on_time", "grace_period"]:
            self.default_reminder_pref = pref
            return True
        return False

    def set_grace_period(self, minutes):
        """
        Set how many minutes late is acceptable
        """
        if minutes > 0:
            self.grace_period_minutes = minutes
            return True
        return False

    def set_snooze_duration(self, minutes):
        """
        Set default snooze time in minutes
        """
        if minutes > 0:
            self.snooze_duration_minutes = minutes
            return True
        return False

    def toggle_notifications(self):
        """
        Turn notifications on or off
        """
        self.notifications_enabled = not self.notifications_enabled

    def toggle_sound(self):
        """
        Turn sound on or off
        """
        self.sound_enabled = not self.sound_enabled

    def toggle_vibration(self):
        """
        Turn vibration on or off
        """
        self.vibration_enabled = not self.vibration_enabled

    def toggle_adherence_tracking(self):
        """
        Turn adherence tracking on or off
        """
        self.track_adherence = not self.track_adherence

    def toggle_weekly_summary(self):
        """
        Turn weekly summary on or off
        """
        self.weekly_summary_enabled = not self.weekly_summary_enabled

    def save_to_dict(self):
        """
        Convert user to dictionary for database storage
        """
        return {
            'user_id': self.user_id,
            'name': self.name,
            'timezone': self.timezone,
            'created_at': self.created_at.isoformat(),
            'default_reminder_pref': self.default_reminder_pref,
            'grace_period_minutes': self.grace_period_minutes,
            'snooze_duration_minutes': self.snooze_duration_minutes,
            'notifications_enabled': self.notifications_enabled,
            'sound_enabled': self.sound_enabled,
            'vibration_enabled': self.vibration_enabled,
            'track_adherence': self.track_adherence,
            'weekly_summary_enabled': self.weekly_summary_enabled
        }

    def load_from_dict(data):
        """
        Create User object from dictionary
        """
        user = User(
            user_id=data['user_id'],
            name=data['name'],
            timezone=data['timezone']
        )
        user.created_at = datetime.fromisoformat(data['created_at'])
        user.default_reminder_pref = data['default_reminder_pref']
        user.grace_period_minutes = data['grace_period_minutes']
        user.snooze_duration_minutes = data['snooze_duration_minutes']
        user.notifications_enabled = data['notifications_enabled']
        user.sound_enabled = data['sound_enabled']
        user.vibration_enabled = data['vibration_enabled']
        user.track_adherence = data['track_adherence']
        user.weekly_summary_enabled = data['weekly_summary_enabled']
        return user