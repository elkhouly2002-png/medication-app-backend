# adherence_predictor.py
# This class predicts missed doses and suggests improvements

from datetime import datetime, timedelta
from typing import Dict, List


class AdherencePredictor:
    """
    Analyzes patterns and predicts when doses might be missed
    """

    def __init__(self, context_manager):
        """
        Create a new adherence predictor

        context_manager: reference to ContextManager for pattern data
        """
        self.context_manager = context_manager
        self.prediction_threshold = 0.6  # 60% confidence to trigger prediction

    def predict_missed_dose(self, med_id, scheduled_time):
        """
        Predict if a dose is likely to be missed

        med_id: medication to check
        scheduled_time: when the dose is scheduled
        Returns: dict with prediction and confidence
        """
        prediction = {
            'will_miss': False,
            'confidence': 0.0,
            'reasons': []
        }

        # Get user patterns for this medication
        patterns = self.context_manager.detect_pattern(med_id)

        # Check if it's a weekend and user has weekend pattern
        if scheduled_time.weekday() >= 5 and patterns.get('weekend_issues', False):
            prediction['confidence'] += 0.3
            prediction['reasons'].append('weekend_pattern')

        # Check if user frequently misses this medication
        missed_count = self.context_manager.get_missed_count(med_id, days=7)
        if missed_count >= 3:
            prediction['confidence'] += 0.4
            prediction['reasons'].append('frequent_misses')

        # Check if user frequently delays (might lead to miss)
        avg_delay = self.context_manager.get_average_delay(med_id, days=7)
        if avg_delay and avg_delay > 30:
            prediction['confidence'] += 0.2
            prediction['reasons'].append('frequent_delays')

        # Check time of day patterns
        hour = scheduled_time.hour
        if hour < 9 and patterns.get('morning_issues', False):
            prediction['confidence'] += 0.3
            prediction['reasons'].append('morning_pattern')
        elif hour >= 20 and patterns.get('evening_issues', False):
            prediction['confidence'] += 0.3
            prediction['reasons'].append('evening_pattern')

        # Make final prediction
        if prediction['confidence'] >= self.prediction_threshold:
            prediction['will_miss'] = True

        return prediction

    def suggest_reminder_time(self, med_id, current_scheduled_time):
        """
        Suggest a better reminder time based on patterns

        med_id: medication to analyze
        current_scheduled_time: current time object
        Returns: suggested time or None
        """
        avg_delay = self.context_manager.get_average_delay(med_id, days=14)

        # If user consistently delays by similar amount, suggest earlier time
        if avg_delay and avg_delay > 15:
            # Suggest moving reminder earlier by average delay amount
            suggested_minutes = int(avg_delay)
            return {
                'suggested_time': current_scheduled_time - timedelta(minutes=suggested_minutes),
                'reason': f'You usually take this {suggested_minutes} minutes late',
                'confidence': 0.7
            }

        return None

    def should_send_early_reminder(self, med_id, scheduled_time):
        """
        Decide if an early reminder should be sent

        Returns: dict with decision and timing
        """
        prediction = self.predict_missed_dose(med_id, scheduled_time)

        if prediction['will_miss'] and prediction['confidence'] >= 0.7:
            return {
                'send_early': True,
                'minutes_before': 15,
                'message': 'You often miss this dose, so I\'m reminding you early.'
            }

        return {'send_early': False}

    def calculate_adherence_score(self, med_id, days=7):
        """
        Calculate adherence percentage for a medication

        med_id: medication to analyze
        days: how many days to look back
        Returns: adherence score (0-100)
        """
        # Get missed count
        missed = self.context_manager.get_missed_count(med_id, days)

        # Estimate total expected doses (this is simplified)
        # In real implementation, would check actual schedule
        expected_doses = days * 2  # Assuming 2 doses per day average

        if expected_doses == 0:
            return 100.0

        taken = expected_doses - missed
        adherence = (taken / expected_doses) * 100

        return max(0.0, min(100.0, adherence))

    def generate_adherence_report(self, med_id, days=7):
        """
        Generate detailed adherence report

        Returns: dict with adherence statistics
        """
        report = {
            'medication_id': med_id,
            'period_days': days,
            'adherence_score': self.calculate_adherence_score(med_id, days),
            'missed_count': self.context_manager.get_missed_count(med_id, days),
            'average_delay': self.context_manager.get_average_delay(med_id, days),
            'patterns': self.context_manager.detect_pattern(med_id),
            'generated_at': datetime.now()
        }

        # Add interpretation
        if report['adherence_score'] >= 90:
            report['interpretation'] = 'Excellent adherence'
        elif report['adherence_score'] >= 75:
            report['interpretation'] = 'Good adherence'
        elif report['adherence_score'] >= 60:
            report['interpretation'] = 'Fair adherence, room for improvement'
        else:
            report['interpretation'] = 'Poor adherence, needs attention'

        return report

    def generate_insights(self, med_id):
        """
        Generate actionable insights for the user

        Returns: list of insight strings
        """
        insights = []
        patterns = self.context_manager.detect_pattern(med_id)

        # Weekend pattern insight
        if patterns.get('weekend_issues', False):
            insights.append("You tend to miss doses on weekends. Consider setting an alarm.")

        # Delay pattern insight
        avg_delay = self.context_manager.get_average_delay(med_id, days=14)
        if avg_delay and avg_delay > 20:
            insights.append(
                f"You usually take this medication {int(avg_delay)} minutes late. Would you like to adjust the reminder time?")

        # Frequent misses insight
        missed = self.context_manager.get_missed_count(med_id, days=7)
        if missed >= 3:
            insights.append(f"You've missed {missed} doses this week. Let me know if you need help staying on track.")

        # Morning/evening pattern insights
        if patterns.get('morning_issues', False):
            insights.append("Morning doses seem difficult for you. Consider moving them to a later time.")
        if patterns.get('evening_issues', False):
            insights.append("Evening doses are often missed. Try setting a phone alarm as backup.")

        return insights

    def predict_weekly_adherence(self, med_id):
        """
        Predict likely adherence for the coming week

        Returns: predicted adherence percentage
        """
        # Use last 2 weeks to predict next week
        recent_score = self.calculate_adherence_score(med_id, days=14)
        patterns = self.context_manager.detect_pattern(med_id)

        # Adjust prediction based on patterns
        predicted_score = recent_score

        if patterns.get('frequently_delayed', False):
            predicted_score -= 5  # Delays might lead to misses

        if patterns.get('weekend_issues', False):
            predicted_score -= 10  # Weekend issues likely to continue

        return max(0.0, min(100.0, predicted_score))