"""
Database Manager for Medication Reminder Chatbot
Handles persistent storage of medications, dose logs, user profiles, and adherence patterns
UPDATED: Added user profile fields (allergies, timezone, age_group) and password authentication
"""

import sqlite3
from datetime import datetime, date, time
import json
import hashlib
from typing import List, Dict, Optional
from medication import Medication
from dose_log import DoseLog


class DatabaseManager:
    def __init__(self, db_path='medication_chatbot.db'):
        """Initialize database connection and create tables"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self.create_tables()

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()

        # Users table with password
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_name TEXT PRIMARY KEY,
                password TEXT DEFAULT '',
                timezone TEXT DEFAULT 'UTC',
                age_group TEXT DEFAULT 'adult',
                allergies TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Medications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medications (
                med_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL,
                name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                times_per_day INTEGER NOT NULL,
                scheduled_times TEXT NOT NULL,
                reminder_pref TEXT NOT NULL,
                start_date DATE,
                end_date DATE,
                instructions TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_name) REFERENCES users(user_name)
            )
        ''')

        # Dose logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dose_logs (
                log_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL,
                med_id TEXT NOT NULL,
                scheduled_time TIMESTAMP NOT NULL,
                actual_time TIMESTAMP,
                status TEXT NOT NULL,
                reason TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (med_id) REFERENCES medications(med_id),
                FOREIGN KEY (user_name) REFERENCES users(user_name)
            )
        ''')

        # Adherence patterns table (for adaptive reminders)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adherence_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                med_id TEXT NOT NULL,
                scheduled_time TIME NOT NULL,
                miss_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reminder_adjustment_minutes INTEGER DEFAULT 0,
                FOREIGN KEY (med_id) REFERENCES medications(med_id),
                FOREIGN KEY (user_name) REFERENCES users(user_name)
            )
        ''')

        self.conn.commit()

        # Migration: add password column if it doesn't exist
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN password TEXT DEFAULT ""')
            self.conn.commit()
            print("✅ Migration: added password column")
        except Exception:
            pass  # Column already exists, ignore

    # ============ AUTH METHODS ============

    def register_user(self, user_name: str, password: str) -> dict:
        """Register a new user with username and password"""
        cursor = self.conn.cursor()

        # Check if username already exists
        cursor.execute('SELECT user_name FROM users WHERE user_name = ?', (user_name,))
        if cursor.fetchone():
            return {'success': False, 'error': 'Username already exists'}

        # Validate username
        if len(user_name) < 3:
            return {'success': False, 'error': 'Username must be at least 3 characters'}
        if not user_name.replace('_', '').isalnum():
            return {'success': False, 'error': 'Username can only contain letters, numbers, and underscores'}

        # Validate password
        if len(password) < 6:
            return {'success': False, 'error': 'Password must be at least 6 characters'}

        try:
            hashed = self._hash_password(password)
            cursor.execute('''
                INSERT INTO users (user_name, password, timezone, age_group, allergies, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_name, hashed, 'UTC', 'adult', '', datetime.now().isoformat(), datetime.now().isoformat()))
            self.conn.commit()
            print(f"✅ User registered: {user_name}")
            return {'success': True}
        except Exception as e:
            print(f"❌ Error registering user: {e}")
            return {'success': False, 'error': str(e)}

    def login_user(self, user_name: str, password: str) -> dict:
        """Login user with username and password"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT user_name, password FROM users WHERE user_name = ?', (user_name,))
        row = cursor.fetchone()

        if not row:
            return {'success': False, 'error': 'Username not found'}

        hashed = self._hash_password(password)
        if row['password'] != hashed:
            return {'success': False, 'error': 'Incorrect password'}

        return {'success': True, 'user_name': user_name}

    def user_exists(self, user_name: str) -> bool:
        """Check if a username already exists"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_name FROM users WHERE user_name = ?', (user_name,))
        return cursor.fetchone() is not None

    # ============ USER PROFILE METHODS ============

    def create_user(self, user_name: str, timezone: str = 'UTC', age_group: str = 'adult', allergies: str = ''):
        """Create a new user with profile information"""
        cursor = self.conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_name, timezone, age_group, allergies, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_name, timezone, age_group, allergies, datetime.now().isoformat(), datetime.now().isoformat()))

            self.conn.commit()
            print(f"✅ User created: {user_name} (timezone: {timezone}, age: {age_group}, allergies: {allergies})")
            return True
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return False

    def get_user_profile(self, user_name: str) -> Optional[Dict]:
        """Get user profile information"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM users WHERE user_name = ?
        ''', (user_name,))

        row = cursor.fetchone()
        if row:
            return {
                'user_name': row['user_name'],
                'timezone': row['timezone'],
                'age_group': row['age_group'],
                'allergies': row['allergies'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
        return None

    def update_user_profile(self, user_name: str, timezone: str = None, age_group: str = None, allergies: str = None):
        """Update user profile information"""
        cursor = self.conn.cursor()

        # Get current profile
        current = self.get_user_profile(user_name)
        if not current:
            print(f"❌ User not found: {user_name}")
            return False

        # Use provided values or keep existing ones
        tz = timezone if timezone else current['timezone']
        ag = age_group if age_group else current['age_group']
        al = allergies if allergies else current['allergies']

        try:
            cursor.execute('''
                UPDATE users 
                SET timezone = ?, age_group = ?, allergies = ?, updated_at = ?
                WHERE user_name = ?
            ''', (tz, ag, al, datetime.now().isoformat(), user_name))

            self.conn.commit()
            print(f"✅ User profile updated: {user_name}")
            return True
        except Exception as e:
            print(f"❌ Error updating profile: {e}")
            return False

    def get_user_allergies(self, user_name: str) -> List[str]:
        """Get user allergies as a list"""
        profile = self.get_user_profile(user_name)
        if not profile:
            return []

        allergies_str = profile['allergies']
        if not allergies_str:
            return []

        # Parse comma-separated allergies
        return [a.strip() for a in allergies_str.split(',')]

    # ============ MEDICATION METHODS ============

    def save_medication(self, user_name: str, medication: Medication, start_date: str = None,
                       end_date: str = None, instructions: str = '', notes: str = ''):
        """Save medication to database"""
        cursor = self.conn.cursor()

        # Convert scheduled_times (list of time objects) to JSON string
        times_json = json.dumps([t.strftime('%H:%M') for t in medication.scheduled_times])

        try:
            # Determine is_active value - default to 1 if not set
            is_active_value = 1 if medication.is_active else 0

            cursor.execute('''
                INSERT OR REPLACE INTO medications 
                (med_id, user_name, name, dosage, times_per_day, scheduled_times, 
                 reminder_pref, start_date, end_date, instructions, notes, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (medication.med_id, user_name, medication.name, medication.dosage,
                  medication.times_per_day, times_json, medication.reminder_pref,
                  start_date, end_date, instructions, notes, is_active_value))

            self.conn.commit()
            print(f"✅ Medication saved: {medication.name} (active: {is_active_value})")
            return True
        except Exception as e:
            print(f"❌ Error saving medication: {e}")
            return False

    def load_medications(self, user_name: str) -> Dict[str, Medication]:
        """Load all medications for a user"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM medications WHERE user_name = ?
        ''', (user_name,))

        medications = {}
        for row in cursor.fetchall():
            # Parse scheduled_times from JSON
            times_list = json.loads(row['scheduled_times'])
            scheduled_times = [datetime.strptime(t, '%H:%M').time() for t in times_list]

            med = Medication(
                med_id=row['med_id'],
                name=row['name'],
                dosage=row['dosage'],
                times_per_day=row['times_per_day'],
                scheduled_times=scheduled_times,
                reminder_pref=row['reminder_pref']
            )

            # Add extra fields
            med.start_date = row['start_date']
            med.end_date = row['end_date']
            med.instructions = row['instructions']
            med.notes = row['notes']
            med.is_active = bool(row['is_active'])  # Set from database!

            medications[med.med_id] = med

        return medications

    def get_medication(self, med_id: str) -> Optional[Dict]:
        """Get a specific medication"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM medications WHERE med_id = ?
        ''', (med_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def edit_medication(self, med_id: str, name: str = None, dosage: str = None,
                       instructions: str = None, notes: str = None):
        """Edit medication details"""
        cursor = self.conn.cursor()

        current = self.get_medication(med_id)
        if not current:
            print(f"❌ Medication not found: {med_id}")
            return False

        try:
            cursor.execute('''
                UPDATE medications 
                SET name = ?, dosage = ?, instructions = ?, notes = ?
                WHERE med_id = ?
            ''', (
                name if name else current['name'],
                dosage if dosage else current['dosage'],
                instructions if instructions else current['instructions'],
                notes if notes else current['notes'],
                med_id
            ))

            self.conn.commit()
            print(f"✅ Medication edited: {med_id}")
            return True
        except Exception as e:
            print(f"❌ Error editing medication: {e}")
            return False

    def delete_medication(self, med_id: str):
        """Hard delete medication from database"""
        cursor = self.conn.cursor()
        try:
            # Actually delete the medication (not just mark as inactive)
            cursor.execute('DELETE FROM medications WHERE med_id = ?', (med_id,))
            # Also delete logs and patterns
            cursor.execute('DELETE FROM dose_logs WHERE med_id = ?', (med_id,))
            cursor.execute('DELETE FROM adherence_patterns WHERE med_id = ?', (med_id,))
            self.conn.commit()
            print(f"✅ Medication deleted: {med_id}")
            return True
        except Exception as e:
            print(f"❌ Error deleting medication: {e}")
            return False

    # ============ DOSE LOG METHODS ============

    def save_dose_log(self, user_name: str, dose_log: DoseLog, reason: str = ''):
        """Save dose log to database"""
        cursor = self.conn.cursor()

        actual_time_str = dose_log.actual_time.isoformat() if dose_log.actual_time else None

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO dose_logs
                (log_id, user_name, med_id, scheduled_time, actual_time, status, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (dose_log.log_id, user_name, dose_log.med_id,
                  dose_log.scheduled_time.isoformat(), actual_time_str, dose_log.status, reason))

            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error saving dose log: {e}")
            return False

    def load_dose_logs(self, user_name: str, days: int = 30) -> List[DoseLog]:
        """Load dose logs for the last N days"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM dose_logs 
            WHERE user_name = ? 
            AND scheduled_time >= datetime('now', '-' || ? || ' days')
            ORDER BY scheduled_time DESC
        ''', (user_name, days))

        logs = []
        for row in cursor.fetchall():
            actual_time = datetime.fromisoformat(row['actual_time']) if row['actual_time'] else None

            log = DoseLog(
                log_id=row['log_id'],
                med_id=row['med_id'],
                scheduled_time=datetime.fromisoformat(row['scheduled_time']),
                actual_time=actual_time,
                status=row['status']
            )
            logs.append(log)

        return logs

    def get_weekly_adherence(self, user_name: str) -> Dict:
        """Get weekly adherence summary"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'taken' THEN 1 ELSE 0 END) as taken,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                SUM(CASE WHEN status = 'missed' THEN 1 ELSE 0 END) as missed
            FROM dose_logs
            WHERE user_name = ?
            AND scheduled_time >= date('now', '-7 days')
        ''', (user_name,))

        row = cursor.fetchone()
        if row:
            total = row['total'] or 0
            taken = row['taken'] or 0
            skipped = row['skipped'] or 0
            missed = row['missed'] or 0

            adherence_percent = (taken / total * 100) if total > 0 else 0

            return {
                'total': total,
                'taken': taken,
                'skipped': skipped,
                'missed': missed,
                'adherence_percent': round(adherence_percent, 1)
            }

        return {
            'total': 0,
            'taken': 0,
            'skipped': 0,
            'missed': 0,
            'adherence_percent': 0
        }

    # ============ ADHERENCE PATTERN METHODS ============

    def get_adherence_pattern(self, user_name: str, med_id: str, scheduled_time: time) -> Optional[Dict]:
        """Get adherence pattern for a specific medication and time"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM adherence_patterns
            WHERE user_name = ? AND med_id = ? AND scheduled_time = ?
        ''', (user_name, med_id, scheduled_time.strftime('%H:%M:%S')))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def update_adherence_pattern(self, user_name: str, med_id: str, scheduled_time: time,
                                 miss_count: int, total_count: int, adjustment_minutes: int):
        """Update or create adherence pattern"""
        cursor = self.conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO adherence_patterns
                (user_name, med_id, scheduled_time, miss_count, total_count, 
                 last_analyzed, reminder_adjustment_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_name, med_id, scheduled_time.strftime('%H:%M:%S'),
                  miss_count, total_count, datetime.now().isoformat(), adjustment_minutes))

            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error updating pattern: {e}")
            return False

    def get_all_patterns(self, user_name: str) -> List[Dict]:
        """Get all adherence patterns for a user"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM adherence_patterns
            WHERE user_name = ?
        ''', (user_name,))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()