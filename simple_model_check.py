import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print('=== Environment Variable Check ===')
openai_model_env = os.getenv('OPENAI_MODEL')
openai_api_key_env = os.getenv('OPENAI_API_KEY')

print(f'OPENAI_MODEL from .env: {repr(openai_model_env)}')
print(f'OPENAI_API_KEY set: {"Yes" if openai_api_key_env else "No"}')

# Check config.py
print('\n=== Config.py Loading ===')
try:
    from config import OPENAI_MODEL, OPENAI_API_KEY
    print(f'OPENAI_MODEL from config.py: {repr(OPENAI_MODEL)}')
    print(f'OPENAI_API_KEY loaded: {"Yes" if OPENAI_API_KEY else "No"}')
    print(f'Model match: {"✅ Yes" if OPENAI_MODEL == openai_model_env else "❌ No"}')
except Exception as e:
    print(f'Error loading config: {e}')

# Simulate the webhook service configuration
print('\n=== Webhook Service Configuration Logic ===')
OPENAI_MODEL_from_config = openai_model_env  # This is what config.py loads
fallback_model = "gpt-4o-mini"

final_model = OPENAI_MODEL_from_config or fallback_model
print(f'Environment OPENAI_MODEL: {repr(OPENAI_MODEL_from_config)}')
print(f'Fallback model: {repr(fallback_model)}')
print(f'Final model used: {repr(final_model)}')

# Check if the model is coming from .env
if OPENAI_MODEL_from_config:
    print('✅ Model is being used from .env file')
else:
    print('❌ Model is using fallback value, .env not set') 