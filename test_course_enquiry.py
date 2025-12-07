#!/usr/bin/env python3
"""
Test script for the course/class enquiry detection function.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_service_factory import AIServiceFactory
from config import OPENAI_API_KEY, OPENAI_MODEL

def test_course_enquiry_detection():
    """Test the course/class enquiry detection function."""
    
    # Create AI service instance
    service_config = {
        'service_name': 'openai',
        'api_key': OPENAI_API_KEY or "",
        'model': OPENAI_MODEL or "gpt-4o-mini",
        'brideside_user_id': 1,
        'business_name': "The Bride Side",
        'services': ['Makeup', 'Photography', 'Decor', 'Wedding Planner']
    }
    
    ai_service = AIServiceFactory.get_service_by_config(service_config)
    
    # Test messages
    test_messages = [
        # Course/Class enquiries (should return True)
        "Hi, I want to learn makeup. Do you offer makeup classes?",
        "What are the course fees for your beauty training program?",
        "I'm interested in your makeup course. Can you tell me more details?",
        "Do you have any online makeup classes available?",
        "What is the duration of your professional makeup course?",
        "I want to enroll in your beauty course. How can I register?",
        "Do you provide certification after completing the makeup course?",
        "What will I learn in your makeup training program?",
        "Are there any workshop sessions for learning makeup techniques?",
        "I'm looking for a diploma course in beauty and makeup.",
        
        # Event services (should return False)
        "Hello, I need makeup for my wedding on 15th November.",
        "What are your charges for bridal makeup?",
        "Are you available for a party makeup on 20th December?",
        "I need makeup services for my engagement ceremony.",
        "Can you do makeup for my sister's wedding?",
        "What is your availability for wedding makeup services?",
        "I want to book makeup for my reception party.",
        "Do you provide makeup services for events?",
        "I need makeup artist for my birthday party.",
        "What are your rates for event makeup services?"
    ]
    
    print("🧪 Testing Course/Class Enquiry Detection")
    print("=" * 60)
    
    for i, message in enumerate(test_messages, 1):
        try:
            result = ai_service.is_course_or_class_enquiry(message)
            status = "✅ COURSE/CLASS" if result else "❌ EVENT SERVICE"
            print(f"{i:2d}. {status} | {message[:50]}{'...' if len(message) > 50 else ''}")
        except Exception as e:
            print(f"{i:2d}. ❌ ERROR | {message[:50]}{'...' if len(message) > 50 else ''} | Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")

if __name__ == "__main__":
    test_course_enquiry_detection()
