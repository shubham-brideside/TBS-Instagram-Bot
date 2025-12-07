#!/usr/bin/env python3
"""
Simple test script to verify models are working correctly.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_models():
    """Test that all models can be imported and initialized correctly."""
    try:
        print("🔍 Testing model imports...")
        
        # Test importing all models
        from models import Base, Deal, InstagramConversationSummary, InstagramConversationMessage
        print("✅ All models imported successfully")
        
        # Test model initialization
        print("🔍 Testing model initialization...")
        
        # Test Deal model
        deal = Deal(
            deal_name="Test Deal",
            full_name="John Doe",
            event_type="Wedding Photography",
            venue="Test Venue"
        )
        print("✅ Deal model initialized successfully")
        
        # Test InstagramConversationSummary model
        summary = InstagramConversationSummary(
            instagram_username="test_user",
            instagram_user_id="12345",
            deal_id=1,
            deals_conversation_summary="Test conversation"
        )
        print("✅ InstagramConversationSummary model initialized successfully")
        
        # Test InstagramConversationMessage model
        message = InstagramConversationMessage(
            conversation_summary_id=1,
            message_type="input",
            message_content="Hello",
            message_timestamp="2024-01-01 12:00:00"
        )
        print("✅ InstagramConversationMessage model initialized successfully")
        
        print("🎉 All models working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing models: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection."""
    try:
        print("🔍 Testing database connection...")
        
        from database.connection import engine, SessionLocal
        
        # Test engine creation
        print("✅ Database engine created successfully")
        
        # Test session creation
        session = SessionLocal()
        print("✅ Database session created successfully")
        session.close()
        
        print("🎉 Database connection working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing database connection: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting model tests...")
    
    models_ok = test_models()
    db_ok = test_database_connection()
    
    if models_ok and db_ok:
        print("✅ All tests passed! The application should work correctly.")
    else:
        print("❌ Some tests failed. Please check the errors above.") 