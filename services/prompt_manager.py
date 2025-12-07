import json
import os
from typing import Dict, Optional, List
from utils.logger import get_logger

logger = get_logger(__name__)

class PromptManager:
    """Manages AI prompts from JSON configuration files."""
    
    def __init__(self, config_dir: str = "config/prompts"):
        """
        Initialize the prompt manager.
        
        Args:
            config_dir: Directory containing prompt configuration files
        """
        self.config_dir = config_dir
        self._service_prompt_cache: Dict[int, str] = {}
        self._collection_prompt_cache: Dict[int, str] = {}
        
        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)
    
    def get_service_prompts(self, brideside_user_id: int) -> str:
        """
        Get prompts for a specific brideside user.
        
        Args:
            brideside_user_id: The brideside user ID
            
        Returns:
            Dict containing prompts configuration
        """
        if brideside_user_id not in self._service_prompt_cache:
            self._load_service_prompts(brideside_user_id)
        
        return self._service_prompt_cache.get(brideside_user_id, '')
    
    def get_collection_prompts(self, brideside_user_id: int) -> str:
        """
        Get collection prompts for a specific brideside user.
        
        Args:
            brideside_user_id: The brideside user ID
            
        Returns:
            Dict containing collection prompts configuration
        """
        if brideside_user_id not in self._collection_prompt_cache:
            self._load_collection_prompts(brideside_user_id)
        
        return self._collection_prompt_cache.get(brideside_user_id, '')
    
    def _load_service_prompts(self, brideside_user_id: int):
        """Load service prompts from JSON file for a specific user."""
        filename = f"brideside_user_{brideside_user_id}_prompts.txt"
        filepath = os.path.join(self.config_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._service_prompt_cache[brideside_user_id] = f.read()
                logger.info(f"Loaded service prompts for brideside_user_{brideside_user_id}")
        except Exception as e:
            logger.error(f"Error loading service prompts for brideside_user_{brideside_user_id}: {e}")
            
    
    def _load_collection_prompts(self, brideside_user_id: int):
        """Load collection prompts from JSON file for a specific user."""
        filename = f"brideside_user_{brideside_user_id}_collection_prompts.txt"
        filepath = os.path.join(self.config_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._collection_prompt_cache[brideside_user_id] = f.read()
                logger.info(f"Loaded collection prompts for brideside_user_{brideside_user_id}")
        except Exception as e:
            logger.error(f"Error loading collection prompts for brideside_user_{brideside_user_id}: {e}")
            self._collection_prompt_cache[brideside_user_id] = ''
    
    def generate_service_prompt(self, brideside_user_id: int, previous_summary: str, message: str = "", business_name: str = "", services: List[str] = [], response: str = "NO_MESSAGE") -> str:
        """Generate service prompt for when all user details are collected."""
        service_prompts = self.get_service_prompts(brideside_user_id)
        service_prompts = service_prompts.format(
            business_name=business_name,
            services=services,
            previous_summary=previous_summary,
            message=message,
            response=response
        )
        return service_prompts
    
    def clear_cache(self, brideside_user_id: int = None):
        """Clear prompt cache for a specific user or all users."""
        if brideside_user_id is None:
            # Clear all caches
            self._service_prompt_cache.clear()
            self._collection_prompt_cache.clear()
            logger.info("Cleared all prompt caches")
        else:
            # Clear cache for specific user
            if brideside_user_id in self._service_prompt_cache:
                del self._service_prompt_cache[brideside_user_id]
            if brideside_user_id in self._collection_prompt_cache:
                del self._collection_prompt_cache[brideside_user_id]
            logger.info(f"Cleared prompt cache for brideside_user_{brideside_user_id}")
    
    def force_reload_prompts(self, brideside_user_id: int):
        """Force reload prompts for a specific user, bypassing cache."""
        if brideside_user_id in self._collection_prompt_cache:
            del self._collection_prompt_cache[brideside_user_id]
        if brideside_user_id in self._service_prompt_cache:
            del self._service_prompt_cache[brideside_user_id]
        # Force reload
        self._load_collection_prompts(brideside_user_id)
        self._load_service_prompts(brideside_user_id)
        logger.info(f"Force reloaded prompts for brideside_user_{brideside_user_id}")

    def generate_collection_prompt(self, brideside_user_id: int, missing_fields: List[str], 
                                   previous_summary: str, current_deal_data: Optional[Dict[str, str]] = None, business_name: str = "", services: List[str] = []) -> str:
        """Generate collection prompt for collecting missing user information."""
        collection_prompts = self.get_collection_prompts(brideside_user_id)
        try:
            # Provide all possible fields for formatting, with safe defaults
            def safe_get(key):
                return (current_deal_data.get(key, '') if current_deal_data else '')
            format_args = {
                'services': services,
                'business_name': business_name,
                'missing_fields': missing_fields,
                'previous_summary': previous_summary,
                'current_details_section': current_deal_data,
                'missing_fields_text': missing_fields if missing_fields else 'NONE - All details collected!',
                'full_name': safe_get('full_name'),
                'event_type': safe_get('event_type'),
                'event_date': safe_get('event_date'),
                'venue': safe_get('venue'),
                'phone_number': safe_get('phone_number'),
                'partial_event_date': safe_get('partial_event_date'),
            }
            collection_prompts = collection_prompts.format(**format_args)
        except KeyError as e:
            logger.error(f"Missing key {e} when generating collection prompt for brideside_user_{brideside_user_id}. Using empty string as fallback.")
            # Try again with the missing key set to empty string
            format_args[e.args[0]] = ''
            try:
                collection_prompts = collection_prompts.format(**format_args)
            except Exception as e2:
                logger.error(f"Failed again generating collection prompt: {e2}")
        except Exception as e:
            logger.error(f"Error generating collection prompt for brideside_user_{brideside_user_id}: {e}")
        return collection_prompts
    
   
# Global instance for easy access
prompt_manager = PromptManager() 