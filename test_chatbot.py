#!/usr/bin/env python3
"""
Automated Test Suite for Medication Reminder Chatbot
Tests intent classification, entity extraction, and conversation flows
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from main import MedicationChatbotApp
from chatbot_engine import ChatbotEngine
from datetime import datetime, time
import json


class ChatbotTester:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        
    def run_all_tests(self):
        """Run all test suites"""
        print("=" * 60)
        print("MEDICATION REMINDER CHATBOT - AUTOMATED TEST SUITE")
        print("=" * 60)
        print()
        
        # Run test suites
        self.test_intent_classification()
        self.test_entity_extraction()
        self.test_add_medication_flow()
        self.test_dose_confirmation()
        self.test_skip_dose()
        self.test_medication_queries()
        self.test_schedule_changes()
        self.test_edge_cases()
        
        # Print summary
        self.print_summary()
        
    def test_intent_classification(self):
        """Test ML intent classification accuracy"""
        print("\n📋 TEST SUITE: Intent Classification")
        print("-" * 60)
        
        # Create a minimal app to get the engine
        from context_manager import ContextManager
        context_mgr = ContextManager()
        engine = ChatbotEngine(context_mgr)
        
        test_cases = [
            # (input, expected_intent)
            ("add aspirin 500mg at 8am", "add_medication"),
            ("my doctor prescribed zoloft 50mg", "add_medication"),
            ("I'm supposed to take lisinopril 5mg", "add_medication"),
            ("starting wellbutrin 150mg", "add_medication"),
            
            ("I took my medication", "confirm_dose"),
            ("just finished my zoloft", "confirm_dose"),
            ("already swallowed the crestor", "confirm_dose"),
            ("nexium is done", "confirm_dose"),
            
            ("skip my next dose", "skip_dose"),
            ("I'm not taking aspirin today", "skip_dose"),
            ("won't take metformin", "skip_dose"),
            
            ("what medications do I have", "medication_info"),
            ("list my current prescriptions", "medication_info"),
            ("which pills am I on", "medication_info"),
            
            ("when is my next dose", "check_next_dose"),
            ("what's coming up next", "check_next_dose"),
            ("which drugs are coming up", "check_next_dose"),
            
            ("show my schedule for today", "check_schedule"),
            ("tell me my medication schedule", "check_schedule"),
            
            ("did I take my medication today", "query_history"),
            ("what have I already consumed", "query_history"),
            ("remind me what I took", "query_history"),
            
            ("how am I doing this week", "adherence_summary"),
            ("how's my pill compliance", "adherence_summary"),
            
            ("change aspirin time to 9am", "change_schedule"),
            ("move my lipitor to 11pm", "change_schedule"),
            ("shift prozac to morning", "change_schedule"),
            
            ("remove aspirin", "delete_medication"),
            ("I'm not on lipitor anymore", "delete_medication"),
            ("discontinue nexium", "delete_medication"),
            
            ("increase zoloft to 100mg", "update_medication"),
            ("decrease crestor dosage", "update_medication"),
        ]
        
        for input_text, expected_intent in test_cases:
            result = engine.process_message(input_text)
            actual_intent = result['intent']
            
            if actual_intent == expected_intent:
                self.test_pass(f"'{input_text}' → {expected_intent}")
            else:
                self.test_fail(f"'{input_text}' → Expected: {expected_intent}, Got: {actual_intent}")
    
    def test_entity_extraction(self):
        """Test entity extraction from messages"""
        print("\n🔍 TEST SUITE: Entity Extraction")
        print("-" * 60)
        
        from context_manager import ContextManager
        context_mgr = ContextManager()
        engine = ChatbotEngine(context_mgr)
        
        test_cases = [
            # (input, expected_entities)
            ("add aspirin 500mg at 8am", {
                'med_name': 'Aspirin',
                'dosage': '500 mg',
                'times': ['8am']
            }),
            
            ("I need to register crestor 10mg bedtime dose", {
                'med_name': 'Crestor',  # Should NOT be "Crestor 10mg"
                'dosage': '10 mg',
            }),
            
            ("please add nexium to my schedule", {
                'med_name': 'Nexium',  # Should NOT be "Nex"
            }),
            
            ("track lisinopril for me", {
                'med_name': 'Lisinopril',  # Should NOT be "Lisinopril Me"
            }),
            
            ("add vitamin d at 7pm", {
                'med_name': 'Vitamin D',  # Multi-word medication
                'times': ['7pm']
            }),
        ]
        
        for input_text, expected_entities in test_cases:
            result = engine.process_message(input_text)
            actual_entities = result['entities']
            
            # Check each expected entity
            all_match = True
            for key, expected_value in expected_entities.items():
                actual_value = actual_entities.get(key)
                if actual_value != expected_value:
                    all_match = False
                    self.test_fail(f"'{input_text}' → {key}: Expected '{expected_value}', Got '{actual_value}'")
                    break
            
            if all_match:
                self.test_pass(f"'{input_text}' → Entities extracted correctly")
    
    def test_add_medication_flow(self):
        """Test complete add medication conversation flow"""
        print("\n💊 TEST SUITE: Add Medication Flow")
        print("-" * 60)
        
        from context_manager import ContextManager
        context_mgr = ContextManager()
        engine = ChatbotEngine(context_mgr)
        
        # Test 1: One-line add with all info
        intent_data = engine.process_message("add aspirin 500mg at 8am")
        if (intent_data['intent'] == 'add_medication' and 
            intent_data['entities'].get('med_name') == 'Aspirin' and
            intent_data['entities'].get('dosage') == '500 mg'):
            self.test_pass("One-line add: Intent and entities correct")
        else:
            self.test_fail("One-line add: Failed")
        
        # Test 2: Multi-turn add (just medication name)
        intent_data2 = engine.process_message("add medication called zoloft")
        if intent_data2['intent'] == 'add_medication':
            self.test_pass("Multi-turn add: Intent detected correctly")
        else:
            self.test_fail("Multi-turn add: Wrong intent")
    
    def test_dose_confirmation(self):
        """Test recording doses correctly"""
        print("\n✅ TEST SUITE: Dose Confirmation")
        print("-" * 60)
        
        from context_manager import ContextManager
        context_mgr = ContextManager()
        engine = ChatbotEngine(context_mgr)
        
        # Test intent detection
        intent_data = engine.process_message("I took aspirin")
        if intent_data['intent'] == 'confirm_dose':
            self.test_pass("Dose confirmation: Intent detected correctly")
        else:
            self.test_fail("Dose confirmation: Wrong intent")
    
    def test_skip_dose(self):
        """Test skipping doses"""
        print("\n⏭️  TEST SUITE: Skip Dose")
        print("-" * 60)
        
        from context_manager import ContextManager
        context_mgr = ContextManager()
        engine = ChatbotEngine(context_mgr)
        
        # Test intent detection
        intent_data = engine.process_message("skip aspirin")
        if intent_data['intent'] == 'skip_dose':
            self.test_pass("Skip dose: Intent detected correctly")
        else:
            self.test_fail("Skip dose: Wrong intent")
    
    def test_medication_queries(self):
        """Test medication information queries"""
        print("\n❓ TEST SUITE: Medication Queries")
        print("-" * 60)
        
        from context_manager import ContextManager
        context_mgr = ContextManager()
        engine = ChatbotEngine(context_mgr)
        
        # Test various query phrasings
        queries = [
            "what medications do I have",
            "list my current prescriptions",
            "which pills am I on",
        ]
        
        for query in queries:
            intent_data = engine.process_message(query)
            if intent_data['intent'] == 'medication_info':
                self.test_pass(f"Query intent correct: '{query}'")
            else:
                self.test_fail(f"Query intent wrong: '{query}' → {intent_data['intent']}")
    
    def test_schedule_changes(self):
        """Test changing medication schedules"""
        print("\n🔄 TEST SUITE: Schedule Changes")
        print("-" * 60)
        
        from context_manager import ContextManager
        context_mgr = ContextManager()
        engine = ChatbotEngine(context_mgr)
        
        # Change time
        intent_data = engine.process_message("change aspirin to 9am")
        
        if intent_data['intent'] == 'change_schedule':
            entities = intent_data['entities']
            if entities.get('med_name') == 'Aspirin':
                self.test_pass("Schedule change: Intent and entities correct")
            else:
                self.test_fail("Schedule change: Entities missing")
        else:
            self.test_fail("Schedule change: Wrong intent")
    
    def test_edge_cases(self):
        """Test edge cases and potential bugs"""
        print("\n⚠️  TEST SUITE: Edge Cases")
        print("-" * 60)
        
        from context_manager import ContextManager
        context_mgr = ContextManager()
        engine = ChatbotEngine(context_mgr)
        
        # Edge case 1: Medication name with dosage should extract clean name
        result = engine.process_message("add crestor 10mg")
        entities = result['entities']
        
        if entities.get('med_name') == 'Crestor':  # NOT "Crestor 10mg"
            self.test_pass("Edge case: Dosage not included in medication name")
        else:
            self.test_fail(f"Edge case: Medication name includes dosage: {entities.get('med_name')}")
        
        # Edge case 2: "for me" should not be part of medication name
        result = engine.process_message("track lisinopril for me")
        entities = result['entities']
        
        if entities.get('med_name') == 'Lisinopril':  # NOT "Lisinopril Me"
            self.test_pass("Edge case: 'for me' not included in medication name")
        else:
            self.test_fail(f"Edge case: 'for me' included in name: {entities.get('med_name')}")
        
        # Edge case 3: "to my schedule" should not be part of medication name
        result = engine.process_message("add nexium to my schedule")
        entities = result['entities']
        
        if entities.get('med_name') == 'Nexium':  # NOT "Nex"
            self.test_pass("Edge case: 'to my' handled correctly")
        else:
            self.test_fail(f"Edge case: 'to my' caused truncation: {entities.get('med_name')}")
    
    def test_pass(self, description):
        """Record a passing test"""
        self.tests_passed += 1
        print(f"✅ PASS: {description}")
    
    def test_fail(self, description):
        """Record a failing test"""
        self.tests_failed += 1
        self.failures.append(description)
        print(f"❌ FAIL: {description}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_passed + self.tests_failed}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        
        if self.tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"\n⚠️  {self.tests_failed} TEST(S) FAILED:")
            for failure in self.failures:
                print(f"   - {failure}")
        
        pass_rate = (self.tests_passed / (self.tests_passed + self.tests_failed)) * 100
        print(f"\nPass Rate: {pass_rate:.1f}%")
        print("=" * 60)


if __name__ == "__main__":
    tester = ChatbotTester()
    tester.run_all_tests()
