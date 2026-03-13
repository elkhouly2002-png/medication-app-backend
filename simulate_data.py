"""
Medication Data Simulator
Generates realistic medication usage data over weeks to test adherence patterns
"""

import sqlite3
from datetime import datetime, timedelta, time
import uuid
import random


class MedicationDataSimulator:
    def __init__(self, db_path='medication_chatbot.db'):
        """Initialize simulator with database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def clear_user_data(self, user_name):
        """Clear all data for a user"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM medications WHERE user_name = ?', (user_name,))
        cursor.execute('DELETE FROM dose_logs WHERE user_name = ?', (user_name,))
        cursor.execute('DELETE FROM adherence_patterns WHERE user_name = ?', (user_name,))
        self.conn.commit()
        print(f"✅ Cleared all data for user: {user_name}")
    
    def add_medication(self, user_name, name, dosage, times):
        """Add a medication for a user"""
        import json
        cursor = self.conn.cursor()
        
        med_id = str(uuid.uuid4())[:8]
        times_json = json.dumps(times)  # Proper JSON format
        
        cursor.execute('''
            INSERT INTO medications 
            (med_id, user_name, name, dosage, times_per_day, scheduled_times, reminder_pref)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (med_id, user_name, name, dosage, len(times), times_json, 'on_time'))
        
        self.conn.commit()
        return med_id
    
    def simulate_dose_pattern(self, user_name, med_id, scheduled_time, start_date, days, 
                             miss_rate=0.0, late_rate=0.0):
        """
        Simulate dose-taking pattern over multiple days
        
        Parameters:
        - miss_rate: Probability of missing a dose (0.0 to 1.0)
        - late_rate: Probability of taking dose late (0.0 to 1.0)
        """
        cursor = self.conn.cursor()
        
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            scheduled_datetime = datetime.combine(current_date, scheduled_time)
            
            # Randomly determine if dose is missed, taken late, or taken on time
            rand = random.random()
            
            if rand < miss_rate:
                # Missed dose - no log entry (will show as missed)
                continue
            else:
                # Dose taken
                log_id = str(uuid.uuid4())[:8]
                
                # Determine if taken late
                if random.random() < late_rate:
                    # Taken late (10-60 minutes)
                    delay_minutes = random.randint(10, 60)
                    actual_time = scheduled_datetime + timedelta(minutes=delay_minutes)
                    status = 'taken'
                else:
                    # Taken on time
                    actual_time = scheduled_datetime
                    status = 'taken'
                
                cursor.execute('''
                    INSERT INTO dose_logs
                    (log_id, user_name, med_id, scheduled_time, actual_time, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (log_id, user_name, med_id, 
                     scheduled_datetime.isoformat(), 
                     actual_time.isoformat(), 
                     status))
        
        self.conn.commit()
    
    def simulate_realistic_scenario(self, user_name, scenario='typical'):
        """
        Simulate realistic medication usage scenarios
        
        Scenarios:
        - typical: Good adherence with occasional misses
        - morning_struggle: Frequently misses morning doses
        - evening_struggle: Frequently misses evening doses
        - excellent: Nearly perfect adherence
        - poor: Frequently misses doses
        """
        print(f"\n{'='*60}")
        print(f"SIMULATING SCENARIO: {scenario.upper()}")
        print(f"User: {user_name}")
        print(f"{'='*60}\n")
        
        # Clear existing data
        self.clear_user_data(user_name)
        
        # Add medications
        aspirin_id = self.add_medication(user_name, 'Aspirin', '500 mg', ['08:00', '20:00'])
        metformin_id = self.add_medication(user_name, 'Metformin', '500 mg', ['08:00', '20:00'])
        vitamin_d_id = self.add_medication(user_name, 'Vitamin D', '2000 IU', ['19:00'])
        
        print(f"✅ Added 3 medications")
        
        # Simulate 30 days of data
        start_date = datetime.now() - timedelta(days=30)
        
        if scenario == 'typical':
            # Good overall adherence, occasional misses
            self.simulate_dose_pattern(user_name, aspirin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.1, late_rate=0.2)
            self.simulate_dose_pattern(user_name, aspirin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.15, late_rate=0.2)
            self.simulate_dose_pattern(user_name, metformin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.1, late_rate=0.15)
            self.simulate_dose_pattern(user_name, metformin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.1, late_rate=0.15)
            self.simulate_dose_pattern(user_name, vitamin_d_id, time(19, 0), start_date, 30, 
                                      miss_rate=0.05, late_rate=0.1)
        
        elif scenario == 'morning_struggle':
            # Frequently misses morning doses, good with evening
            self.simulate_dose_pattern(user_name, aspirin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.4, late_rate=0.3)  # 40% miss rate
            self.simulate_dose_pattern(user_name, aspirin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.1, late_rate=0.15)
            self.simulate_dose_pattern(user_name, metformin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.35, late_rate=0.25)  # 35% miss rate
            self.simulate_dose_pattern(user_name, metformin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.1, late_rate=0.1)
            self.simulate_dose_pattern(user_name, vitamin_d_id, time(19, 0), start_date, 30, 
                                      miss_rate=0.05, late_rate=0.1)
        
        elif scenario == 'evening_struggle':
            # Good with morning, frequently misses evening
            self.simulate_dose_pattern(user_name, aspirin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.1, late_rate=0.15)
            self.simulate_dose_pattern(user_name, aspirin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.4, late_rate=0.3)  # 40% miss rate
            self.simulate_dose_pattern(user_name, metformin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.1, late_rate=0.1)
            self.simulate_dose_pattern(user_name, metformin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.35, late_rate=0.25)  # 35% miss rate
            self.simulate_dose_pattern(user_name, vitamin_d_id, time(19, 0), start_date, 30, 
                                      miss_rate=0.3, late_rate=0.2)
        
        elif scenario == 'excellent':
            # Nearly perfect adherence
            self.simulate_dose_pattern(user_name, aspirin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.03, late_rate=0.05)
            self.simulate_dose_pattern(user_name, aspirin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.03, late_rate=0.05)
            self.simulate_dose_pattern(user_name, metformin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.03, late_rate=0.05)
            self.simulate_dose_pattern(user_name, metformin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.03, late_rate=0.05)
            self.simulate_dose_pattern(user_name, vitamin_d_id, time(19, 0), start_date, 30, 
                                      miss_rate=0.0, late_rate=0.05)
        
        elif scenario == 'poor':
            # Frequently misses doses across the board
            self.simulate_dose_pattern(user_name, aspirin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.4, late_rate=0.3)
            self.simulate_dose_pattern(user_name, aspirin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.4, late_rate=0.3)
            self.simulate_dose_pattern(user_name, metformin_id, time(8, 0), start_date, 30, 
                                      miss_rate=0.45, late_rate=0.3)
            self.simulate_dose_pattern(user_name, metformin_id, time(20, 0), start_date, 30, 
                                      miss_rate=0.45, late_rate=0.3)
            self.simulate_dose_pattern(user_name, vitamin_d_id, time(19, 0), start_date, 30, 
                                      miss_rate=0.35, late_rate=0.25)
        
        print(f"✅ Generated 30 days of dose logs")
        print(f"\n{'='*60}")
        print(f"SIMULATION COMPLETE!")
        print(f"{'='*60}\n")
        print(f"Run the chatbot as user '{user_name}' to see:")
        print(f"  • Adherence statistics")
        print(f"  • Pattern detection")
        print(f"  • Automatic reminder adjustments")
        print(f"\nCommand: python3 main.py")
        print(f"Then enter name: {user_name}\n")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Run simulation scenarios"""
    print("=" * 60)
    print("MEDICATION DATA SIMULATOR")
    print("=" * 60)
    print("\nAvailable scenarios:")
    print("  1. typical - Good adherence with occasional misses")
    print("  2. morning_struggle - Frequently misses morning doses")
    print("  3. evening_struggle - Frequently misses evening doses")
    print("  4. excellent - Nearly perfect adherence")
    print("  5. poor - Frequently misses doses")
    print("  6. all - Run all scenarios with different users")
    
    choice = input("\nSelect scenario (1-6): ").strip()
    
    simulator = MedicationDataSimulator()
    
    scenarios = {
        '1': ('typical', 'TestUser_Typical'),
        '2': ('morning_struggle', 'TestUser_Morning'),
        '3': ('evening_struggle', 'TestUser_Evening'),
        '4': ('excellent', 'TestUser_Excellent'),
        '5': ('poor', 'TestUser_Poor'),
    }
    
    if choice == '6':
        # Run all scenarios
        for scenario_type, user_name in scenarios.values():
            simulator.simulate_realistic_scenario(user_name, scenario_type)
    elif choice in scenarios:
        scenario_type, user_name = scenarios[choice]
        simulator.simulate_realistic_scenario(user_name, scenario_type)
    else:
        print("Invalid choice!")
    
    simulator.close()


if __name__ == "__main__":
    main()
