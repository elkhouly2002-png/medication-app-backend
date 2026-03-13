# medication.py
# This class stores information about a medication

from datetime import time


class Medication:
    """
    Represents one medication with its schedule and settings
    """

    def __init__(self, med_id, name, dosage, times_per_day, scheduled_times, reminder_pref="on_time", is_active=True):
        """
        Create a new medication

        med_id: unique ID for this medication
        name: medication name like "Paracetamol"
        dosage: amount like "500mg"
        times_per_day: how many times daily (example: 2)
        scheduled_times: list of times (example: [08:00, 20:00])
        reminder_pref: "on_time" or "grace_period"
        is_active: whether medication is active (True) or paused (False)
        """
        self.med_id = med_id
        self.name = name
        self.dosage = dosage
        self.times_per_day = times_per_day
        self.scheduled_times = scheduled_times
        self.reminder_pref = reminder_pref
        self.is_active = is_active

    def get_next_time(self, current_time):
        """
        Find the next scheduled time after current time
        Returns None if no more doses today
        """
        sorted_times = sorted(self.scheduled_times)

        for sched_time in sorted_times:
            if sched_time > current_time:
                return sched_time

        return None

    def change_schedule(self, new_times):
        """
        Update medication schedule to new times
        Returns True if successful, False if wrong number of times
        """
        if len(new_times) != self.times_per_day:
            return False

        self.scheduled_times = sorted(new_times)
        return True

    def pause(self):
        """Turn off reminders temporarily"""
        self.is_active = False

    def unpause(self):
        """Turn reminders back on"""
        self.is_active = True

    def get_info_string(self):
        """Return readable medication info"""
        return f"{self.name} ({self.dosage}) - {self.times_per_day} times per day"

    def save_to_dict(self):
        """
        Convert medication to dictionary for database storage
        Converts time objects to string format
        """
        return {
            'med_id': self.med_id,
            'name': self.name,
            'dosage': self.dosage,
            'times_per_day': self.times_per_day,
            'scheduled_times': [t.strftime('%H:%M') for t in self.scheduled_times],
            'reminder_pref': self.reminder_pref,
            'is_active': self.is_active
        }

    def load_from_dict(data):
        """
        Create Medication object from dictionary
        Converts time strings back to time objects
        """
        # Convert time strings like "08:00" back to time objects
        times_list = []
        for time_str in data['scheduled_times']:
            hour, minute = time_str.split(':')
            times_list.append(time(int(hour), int(minute)))

        # Create the medication object
        med = Medication(
            med_id=data['med_id'],
            name=data['name'],
            dosage=data['dosage'],
            times_per_day=data['times_per_day'],
            scheduled_times=times_list,
            reminder_pref=data['reminder_pref'],
            is_active=data.get('is_active', True)
        )
        return med