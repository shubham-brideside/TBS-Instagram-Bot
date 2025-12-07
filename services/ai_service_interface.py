from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import json
import re
from .prompt_manager import prompt_manager

class AIServiceInterface(ABC):
    """Abstract base class for AI services with common utility methods."""
    
    def __init__(self, api_key: str, model: str, brideside_user_id: int = 1, business_name: str = "", services: List[str] = []):
        """
        Initialize the AI service.
        
        Args:
            api_key: API key for the AI service
            model: Model name to use
            brideside_user_id: Brideside user ID for configuration
        """
        self.api_key = api_key
        self.model = model
        self.brideside_user_id = brideside_user_id
        self.current_message = ""  # Store current message for prompt generation
        self.previous_summary = ""  # Store previous conversation summary
        
        # Load business configuration
        self.required_fields = [
            "full_name",
            "event_type",
            "event_date",
            "venue",
            "phone_number"
        ]
        self.ad_keywords = [
            "promotion",
            "promote",
            "collab",
            "collaboration",
            "ad",
            "sponsor",
            "advertising",
            "influencer"
        ]
        # Common configurable settings
        self.temperature = 0.7
        self.max_tokens = 1024
        self.top_p = 1.0
        self.business_name = business_name
        self.services = services
    
    @abstractmethod
    def get_response_with_json(self, user_message: str, user_id: int, instagram_user_id: int,
                             instagram_username: str, deal_id: int, missing_fields: List[str],
                             previous_conversation_summary: str = "", current_deal_data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        # Store current message and previous summary for prompt generation and fallback handling
        self.current_message = user_message
        self.previous_summary = previous_conversation_summary
        """
        Get AI response with structured JSON output.
        
        Args:
            user_message: User's message
            user_id: Brideside user ID
            instagram_user_id: Instagram user ID
            instagram_username: Instagram username
            deal_id: Deal ID
            missing_fields: List of missing fields
            previous_conversation_summary: Previous conversation summary
            current_deal_data: Current deal data
            
        Returns:
            Dict containing AI response and extracted data
        """
        pass
    
    @abstractmethod
    def is_emoji_or_appreciation(self, message: str) -> bool:
        """
        Check if message is just emojis or simple appreciation.
        
        Args:
            message: Message to check
        
        Returns:
            True if message is emoji/appreciation, False otherwise
        """
        pass
    
    @abstractmethod
    def is_collab_or_advertisement(self, message: str) -> bool:
        """
        Check if message is promotional or collaboration/advertisement related.
        
        Args:
            message: Message to check
            
        Returns:
            True if message is advertisement/collaboration, False otherwise
        """
        pass
    
    @abstractmethod
    def is_message_not_related_to_provided_service(self, message: str, services: List[str]) -> bool:
        """
        Check if message is related to the provided service.
        
        Args:
            message: Message to check
            
        Returns:
            True if message is not related to the provided service, False otherwise
        """
        pass
    
    @abstractmethod
    def is_course_or_class_enquiry(self, message: str) -> bool:
        """
        Check if message is related to course or class enquiries.
        
        Args:
            message: Message to check
            
        Returns:
            True if message is about courses/classes, False otherwise
        """
        pass
    
    def test_connection(self) -> bool:
        """
        Test connection to the AI service.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try a simple test request
            test_response = self.get_response_with_json(
                user_message="test",
                user_id=1,
                instagram_user_id=1,
                instagram_username="test_user",
                deal_id=1,
                missing_fields=["full_name"],
                previous_conversation_summary=""
            )
            return test_response is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def _generate_system_prompt(self, missing_fields: List[str], previous_summary: str, current_deal_data: Optional[Dict[str, str]] = None) -> str:
        """Generate system prompt based on missing fields."""
        if not missing_fields:
            # For service prompt, we know the response will be "NO_MESSAGE" for greetings
            return prompt_manager.generate_service_prompt(
                brideside_user_id=self.brideside_user_id,
                previous_summary=previous_summary,
                message=self.current_message,  # Add current message to prompt
                business_name=self.business_name,
                services=self.services,
                response="NO_MESSAGE"  # Add expected response for conversation summary
            )
        else:
            return prompt_manager.generate_collection_prompt(
                brideside_user_id=self.brideside_user_id,
                missing_fields=missing_fields,
                previous_summary=previous_summary,
                current_deal_data=current_deal_data,
                business_name=self.business_name,
                services=self.services
            )
    
    
    def _is_ad_spam(self, message: str) -> bool:
        """Check if message is likely advertisement/spam."""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.ad_keywords)
    
    def _is_advertisement_message(self, message: str) -> bool:
        """Check if message contains advertisement keywords."""
        return any(kw in message.lower() for kw in self.ad_keywords)
    
    def _create_ad_decline_response(self, user_message: str, previous_summary: str) -> Dict[str, Any]:
        """Create polite decline response for advertisement messages."""
        decline_message = (
            "Thank you for reaching out. We truly appreciate your interest, "
            "but we're not exploring promotional opportunities at the moment. 🌸"
        )
        
        return {
            "message_to_be_sent": decline_message,
            "contains_structured_data": False,
            "full_name": "",
            "event_type": "",
            "event_date": "",
            "venue": "",
            "phone_number": "",
            "conversation_summary": f"{previous_summary}\nUser: {user_message}\nBot: {decline_message}"
        }
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from AI service."""
        try:
            # Remove leading/trailing whitespace and newlines
            response_text = response_text.strip()
            # Remove markdown code block markers if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # If no JSON found, create a basic response
                return {
                    "message_to_be_sent": response_text,
                    "contains_structured_data": False,
                    "full_name": "",
                    "event_type": "",
                    "event_date": "",
                    "venue": "",
                    "phone_number": "",
                    "conversation_summary": f"AI Response: {response_text}"
                }
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}. Raw response: {response_text}")
            return self._get_fallback_response()
        except Exception as e:
            print(f"❌ Error parsing response: {e}. Raw response: {response_text}")
            return self._get_fallback_response()
    
    def _save_conversation_to_db(self, instagram_user_id: int, deal_id: int, 
                               user_message: str, bot_response: str, 
                               extracted_data: Dict[str, Any]) -> bool:
        """Save conversation to database."""
        try:
            from repository.conversation_repository import ConversationRepository
            
            # Get or create conversation summary
            summary = ConversationRepository.get_or_create_conversation_summary(
                instagram_username=extracted_data.get('instagram_username', f"user_{instagram_user_id}"),
                instagram_user_id=str(instagram_user_id),
                deal_id=deal_id
            )
            
            # Save conversation messages
            summary_id = getattr(summary, 'id', None)
            if summary_id is None:
                return False
                
            success = ConversationRepository.save_conversation_messages(
                conversation_summary_id=summary_id,
                user_message=user_message,
                bot_response=bot_response
            )
            
            return success
            
        except Exception as e:
            print(f"❌ Error saving conversation to database: {e}")
            return False
    
    def _extract_basic_info(self, user_message: str, business_name: str, services: List[str]) -> Dict[str, str]:
        """Extract basic information from user message."""
        extracted = {
            "full_name": "",
            "event_type": "",
            "event_date": "",
            "venue": "",
            "phone_number": ""
        }

        # Extract event types
        event_types = [
            "wedding", "reception", "ceremony", "cocktail", "mehendi", "sangeet",
            "engagement", "birthday", "anniversary", "party", "celebration",
            "function", "satsang", "puja", "haldi"
        ]
        
        found_events = []
        for event in event_types:
            if event in user_message.lower():
                found_events.append(event.title())
        if found_events:
            extracted['event_type'] = ", ".join(found_events)

        # Extract venue information
        venue_indicators = [
            "at", "in", "venue", "location", "place", "hall", "hotel", "resort",
            "banquet", "garden", "home", "house", "palace", "ground", "club"
        ]
        
        for indicator in venue_indicators:
            match = re.search(f"{indicator}\\s+([^,.!?\\n]+)", user_message, re.IGNORECASE)
            if match:
                venue = match.group(1).strip()
                if venue and len(venue) > 2:  # Avoid single letter matches
                    extracted['venue'] = venue
                    break

        # Extract dates - look for both specific and range formats
        # Example patterns: "5th February 2026", "Feb 5-7 2026", "5-7 Feb 2026"
        date_patterns = [
            r'(\d{1,2}(?:st|nd|rd|th)?\s*(?:to|-|/)\s*\d{1,2}(?:st|nd|rd|th)?\s*(?:of\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*,?\s*\d{4})',
            r'(\d{1,2}(?:st|nd|rd|th)?\s*(?:of\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*,?\s*\d{4})',
            r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*\d{1,2}(?:st|nd|rd|th)?\s*(?:to|-|/)\s*\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{4})',
            r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                extracted['event_date'] = match.group(1)
                break

        # Extract phone numbers if present
        phone_pattern = r'(?:(?:\+\d{1,3}[-.\s]?)?(?:\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\(\d{3}\)\s*\d{3}[-.\s]?\d{4}|\d{10}))'
        phone_match = re.search(phone_pattern, user_message)
        if phone_match:
            extracted['phone_number'] = phone_match.group(0)

        return extracted

    def _has_event_details(self, user_message: str) -> bool:
        """Check if message contains event-related information."""
        # Keywords that indicate event details
        event_indicators = [
            'wedding', 'event', 'function', 'ceremony', 'reception', 'venue',
            'date', 'celebration', 'party', 'anniversary', 'birthday',
            'engagement', 'sangeet', 'mehendi', 'haldi', 'cocktail',
            'schedule', 'itinerary', 'plan', 'booking', 'location',
            'hall', 'hotel', 'resort', 'banquet', 'garden'
        ]
        
        # Check for date patterns
        has_date = any(re.search(pattern, user_message, re.IGNORECASE) for pattern in [
            r'\d{1,2}(?:st|nd|rd|th)?[\s-]*(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)',
            r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}',
            r'\d{4}'
        ])

        # Check for event keywords
        has_event_keyword = any(indicator in user_message.lower() for indicator in event_indicators)
        
        return has_event_keyword or has_date
    
    def _get_fallback_response(self) -> Dict[str, Any]:
        """Get fallback response when AI service fails."""
        # Get the previous summary from the current conversation
        previous_summary = getattr(self, 'previous_summary', '')
        current_message = getattr(self, 'current_message', '')
        fallback_message = "Thank you for your message! Our team will get back to you soon. 🌸"
        
        # Build the conversation summary
        conversation_summary = previous_summary
        if current_message:
            conversation_summary = f"{previous_summary}\nUser: {current_message}\nBot: {fallback_message}"
        
        return {
            "message_to_be_sent": fallback_message,
            "contains_structured_data": False,
            "full_name": "",
            "event_type": "",
            "event_date": "",
            "venue": "",
            "phone_number": "",
            "conversation_summary": conversation_summary
        }
    
    def _validate_response_format(self, response_data: Dict[str, Any]) -> bool:
        """Validate that response has required fields."""
        required_fields = [
            "message_to_be_sent",
            "contains_structured_data", 
            "full_name",
            "event_type",
            "event_date",
            "venue",
            "phone_number",
            "conversation_summary"
        ]
        
        return all(field in response_data for field in required_fields)
    
    def _clean_response_data(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate response data."""
        # Ensure all required fields exist
        default_response = {
            "message_to_be_sent": "",
            "contains_structured_data": False,
            "full_name": "",
            "event_type": "",
            "event_date": "",
            "venue": "",
            "phone_number": "",
            "conversation_summary": ""
        }
        
        # Merge with defaults
        cleaned_data = {**default_response, **response_data}
        
        # Clean string fields
        for field in ["message_to_be_sent", "full_name", "event_type", "event_date", "venue", "phone_number", "conversation_summary"]:
            if field in cleaned_data:
                cleaned_data[field] = str(cleaned_data[field]).strip()
        
        # Ensure boolean field
        cleaned_data["contains_structured_data"] = bool(cleaned_data.get("contains_structured_data", False))
        
        return cleaned_data 