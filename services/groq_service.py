from typing import Dict, List, Optional, Any
from groq import Groq
import json
import re
from config import GROQ_API_KEY, GROQ_MODEL
from .ai_service_interface import AIServiceInterface
from services.prompt_manager import prompt_manager
from repository.conversation_repository import ConversationRepository
from repository.brideside_vendor_repository import get_brideside_vendor_by_ig_account_id
import traceback
from utils.logger import logger


class GroqService(AIServiceInterface):
    """Configurable Groq AI service for Instagram conversation handling."""
    
    def __init__(self, api_key: str = "", model: str = GROQ_MODEL or "meta-llama/llama-4-scout-17b-16e-instruct", brideside_user_id: int = 1, business_name: str = "The Bride Side", services: List[str] = []):
        # Initialize parent class
        effective_api_key = api_key or GROQ_API_KEY or ""
        super().__init__(effective_api_key, model, brideside_user_id)
        
        # Groq-specific client
        self.client = Groq(api_key=self.api_key)
        
        self.business_name = business_name
        self.services = services
    
    
    def get_response_with_json(
        self,         
        user_id: int, 
        instagram_user_id: int,
        deal_id: int,
        instagram_username: str,
        user_message: str, 
        missing_fields: List[str], 
        previous_conversation_summary: str = "",
        current_deal_data: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Get AI response in JSON format with conversation tracking."""
        try:
            # Generate system prompt based on conversation state
            system_prompt = self._generate_system_prompt(missing_fields, previous_conversation_summary, current_deal_data)
            
            # Get AI response
            ai_response = self._call_groq_api(system_prompt, user_message)
            
            # Parse JSON response
            response_data = self._parse_json_response(ai_response)
            
            # Save conversation to database using repository
            self._save_conversation_to_db(instagram_user_id, instagram_username, deal_id, user_message, response_data)
            
            return response_data

        except Exception as e:
            print(f"❌ Error in GroqService.get_response_with_json: {e}")
            return self._create_fallback_response(user_message, missing_fields, previous_conversation_summary)

    def _is_advertisement_message(self, message: str) -> bool:
        """Check if message contains advertisement keywords."""
        return any(kw in message.lower() for kw in self.ad_keywords)

    def _create_ad_decline_response(self, user_message: str, previous_summary: str) -> Dict[str, str]:
        """Create polite decline response for advertisement messages."""
        decline_message = (
            "Thank you for reaching out. We truly appreciate your interest, "
            "but we're not exploring promotional opportunities at the moment. 🌸"
        )
        
        return {
            "message_to_be_sent": decline_message,
            "full_name": "",
            "event_type": "",
            "event_date": "",
            "venue": "",
            "phone_number": "",
            "conversation_summary": f"{previous_summary}\nUser: {user_message}\nBot: {decline_message}"
        }

    def _generate_system_prompt(self, missing_fields: List[str], previous_summary: str, current_deal_data: Optional[Dict[str, str]] = None) -> str:
        """Generate system prompt based on missing fields."""
        if not missing_fields:
            return self._generate_service_prompt(previous_summary)
        else:
            return self._generate_collection_prompt(missing_fields, previous_summary, current_deal_data)

    def _generate_service_prompt(self, previous_summary: str) -> str:
        """Generate prompt for when all user details are collected."""
        return prompt_manager.generate_service_prompt(self.brideside_user_id, previous_summary, self.business_name, self.services)

    def _generate_collection_prompt(self, missing_fields: List[str], previous_summary: str, current_deal_data: Optional[Dict[str, str]] = None) -> str:
        """Generate prompt for collecting missing user information."""
        
        # Prepare current details section if available
        current_details_section = ""
        if current_deal_data:
            current_details_section = f"""
CURRENT USER DETAILS:
- Full Name: {current_deal_data.get('full_name', 'Not provided')}
- Event Type: {current_deal_data.get('event_type', 'Not provided')}
- Event Date: {current_deal_data.get('event_date', 'Not provided')}
- Venue: {current_deal_data.get('venue', 'Not provided')}
- Phone Number: {current_deal_data.get('phone_number', 'Not provided')}

"""

        return prompt_manager.generate_collection_prompt(
            self.brideside_user_id,
            missing_fields,
            previous_summary,
            current_deal_data,
            self.business_name,
            self.services
        )

    def _call_groq_api(self, system_prompt: str, user_message: str) -> str:
        """Call Groq API with the given prompts."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            response_format={"type": "json_object"},
            stream=False
        )
        
        response = completion.choices[0].message.content
        if response is None:
            response = "{}"  # Default empty JSON if no content
        
        return response

    def _parse_json_response(self, ai_response: str) -> Dict[str, str]:
        """Parse JSON from AI response."""
        try:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = ai_response[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Failed to parse JSON response: {e}")
            raise

    def _save_conversation_to_db(self, user_id: int, instagram_username: str, deal_id: int, user_message: str, response_data: Dict[str, str]):
        """Save conversation to database using repository pattern."""
        try:
            # Get or create conversation summary
            summary = ConversationRepository.get_conversation_summary_by_deal_id(deal_id)
            
            if not summary:
                # Create new summary record
                summary = ConversationRepository.create_conversation_summary(
                    instagram_username=instagram_username,
                    instagram_user_id=user_id,  # This is actually the instagram_user_id
                    deal_id=deal_id
                )
            
            # Update conversation summary
            new_summary = str(summary.deals_conversation_summary or "") + "\n" + response_data.get('conversation_summary', '')
            
            # Add email information to summary if provided
            if response_data.get('phone_number', '') and '@' in response_data.get('phone_number', ''):
                new_summary += f"\n[Email provided as contact method: {response_data.get('phone_number', '')}]"
            
            if new_summary:
                success = ConversationRepository.update_conversation_summary(user_id, new_summary)  # This should also use instagram_user_id
                if not success:
                    logger.error(f"❌ Failed to update conversation summary for Instagram user {user_id}")
                else:
                    logger.info(f"✅ Conversation saved to database for Instagram user {user_id}")
                
        except Exception as e:
            logger.error(f"❌ Error saving conversation to database: {e}")
            logger.error(traceback.format_exc())

    def _extract_basic_info(self, user_message: str, business_name: str, services: List[str]) -> Dict[str, str]:
        """Extract basic information from user message using simple matching."""
        extracted = {
            "full_name": "",
            "event_type": "",
            "event_date": "",
            "venue": "",
            "phone_number": ""
        }
        
        message_lower = user_message.lower()
        
        # 🚨 CRITICAL: Never extract business name as user data
        business_names = [business_name.lower(), 'the bride side', 'bride side', 'thebrideside']
        if any(business_name in message_lower for business_name in business_names):
            # Don't extract business name as full_name
            pass
        else:
            # Enhanced event type detection to match system expectations
            if any(keyword in message_lower for keyword in ['wedding photography', 'wedding photo']):
                extracted['event_type'] = 'Wedding Photography'
            elif any(keyword in message_lower for keyword in ['photoshoot', 'photo shoot']):
                extracted['event_type'] = 'Photoshoot'
            elif any(keyword in message_lower for keyword in ['bridal makeup', 'bride makeup']):
                extracted['event_type'] = 'Bridal Makeup'
            elif any(keyword in message_lower for keyword in ['party makeup']):
                extracted['event_type'] = 'Party Makeup'
            elif any(keyword in message_lower for keyword in ['wedding planner', 'wedding planning']):
                extracted['event_type'] = 'Wedding Planning'
            elif any(keyword in message_lower for keyword in ['wedding decor', 'decoration']):
                extracted['event_type'] = 'Wedding Decor'
            elif any(keyword in message_lower for keyword in ['makeup']):
                extracted['event_type'] = 'Makeup'
            elif any(keyword in message_lower for keyword in ['wedding', 'marriage']):
                extracted['event_type'] = 'Wedding'
        
        # Extract phone number using regex
        import re
        phone_match = re.search(r'\b\d{10}\b', user_message)
        if phone_match:
            extracted['phone_number'] = phone_match.group()
        else:
            # Check for email address
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', user_message)
            if email_match:
                extracted['phone_number'] = email_match.group()  # Store email as phone_number (contact method)
        
        # Extract venue/location information
        venue_patterns = [
            r'venue(?:\s+is|\s+will\s+be|\s*:)?\s+(.+?)(?:\s*[.!,]|$)',
            r'location(?:\s+is|\s+will\s+be|\s*:)?\s+(.+?)(?:\s*[.!,]|$)',
            r'(?:at|in)\s+([A-Za-z\s,]+?)(?:\s+hotel|\s+resort|\s+hall|\s+garden|\s+banquet|\s+club|$)',
            r'wedding(?:\s+is|\s+will\s+be)?\s+(?:at|in)\s+(.+?)(?:\s*[.!,]|$)',
            r'event(?:\s+is|\s+will\s+be)?\s+(?:at|in)\s+(.+?)(?:\s*[.!,]|$)',
            r'ceremony(?:\s+is|\s+will\s+be)?\s+(?:at|in)\s+(.+?)(?:\s*[.!,]|$)',
            r'its?\s+(?:at|in)\s+(.+?)(?:\s*[.!,]|$)',
        ]
        
        # Common venue/location keywords and place names
        venue_keywords = [
            'hotel', 'resort', 'hall', 'banquet', 'garden', 'club', 'palace', 'farmhouse',
            'venue', 'location', 'place', 'temple', 'church', 'gurdwara', 'mosque',
            'goa', 'delhi', 'mumbai', 'bangalore', 'pune', 'jaipur', 'udaipur', 'agra', 
            'chennai', 'kolkata', 'hyderabad', 'ahmedabad', 'chandigarh', 'lucknow', 
            'indore', 'bhopal', 'nagpur', 'kochi', 'thiruvananthapuram', 'srinagar',
            'manali', 'shimla', 'rishikesh', 'haridwar', 'pushkar', 'jodhpur',
            'noida', 'gurgaon', 'gurugram', 'faridabad', 'ghaziabad'
        ]
        
        # Try to extract venue using patterns
        for pattern in venue_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                potential_venue = match.group(1).strip()
                # Clean up the venue name
                potential_venue = re.sub(r'[.!,]+$', '', potential_venue)
                if len(potential_venue) > 2:
                    extracted['venue'] = potential_venue.title()
                    break
        
        # If no pattern matched, check for standalone venue/location mentions
        if not extracted['venue']:
            words = message_lower.split()
            for i, word in enumerate(words):
                if word in venue_keywords:
                    # Try to capture context around the keyword
                    start_idx = max(0, i-2)
                    end_idx = min(len(words), i+3)
                    venue_candidate = ' '.join(words[start_idx:end_idx])
                    # Clean up and validate
                    venue_candidate = re.sub(r'[.!,]+$', '', venue_candidate)
                    if len(venue_candidate) > 3:
                        extracted['venue'] = venue_candidate.title()
                        break
        
        # Extract names (basic pattern) - but never extract business name
        name_patterns = [
            r'my name is (\w+(?:\s+\w+)*)',
            r'i am (\w+(?:\s+\w+)*)',
            r'name:\s*(\w+(?:\s+\w+)*)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                name = match.group(1).title()
                # Never extract business name as user name
                if name.lower() not in ['the bride side', 'bride side']:
                    extracted['full_name'] = name
                break
        
        # Date extraction following same rules as main AI processing
        # Only extract dates that explicitly include the year
        # DO NOT assume current year for dates without year
        date_patterns_with_year = [
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
            r'(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',  # YYYY/MM/DD or YYYY/DD/MM
            r'(\w+\s+\d{1,2}[,\s]+\d{4})',        # March 15, 2025 or March 15 2025
            r'(\d{1,2}(?:st|nd|rd|th)\s+\w+\s+\d{4})',  # 15th March 2025
        ]
        
        for pattern in date_patterns_with_year:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                # Found a date with year - this is safe to extract
                # Note: We're not doing date format conversion here, just detection
                # The AI will handle the actual formatting
                extracted['event_date'] = match.group(1)
                break
        
        # Note: We intentionally do NOT extract dates without years
        # This prevents the same issue we fixed in the main AI processing
        # where dates like "30th July" would be incorrectly assumed to be current year
        
        return extracted

    def _create_fallback_response(
        self, 
        user_message: str, 
        missing_fields: List[str], 
        previous_summary: str
    ) -> Dict[str, Any]:
        """Create fallback response when AI fails."""
        message_lower = user_message.lower()
        
        if not missing_fields:
            # If no missing fields, check if user is asking for updates or providing new data
            message_lower = user_message.lower()
            update_keywords = ['update', 'change', 'modify', 'edit', 'correct', 'fix', 'new', 'different']
            
            # First, check if user provided a date without year (needs year confirmation)
            date_without_year_patterns = [
                r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)\b',
                r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:st|nd|rd|th)?\b',
                r'\b\d{1,2}[/-]\d{1,2}\b'
            ]
            
            has_date_without_year = False
            for pattern in date_without_year_patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    # Check if it doesn't contain a year (4 digits)
                    if not re.search(r'\b20\d{2}\b', user_message):
                        has_date_without_year = True
                        break
            
            # If user provided date without year, ask for year confirmation
            if has_date_without_year:
                fallback_message = "Thank you! Just to confirm - can you please provide the year of the event as well?"
            # Check if user is explicitly asking for updates
            elif any(keyword in message_lower for keyword in update_keywords):
                # Check if it's a specific field update request without new value
                if any(phrase in message_lower for phrase in ['change my event date', 'update my date', 'change my date', 'modify my date', 'change event date', 'update event date']):
                    fallback_message = "What is your new event date?"
                elif any(phrase in message_lower for phrase in ['change my name', 'update my name', 'change my full name', 'update my full name']):
                    fallback_message = "What would you like to change your name to?"
                elif any(phrase in message_lower for phrase in ['change my venue', 'update my venue', 'change my location', 'update my location']):
                    fallback_message = "What is your new venue/location?"
                elif any(phrase in message_lower for phrase in ['change my phone', 'update my phone', 'change my number', 'update my number', 'change my contact']):
                    fallback_message = "What is your new contact number?"
                # Check if it's a specific update request (contains field + value)
                elif any(field in message_lower for field in ['name', 'date', 'venue', 'phone', 'number', 'contact', 'event']):
                    fallback_message = "Perfect! I've updated your details. Is there anything else you'd like to change?"
                else:
                    # Generic update request
                    fallback_message = "Sure! I can help you update your details. What would you like to change?\n• Full name\n• Event date\n• Venue/location\n• Contact number\n• Event type\n\nPlease let me know which detail you'd like to update."
            else:
                # No update request, return NO_MESSAGE
                fallback_message = "NO_MESSAGE"
        elif 'phone_number' in missing_fields:
            # Handle special scenarios when phone is missing
            if any(keyword in message_lower for keyword in ['edit', 'editing']):
                fallback_message = "Sure! Please share your contact number — our editing team will get in touch with you shortly."
            elif any(keyword in message_lower for keyword in ['budget', 'quote', 'price']) and any(keyword in message_lower for keyword in ['lakh', '1l', '100000', 'low']):
                fallback_message = "Thanks for sharing your budget! Our packages usually start above ₹1 lakh to ensure premium quality and service. Let us know if there's flexibility — and please share your contact number so our team can guide you better ✨"
            elif any(keyword in message_lower for keyword in ['budget', 'quote', 'price', 'cost']):
                fallback_message = "Our packages start from ₹1.5L - ₹6L depending on your requirements. Please share your event details and contact number. We'll then share suitable package options."
            elif any(keyword in message_lower for keyword in ['portfolio', 'work', 'photos', 'pictures']):
                fallback_message = "Please share your event details and contact number. We'll then send you a curated portfolio that matches your vision ✨"
            elif any(keyword in message_lower for keyword in ['goa', 'delhi', 'mumbai', 'punjab', 'location']):
                if 'based' in message_lower or 'location' in message_lower:
                    fallback_message = "We're based in Delhi, Mumbai, and Punjab — and we handle weddings across Pan India!"
                else:
                    fallback_message = "That sounds amazing! Please share your event details and contact number. We'll suggest options best suited to your event ✨"
            elif any(keyword in message_lower for keyword in ['available', 'availability', 'date']):
                fallback_message = "We'd love to check availability for you! ✨ Please share your event details and contact number."
            elif any(keyword in message_lower for keyword in ['birthday', 'baby shower', 'anniversary', 'corporate']):
                fallback_message = "Thank you so much for reaching out! We currently focus only on wedding-related services — Photography, Makeup, Planning, and Decor. We're not taking non-wedding events at the moment. Wishing you a beautiful celebration! ✨"
            elif any(keyword in message_lower for keyword in ['friend', 'booked', 'before', 'referral']):
                fallback_message = "We're so happy to hear that! Please share your details and contact number."
            else:
                fallback_message = "Perfect! We have most of your wedding details. To finalize your booking and send you our detailed packages, could you please share your contact number? 📞✨"
        elif 'event_date' in missing_fields:
            fallback_message = "Great choice for your Wedding Photography! 📸 When is your special day? This helps us check availability and suggest the best photography timeline for your celebration! 💍✨"
        elif 'venue' in missing_fields:
            fallback_message = "Wonderful! Could you please tell us your wedding venue? This helps us plan the perfect photography setup and coordinate with the venue management! 🏛️✨"
        else:
            fallback_message = "Thank you for the information! Based on your requirements, our team will create a customized package for you. Is there anything specific about our Wedding Photography services you'd like to know? 📸✨"
        
        # Check if user provided a date without year (needs year confirmation)
        date_without_year_patterns = [
            r'\b(\d{1,2}[\/\-]\d{1,2})\b(?!\d)',  # MM/DD or DD/MM (not followed by year)
            r'\b(\w+\s+\d{1,2})(?!\s*[,\s]*\d{4})\b',  # March 15 (not followed by year)
            r'\b(\d{1,2}(?:st|nd|rd|th)\s+\w+)(?!\s+\d{4})\b',  # 15th March (not followed by year)
        ]
        
        has_date_without_year = False
        for pattern in date_without_year_patterns:
            if re.search(pattern, user_message, re.IGNORECASE):
                has_date_without_year = True
                break
        
        # Try to extract basic information from user message even when AI fails
        extracted_info = self._extract_basic_info(user_message, self.business_name, self.services)
        
        # If user provided date without year, ask for year confirmation
        if has_date_without_year and 'event_date' in missing_fields:
            fallback_message = "Thank you! Just to confirm - can you please provide the year of the event as well?"
            # CRITICAL: Do not extract the date without year - leave event_date empty
            extracted_info["event_date"] = ""
        # If user provided date without year for updates (no missing fields)
        elif has_date_without_year and not missing_fields:
            fallback_message = "Thank you! Just to confirm - can you please provide the year of the event as well?"
            # CRITICAL: Do not extract the date without year - leave event_date empty  
            extracted_info["event_date"] = ""
        else:
            # Check if user just provided all missing details
            extracted_fields = [k for k, v in extracted_info.items() if v]
            newly_missing_fields = [field for field in missing_fields if field not in extracted_fields]
            
            # If user just provided all missing details, send special completion message
            if missing_fields and not newly_missing_fields:
                fallback_message = "Thanks again! 🌸\nOur team will get in touch with you shortly to take things forward.\nCan't wait to be a part of your special day! 💫"
        
        return {
            "message_to_be_sent": fallback_message,
            "contains_structured_data": len(missing_fields) < 6,  # If we have some fields, it contains data
            "full_name": extracted_info.get("full_name", ""),
            "event_type": extracted_info.get("event_type", ""), 
            "event_date": extracted_info.get("event_date", ""),
            "venue": extracted_info.get("venue", ""),
            "phone_number": extracted_info.get("phone_number", ""),
            "conversation_summary": f"{previous_summary}\n\nUser: {user_message}\nBot: {fallback_message}" if previous_summary else f"User: {user_message}\nBot: {fallback_message}"
        }

    def is_emoji_or_appreciation(self, message: str) -> bool:
        """Check if message is just emojis or simple appreciation."""
        try:
            prompts = "You are a smart assistant. Classify the following message.Only return json like this: {{ \"result\": true }} or {{ \"result\": false }}Examples:\"❤️❤️\" → true\"thank you so much\" → true\"wow😍\" → true\"Hi, I'm looking for a makeup artist\" → false\"Can I know your pricing?\" → falseNow classify:\"\"\"{message}\"\"\""
            
            messages = [
                {"role": "system", "content": prompts},
                {"role": "user", "content": message}
            ]

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=0,
                max_completion_tokens=256,
                top_p=1,
                stream=False
            )

            ai_response = completion.choices[0].message.content
            json_str = ai_response[ai_response.find('{'): ai_response.rfind('}') + 1]
            parsed = json.loads(json_str)
            return parsed.get("result", False)

        except Exception as e:
            print(f"❌ Groq error in is_emoji_or_appreciation: {e}")
            return False

    def is_collab_or_advertisement(self, message: str) -> bool:
        """Check if message is promotional or collaboration/advertisement related."""
        try:
            prompts = "You are an assistant helping classify Instagram DMs.Respond ONLY in this json format:{ \"result\": true } or { \"result\": false }Definition:- Return true if the message is about collaboration, sponsorship, influencer work, advertising, or includes a link (like https:// or bit.ly).- Return false otherwise.Message:\"\"\"{message}\"\"\""
            
            messages = [
                {"role": "system", "content": prompts},
                {"role": "user", "content": message}
            ]

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_completion_tokens=256,
                top_p=1,
                stream=False
            )

            ai_response = completion.choices[0].message.content
            json_str = ai_response[ai_response.find('{'): ai_response.rfind('}') + 1]
            parsed = json.loads(json_str)
            return parsed.get("result", False)

        except Exception as e:
            print(f"❌ Groq error in is_collab_or_advertisement: {e}")
            return False
        
    def is_message_not_related_to_provided_service(self, message: str, services: List[str]) -> bool:
        """
        Uses the AI model to determine if the message is NOT related to any of the provided services.
        
        Returns True if message is unrelated to services, else False.
        """
        try:
            logger.info(f"services: {services}")
            services_text = ", ".join(services)
            logger.info(f"services_text: {services_text}")

            system_prompt = (
                "You are an assistant helping classify Instagram DMs.\n"
                "Respond ONLY in this JSON format: { \"result\": true } or { \"result\": false }\n\n"
                "Definition:\n"
                "- Provided services: " + services_text + "\n"
                "- Return false if the message is about any of these services (even indirectly).\n"
                "- Return true if the message is unrelated to the above services (e.g. ads, collab, spam, other topics).\n"
            )

            logger.info(f"System prompt: {system_prompt}")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            logger.info(f"Messages: {messages}")
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=256,
                top_p=1,
                stream=False
            )

            ai_response = completion.choices[0].message.content
            logger.info(f"AI response: {ai_response}")
            # Extract JSON result
            start = ai_response.find('{')
            end = ai_response.rfind('}') + 1
            if start == -1 or end == -1:
                raise ValueError("No valid JSON in AI response")

            parsed = json.loads(ai_response[start:end])
            return parsed.get("result", False)

        except Exception as e:
            logger.error(f"❌ Error in is_message_not_related_to_provided_services: {e}")
            return False

    def is_course_or_class_enquiry(self, message: str) -> bool:
        """
        Uses the AI model to determine if the message is related to course or class enquiries.
        
        Returns True if message is about courses/classes, else False.
        """
        try:
            system_prompt = (
                "You are an assistant that classifies Instagram DMs for course/class enquiries.\n"
                "Respond ONLY in this JSON format: { \"result\": true } or { \"result\": false }\n\n"
                "Rules:\n"
                "Return { \"result\": true } if the message is about:\n"
                "- Course enquiries (e.g., 'course details', 'course fees', 'course duration')\n"
                "- Class enquiries (e.g., 'class timings', 'class schedule', 'class availability')\n"
                "- Training programmes (e.g., 'training course', 'professional training')\n"
                "- Educational services (e.g., 'learn makeup', 'makeup classes', 'beauty course', 'masterclass')\n"
                "- Workshop enquiries (e.g., 'workshop details', 'workshop fees')\n"
                "- Certification courses (e.g., 'certification', 'diploma course')\n"
                "- Skill development courses (e.g., 'skill training', 'learn skills')\n"
                "- Online/offline classes (e.g., 'online course', 'offline classes')\n"
                "- Course registration (e.g., 'enroll in course', 'course booking')\n"
                "- Course curriculum (e.g., 'what will I learn', 'course content')\n"
                "- Course instructor (e.g., 'who teaches', 'instructor details')\n"
                "- Course materials (e.g., 'course kit', 'study materials')\n"
                "- Course completion (e.g., 'course completion', 'certificate')\n"
                "- Hairstylist training (e.g., 'hairstylist course', 'learn hairstyling', 'hair styling classes')\n"
                "- Model training (e.g., 'modeling course', 'learn modeling', 'model training classes')\n"
                "- Freelancer training (e.g., 'freelancer course', 'freelancing training', 'freelance skills')\n\n"
                "Return { \"result\": false } if the message is about:\n"
                "- Event services (e.g., 'wedding makeup', 'bridal makeup', 'party makeup')\n"
                "- Service bookings (e.g., 'book for wedding', 'makeup for event')\n"
                "- General greetings (e.g., 'hi', 'hello', 'good morning')\n"
                "- Pricing for services (e.g., 'makeup charges', 'service rates')\n"
                "- Availability for events (e.g., 'available for wedding', 'free on date')\n"
                "- Event details (e.g., 'wedding date', 'event venue')\n"
                "- Personal consultations (e.g., 'consultation', 'meeting')\n"
            )

            logger.info(f"Checking course/class enquiry for message: {message[:100]}...")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=256,
                top_p=1,
                stream=False
            )

            ai_response = completion.choices[0].message.content
            logger.info(f"Course/class enquiry AI response: {ai_response}")
            
            # Extract JSON result
            start = ai_response.find('{')
            end = ai_response.rfind('}') + 1
            if start == -1 or end == -1:
                raise ValueError("No valid JSON in AI response")

            parsed = json.loads(ai_response[start:end])
            result = parsed.get("result", False)
            
            if result:
                logger.info(f"✅ Message identified as course/class enquiry")
            else:
                logger.info(f"❌ Message is NOT a course/class enquiry")
                
            return result

        except Exception as e:
            logger.error(f"❌ Error in is_course_or_class_enquiry: {e}")
            return False

# Global instance for backward compatibility
groq_service = GroqService()

# Backward compatibility functions
def get_groq_response_with_json(user_message: str, user_id: int, instagram_user_id: int, instagram_username: str, deal_id: int, missing_fields: List[str], previous_conversation_summary: str, current_deal_data: Optional[Dict[str, str]] = None):
    return groq_service.get_response_with_json(user_message = user_message, user_id = user_id, instagram_user_id = instagram_user_id, instagram_username = instagram_username, deal_id = deal_id, missing_fields = missing_fields, previous_conversation_summary = previous_conversation_summary, current_deal_data = current_deal_data)

def is_emoji_or_appreciation(message: str) -> bool:
    return groq_service.is_emoji_or_appreciation(message)

def is_collab_or_advertisement(message: str) -> bool:
    return groq_service.is_collab_or_advertisement(message)
