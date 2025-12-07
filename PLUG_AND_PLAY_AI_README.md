# Plug-and-Play AI Service Architecture

A flexible, modular AI service architecture that allows easy switching between different AI providers (Groq, OpenAI, DeepSeek, etc.) with configurable prompts for different brideside users.

## 🚀 Features

- **Plug-and-Play Architecture**: Easy switching between AI services
- **Configurable Prompts**: JSON-based prompt configuration per brideside user
- **Multiple AI Providers**: Support for Groq, OpenAI, DeepSeek, and extensible to others
- **Factory Pattern**: Clean service creation and management
- **Caching**: Efficient service instance caching
- **Fallback Handling**: Graceful degradation when services fail

## 📁 Project Structure

```
services/
├── ai_service_interface.py      # Abstract base class for all AI services
├── ai_service_factory.py        # Factory pattern for service creation
├── prompt_manager.py            # JSON-based prompt configuration manager
├── groq_service.py              # Groq implementation
├── openai_service.py            # OpenAI implementation
├── deepseek_service.py          # DeepSeek implementation
└── ...

config/
└── prompts/
    ├── brideside_user_1_prompts.json
    ├── brideside_user_2_prompts.json
    └── ...
```

## 🔧 Installation

1. Install required dependencies:
```bash
pip install groq openai requests
```

2. Set up your API keys:
```bash
export GROQ_API_KEY="your-groq-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

## 🚀 Quick Start

### Basic Usage

```python
from services.ai_service_factory import ai_service_manager

# Set API keys
ai_service_manager.set_api_keys({
    'groq': 'your-groq-api-key',
    'openai': 'your-openai-api-key',
    'deepseek': 'your-deepseek-api-key'
})

# Use the service (defaults to Groq)
response = ai_service_manager.get_response_with_json(
    user_id=123,
    instagram_user_id=456,
    deal_id=789,
    instagram_username='user123',
    user_message='Hi, I need wedding photography',
    missing_fields=['full_name', 'event_date', 'venue', 'phone_number']
)

# Switch to OpenAI
ai_service_manager.switch_service('openai', model='gpt-4o-mini')
response = ai_service_manager.get_response_with_json(...)

# Switch to DeepSeek
ai_service_manager.switch_service('deepseek')
response = ai_service_manager.get_response_with_json(...)
```

### Factory Pattern Usage

```python
from services.ai_service_factory import AIServiceFactory

# Create specific service instances
groq_service = AIServiceFactory.create_service(
    service_name='groq',
    api_key='your-groq-api-key',
    model='meta-llama/llama-4-scout-17b-16e-instruct',
    brideside_user_id=1
)

openai_service = AIServiceFactory.create_service(
    service_name='openai',
    api_key='your-openai-api-key',
    model='gpt-4o-mini',
    brideside_user_id=1
)

# Use the services
response = groq_service.get_response_with_json(...)
response = openai_service.get_response_with_json(...)
```

### Configuration-based Creation

```python
from services.ai_service_factory import AIServiceFactory

config = {
    'service_name': 'groq',
    'api_key': 'your-groq-api-key',
    'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
    'brideside_user_id': 1
}

service = AIServiceFactory.get_service_by_config(config)
```

## 📝 Prompt Configuration

### JSON Structure

Each brideside user has their own prompt configuration file:

```json
{
  "business_config": {
    "business_name": "The Bride Side",
    "services": [
      "Wedding Photography",
      "Bridal Makeup",
      "Party Makeup",
      "Event Photography"
    ],
    "required_fields": [
      "full_name",
      "event_type", 
      "event_date",
      "venue",
      "phone_number"
    ],
    "ad_keywords": [
      "promotion",
      "collab",
      "advertising"
    ]
  },
  "service_responses": {
    "wedding_photography": "Let's start with a few details...",
    "bridal_makeup": "Let's begin with a few details...",
    "party_makeup": "Please share the following details..."
  },
  "service_prompt": "You are a professional assistant for {business_name}...",
  "collection_prompt": "You are a conversational assistant for {business_name}...",
  "classification_prompts": {
    "emoji_appreciation": "You are a smart assistant. Classify the following message...",
    "advertisement": "You are an assistant helping classify Instagram DMs..."
  }
}
```

### Managing Prompts

```python
from services.prompt_manager import prompt_manager

# Get prompts for a specific user
prompts = prompt_manager.get_prompts(brideside_user_id=1)

# Get business configuration
business_config = prompt_manager.get_business_config(brideside_user_id=1)

# Get a specific prompt with variables
prompt = prompt_manager.get_system_prompt(
    brideside_user_id=1,
    prompt_type='collection_prompt',
    business_name='The Bride Side',
    missing_fields=['full_name', 'phone_number']
)

# Validate prompt structure
errors = prompt_manager.validate_prompt_structure(brideside_user_id=1)
if errors:
    print("Validation errors:", errors)
```

## 🔌 Adding New AI Services

### Step 1: Create Service Class

```python
from services.ai_service_interface import AIServiceInterface

class YourAIService(AIServiceInterface):
    def __init__(self, api_key: str, model: str = "default-model", brideside_user_id: int = 1):
        super().__init__(api_key, model, brideside_user_id)
        # Initialize your AI client here
        self.client = YourAIClient(api_key=api_key)
        self._load_business_config()
    
    def get_response_with_json(self, *args, **kwargs):
        # Implement your AI service logic
        pass
    
    def is_emoji_or_appreciation(self, message: str) -> bool:
        # Implement classification logic
        pass
    
    def is_collab_or_advertisement(self, message: str) -> bool:
        # Implement classification logic
        pass
```

### Step 2: Register Service

```python
from services.ai_service_factory import AIServiceFactory

AIServiceFactory.register_service('your_service', YourAIService)
```

### Step 3: Use Your Service

```python
service = AIServiceFactory.create_service(
    service_name='your_service',
    api_key='your-api-key',
    brideside_user_id=1
)
```

## 🛠️ Available Services

### Groq Service
- **Models**: `meta-llama/llama-4-scout-17b-16e-instruct`, etc.
- **Features**: Fast inference, good for production
- **API**: Uses Groq SDK

### OpenAI Service
- **Models**: `gpt-4o-mini`, `gpt-4`, `gpt-3.5-turbo`
- **Features**: High quality responses, structured output
- **API**: Uses OpenAI SDK

### DeepSeek Service
- **Models**: `deepseek-chat`, `deepseek-coder`
- **Features**: Cost-effective, good performance
- **API**: Uses HTTP requests

## 🎯 Use Cases

### Different Services for Different Scenarios

```python
# Use Groq for fast responses
ai_service_manager.switch_service('groq')
response = ai_service_manager.get_response_with_json(...)

# Use OpenAI for complex reasoning
ai_service_manager.switch_service('openai', model='gpt-4')
response = ai_service_manager.get_response_with_json(...)

# Use DeepSeek for cost optimization
ai_service_manager.switch_service('deepseek')
response = ai_service_manager.get_response_with_json(...)
```

### Different Configurations per User

```python
# Different business configurations
user1_service = AIServiceFactory.create_service(
    service_name='groq',
    api_key='your-key',
    brideside_user_id=1  # Uses brideside_user_1_prompts.json
)

user2_service = AIServiceFactory.create_service(
    service_name='groq',
    api_key='your-key',
    brideside_user_id=2  # Uses brideside_user_2_prompts.json
)
```

## 📊 Monitoring and Debugging

### Service Information

```python
# Get current service info
info = ai_service_manager.get_service_info()
print(f"Current service: {info['service_name']}")
print(f"Model: {info['model']}")
print(f"Status: {info['status']}")
```

### Available Services

```python
# List available services
services = AIServiceFactory.get_available_services()
print(f"Available services: {services}")

# Get default models
models = AIServiceFactory.get_default_models()
print(f"Default models: {models}")
```

### Cache Management

```python
# Clear service cache
AIServiceFactory.clear_cache()
```

## 🔄 Migration from Old System

### Before (Old System)
```python
from services.groq_service import get_groq_response_with_json

response = get_groq_response_with_json(
    user_message="Hi",
    user_id=123,
    # ... other parameters
)
```

### After (New System)
```python
from services.ai_service_factory import ai_service_manager

# Set API keys once
ai_service_manager.set_api_key('groq', 'your-groq-api-key')

# Use the service
response = ai_service_manager.get_response_with_json(
    user_message="Hi",
    user_id=123,
    # ... same parameters
)

# Switch services easily
ai_service_manager.switch_service('openai')
response = ai_service_manager.get_response_with_json(...)
```

## 🛡️ Error Handling

The system includes comprehensive error handling:

- **Service Creation Errors**: Invalid service names, missing API keys
- **API Errors**: Network issues, authentication failures
- **Prompt Errors**: Missing or invalid prompt configurations
- **Fallback Responses**: Graceful degradation when AI services fail

## 🔧 Configuration Files

### Environment Variables
```bash
# API Keys
GROQ_API_KEY=your-groq-api-key
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# Default service (optional)
DEFAULT_AI_SERVICE=groq
```

### Prompt Configuration
- Location: `config/prompts/`
- Format: JSON
- Naming: `brideside_user_{id}_prompts.json`

## 📈 Performance Considerations

- **Caching**: Service instances are cached for efficiency
- **Lazy Loading**: Prompts are loaded on-demand
- **Connection Pooling**: HTTP clients reuse connections
- **Fallback Logic**: Quick fallback when services fail

## 🤝 Contributing

To add support for a new AI service:

1. Create a new service class inheriting from `AIServiceInterface`
2. Implement all required methods
3. Add tests for the new service
4. Register the service in the factory
5. Update documentation

## 🔍 Troubleshooting

### Common Issues

1. **Service Not Found**: Check if service is registered
2. **API Key Missing**: Ensure API keys are set
3. **Prompt Not Found**: Check if prompt configuration exists
4. **Model Not Supported**: Verify model name with service provider

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Validate configuration
errors = prompt_manager.validate_prompt_structure(brideside_user_id=1)
if errors:
    print("Configuration errors:", errors)
```

## 📄 License

This project is part of the Formated Lead Automation system.

---

## 🎉 Getting Started

1. Run the example script:
```bash
python example_usage.py
```

2. Check the prompt configuration:
```bash
python -c "from services.prompt_manager import prompt_manager; print(prompt_manager.get_business_config(1))"
```

3. Start using the new architecture in your application!

The system is now fully plug-and-play ready! 🚀 