"""
Adherence Pattern Analyzer
Detects patterns in missed doses and adjusts reminder times automatically
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Tuple
from collections import defaultdict


class AdherenceAnalyzer:
    def __init__(self, db_manager):
        """Initialize with database manager"""
        self.db = db_manager

        # Thresholds for pattern detection
        self.MIN_SAMPLES = 5  # Minimum doses to analyze
        self.MISS_THRESHOLD = 0.3  # 30% miss rate triggers adjustment
        self.ADJUSTMENT_INCREMENT = 15  # Adjust by 15 minutes
        self.MAX_ADJUSTMENT = 60  # Maximum 1 hour early

    def analyze_patterns(self, user_name: str, medications: Dict) -> Dict[str, Dict]:
        """
        Analyze adherence patterns for all medications
        Returns dict of medication patterns and recommended adjustments
        """
        # Get dose logs from last 30 days
        dose_logs = self.db.load_dose_logs(user_name, days=30)

        # Group logs by medication and scheduled time
        patterns = defaultdict(lambda: {'missed': 0, 'taken': 0, 'skipped': 0, 'total': 0})

        # First, count actual logs
        for log in dose_logs:
            if log.med_id not in medications:
                continue

            med = medications[log.med_id]
            scheduled_time = log.scheduled_time.time()

            key = (log.med_id, scheduled_time.strftime('%H:%M'))

            if log.status == 'missed':
                patterns[key]['missed'] += 1
            elif log.status == 'taken':
                patterns[key]['taken'] += 1
            elif log.status == 'skipped':
                patterns[key]['skipped'] += 1

        # Now calculate expected doses and missed doses
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        for med_id, med in medications.items():
            for scheduled_time in med.scheduled_times:
                key = (med_id, scheduled_time.strftime('%H:%M'))

                # Expected doses = 30 days
                expected_doses = 30

                # Actual doses logged
                actual_logged = patterns[key]['taken'] + patterns[key]['skipped']

                # Missed = expected - logged
                missed = expected_doses - actual_logged

                # Update counts
                patterns[key]['missed'] = missed
                patterns[key]['total'] = expected_doses

        # Analyze each pattern and determine adjustments
        results = {}
        for (med_id, time_str), stats in patterns.items():
            if stats['total'] < self.MIN_SAMPLES:
                continue  # Not enough data

            med = medications[med_id]
            scheduled_time = datetime.strptime(time_str, '%H:%M').time()

            miss_rate = stats['missed'] / stats['total']

            # Get existing pattern from database
            existing = self.db.get_adherence_pattern(user_name, med_id, scheduled_time)
            current_adjustment = existing['reminder_adjustment_minutes'] if existing else 0

            # Determine if adjustment is needed
            new_adjustment = current_adjustment
            recommendation = "on_time"

            if miss_rate >= self.MISS_THRESHOLD:
                # User frequently misses this dose - remind earlier
                if current_adjustment < self.MAX_ADJUSTMENT:
                    new_adjustment = min(current_adjustment + self.ADJUSTMENT_INCREMENT,
                                        self.MAX_ADJUSTMENT)
                    recommendation = "remind_earlier"
            elif miss_rate < 0.1 and current_adjustment > 0:
                # User is doing well - can reduce early reminders
                new_adjustment = max(0, current_adjustment - self.ADJUSTMENT_INCREMENT)
                recommendation = "reduce_early_reminder"

            # Update pattern in database
            self.db.update_adherence_pattern(
                user_name, med_id, scheduled_time,
                stats['missed'], stats['total'], new_adjustment
            )

            # Store results
            key = f"{med.name}_{time_str}"
            results[key] = {
                'medication': med.name,
                'scheduled_time': time_str,
                'miss_rate': miss_rate,
                'stats': stats,
                'current_adjustment': current_adjustment,
                'new_adjustment': new_adjustment,
                'recommendation': recommendation
            }

        return results

    def get_adjusted_reminder_time(self, user_name: str, med_id: str,
                                   scheduled_time: time) -> Tuple[time, int]:
        """
        Get adjusted reminder time based on adherence patterns
        Returns (adjusted_time, adjustment_minutes)
        """
        pattern = self.db.get_adherence_pattern(user_name, med_id, scheduled_time)

        if not pattern or pattern['reminder_adjustment_minutes'] == 0:
            return scheduled_time, 0

        # Calculate adjusted time
        adjustment_minutes = pattern['reminder_adjustment_minutes']
        scheduled_datetime = datetime.combine(datetime.today(), scheduled_time)
        adjusted_datetime = scheduled_datetime - timedelta(minutes=adjustment_minutes)

        return adjusted_datetime.time(), adjustment_minutes

    def generate_adherence_insights(self, user_name: str, medications: Dict) -> str:
        """
        Generate human-readable insights about adherence patterns
        """
        patterns = self.analyze_patterns(user_name, medications)

        if not patterns:
            return "Not enough data yet to detect patterns. Keep tracking your medications!"

        insights = []
        insights.append("📊 **Adherence Pattern Analysis:**\n")

        # Group by recommendation type
        early_reminders = []
        good_adherence = []
        needs_attention = []

        for key, data in patterns.items():
            med_name = data['medication']
            time_str = data['scheduled_time']
            miss_rate = data['miss_rate']
            adjustment = data['new_adjustment']

            if data['recommendation'] == 'remind_earlier':
                early_reminders.append(
                    f"  • **{med_name} at {time_str}**: {miss_rate*100:.0f}% missed - "
                    f"I'll remind you {adjustment} minutes earlier now"
                )
            elif miss_rate < 0.1:
                good_adherence.append(
                    f"  • **{med_name} at {time_str}**: Excellent! {data['stats']['taken']} taken, "
                    f"{data['stats']['missed']} missed"
                )
            elif miss_rate >= 0.2:
                needs_attention.append(
                    f"  • **{med_name} at {time_str}**: {miss_rate*100:.0f}% missed - "
                    f"consider setting a phone alarm too"
                )

        if good_adherence:
            insights.append("✅ **Great adherence:**")
            insights.extend(good_adherence)
            insights.append("")

        if early_reminders:
            insights.append("⏰ **Automatic adjustments made:**")
            insights.extend(early_reminders)
            insights.append("")

        if needs_attention:
            insights.append("⚠️ **Needs attention:**")
            insights.extend(needs_attention)
            insights.append("")

        return "\n".join(insights)

    def should_send_reminder(self, user_name: str, med_id: str,
                           scheduled_time: time, current_time: time) -> bool:
        """
        Determine if reminder should be sent based on adjusted time
        """
        adjusted_time, adjustment = self.get_adjusted_reminder_time(
            user_name, med_id, scheduled_time
        )

        # Send reminder if current time matches adjusted time (within 1 minute)
        time_diff = abs(
            (datetime.combine(datetime.today(), current_time) -
             datetime.combine(datetime.today(), adjusted_time)).total_seconds()
        )

        return time_diff <= 60  # Within 1 minute