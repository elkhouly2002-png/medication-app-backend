# dose_log.py
# This class records each dose taken, delayed, or missed

from datetime import datetime


class DoseLog:
    """
    Records a single dose event (taken, missed, or delayed)
    """

    def __init__(self, log_id, med_id, scheduled_time, status, actual_time=None):
        """
        Create a new dose log entry

        log_id: unique ID for this log entry
        med_id: which medication this is for
        scheduled_time: when the dose was supposed to be taken
        status: "taken", "missed", "delayed", or "skipped"
        actual_time: when it was actually taken (None if missed/skipped)
        """
        self.log_id = log_id
        self.med_id = med_id
        self.scheduled_time = scheduled_time
        self.status = status
        self.actual_time = actual_time
        self.logged_at = datetime.now()  # When this log was created

    def mark_as_taken(self, taken_time):
        """
        Update the log to show dose was taken
        """
        self.status = "taken"
        self.actual_time = taken_time

    def mark_as_missed(self):
        """
        Update the log to show dose was missed
        """
        self.status = "missed"
        self.actual_time = None

    def mark_as_delayed(self, new_time):
        """
        Update the log to show dose was delayed
        """
        self.status = "delayed"
        self.actual_time = new_time

    def mark_as_skipped(self):
        """
        Update the log when user intentionally skips dose
        """
        self.status = "skipped"
        self.actual_time = None

    def get_delay_minutes(self):
        """
        Calculate how many minutes late the dose was taken
        Returns 0 if taken on time, None if not taken
        """
        if self.actual_time is None:
            return None

        # Calculate difference in minutes
        delay = (self.actual_time - self.scheduled_time).total_seconds() / 60
        return max(0, delay)  # Return 0 if taken early

    def was_on_time(self, grace_minutes=15):
        """
        Check if dose was taken within acceptable time window
        grace_minutes: how many minutes late is still "on time"
        """
        if self.status != "taken":
            return False

        delay = self.get_delay_minutes()
        if delay is None:
            return False

        return delay <= grace_minutes

    def save_to_dict(self):
        """
        Convert log to dictionary for database storage
        """
        return {
            'log_id': self.log_id,
            'med_id': self.med_id,
            'scheduled_time': self.scheduled_time.isoformat(),
            'status': self.status,
            'actual_time': self.actual_time.isoformat() if self.actual_time else None,
            'logged_at': self.logged_at.isoformat()
        }

    def load_from_dict(data):
        """
        Create DoseLog object from dictionary
        """
        log = DoseLog(
            log_id=data['log_id'],
            med_id=data['med_id'],
            scheduled_time=datetime.fromisoformat(data['scheduled_time']),
            status=data['status'],
            actual_time=datetime.fromisoformat(data['actual_time']) if data['actual_time'] else None
        )
        log.logged_at = datetime.fromisoformat(data['logged_at'])
        return log