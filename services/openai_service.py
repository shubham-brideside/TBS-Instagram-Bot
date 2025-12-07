import json
import re
from typing import Dict, List, Optional, Any
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from config import OPENAI_BASE_URL, OPENAI_MODEL
from .ai_service_interface import AIServiceInterface
from .prompt_manager import prompt_manager
from repository.conversation_repository import ConversationRepository
from repository.brideside_vendor_repository import get_brideside_vendor_by_ig_account_id
from utils.logger import logger
from typing import List

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenAIService(AIServiceInterface):
    """OpenAI service implementation for Instagram conversation handling."""
    
    def __init__(self, api_key: str = "", model: str = "", brideside_user_id: int = 1, business_name: str = "", services: List[str] = []):
        """Initialize OpenAI service."""
        if OpenAI is None:
            raise ImportError("OpenAI package is not installed. Please install it with 'pip install openai'")
        
        # Use model from environment variable if not provided
        if not model:
            model = OPENAI_MODEL or "gpt-4-turbo-preview"
            
        super().__init__(api_key, model, brideside_user_id, business_name, services)
        self.client = OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)

    def get_response_with_json(self, user_message: str, user_id: int, instagram_user_id: int,
                             instagram_username: str, deal_id: int, missing_fields: List[str],
                             previous_conversation_summary: str = "", current_deal_data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get AI response with structured JSON output."""
        try:
            # Check for advertisement/spam
            if self.is_collab_or_advertisement(user_message):
                return self._create_ad_decline_response(user_message, previous_conversation_summary)

            # Check for emoji/appreciation
            if self.is_emoji_or_appreciation(user_message):
                return {
                    "message_to_be_sent": "NO_MESSAGE",
                    "contains_structured_data": False,
                    "full_name": "",
                    "event_type": "",
                    "event_date": "",
                    "venue": "",
                    "phone_number": "",
                    "conversation_summary": f"{previous_conversation_summary}\nUser: {user_message}\nBot: NO_MESSAGE"
                }

            # Generate system prompt
            system_prompt = self._generate_system_prompt(missing_fields, previous_conversation_summary, current_deal_data)

            # Prepare messages for chat completion
            messages: List[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            # Get completion from OpenAI
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                response_format={"type": "json_object"}
            )

            # Parse response
            if completion.choices and completion.choices[0].message.content:
                response_text = completion.choices[0].message.content
                response_data = self._parse_json_response(response_text)

                # Save conversation to database
                self._save_conversation_to_db(
                    instagram_user_id=instagram_user_id,
                    deal_id=deal_id,
                    user_message=user_message,
                    bot_response=response_data.get("message_to_be_sent", ""),
                    extracted_data={**response_data, "instagram_username": instagram_username}
                )

                return response_data
            else:
                return self._get_fallback_response()

        except Exception as e:
            print(f"❌ Error getting response: {e}")
            return self._get_fallback_response()

    def is_emoji_or_appreciation(self, message: str) -> bool:
        """Check if message is just emojis or simple appreciation."""
        # Remove all emojis and whitespace
        message_no_emoji = re.sub(r'[\U0001F300-\U0001F9FF]', '', message)
        message_clean = message_no_emoji.strip().lower()
        
        # List of common appreciation words
        appreciation_words = {'ok', 'okay', 'thanks', 'thank', 'ty', 'thx', 'sure', 'yes', 'yeah', 'yep', 'k', 'kk', 'good', 'great', 'nice', 'perfect', 'awesome', 'cool', 'fine', 'alright', 'right', 'got it', 'understood', 'done', 'noted', 'hmm', 'hm', 'hmmmm'}
        
        # Check if message is empty after removing emojis or contains only appreciation words
        return not message_clean or message_clean in appreciation_words or all(word in appreciation_words for word in message_clean.split())

    def is_collab_or_advertisement(self, message: str) -> bool:
        """Check if message is promotional or collaboration/advertisement related."""
        message_lower = message.lower().strip()
        
        # Check for common ad/collab keywords
        ad_keywords = [
            'promote', 'promotion', 'collab', 'collaboration', 'sponsor', 'sponsored',
            'advertise', 'advertisement', 'marketing', 'partnership', 'influencer',
            'paid', 'deal', 'business opportunity', 'opportunity', 'proposal',
            'campaign', 'brand', 'promote your', 'promoting your', 'work with',
            'work together', 'paid promotion', 'paid partnership', 'paid collab',
            'affiliate', 'commission', 'earn', 'revenue', 'monetize', 'monetization','followers',
            'views', 'comments','gain your insta', 'increase followers', 'increase likes', 'boost followers'
        ]
        
        # Check for common ad patterns
        ad_patterns = [
            r'(?i)dm\s+for\s+collab',
            r'(?i)check\s+(?:out\s+)?my\s+(?:page|profile|account)',
            r'(?i)follow\s+(?:back|me)',
            r'(?i)check\s+my\s+bio',
            r'(?i)visit\s+my\s+(?:page|profile)',
            r'(?i)interested\s+in\s+collab',
            r'(?i)business\s+proposal',
            r'(?i)marketing\s+opportunity'
        ]
        
        # Check for keywords
        if any(kw in message_lower for kw in ad_keywords):
            return True
            
        # Check for patterns
        if any(re.search(pattern, message) for pattern in ad_patterns):
            return True
            
        # URL-only check (Instagram, Facebook, WhatsApp, etc.)
        if re.fullmatch(r'https?://[\w./?=&%\-]+', message_lower):
            return True
        # Instagram handle only check
        if re.fullmatch(r'@?[\w.]+', message_lower) and (message_lower.startswith('@') or 'instagram.com' in message_lower):
            return True
            
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
            "You are an assistant that classifies Instagram DMs.\n"
            "Respond ONLY in this JSON format: { \"result\": true } or { \"result\": false }\n\n"
            "Rules:\n"
            "- Provided services: " + services_text + "\n\n"
            "Return { \"result\": false } if the message:\n"
            "- Mentions or asks about any of the provided services (even indirectly)\n"
            "- Is a greeting (e.g., 'Hi', 'Hello', 'Good morning')\n"
            "- Includes any event details like:\n"
            "  - Event date\n"
            "  - Event venue or location\n"
            "  - Event name or type (e.g., wedding, reception)\n"
            "  - Contact number or phone query\n\n"
            "Return { \"result\": true } if the message is clearly unrelated, such as:\n"
            "- Asking about vendor details\n"
            "- Advertising, spam, promotions, collab, influencer messages\n"
            "- Messages with external links (e.g., https://, bit.ly)\n"
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
        Uses the AI model to determine if the message is related to course, class, model, or editing enquiries.
        
        Returns True if message is about courses/classes/modeling/editing, else False.
        """
        try:
            # 🚨 QUICK KEYWORD CHECK: Catch obvious promotional/unrelated messages before AI call
            message_lower = message.lower().strip()
            
            # Promotional message starters
            promotional_starters = [
                'book your', 'hire your', 'get your', 'book our', 'hire our', 
                'contact us for', 'we provide', 'we offer', 'our services include',
                'check out our', 'visit our', 'best wedding', 'top wedding',
                'call us for', 'dm us for', 'book now', 'contact for'
            ]
            if any(message_lower.startswith(starter) for starter in promotional_starters):
                logger.info(f"✅ Promotional message detected via keyword check: {message[:50]}...")
                return True
            
            # Unrelated keywords (choreographer, camera brands, technical equipment)
            unrelated_keywords = [
                'choreographer', 'choreography', 'dance choreographer', 'sangeet choreographer',
                'sony', 'canon', 'nikon', 'fujifilm', 'panasonic', 'olympus', 'leica',
                'sony camera', 'canon camera', 'camera gear', 'camera equipment',
                'what camera', 'which camera', 'camera model', 'camera body', 'camera lens', 'freelance'
            ]
            if any(keyword in message_lower for keyword in unrelated_keywords):
                logger.info(f"✅ Unrelated message detected via keyword check (choreographer/equipment): {message[:50]}...")
                return True

            # Customer booking inquiries - these are VALID customer questions, NOT course enquiries
            customer_booking_keywords = [
                 'how do i book', 'how to book', 'how can i book', 
                 'how do i book your', 'how to book your', 'how can i book your',
                 'how do i book your service', 'how to book your service', 'how can i book your service',
                 'how do i book a session', 'how to book a session', 'how can i book a session'
            ]
            if any(keyword in message_lower for keyword in customer_booking_keywords):
                logger.info(f"✅ Customer booking inquiry detected via keyword check: {message[:50]}...")
                return False  # NOT a course enquiry - it's a valid customer question

            
            system_prompt = (
                "You are an assistant that classifies Instagram DMs for course/class/model/editing enquiries.\n"
                "Respond ONLY in this JSON format: { \"result\": true } or { \"result\": false }\n\n"
                "🚨 CRITICAL: Return { \"result\": true } for ANY message that starts with promotional commands like:\n"
                "- 'Book your...'\n"
                "- 'Hire your...'\n"
                "- 'Get your...'\n"
                "- 'Book our...'\n"
                "- 'Contact us for...'\n"
                "- 'We provide...'\n"
                "- 'We offer...'\n"
                "These are promotional messages trying to sell services, NOT customer inquiries.\n\n"
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
                "- Freelancer training (e.g., 'freelancer course', 'freelancing training', 'freelance skills')\n"
                "- Model enquiries (e.g., 'are you looking for model', 'model opportunities', 'modeling work')\n"
                "- Model recruitment (e.g., 'model search', 'looking for models', 'model casting')\n"
                "- Model requirements (e.g., 'model criteria', 'model specifications', 'model qualifications')\n"
                "- Model portfolio (e.g., 'model portfolio', 'model photos', 'model profile')\n"
                "- Model auditions (e.g., 'model audition', 'model tryouts', 'model selection')\n"
                "- Model collaboration (e.g., 'model collaboration', 'work with models', 'model partnership')\n"
                "- Model bookings (e.g., 'book model', 'model availability', 'model schedule')\n"
                "- Model rates (e.g., 'model fees', 'model charges', 'model pricing')\n"
                "- Model experience (e.g., 'experienced model', 'model background', 'model history')\n"
                "- Model types (e.g., 'fashion model', 'commercial model', 'runway model', 'photo model')\n"
                "- Editing enquiries (e.g., 'photo editing', 'video editing', 'image editing', 'edit photos')\n"
                "- Editing services (e.g., 'editing services', 'photo retouching', 'video post-production')\n"
                "- Editing courses (e.g., 'learn photo editing', 'editing classes', 'photoshop course')\n"
                "- Editing software (e.g., 'photoshop training', 'premiere pro course', 'lightroom classes')\n"
                "- Editing techniques (e.g., 'color correction', 'photo manipulation', 'video effects')\n"
                "- Editing rates (e.g., 'editing charges', 'photo editing fees', 'video editing cost')\n"
                "- Editing portfolio (e.g., 'editing portfolio', 'before after photos', 'editing samples')\n"
                "- Editing turnaround (e.g., 'editing time', 'delivery time', 'editing duration')\n"
                "- Editing requirements (e.g., 'editing specifications', 'file formats', 'resolution')\n"
                "- Editing collaboration (e.g., 'editing partnership', 'work with editors', 'editing team')\n"
                "- Editing tools (e.g., 'editing software', 'editing equipment', 'editing setup')\n"
                "- Editing styles (e.g., 'editing style', 'photo style', 'video style', 'aesthetic')\n"
                "- Editing packages (e.g., 'editing packages', 'editing plans', 'editing deals')\n"
                "- Editing consultation (e.g., 'editing consultation', 'editing advice', 'editing tips')\n"
                "- Editing booking (e.g., 'book editing', 'editing appointment', 'editing schedule')\n"
                "- Job applications (e.g., 'looking for job', 'hiring', 'job opportunity', 'work opportunity')\n"
                "- Collaboration requests (e.g., 'collaboration', 'collab', 'work together', 'partnership')\n"
                "- Artist applications (e.g., 'I am an artist', 'I am a makeup artist', 'I do makeup', 'I am a photographer')\n"
                "- Looking for artists (e.g., 'looking for artists', 'need artists', 'hiring artists', 'artist openings')\n"
                "- Assistant positions (e.g., 'assistant position', 'assistant work', 'assistant opportunity', 'makeup assistant')\n"
                "- Looking for assistants (e.g., 'looking for assistants', 'need assistant', 'hiring assistant', 'assistant vacancy')\n"
                "- Portfolio showcase (e.g., 'show my portfolio', 'my work samples', 'trial work', 'see my work')\n"
                "- Trial offers (e.g., 'do a trial', 'trial look', 'test my skills', 'sample work')\n"
                "- Work inquiries (e.g., 'do you need help', 'are you hiring', 'looking for team members', 'need someone')\n"
                "- Freelancer requests (e.g., 'freelance work', 'freelance opportunity', 'freelance artist', 'freelance photographer')\n"
                "- Team member inquiries (e.g., 'join your team', 'work with you', 'be part of team', 'work in your team')\n"
                "- Vendor inquiries (e.g., 'vendor details', 'vendor contact', 'vendor information', 'vendor requirements')\n"
                "- Professional networking (e.g., 'connect professionally', 'professional opportunity', 'career opportunity')\n"
                "- Skill showcase (e.g., 'my skills', 'what I can do', 'my expertise', 'my experience')\n"
                "- Resume/CV sharing (e.g., 'my resume', 'my CV', 'my background', 'my qualifications')\n"
                "- Service promotions (e.g., 'book your', 'hire our', 'get your')\n"
                "- Vendor promotions (e.g., 'wedding album designer', 'event planner services', 'catering services')\n"
                "- Business advertisements (e.g., 'we provide', 'we offer', 'our services include', 'contact us for')\n"
                "- Third-party service selling (e.g., 'book designer', 'hire decorator', 'best photographer', 'top makeup artist')\n"
                "- Promotional commands (e.g., 'book now', 'call us', 'dm us', 'contact for services')\n"
                "- Service provider advertisements (e.g., 'we are photographers', 'we do makeup', 'we provide decor')\n"
                "- Choreographer inquiries (e.g., 'choreographer', 'dance choreographer', 'wedding choreographer', 'sangeet choreographer', 'choreography services')\n"
                "- Dance services (e.g., 'dance classes', 'wedding dance', 'couple dance', 'sangeet dance', 'dance performance')\n"
                "- Camera brand mentions (e.g., 'Sony', 'Canon', 'Nikon', 'Fujifilm', 'Panasonic', 'Sony camera', 'Canon camera')\n"
                "- Photography equipment (e.g., 'camera gear', 'lenses', 'camera equipment', 'photography equipment', 'camera body', 'camera lens')\n"
                "- Technical equipment queries (e.g., 'what camera do you use', 'which camera', 'camera model', 'gear details')\n\n"
                "Return { \"result\": false } if the message is about:\n"
                "- Event services (e.g., 'wedding makeup', 'bridal makeup', 'party makeup')\n"
                "- Service bookings (e.g., 'book for wedding', 'makeup for event')\n"
                "- General greetings (e.g., 'hi', 'hello', 'good morning')\n"
                "- Pricing for services (e.g., 'makeup charges', 'service rates')\n"
                "- Customer booking inquiries (e.g., 'how do I book', 'how to book', 'how can I book', 'how do I book your service', 'how to book your service')\n"
                "- Availability for events (e.g., 'available for wedding', 'free on date')\n"
                "- Event details (e.g., 'wedding date', 'event venue')\n"
                "- Personal consultations (e.g., 'consultation', 'meeting')\n"
            )

            logger.info(f"Checking course/class/model/editing enquiry for message: {message[:100]}...")
            
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
            logger.info(f"Course/class/model/editing enquiry AI response: {ai_response}")
            
            # Extract JSON result
            start = ai_response.find('{')
            end = ai_response.rfind('}') + 1
            if start == -1 or end == -1:
                raise ValueError("No valid JSON in AI response")

            parsed = json.loads(ai_response[start:end])
            result = parsed.get("result", False)
            
            if result:
                logger.info(f"✅ Message identified as course/class/model/editing enquiry")
            else:
                logger.info(f"❌ Message is NOT a course/class/model/editing enquiry")
                
            return result

        except Exception as e:
            logger.error(f"❌ Error in is_course_or_class_enquiry: {e}")
            return False

    def _save_conversation_to_db(self, instagram_user_id: int, deal_id: int, 
                               user_message: str, bot_response: str, 
                               extracted_data: Dict[str, Any]) -> bool:
        """Save conversation to database using repository pattern."""
        try:
            from repository.conversation_repository import ConversationRepository
            
            # Get or create conversation summary
            summary = ConversationRepository.get_conversation_summary_by_deal_id(deal_id)
            
            if not summary:
                # Create new summary record
                summary = ConversationRepository.create_conversation_summary(
                    instagram_username=extracted_data.get('instagram_username', f"user_{instagram_user_id}"),
                    instagram_user_id=instagram_user_id,
                    deal_id=deal_id
                )
            
            # Update conversation summary
            new_summary = str(summary.deals_conversation_summary or "") + "\n" + extracted_data.get('conversation_summary', '')
            
            # Add email information to summary if provided
            if extracted_data.get('phone_number', '') and '@' in extracted_data.get('phone_number', ''):
                new_summary += f"\n[Email provided as contact method: {extracted_data.get('phone_number', '')}]"
            
            if new_summary:
                success = ConversationRepository.update_conversation_summary(
                    instagram_user_id=instagram_user_id,
                    deal_id=deal_id,
                    new_summary=new_summary
                )
                if not success:
                    logger.error(f"❌ Failed to update conversation summary for Instagram user {instagram_user_id}")
                else:
                    logger.info(f"✅ Conversation saved to database for Instagram user {instagram_user_id}")
                
        except Exception as e:
            logger.error(f"❌ Error saving conversation to database: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

