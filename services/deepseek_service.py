import json
import re
import requests
from typing import Dict, List, Optional, Any
from .ai_service_interface import AIServiceInterface
from .prompt_manager import prompt_manager
from repository.conversation_repository import ConversationRepository
import traceback
from utils.logger import logger


class DeepSeekService(AIServiceInterface):
    """DeepSeek service implementation for Instagram conversation handling."""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat", brideside_user_id: int = 1, business_name: str = "The Bride Side", services: List[str] = []):
        """Initialize DeepSeek service."""
        # Initialize parent class
        super().__init__(api_key, model, brideside_user_id)
        
        # DeepSeek API configuration
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
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
            # Check if message contains event details
            if self._has_event_details(user_message):
                # Extract event details
                extracted_info = self._extract_basic_info(user_message, self.business_name, self.services)
                
                # Build conversation summary
                event_summary = []
                if extracted_info['event_type']:
                    event_summary.append(f"Event type: {extracted_info['event_type']}")
                if extracted_info['event_date']:
                    event_summary.append(f"Date: {extracted_info['event_date']}")
                if extracted_info['venue']:
                    event_summary.append(f"Venue: {extracted_info['venue']}")
                
                summary = "User shared event details: " + "; ".join(event_summary) if event_summary else "User shared event details"
                
                response_data = {
                    "message_to_be_sent": "Thank you for sharing your event details! To help you better, could you please share your phone number?",
                    "contains_structured_data": True,
                    "full_name": extracted_info['full_name'],
                    "event_type": extracted_info['event_type'],
                    "event_date": extracted_info['event_date'],
                    "venue": extracted_info['venue'],
                    "phone_number": extracted_info['phone_number'],
                    "conversation_summary": f"{previous_conversation_summary}\n{summary}"
                }

                # Save conversation to database
                self._save_conversation_to_db(instagram_user_id, instagram_username, deal_id, user_message, response_data)
                
                return response_data

            # Generate system prompt based on conversation state
            system_prompt = self._generate_system_prompt(missing_fields, previous_conversation_summary, current_deal_data)
            
            # Get AI response
            ai_response = self._call_deepseek_api(system_prompt, user_message)
            
            # Parse JSON response
            response_data = self._parse_json_response(ai_response)
            
            # Save conversation to database
            self._save_conversation_to_db(instagram_user_id, instagram_username, deal_id, user_message, response_data)
            
            return response_data

        except Exception as e:
            print(f"❌ Error in DeepSeekService.get_response_with_json: {e}")
            return self._create_fallback_response(user_message, missing_fields, previous_conversation_summary)

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
        
        return prompt_manager.generate_collection_prompt(self.brideside_user_id, missing_fields, previous_summary, current_deal_data, self.business_name, self.services)

    def _call_deepseek_api(self, system_prompt: str, user_message: str) -> str:
        """Call DeepSeek API with the given prompts."""
        # First check if the message is a simple greeting
        is_greeting = self._is_greeting(user_message)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "stream": False
        }
        
        response = requests.post(self.api_url, json=payload, headers=self.headers)
        response.raise_for_status()
        
        result = response.json()
        response_text = result["choices"][0]["message"]["content"]
        if response_text is None:
            response_text = "{}"  # Default empty JSON if no content
        
        # Parse the response and add the is_greeting flag
        try:
            response_dict = json.loads(response_text)
            response_dict['is_greeting'] = is_greeting
            return json.dumps(response_dict)
        except json.JSONDecodeError:
            # If JSON parsing fails, return a properly formatted response
            return json.dumps({
                "message_to_be_sent": response_text,
                "contains_structured_data": False,
                "is_greeting": is_greeting,
                "full_name": "",
                "event_type": "",
                "event_date": "",
                "venue": "",
                "phone_number": "",
                "conversation_summary": f"AI Response: {response_text}"
            })

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

    def _create_fallback_response(self, user_message: str, missing_fields: List[str], previous_summary: str) -> Dict[str, Any]:
        """Create fallback response when AI fails."""
        message_lower = user_message.lower()
        
        if not missing_fields:
            # If no missing fields, check if user is asking for updates
            update_keywords = ['update', 'change', 'modify', 'edit', 'correct', 'fix', 'new', 'different']
            
            if any(keyword in message_lower for keyword in update_keywords):
                fallback_message = "Sure! I can help you update your details. What would you like to change?"
            else:
                fallback_message = "NO_MESSAGE"
        else:
            fallback_message = "Thank you for the information! Our team will contact you shortly to discuss your requirements."
        
        # Try to extract basic information from user message
        extracted_info = self._extract_basic_info(user_message, self.business_name, self.services)
        
        return {
            "message_to_be_sent": fallback_message,
            "contains_structured_data": len(missing_fields) < 6,
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
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 50,
                "top_p": 1,
                "stream": False
            }
            
            response = requests.post(self.api_url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            json_str = ai_response[ai_response.find('{'): ai_response.rfind('}') + 1]
            parsed = json.loads(json_str)
            return parsed.get("result", False)

        except Exception as e:
            print(f"❌ DeepSeek error in is_emoji_or_appreciation: {e}")
            return False

    def is_collab_or_advertisement(self, message: str) -> bool:
        """Check if message is promotional or collaboration/advertisement related."""
        try:
            prompts = "You are a smart assistant. Classify the following message.Only return json like this: { \"result\": true } or { \"result\": false }Examples:\"❤️❤️\" → true\"thank you so much\" → true\"wow😍\" → true\"Hi, I'm looking for a makeup artist\" → false\"Can I know your pricing?\" → falseNow classify:\"\"\"{message}\"\"\""
            
            messages = [
                {"role": "system", "content": prompts},
                {"role": "user", "content": message}
            ]
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 50,
                "top_p": 1,
                "stream": False
            }
            
            response = requests.post(self.api_url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            json_str = ai_response[ai_response.find('{'): ai_response.rfind('}') + 1]
            parsed = json.loads(json_str)
            return parsed.get("result", False)

        except Exception as e:
            print(f"❌ DeepSeek error in is_collab_or_advertisement: {e}")
            return False 
    def _is_greeting(self, message: str) -> bool:
        """Check if a message is a simple greeting."""
        # Convert to lowercase and strip whitespace
        message = message.lower().strip()
        
        # If message contains business name or asks about services, it's not a greeting
        business_names = [self.business_name.lower(), 'the bride side', 'bride side', 'thebrideside']
        if any(name in message for name in business_names):
            return False
            
        # If message asks about services or contains question words, it's not a greeting
        question_patterns = [
            'what', 'how', 'when', 'where', 'who', 'which', 'why',
            'can you', 'could you', 'tell me', 'looking for',
            'service', 'price', 'cost', 'package', 'booking'
        ]
        if any(pattern in message for pattern in question_patterns):
            return False
        
        # Common greeting patterns
        greeting_patterns = [
            r'^hi+\s*$',  # hi, hii, hiii
            r'^he+y+\s*$',  # hey, heey
            r'^he+llo+\s*$',  # hello, helloo
            r'^(good\s*)?(morning|afternoon|evening|day)',  # good morning, etc.
            r'^namaste\s*$',
            r'^hola\s*$',
            r'^greetings\s*$',
            r'^hi\s+there\s*$',
            r'^hey\s+there\s*$',
            r'^hello\s+there\s*$',
        ]
        
        # Check if message matches any greeting pattern
        return any(re.match(pattern, message) for pattern in greeting_patterns) 
    
    def is_message_not_related_to_provided_service(self, message: str, services: List[str]) -> bool:
        """
        Uses the AI model to determine if the message is NOT related to any of the provided services.
        
        Returns True if message is unrelated to services, else False.
        """
        try:
            services_text = ", ".join(services)

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