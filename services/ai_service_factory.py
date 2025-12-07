from typing import Dict, List, Type, Optional
from .ai_service_interface import AIServiceInterface
from .groq_service import GroqService
from .openai_service import OpenAIService
from .deepseek_service import DeepSeekService


class AIServiceFactory:
    """Factory class for creating and managing AI service instances."""
    
    # Registry of available AI services
    _services: Dict[str, Type[AIServiceInterface]] = {
        'groq': GroqService,
        'openai': OpenAIService,
        'deepseek': DeepSeekService,
    }
    
    # Cache for service instances
    _instances: Dict[str, AIServiceInterface] = {}
    
    @classmethod
    def register_service(cls, name: str, service_class: Type[AIServiceInterface]):
        """Register a new AI service class."""
        cls._services[name] = service_class
        print(f"✅ Registered AI service: {name}")
    
    @classmethod
    def get_available_services(cls) -> list:
        """Get list of available AI service names."""
        return list(cls._services.keys())
    
    @classmethod
    def create_service(
        cls,
        service_name: str,
        api_key: str,
        model: str = "",
        brideside_user_id: int = 1,
        business_name: str = "",
        services: List[str] = [],
        force_new: bool = False
    ) -> AIServiceInterface:
        """
        Create or get an AI service instance.
        
        Args:
            service_name: Name of the AI service ('groq', 'openai', 'deepseek')
            api_key: API key for the service
            model: Model name (optional, uses service default if empty)
            brideside_user_id: Brideside user ID for configuration
            force_new: Force creation of new instance instead of using cached one
        
        Returns:
            AIServiceInterface instance
        
        Raises:
            ValueError: If service_name is not registered
        """
        service_name = service_name.lower()
        
        if service_name not in cls._services:
            raise ValueError(f"Unknown AI service: {service_name}. Available services: {list(cls._services.keys())}")
        
        # Create unique key for caching
        cache_key = f"{service_name}_{brideside_user_id}_{model}"
        
        # Return cached instance if available and not forcing new
        if not force_new and cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Create new instance
        service_class = cls._services[service_name]
        
        # Handle model parameter
        if model:
            instance = service_class(api_key=api_key, model=model, brideside_user_id=brideside_user_id, business_name=business_name, services=services)
        else:
            raise ValueError("Model is required")
        
        # Cache the instance
        cls._instances[cache_key] = instance
        
        print(f"✅ Created {service_name} service instance for brideside_user_{brideside_user_id}")
        return instance
    
    @classmethod
    def get_service_by_config(cls, config: Dict) -> AIServiceInterface:
        """
        Create service instance from configuration dictionary.
        
        Args:
            config: Configuration dictionary with keys:
                - service_name: Name of the AI service
                - api_key: API key
                - model: Model name (optional)
                - brideside_user_id: Brideside user ID (optional, defaults to 1)
        
        Returns:
            AIServiceInterface instance
        """
        service_name = config.get('service_name', '')
        api_key = config.get('api_key', '')
        model = config.get('model', '')
        brideside_user_id = config.get('brideside_user_id', 1)
        business_name = config.get('business_name', '')
        services = config.get('services', [])
        
        if not service_name:
            raise ValueError("service_name is required in config")
        if not api_key:
            raise ValueError("api_key is required in config")
        
        return cls.create_service(
            service_name=service_name,
            api_key=api_key,
            model=model,
            brideside_user_id=brideside_user_id,
            business_name=business_name,
            services=services
        )
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached service instances."""
        cls._instances.clear()
        print("✅ Cleared AI service cache")
    
    @classmethod
    def get_default_models(cls) -> Dict[str, str]:
        """Get default models for each service."""
        return {
            'groq': 'meta-llama/llama-4-scout-17b-16e-instruct',
            'openai': 'gpt-4.1-mini-2025-04-14',  # Updated to use the new GPT-4.1 Mini model
            'deepseek': 'deepseek-chat'
        }


class AIServiceManager:
    """High-level manager for AI services with easy switching."""
    
    def __init__(self, default_service: str = 'groq', brideside_user_id: int = 1):
        """
        Initialize the AI service manager.
        
        Args:
            default_service: Default AI service to use
            brideside_user_id: Brideside user ID for configuration
        """
        self.default_service = default_service
        self.brideside_user_id = brideside_user_id
        self.current_service: Optional[AIServiceInterface] = None
        self.api_keys: Dict[str, str] = {}
    
    def set_api_key(self, service_name: str, api_key: str):
        """Set API key for a specific service."""
        self.api_keys[service_name.lower()] = api_key
    
    def set_api_keys(self, api_keys: Dict[str, str]):
        """Set multiple API keys at once."""
        for service_name, api_key in api_keys.items():
            self.api_keys[service_name.lower()] = api_key
    
    def switch_service(self, service_name: str, model: str = "") -> AIServiceInterface:
        """
        Switch to a different AI service.
        
        Args:
            service_name: Name of the AI service to switch to
            model: Model name (optional)
        
        Returns:
            AIServiceInterface instance
        """
        service_name = service_name.lower()
        
        if service_name not in self.api_keys:
            raise ValueError(f"API key not set for service: {service_name}. Call set_api_key() first.")
        
        self.current_service = AIServiceFactory.create_service(
            service_name=service_name,
            api_key=self.api_keys[service_name],
            model=model,
            brideside_user_id=self.brideside_user_id
        )
        
        self.default_service = service_name
        return self.current_service
    
    def get_current_service(self) -> AIServiceInterface:
        """Get current AI service instance."""
        if self.current_service is None:
            if self.default_service not in self.api_keys:
                raise ValueError(f"API key not set for default service: {self.default_service}. Call set_api_key() first.")
            
            self.current_service = AIServiceFactory.create_service(
                service_name=self.default_service,
                api_key=self.api_keys[self.default_service],
                brideside_user_id=self.brideside_user_id
            )
        
        return self.current_service
    
    def get_response_with_json(self, *args, **kwargs):
        """Proxy method to current service."""
        return self.get_current_service().get_response_with_json(*args, **kwargs)
    
    def is_emoji_or_appreciation(self, message: str) -> bool:
        """Proxy method to current service."""
        return self.get_current_service().is_emoji_or_appreciation(message)
    
    def is_collab_or_advertisement(self, message: str) -> bool:
        """Proxy method to current service."""
        return self.get_current_service().is_collab_or_advertisement(message)
    
    def get_service_info(self) -> Dict:
        """Get information about current service."""
        if self.current_service is None:
            return {
                'service_name': self.default_service,
                'status': 'not_initialized',
                'brideside_user_id': self.brideside_user_id
            }
        
        return {
            'service_name': self.default_service,
            'model': self.current_service.model,
            'brideside_user_id': self.current_service.brideside_user_id,
            'status': 'active'
        }


# Global service manager instance
ai_service_manager = AIServiceManager()

# Convenience functions for backward compatibility
def get_ai_service(service_name: str = 'groq', **kwargs) -> AIServiceInterface:
    """Get AI service instance."""
    return ai_service_manager.switch_service(service_name, **kwargs)

def set_ai_service_api_keys(api_keys: Dict[str, str]):
    """Set API keys for AI services."""
    ai_service_manager.set_api_keys(api_keys) 