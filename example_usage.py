#!/usr/bin/env python3
"""
Example script demonstrating the plug-and-play AI service architecture.

This script shows how to:
1. Switch between different AI services (Groq, OpenAI, DeepSeek)
2. Use different brideside user configurations
3. Use the AI service factory and manager
"""

import os
from services.ai_service_factory import AIServiceFactory, AIServiceManager, ai_service_manager
from services.prompt_manager import prompt_manager


def main():
    """Main demonstration function."""
    
    print("🚀 Plug-and-Play AI Service Architecture Demo")
    print("=" * 50)
    
    # Example 1: Using the Factory Pattern
    print("\n📦 Example 1: Using AI Service Factory")
    print("-" * 30)
    
    # Create different AI services
    try:
        # You would need to set actual API keys
        groq_service = AIServiceFactory.create_service(
            service_name='groq',
            api_key='your-groq-api-key',  # Replace with actual key
            model='meta-llama/llama-4-scout-17b-16e-instruct',
            brideside_user_id=1
        )
        print(f"✅ Created Groq service: {groq_service.__class__.__name__}")
        
        openai_service = AIServiceFactory.create_service(
            service_name='openai',
            api_key='your-openai-api-key',  # Replace with actual key
            model='gpt-4o-mini',
            brideside_user_id=1
        )
        print(f"✅ Created OpenAI service: {openai_service.__class__.__name__}")
        
        deepseek_service = AIServiceFactory.create_service(
            service_name='deepseek',
            api_key='your-deepseek-api-key',  # Replace with actual key
            model='deepseek-chat',
            brideside_user_id=1
        )
        print(f"✅ Created DeepSeek service: {deepseek_service.__class__.__name__}")
        
    except Exception as e:
        print(f"❌ Error creating services: {e}")
        print("💡 This is expected without real API keys")
    
    # Example 2: Using the Service Manager
    print("\n🎛️ Example 2: Using AI Service Manager")
    print("-" * 30)
    
    # Set up API keys (you would use real keys)
    api_keys = {
        'groq': 'your-groq-api-key',
        'openai': 'your-openai-api-key',
        'deepseek': 'your-deepseek-api-key'
    }
    
    # Create service manager for brideside_user_1
    manager = AIServiceManager(default_service='groq', brideside_user_id=1)
    manager.set_api_keys(api_keys)
    
    try:
        # Switch between services
        print("🔄 Switching to Groq service...")
        groq_service = manager.switch_service('groq')
        print(f"✅ Current service: {manager.get_service_info()}")
        
        print("\n🔄 Switching to OpenAI service...")
        openai_service = manager.switch_service('openai', model='gpt-4o-mini')
        print(f"✅ Current service: {manager.get_service_info()}")
        
        print("\n🔄 Switching to DeepSeek service...")
        deepseek_service = manager.switch_service('deepseek')
        print(f"✅ Current service: {manager.get_service_info()}")
        
    except Exception as e:
        print(f"❌ Error switching services: {e}")
        print("💡 This is expected without real API keys")
    
    # Example 3: Different Brideside User Configurations
    print("\n👥 Example 3: Different User Configurations")
    print("-" * 30)
    
    # Show available services
    print(f"📋 Available AI services: {AIServiceFactory.get_available_services()}")
    print(f"📋 Default models: {AIServiceFactory.get_default_models()}")
    
    # Show prompt validation for different users
    print("\n📝 Prompt Configuration Validation:")
    for user_id in [1, 2]:
        print(f"\n👤 Brideside User {user_id}:")
        errors = prompt_manager.validate_prompt_structure(user_id)
        if errors:
            print(f"❌ Validation errors:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("✅ Prompt structure is valid")
        
        # Show business config
        business_config = prompt_manager.get_business_config(user_id)
        if business_config:
            print(f"🏢 Business name: {business_config.get('business_name', 'N/A')}")
            print(f"🛍️ Services: {len(business_config.get('services', []))} services")
        else:
            print("⚠️ No business configuration found")
    
    # Example 4: Using Configuration Dictionary
    print("\n📄 Example 4: Configuration-based Service Creation")
    print("-" * 30)
    
    config = {
        'service_name': 'groq',
        'api_key': 'your-groq-api-key',
        'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
        'brideside_user_id': 1
    }
    
    try:
        service = AIServiceFactory.get_service_by_config(config)
        print(f"✅ Created service from config: {service.__class__.__name__}")
        print(f"📊 Service details: {service.model}, User: {service.brideside_user_id}")
    except Exception as e:
        print(f"❌ Error creating service from config: {e}")
        print("💡 This is expected without real API keys")
    
    # Example 5: Adding a New AI Service
    print("\n🔧 Example 5: Adding a New AI Service")
    print("-" * 30)
    
    # This shows how you could add a new AI service
    class CustomAIService:
        """Example of how to add a new AI service."""
        pass
    
    # Register a new service (this would be a real implementation)
    # AIServiceFactory.register_service('custom', CustomAIService)
    
    print("💡 To add a new AI service:")
    print("1. Create a class that inherits from AIServiceInterface")
    print("2. Implement all required methods")
    print("3. Register it with AIServiceFactory.register_service('name', YourClass)")
    print("4. Use it like any other service!")
    
    print("\n🎯 Example Usage in Production:")
    print("-" * 30)
    print("""
# In your main application:
from services.ai_service_factory import ai_service_manager

# Set API keys
ai_service_manager.set_api_keys({
    'groq': os.getenv('GROQ_API_KEY'),
    'openai': os.getenv('OPENAI_API_KEY'),
    'deepseek': os.getenv('DEEPSEEK_API_KEY')
})

# Use the service (will use default 'groq')
response = ai_service_manager.get_response_with_json(
    user_id=123,
    instagram_user_id=456,
    deal_id=789,
    instagram_username='user123',
    user_message='Hi, I need wedding photography',
    missing_fields=['full_name', 'event_date', 'venue', 'phone_number']
)

# Switch to OpenAI for better performance
ai_service_manager.switch_service('openai', model='gpt-4o-mini')
response = ai_service_manager.get_response_with_json(...)

# Switch to DeepSeek for cost savings
ai_service_manager.switch_service('deepseek')
response = ai_service_manager.get_response_with_json(...)
""")
    
    print("\n✅ Demo completed!")
    print("🔗 The system is now plug-and-play ready!")


if __name__ == "__main__":
    main() 