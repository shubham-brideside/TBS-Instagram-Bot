import json
import re
import traceback
from flask import request

# 🚨 ESSENTIAL DETAILS RULE: If ALL required fields (event_date, venue, phone_number) 
# already exist in the deal, the bot will NOT send any reply and will NOT call the AI service.
# This rule applies to ALL clients automatically without needing prompt modifications.
from config import DEEPSEEK_API_KEY, GROQ_API_KEY, GROQ_MODEL, IG_ACCOUNT_ID, OPENAI_API_KEY, OPENAI_MODEL
from models import brideside_user
from models.brideside_user import BridesideUser
from models.deal import Deal
from models.processed_message import ProcessedMessage
from repository.conversation_repository import ConversationRepository
from repository.deal_repository import update_deal_fields, update_deal_fields_force, get_deal_by_id
from services.instagram_service import send_instagram_message, get_instagram_username, checkIfUserIsAlreadyContactedOrFriend, send_initial_greetings_message
from services.pipedrive_service import (
    create_pipedrive_contact,
    create_pipedrive_deal,
    update_pipedrive_contact_fields,
    update_pipedrive_deal_fields
)
from utils.validators import is_valid_phone_number
from repository.brideside_user_repository import (
    get_brideside_user_by_username,
    get_brideside_user_by_ig_account_id,
    is_sender_a_brideside_user,
    get_instagram_credentials_by_account_id
)
from repository.instagram_user_repository import is_user_present, create_instagram_user
from repository.contact_repository import create_contact_entry, get_contact_id_by_username
from repository.deal_repository import deal_exists, create_deal, get_deal_by_user_name, update_deal_fields, update_deal_fields_force
from repository.processed_message_repository import is_message_processed, mark_message_as_processed, cleanup_old_processed_messages
from utils.logger import logger
from services.ai_service_factory import AIServiceFactory
from dateutil import parser as date_parser
from datetime import datetime
from zoneinfo import ZoneInfo


def _handle_get_request() -> tuple[str, int]:
    """Handle GET requests for webhook verification."""
    hub_challenge = request.args.get("hub.challenge")
    return (hub_challenge if hub_challenge else "Webhook endpoint."), 200


def _validate_webhook_data(data: dict) -> tuple[bool, str]:
    """Validate webhook data structure."""
    if "entry" not in data or not data["entry"]:
        return False, "No entry"
    
    entry = data.get("entry", [])[0]
    if "messaging" not in entry or not entry["messaging"]:
        return False, "No messaging"
    
    messaging_event = entry["messaging"][0]
    
    if "message" not in messaging_event or not messaging_event["message"]:
        return False, "No message"
    
    return True, ""


def _should_skip_message(sender_id: str, recipient_id: str, message_text: str, message: dict) -> tuple[bool, str]:
    """Check if message should be skipped based on various criteria."""
    if sender_id == IG_ACCOUNT_ID:
        return True, "Ignored self message"
    
    # Check if sender is a brideside user (bride sending message)
    if is_sender_a_brideside_user(sender_id):
        return True, "Ignored message from brideside user"
    
    if not message_text:
        return True, "Skipping non-text message"
    
    # Create a basic AI service instance for utility functions
    from services.ai_service_factory import AIServiceFactory
    basic_service_config = {
        'service_name': 'openai',
        'api_key': OPENAI_API_KEY or "",
        'model': OPENAI_MODEL or "gpt-4o-mini",
        'brideside_user_id': 1,
        'business_name': "",
        'services': []
    }
    ai_service = AIServiceFactory.get_service_by_config(basic_service_config)
    
    # Check for story reply with emoji
    if "reply_to" in message and "story" in message["reply_to"]:
        return True, "Skipping story reply"
    
    # Check for collab/advertisement
    if ai_service.is_collab_or_advertisement(message_text):
        return True, "Skipping collab/ad"
    
    brideside_user = get_brideside_user_by_ig_account_id(recipient_id)

    insta_user =get_instagram_username(sender_id,brideside_user.access_token,brideside_user.id)
    instagram_user_present = is_user_present(insta_user)
    
    # Check if user is already in course_related_users table
    from repository.course_related_user_repository import is_course_related_user, create_course_related_user
    if is_course_related_user(insta_user):
        return True, "Skipping message from course-related user"
    
    # Check for course/class enquiry regardless of user presence
    try:
        is_course_enquiry = ai_service.is_course_or_class_enquiry(message_text)
        if is_course_enquiry:
            # Store the user in course_related_users table
            create_course_related_user(insta_user, brideside_user.id)
            return True, "Skipping message is related to course or class enquiry"
    except Exception as e:
        logger.error(f"❌ Error during course enquiry check: {e}")
        # Continue with normal processing if course check fails
    
    if not instagram_user_present:
        if ai_service.is_message_not_related_to_provided_service(message_text, brideside_user.services):
            return True, "Skipping message not related to provided service"
    return False, ""


def _validate_and_format_date(date_str: str) -> str:
    """Validate and format date string to YYYY-MM-DD format or return empty string if invalid."""
    if not date_str or not date_str.strip():
        return ""
    
    date_str = date_str.strip()
    
    # If date is already in YYYY-MM-DD format, return as is
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # If date contains text like "30th July" without year, return empty (invalid)
    if re.search(r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b', date_str, re.IGNORECASE):
        if not re.search(r'\b20\d{2}\b', date_str):
            logger.warning(f"⚠️ Date without year detected, rejecting: {date_str}")
            return ""  # Don't allow dates without years
    
    # If date looks like "2024-07-26" or similar valid formats, allow it
    try:
        from datetime import datetime
        # Try to parse various formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d %B %Y',      # 30 July 2025
            '%dth %B %Y',    # 30th July 2025
            '%dst %B %Y',    # 1st July 2025
            '%dnd %B %Y',    # 2nd July 2025
            '%drd %B %Y',    # 3rd July 2025
            '%d %b %Y',      # 30 Jul 2025
            '%dth %b %Y',    # 30th Jul 2025
            '%dst %b %Y',    # 1st Jul 2025
            '%dnd %b %Y',    # 2nd Jul 2025
            '%drd %b %Y',    # 3rd Jul 2025
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Fallback: Use dateutil.parser for natural language dates
        try:
            parsed_date = date_parser.parse(date_str, fuzzy=False)
            # Only accept if year is 2020 or later (reasonable for wedding dates)
            if parsed_date.year >= 2020:
                return parsed_date.strftime('%Y-%m-%d')
            else:
                logger.warning(f"⚠️ Date year too old, rejecting: {date_str}")
                return ""
        except Exception:
            pass
        
        # If no format worked, reject the date
        logger.warning(f"⚠️ Invalid date format, rejecting: {date_str}")
        return ""
        
    except Exception as e:
        logger.warning(f"⚠️ Error validating date '{date_str}': {e}")
        return ""


def _reset_contact_number_asked_flag(deal_id: int) -> None:
    """Reset the contact_number_asked flag when phone number is provided"""
    try:
        update_deal_fields(deal_id, contact_number_asked=False)
        logger.info("✅ Reset contact_number_asked flag to False for deal %s", deal_id)
    except Exception as e:
        logger.error("❌ Error resetting contact_number_asked flag: %s", e)

def _reset_event_date_asked_flag(deal_id: int) -> None:
    """Reset the event_date_asked flag when event date is provided"""
    try:
        update_deal_fields(deal_id, event_date_asked=False)
        logger.info("✅ Reset event_date_asked flag to False for deal %s", deal_id)
    except Exception as e:
        logger.error("❌ Error resetting event_date_asked flag: %s", e)

def _reset_venue_asked_flag(deal_id: int) -> None:
    """Reset the venue_asked flag when venue is provided"""
    try:
        update_deal_fields(deal_id, venue_asked=False)
        logger.info("✅ Reset venue_asked flag to False for deal %s", deal_id)
    except Exception as e:
        logger.error("❌ Error resetting venue_asked flag: %s", e)

def _smart_clean_message(message: str, missing_fields: list) -> str:
    """Remove fields from message that were already provided by user"""
    smart_message = message
    
    # If event date was provided, remove event date request from message
    if 'event_date' not in missing_fields and ('event date' in smart_message.lower() or 'date' in smart_message.lower()):
        # Remove event date related text from the message
        smart_message = smart_message.replace('event date, ', '').replace('event date and ', '').replace('event date', '')
        smart_message = smart_message.replace('date, ', '').replace('date and ', '').replace('date', '')
        # Clean up any double commas or "and" issues
        smart_message = smart_message.replace(', ,', ',').replace('and ,', 'and').replace(', and', ',')
        smart_message = smart_message.replace('  ', ' ').strip()
        logger.info("🔧 Removed event date request from message since it was already provided")
    
    # If venue was provided, remove venue request from message
    if 'venue' not in missing_fields and ('venue' in smart_message.lower() or 'location' in smart_message.lower()):
        smart_message = smart_message.replace('venue, ', '').replace('venue and ', '').replace('venue', '')
        smart_message = smart_message.replace('location, ', '').replace('location and ', '').replace('location', '')
        # Clean up any double commas or "and" issues
        smart_message = smart_message.replace(', ,', ',').replace('and ,', 'and').replace(', and', ',')
        smart_message = smart_message.replace('  ', ' ').strip()
        logger.info("🔧 Removed venue request from message since it was already provided")
    
    # If phone number was provided, remove phone number request from message
    if 'phone_number' not in missing_fields and ('phone' in smart_message.lower() or 'contact' in smart_message.lower() or 'number' in smart_message.lower()):
        smart_message = smart_message.replace('contact number, ', '').replace('contact number and ', '').replace('contact number', '')
        smart_message = smart_message.replace('phone number, ', '').replace('phone number and ', '').replace('phone number', '')
        smart_message = smart_message.replace('phone, ', '').replace('phone and ', '').replace('phone', '')
        smart_message = smart_message.replace('contact, ', '').replace('contact and ', '').replace('contact', '')
        # Clean up any double commas or "and" issues
        smart_message = smart_message.replace(', ,', ',').replace('and ,', 'and').replace(', and', ',')
        smart_message = smart_message.replace('  ', ' ').strip()
        logger.info("🔧 Removed contact number request from message since it was already provided")
    
    return smart_message

def _get_missing_fields_from_deal(deal) -> list[str]:
    """Get list of fields that are null in the deal object."""
    missing_fields = []
    
    # Check each REQUIRED field and add to missing_fields if it's None or empty
    # Note: full_name and event_type are NOT required fields - they are set automatically
    if not deal.event_date:
        missing_fields.append('event_date')
    
    if not deal.venue or str(deal.venue).strip() == "":
        missing_fields.append('venue')
    
    if not deal.phone_number or str(deal.phone_number).strip() == "":
        missing_fields.append('phone_number')
    
    return missing_fields


def _get_changed_fields_from_deal(deal, extracted_fields: dict) -> dict:
    """Compare extracted fields with existing deal fields and return only changed fields."""
    changed_fields = {}
    
    # Check each extracted field against existing deal field
    for field_name, new_value in extracted_fields.items():
        if not new_value or not new_value.strip():
            continue  # Skip empty values
            
        # Get current value from deal
        current_value = getattr(deal, field_name, None)
        current_value_str = str(current_value).strip() if current_value else ""
        new_value_str = str(new_value).strip()
        
        # Compare values (case-insensitive for strings)
        if field_name == 'event_date':
            # For dates, handle different formats
            if current_value_str.lower() != new_value_str.lower():
                logger.info(f"🔄 Field '{field_name}' changed: '{current_value_str}' → '{new_value_str}'")
                changed_fields[field_name] = new_value
            else:
                logger.info(f"✓ Field '{field_name}' unchanged: '{current_value_str}'")
        else:
            # For other fields, do case-insensitive comparison
            if current_value_str.lower() != new_value_str.lower():
                logger.info(f"🔄 Field '{field_name}' changed: '{current_value_str}' → '{new_value_str}'")
                changed_fields[field_name] = new_value
            else:
                logger.info(f"✓ Field '{field_name}' unchanged: '{current_value_str}'")
                
    return changed_fields


def _handle_user_message_flow(message_text: str, sender_username: str, brideside_user: BridesideUser, recipient_id: str, sender_id: str, message_id: str) -> tuple[bool, str]:
    """
    Handle user message flow by creating contact and deal as needed.
    
    🚨 ESSENTIAL DETAILS RULE: If ALL required fields (event_date, venue, phone_number)
    already exist in the deal, this function will return early without calling the AI service or sending any message.
    This ensures that once all essential details are collected, the bot stops responding.
    This rule applies to ALL clients automatically without needing prompt modifications.
    """
    # Initialize AI services
    default_service_config = {
        'service_name': 'openai',
        'api_key': OPENAI_API_KEY or "",
        'model': OPENAI_MODEL or "gpt-4o-mini",
        'brideside_user_id': brideside_user.id,
        'business_name': brideside_user.business_name or "",
        'services': brideside_user.services or []
    }

    ai_service = AIServiceFactory.get_service_by_config(default_service_config)
    # Extract access token from user object
    access_token = brideside_user.access_token or ""
    
    user_already_contacted = checkIfUserIsAlreadyContactedOrFriend(sender_id, access_token, brideside_user.id)
    if user_already_contacted:
        logger.info("User %s has already been contacted before or a friend. Skipping.", sender_username)
        return False, "User already contacted before"
    
    logger.info("User %s is not already contacted or a friend. Checking if user already exists.", sender_username)
    
    # Check if user already exists
    user_already_present = is_user_present(sender_username)
    if user_already_present:
        deal = get_deal_by_user_name(sender_username, brideside_user.id)
        if deal:
            logger.info("deal %s is already present in the database and contacted by the same brideside user %s", sender_username, brideside_user.username)
            
            # 🔧 CRITICAL FIX: Always refresh deal from database to get latest field values
            deal = get_deal_by_user_name(sender_username, brideside_user.id)
            logger.info("🔄 Refreshed deal object to get latest field values")
            
            missing_fields = _get_missing_fields_from_deal(deal)
            logger.info("Missing fields for user %s: %s", sender_username, missing_fields)
            
            # 🚨 ESSENTIAL DETAILS CHECK - NO REPLY IF ALL REQUIRED FIELDS ARE COLLECTED
            required_fields = ['event_date', 'venue', 'phone_number']
            missing_required_fields = [field for field in required_fields if field in missing_fields]
            
            if not missing_required_fields:
                logger.info("🚨 All essential details (Event Date, Venue, Phone Number) already collected for %s.", sender_username)
                
                # Check if final thank you message has been sent
                final_thank_you_sent = getattr(deal, 'final_thank_you_sent', False)
                
                if not final_thank_you_sent:
                    logger.info("📧 Final thank you message not sent yet. Sending final thank you message and marking as sent.")
                    
                    # Send final thank you message
                    final_message = "Thank you for sharing all the details! will connect shortly!"
                    send_instagram_message(
                        brideside_user=brideside_user,
                        message_id=message_id, 
                        sender_username=sender_username, 
                        sender_id=sender_id, 
                        message=final_message, 
                        access_token=access_token, 
                        user_id=brideside_user.id
                    )
                    logger.info("✅ Sent final thank you message to %s", sender_username)
                    
                    # Mark final thank you as sent
                    update_success = update_deal_fields(deal.id, final_thank_you_sent=True)
                    if update_success:
                        logger.info("✅ Marked final_thank_you_sent as True for %s", sender_username)
                    else:
                        logger.error("❌ Failed to mark final_thank_you_sent as True for %s", sender_username)
                    
                    return True, "Processed - Final thank you message sent"
                else:
                    logger.info("📧 Final thank you message already sent to %s. No message will be sent.", sender_username)
                    return True, "Processed - No message sent (final thank you already sent)"
            else:
                logger.info("📝 Missing required fields for %s: %s. Continuing with AI service.", sender_username, missing_required_fields)
            
            # Get conversation summary from conversation repository
            conversation_summary = ConversationRepository.get_conversation_summary_by_deal_id(deal.id)  # type: ignore
            
            # Prepare current deal data for AI service
            current_deal_data = {
                'full_name': str(deal.full_name) if deal.full_name is not None else "",
                'event_type': str(deal.event_type) if deal.event_type is not None else "",
                'event_date': str(deal.event_date) if deal.event_date is not None else "",
                'venue': str(deal.venue) if deal.venue is not None else "",
                'phone_number': str(deal.phone_number) if deal.phone_number is not None else ""
            }
            
            # Pass empty missing_fields list to use regular prompt if all fields are collected
            response = ai_service.get_response_with_json(
                user_message=message_text,
                user_id=brideside_user.id,
                instagram_user_id=user_already_present.id,
                instagram_username=sender_username,
                deal_id=deal.id,
                missing_fields=missing_fields,  # Empty list will trigger regular prompt
                previous_conversation_summary=conversation_summary.deals_conversation_summary if conversation_summary else "",
                current_deal_data=current_deal_data
            )

            
            
            logger.info("Response content: %s", response)
            
            # Ensure response is a dictionary and has the expected key
            if isinstance(response, dict) and 'message_to_be_sent' in response:
                message_to_send = response['message_to_be_sent']
                
                # Extract additional response fields for existing user flow
                contains_structured_data = response.get('contains_structured_data', False)
                contains_valid_query = response.get('contains_valid_query', False)
                is_greeting_message = response.get('is_greeting_message', False)
                
                
                # Refresh deal object to get latest flag values
                deal = get_deal_by_id(deal.id)
                if not deal:
                    logger.error("❌ Failed to refresh deal object after flag updates")
                    return False, "Failed to refresh deal object"
                
                # 🚨 FLAG REFUSAL LOGIC - Check all flags and send message if any flag changes
                contact_number_asked = getattr(deal, 'contact_number_asked', False)
                event_date_asked = getattr(deal, 'event_date_asked', False)
                venue_asked = getattr(deal, 'venue_asked', False)
                logger.info("🔍 DEBUG: contact_number_asked = %s, event_date_asked = %s, venue_asked = %s, missing_fields = %s", 
                           contact_number_asked, event_date_asked, venue_asked, missing_fields)
                
                # Check if any flags are True and user was asked for something
                any_flag_asked = contact_number_asked or event_date_asked or venue_asked
                
                if any_flag_asked:
                    # Check what user provided in this message
                    phone_number_provided = response.get('phone_number', '').strip()
                    event_date_provided = response.get('event_date', '').strip()
                    venue_provided = response.get('venue', '').strip()
                    
                    # Track which flags will be reset
                    flags_to_reset = []
                    
                    # Check if user provided event date and reset flag
                    if event_date_asked and event_date_provided and 'event_date' in missing_fields:
                        flags_to_reset.append('event_date_asked')
                        logger.info("📅 User provided event date - will reset event_date_asked flag to False")
                    
                    # Check if user provided venue and reset flag
                    if venue_asked and venue_provided and 'venue' in missing_fields:
                        flags_to_reset.append('venue_asked')
                        logger.info("🏢 User provided venue - will reset venue_asked flag to False")
                    
                    # Check if user provided phone number and reset flag
                    if contact_number_asked and phone_number_provided and 'phone_number' in missing_fields:
                        flags_to_reset.append('contact_number_asked')
                        logger.info("📞 User provided phone number - will reset contact_number_asked flag to False")
                    
                    # If any flags will be reset, send the message
                    if flags_to_reset:
                        logger.info("✅ User provided information - flags will be reset: %s. Message will be sent.", flags_to_reset)
                        # Continue with normal flow to send the message
                    else:
                        # No flags will be reset, check if we should block the message
                        if contact_number_asked and 'phone_number' in missing_fields and not phone_number_provided:
                            logger.info("🚫 User was asked for contact number but didn't provide it. No message will be sent.")
                            
                            # 🔧 CRITICAL FIX: Still save extracted fields even when phone number is not provided
                            extracted_fields = {
                                'full_name': response.get('full_name', ''),
                                'event_type': response.get('event_type', ''),
                                'event_date': _validate_and_format_date(response.get('event_date', '')),
                                'venue': response.get('venue', ''),
                                'phone_number': response.get('phone_number', '')
                            }
                            
                            # Check for changed fields (comparing with existing deal data)
                            changed_fields = _get_changed_fields_from_deal(deal, extracted_fields)
                            
                            # Also include fields that are missing (empty in deal but provided now)
                            missing_field_updates = {k: v for k, v in extracted_fields.items() 
                                                   if v and v.strip() and k in missing_fields}
                            
                            # Include any extracted fields from fallback responses (when AI fails to parse JSON)
                            fallback_extracted_fields = {k: v for k, v in extracted_fields.items() 
                                                       if v and v.strip() and k not in changed_fields and k not in missing_field_updates}
                            
                            # Combine all field updates
                            fields_to_update = {**changed_fields, **missing_field_updates, **fallback_extracted_fields}
                            
                            # Log summary of what's happening
                            if changed_fields:
                                logger.info("🔄 Changed fields detected: %s", list(changed_fields.keys()))
                            if missing_field_updates:
                                logger.info("➕ New fields filled: %s", list(missing_field_updates.keys()))
                            
                            # Update database with extracted fields
                            if fields_to_update:
                                logger.info("Updating deal %s with extracted fields (no message sent): %s", deal.id, fields_to_update)
                                update_success = update_deal_fields(deal.id, **fields_to_update)
                                if update_success:
                                    logger.info("✅ Successfully updated local deal fields (no message sent)")
                            
                            # Update conversation summary but don't send any message
                            conversation_summary_text = response.get('conversation_summary', '')
                            if conversation_summary_text and deal.pipedrive_deal_id is not None:
                                update_pipedrive_deal_fields(deal.pipedrive_deal_id, conversation_summary=conversation_summary_text)
                            
                            return True, "Contact number requested but not provided - no message sent"
                        elif event_date_asked and 'event_date' in missing_fields and not event_date_provided:
                            logger.info("🚫 User was asked for event date but didn't provide it. No message will be sent.")
                            return True, "Event date requested but not provided - no message sent"
                        elif venue_asked and 'venue' in missing_fields and not venue_provided:
                            logger.info("🚫 User was asked for venue but didn't provide it. No message will be sent.")
                            return True, "Venue requested but not provided - no message sent"
                
                
                # Check if we should send no message (all details collected)
                if message_to_send == "NO_MESSAGE":
                    logger.info("All details collected for %s or the message does not related to wedding queries. No message will be sent.", sender_username)
                    
                    # Still update conversation summary in Pipedrive
                    conversation_summary_text = response.get('conversation_summary', '')
                    if conversation_summary_text and deal.pipedrive_deal_id is not None:
                        update_pipedrive_deal_fields(
                            deal.pipedrive_deal_id,  # type: ignore
                            conversation_summary=conversation_summary_text
                        )
                        logger.info("✅ Updated Pipedrive deal with conversation summary only")
                        # Update or create conversation summary in DB
                        summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal))
                        if summary:
                            # Use the new summary directly since it already contains the full conversation history
                            # The AI service already has access to the previous summary and includes it in its response
                            combined_summary = conversation_summary_text.strip()
                            
                            ConversationRepository.update_conversation_summary(
                                instagram_user_id=to_int(summary.instagram_user_id),
                                deal_id=to_int(deal),
                                new_summary=combined_summary
                            )
                            logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal)} | summary='{combined_summary}'")
                        else:
                            ConversationRepository.create_conversation_summary(
                                instagram_username=sender_username,
                                instagram_user_id=to_int(user_already_present),
                                deal_id=to_int(deal),
                                conversation_summary=conversation_summary_text
                            )
                            logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                    
                    return True, "Processed - No message sent (all details collected)"
                
                # Get conversation summary to send to Pipedrive
                conversation_summary_text = response.get('conversation_summary', '')
                
                # Update deal fields with extracted information
                extracted_fields = {
                    'full_name': response.get('full_name', ''),
                    'event_type': response.get('event_type', ''),
                    'event_date': _validate_and_format_date(response.get('event_date', '')),
                    'venue': response.get('venue', ''),
                    'phone_number': response.get('phone_number', '')
                }
                
                # Check for changed fields (comparing with existing deal data)
                changed_fields = _get_changed_fields_from_deal(deal, extracted_fields)
                
                # Also include fields that are missing (empty in deal but provided now)
                missing_field_updates = {k: v for k, v in extracted_fields.items() 
                                       if v and v.strip() and k in missing_fields}
                
                # Include any extracted fields from fallback responses (when AI fails to parse JSON)
                fallback_extracted_fields = {k: v for k, v in extracted_fields.items() 
                                           if v and v.strip() and k not in changed_fields and k not in missing_field_updates}
                
                # Combine all field updates
                fields_to_update = {**changed_fields, **missing_field_updates, **fallback_extracted_fields}
                
                # Log fallback extractions
                if fallback_extracted_fields:
                    logger.info("🔧 Fallback extracted fields: %s", list(fallback_extracted_fields.keys()))
                
                # Log summary of what's happening
                if changed_fields:
                    logger.info("🔄 Changed fields detected: %s", list(changed_fields.keys()))
                if missing_field_updates:
                    logger.info("➕ New fields filled: %s", list(missing_field_updates.keys()))
                
                if fields_to_update:
                    # Check if deal is valid before proceeding
                    if deal is None:
                        logger.error("❌ Deal is None, cannot update deal fields. Skipping update.")
                        return False, "Failed - Deal object is None"
                        
                    logger.info("Updating deal %s with changed/new fields: %s", deal.id, fields_to_update)  # type: ignore
                    
                    # Update local database - use force update if no missing fields (user update request)
                    if not missing_fields:  # No missing fields = user update request, overwrite existing values
                        logger.info("🔄 Using force update for user change request")
                        update_success = update_deal_fields_force(deal.id, **fields_to_update)  # type: ignore
                    else:  # Missing fields = initial data collection, only fill empty fields
                        logger.info("📝 Using regular update for data collection")
                        update_success = update_deal_fields(deal.id, **fields_to_update)  # type: ignore
                    if update_success:
                        logger.info("✅ Successfully updated local deal fields")
                        
                        # 🔧 CRITICAL FIX: Refresh deal object from database to get latest values
                        deal = get_deal_by_user_name(sender_username, brideside_user.id)
                        logger.info("🔄 Refreshed deal object from database after update")
                        # Recalculate missing_fields after refresh
                        updated_missing_fields = _get_missing_fields_from_deal(deal)
                        logger.info("[AFTER UPDATE] Missing fields for user %s: %s", sender_username, updated_missing_fields)
                        
                        # 🚨 CRITICAL: If missing_fields changed from non-empty to empty, override AI response
                        if missing_fields and not updated_missing_fields:
                            logger.info("🎯 ALL FIELDS NOW COMPLETE! Overriding AI response with final thank you message")
                            message_to_send = ("Thank you. Will connect shortly!")
                            # Set the flag to prevent duplicate thank you messages
                            try:
                                update_deal_fields_force(to_int(deal_id), final_thank_you_sent=True)  # type: ignore
                                logger.info("✅ Set final_thank_you_sent=True for completed deal")
                            except Exception:
                                pass
                        
                        # Update missing_fields for any further processing
                        missing_fields = updated_missing_fields
                        
                        # Update Pipedrive contact if name or phone is updated
                        if 'full_name' in fields_to_update or 'phone_number' in fields_to_update:
                            pipedrive_contact_id = get_contact_id_by_username(sender_username)
                            if pipedrive_contact_id is not None:  # type: ignore
                                update_pipedrive_contact_fields(
                                    pipedrive_contact_id,
                                    instagram_username=sender_username,
                                    phone=fields_to_update.get('phone_number')
                                )
                                logger.info("✅ Updated Pipedrive contact")
                            
                            # 🚨 RESET CONTACT_NUMBER_ASKED FLAG
                            # If phone number was provided, reset the contact_number_asked flag
                            if 'phone_number' in fields_to_update:
                                logger.info("📞 Phone number provided - resetting contact_number_asked flag to False")
                                _reset_contact_number_asked_flag(deal.id)
                            
                            # If event date was provided, reset the event_date_asked flag
                            if 'event_date' in fields_to_update:
                                logger.info("📅 Event date provided - resetting event_date_asked flag to False")
                                _reset_event_date_asked_flag(deal.id)
                            
                            # If venue was provided, reset the venue_asked flag
                            if 'venue' in fields_to_update:
                                logger.info("🏢 Venue provided - resetting venue_asked flag to False")
                                _reset_venue_asked_flag(deal.id)
                        else:
                            logger.warning("⚠️ Could not find Pipedrive contact ID for user")
                        
                        # Update Pipedrive deal if other fields are updated
                        deal_fields_to_update = {k: v for k, v in fields_to_update.items() 
                                               if k in ['event_type', 'event_date', 'venue']}
                        # type: ignore[misc]
                        if deal_fields_to_update and deal.pipedrive_deal_id is not None:
                            update_pipedrive_deal_fields(
                                deal.pipedrive_deal_id,  # type: ignore
                                event_type=deal_fields_to_update.get('event_type'),
                                event_date=deal_fields_to_update.get('event_date'),
                                venue=deal_fields_to_update.get('venue'),
                                conversation_summary=conversation_summary_text,
                                full_name=fields_to_update.get('full_name'),
                                phone=fields_to_update.get('phone_number')
                            )
                            logger.info("✅ Updated Pipedrive deal with fields and conversation summary")
                            # Update or create conversation summary in DB
                            summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal))
                            if summary:
                                ConversationRepository.update_conversation_summary(
                                    instagram_user_id=to_int(summary.instagram_user_id),
                                    deal_id=to_int(deal),
                                    new_summary=conversation_summary_text
                                )
                                logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                            else:
                                ConversationRepository.create_conversation_summary(
                                    instagram_username=sender_username,
                                    instagram_user_id=to_int(user_already_present),
                                    deal_id=to_int(deal),
                                    conversation_summary=conversation_summary_text
                                )
                                logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                        elif deal.pipedrive_deal_id is not None and conversation_summary_text:
                            # Update only conversation summary if no other fields
                            update_pipedrive_deal_fields(
                                deal.pipedrive_deal_id,  # type: ignore
                                conversation_summary=conversation_summary_text,
                                full_name=fields_to_update.get('full_name'),
                                phone=fields_to_update.get('phone_number')
                            )
                            logger.info("✅ Updated Pipedrive deal with conversation summary")
                            # Update or create conversation summary in DB
                            summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal))
                            if summary:
                                ConversationRepository.update_conversation_summary(
                                    instagram_user_id=to_int(summary.instagram_user_id),
                                    deal_id=to_int(deal),
                                    new_summary=conversation_summary_text
                                )
                                logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                            else:
                                ConversationRepository.create_conversation_summary(
                                    instagram_username=sender_username,
                                    instagram_user_id=to_int(user_already_present),
                                    deal_id=to_int(deal),
                                    conversation_summary=conversation_summary_text
                                )
                                logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                    else:
                        logger.warning("⚠️ Failed to update local deal fields")
                elif conversation_summary_text and deal.pipedrive_deal_id is not None:
                    # Update Pipedrive with conversation summary even if no other fields extracted
                    update_pipedrive_deal_fields(
                        deal.pipedrive_deal_id,  # type: ignore
                        conversation_summary=conversation_summary_text
                    )
                    logger.info("✅ Updated Pipedrive deal with conversation summary only")
                    # Update or create conversation summary in DB
                    summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal))
                    if summary:
                        ConversationRepository.update_conversation_summary(
                            instagram_user_id=to_int(summary.instagram_user_id),
                            deal_id=to_int(deal),
                            new_summary=conversation_summary_text
                        )
                        logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                    else:
                        ConversationRepository.create_conversation_summary(
                            instagram_username=sender_username,
                            instagram_user_id=to_int(user_already_present),
                            deal_id=to_int(deal),
                            conversation_summary=conversation_summary_text
                        )
                        logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                else:
                    logger.info("No new fields extracted to update")
                
                # 🚨 CRITICAL FIX: If AI extracts structured data but doesn't save it, ensure data is saved
                # This handles cases where AI returns "Thank you" or other messages with structured data
                if contains_structured_data and not fields_to_update and (message_to_send == "Thank you. Will connect shortly!" or is_greeting_message):
                    logger.info("🎯 AI extracted structured data but no fields were updated - ensuring data is saved to database")
                    
                    # Extract and save the structured data
                    full_name = response.get('full_name', '')
                    event_type = response.get('event_type', '')
                    event_date = response.get('event_date', '')
                    venue = response.get('venue', '')
                    phone_number_extracted = response.get('phone_number', '')
                    
                    # Process and save the extracted data
                    thank_you_fields_to_update = {}
                    
                    if full_name:
                        thank_you_fields_to_update['full_name'] = full_name
                    if event_type:
                        thank_you_fields_to_update['event_type'] = event_type
                    if event_date:
                        thank_you_fields_to_update['event_date'] = event_date
                    if venue:
                        thank_you_fields_to_update['venue'] = venue
                    if phone_number_extracted:
                        thank_you_fields_to_update['phone_number'] = phone_number_extracted
                    
                    # Update the deal with extracted data
                    if thank_you_fields_to_update:
                        update_success = update_deal_fields(deal.id, **thank_you_fields_to_update)
                        if update_success:
                            logger.info("✅ Saved structured data from 'Thank you' response: %s", thank_you_fields_to_update)
                        else:
                            logger.error("❌ Failed to save structured data from 'Thank you' response: %s", thank_you_fields_to_update)
                    
                    # Also update conversation summary in Pipedrive
                    conversation_summary_text = response.get('conversation_summary', '')
                    if conversation_summary_text:
                        update_pipedrive_deal_fields(
                            pipedrive_deal_id,
                            conversation_summary=conversation_summary_text
                        )
                        logger.info("✅ Updated Pipedrive deal with conversation summary from 'Thank you' response")
                
                # 🚨 PROTECT: If we already set a thank you message, don't let AI override it
                if message_to_send == "Thank you. Will connect shortly!":
                    logger.info("🎯 Preserving thank you message - AI response overridden")
                    
                    # Update final_thank_you_sent flag in the database
                    try:
                        update_success = update_deal_fields(deal.id, final_thank_you_sent=True)
                        if update_success:
                            logger.info("✅ Updated final_thank_you_sent to True for deal %s", deal.id)
                        else:
                            logger.error("❌ Failed to update final_thank_you_sent for deal %s", deal.id)
                    except Exception as e:
                        logger.error("❌ Error updating final_thank_you_sent for deal %s: %s", deal.id, e)
                        
                elif message_to_send == "GREETING_WITH_DATA":
                    # Handle special case for greeting with data - send static greeting + dynamic AI message
                    logger.info("🎯 GREETING_WITH_DATA detected - sending static greeting + dynamic AI message")
                    
                    # Get the original AI response message
                    original_message = response.get('message_to_be_sent', '')
                    if original_message and original_message != "GREETING_WITH_DATA":
                        # Check if we're asking for contact number and set the flag
                        if 'phone_number' in missing_fields and 'contact number' in original_message.lower():
                            logger.info("📞 Asking for contact number in greeting - setting contact_number_asked flag to True")
                            update_deal_fields(deal.id, contact_number_asked=True)
                            logger.info("✅ Updated contact_number_asked flag to True for deal %s", deal.id)
                        
                        # Check if we're asking for event date and set the flag
                        if 'event_date' in missing_fields and ('event date' in original_message.lower() or 'date' in original_message.lower() or 'when' in original_message.lower()):
                            logger.info("📅 Asking for event date in greeting - setting event_date_asked flag to True")
                            update_deal_fields(deal.id, event_date_asked=True)
                            logger.info("✅ Updated event_date_asked flag to True for deal %s", deal.id)
                        
                        # Check if we're asking for venue and set the flag
                        if 'venue' in missing_fields and ('venue' in original_message.lower() or 'location' in original_message.lower() or 'where' in original_message.lower()):
                            logger.info("🏢 Asking for venue in greeting - setting venue_asked flag to True")
                            update_deal_fields(deal.id, venue_asked=True)
                            logger.info("✅ Updated venue_asked flag to True for deal %s", deal.id)
                        
                        # Check if we're asking for event date and set the flag
                        if 'event_date' in missing_fields and ('event date' in original_message.lower() or 'date' in original_message.lower() or 'when' in original_message.lower()):
                            logger.info("📅 Asking for event date in greeting - setting event_date_asked flag to True")
                            update_deal_fields(deal.id, event_date_asked=True)
                            logger.info("✅ Updated event_date_asked flag to True for deal %s", deal.id)
                        
                        # Check if we're asking for venue and set the flag
                        if 'venue' in missing_fields and ('venue' in original_message.lower() or 'location' in original_message.lower() or 'where' in original_message.lower()):
                            logger.info("🏢 Asking for venue in greeting - setting venue_asked flag to True")
                            update_deal_fields(deal.id, venue_asked=True)
                            logger.info("✅ Updated venue_asked flag to True for deal %s", deal.id)
                        
                        # Combine static greeting with dynamic AI message
                        # 🚨 CRITICAL FIX: Handle "Thank you. Will connect shortly!" specially to avoid double "thank you"
                        if original_message == "Thank you. Will connect shortly!":
                            combined_message = "Hello! Thanks for reaching out✨ Will connect shortly!"
                        else:
                            # 🚨 SMART FIX: Remove fields from message that were already provided by user
                            smart_message = _smart_clean_message(original_message, missing_fields)
                            combined_message = f"Hello! Thanks for reaching out✨ {smart_message}"
                        logger.info("📝 Using combined message: %s", combined_message)
                        
                        # Send the combined message
                        send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=combined_message, access_token=access_token, user_id=brideside_user.id)
                        logger.info("Sent combined greeting + AI message to %s: %s", sender_username, combined_message)
                        
                        # 🚨 CRITICAL FIX: Update final_thank_you_sent flag if sending thank you message
                        if "Thank you. Will connect shortly!" in original_message:
                            try:
                                update_success = update_deal_fields(deal.id, final_thank_you_sent=True)
                                if update_success:
                                    logger.info("✅ Updated final_thank_you_sent to True for deal %s", deal.id)
                                else:
                                    logger.error("❌ Failed to update final_thank_you_sent for deal %s", deal.id)
                            except Exception as e:
                                logger.error("❌ Error updating final_thank_you_sent for deal %s: %s", deal.id, e)
                    else:
                        # Fallback to regular greeting sequence if no AI message
                        send_initial_greetings_message(sender_id, brideside_user, message_id, sender_username, access_token, brideside_user.id)
                        logger.info("Sent initial greeting message sequence to %s (fallback)", sender_username)
                    
                    return True, "Processed - Greeting with data: combined message sent"
                else:
                    logger.info("📝 Using AI response: %s", message_to_send)
                
                # Send the message
                send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=message_to_send, access_token=access_token, user_id=brideside_user.id)
                logger.info("Sent message to %s: %s", sender_username, message_to_send)
                
                # 🚨 FLAG SETTING LOGIC - Set flags AFTER message is sent
                # 🚨 CONTACT NUMBER ASKED LOGIC
                # For existing deals, set flag when asking for contact number (regardless of greeting message status)
                if (message_to_send != "GREETING_WITH_DATA" and
                    ('phone' in message_to_send.lower() or 'contact' in message_to_send.lower() or 'number' in message_to_send.lower())):
                    if 'phone_number' in missing_fields:
                        logger.info("📞 Asking for contact number - setting contact_number_asked flag to True")
                        # Update the contact_number_asked flag in the database
                        update_deal_fields(deal.id, contact_number_asked=True)
                        logger.info("✅ Updated contact_number_asked flag to True for deal %s", deal.id)
                
                # 🚨 EVENT DATE ASKED LOGIC
                # For existing deals, set flag when asking for event date (regardless of greeting message status)
                if (message_to_send != "GREETING_WITH_DATA" and
                    ('event date' in message_to_send.lower() or 'date' in message_to_send.lower() or 'when' in message_to_send.lower())):
                    if 'event_date' in missing_fields:
                        logger.info("📅 Asking for event date - setting event_date_asked flag to True")
                        # Update the event_date_asked flag in the database
                        update_deal_fields(deal.id, event_date_asked=True)
                        logger.info("✅ Updated event_date_asked flag to True for deal %s", deal.id)
                
                # 🚨 VENUE ASKED LOGIC
                # For existing deals, set flag when asking for venue (regardless of greeting message status)
                if (message_to_send != "GREETING_WITH_DATA" and
                    ('venue' in message_to_send.lower() or 'location' in message_to_send.lower() or 'where' in message_to_send.lower())):
                    if 'venue' in missing_fields:
                        logger.info("🏢 Asking for venue - setting venue_asked flag to True")
                        # Update the venue_asked flag in the database
                        update_deal_fields(deal.id, venue_asked=True)
                        logger.info("✅ Updated venue_asked flag to True for deal %s", deal.id)
                
            else:
                logger.error("❌ Response is not a valid dictionary or missing 'message_to_be_sent' key")
                message_to_send = "Thank you for your message! Our team will get back to you soon. 🌸"
                send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=message_to_send, access_token=access_token, user_id=brideside_user.id)
                logger.info("Sent fallback message to %s: %s", sender_username, message_to_send)
        else:
            # User exists but no deal found - check if contact exists, create if needed
            logger.info("User %s exists but no deal found. Checking contacts table.", sender_username)
            
            # Check if contact exists in our database
            contact_id = get_contact_id_by_username(sender_username)
            
            if contact_id is None:
                # Contact doesn't exist, create it
                logger.info("Contact not found for %s. Creating new contact...", sender_username)
                
                # Create Pipedrive contact
                success, pipedrive_contact_id = create_pipedrive_contact(sender_username, sender_username)
                if not success:
                    logger.error("❌ Failed to create Pipedrive contact for %s.", sender_username)
                    deal_id = None
                else:
                    logger.info("✅ Created Pipedrive contact for %s with ID %s.", sender_username, pipedrive_contact_id)
                    
                    # Create local contact entry
                    create_contact_entry(sender_username, pipedrive_contact_id)
                    contact_id = pipedrive_contact_id
            else:
                logger.info("✅ Contact already exists for %s with ID %s.", sender_username, contact_id)
            
            if contact_id is not None:
                # Now create the deal using the contact_id
                logger.info("Creating Pipedrive deal for %s...", sender_username)
                business_name = brideside_user.business_name
                deal_created, pipedrive_deal_id = create_pipedrive_deal(sender_username, brideside_user.organization_id, brideside_user.pipeline_id, contact_id, business_name)
                
                if not deal_created:
                    logger.error("❌ Failed to create Pipedrive deal for %s.", sender_username)
                    deal_id = None
                else:
                    logger.info("✅ Created Pipedrive deal for %s with ID %s.", sender_username, pipedrive_deal_id)
                    deal_id = create_deal(sender_username, brideside_user.organization_id, brideside_user.pipeline_id, brideside_user.id, pipedrive_deal_id)
                    deal = get_deal_by_user_name(sender_username, brideside_user.id)  # <-- fetch the actual deal object
                    
                    # Process the message with Groq AI (same as new user flow)
                    logger.info("Analyzing initial message from %s with Groq AI...", sender_username)
                    
                    # Use AI to analyze the message and determine if it contains structured data
                    missing_fields = ['event_date', 'venue', 'phone_number']
                    
                    # Ensure we have valid IDs before proceeding
                    if deal is None or deal.id is None:
                        logger.error("❌ Invalid deal object, cannot proceed with AI analysis.")
                        return False, "Failed - Invalid deal object"
                    
                    response = ai_service.get_response_with_json(user_message = message_text, user_id = brideside_user.id, instagram_user_id = int(getattr(user_already_present, 'id', 0)), instagram_username = sender_username, deal_id = to_int(deal), missing_fields = missing_fields)
                    
                    
                    logger.info(" AI analysis response: %s", response)
                    
                    # Check if AI detected structured data in the message
                    if isinstance(response, dict):
                        contains_structured_data = response.get('contains_structured_data', False)
                        contains_valid_query = response.get('contains_valid_query', False)
                        message_to_send = response.get('message_to_be_sent', 'Thank you for your message! Our team will get back to you soon. 🌸')
                        is_greeting_message = response.get('is_greeting_message', False)
                        logger.info("is_greeting_message: %s", is_greeting_message)
                        
                        # 🚨 CONTACT NUMBER ASKED LOGIC
                        # Check if we're asking for phone number and set the flag (but NOT for greeting messages)
                        # Additional check: Don't set flag if message_to_be_sent is "GREETING_WITH_DATA" or if we're sending greeting sequence
                        if (not is_greeting_message and 
                            message_to_send != "GREETING_WITH_DATA" and
                            ('phone' in message_to_send.lower() or 'contact' in message_to_send.lower() or 'number' in message_to_send.lower())):
                            if 'phone_number' in missing_fields:
                                logger.info("📞 Asking for contact number - setting contact_number_asked flag to True")
                                # Update the contact_number_asked flag in the database
                                update_deal_fields(deal.id, contact_number_asked=True)
                                logger.info("✅ Updated contact_number_asked flag to True for deal %s", deal.id)
                        
                        # 🚨 CONTACT NUMBER REFUSAL LOGIC
                        # Check if contact_number_asked is True but user didn't provide phone number
                        contact_number_asked = getattr(deal, 'contact_number_asked', False)
                        logger.info("🔍 DEBUG: contact_number_asked = %s, missing_fields = %s", contact_number_asked, missing_fields)
                        if contact_number_asked and 'phone_number' in missing_fields:
                            # Check if user provided phone number in this message
                            phone_number_provided = response.get('phone_number', '').strip()
                            if not phone_number_provided:
                                logger.info("🚫 User was asked for contact number but didn't provide it. No message will be sent.")
                                # Update conversation summary but don't send any message
                                conversation_summary_text = response.get('conversation_summary', '')
                                if conversation_summary_text and deal.pipedrive_deal_id is not None:
                                    update_pipedrive_deal_fields(deal.pipedrive_deal_id, conversation_summary=conversation_summary_text)
                                return True, "Contact number requested but not provided - no message sent"
                        
                        # Check for special GREETING_WITH_DATA flag FIRST (before regular greeting check)
                        if message_to_send == "GREETING_WITH_DATA":
                            logger.info("Greeting with structured data detected for %s - sending greeting sequence AND storing extracted data", sender_username)
                            # First, process and store the extracted data
                            if contains_structured_data:
                                full_name = response.get('full_name', '')
                                event_type = response.get('event_type', '')
                                event_date = response.get('event_date', '')
                                venue = response.get('venue', '')
                                phone_number_extracted = response.get('phone_number', '')
                                
                                # Process and save the extracted data
                                fields_to_update = {}
                                
                                if full_name:
                                    fields_to_update['full_name'] = full_name
                                if event_type:
                                    fields_to_update['event_type'] = event_type
                                if event_date:
                                    fields_to_update['event_date'] = event_date
                                if venue:
                                    fields_to_update['venue'] = venue
                                if phone_number_extracted:
                                    fields_to_update['phone_number'] = phone_number_extracted
                                
                                # Update the deal with extracted data
                                if fields_to_update:
                                    update_success = update_deal_fields(deal.id, **fields_to_update)
                                    if update_success:
                                        logger.info("Updated deal %s with extracted data: %s", deal.id, fields_to_update)
                                    else:
                                        logger.error("Failed to update deal %s with extracted data: %s", deal.id, fields_to_update)
                                
                                # Also update conversation summary in Pipedrive
                                conversation_summary_text = response.get('conversation_summary', '')
                                if conversation_summary_text:
                                    update_pipedrive_deal_fields(
                                        pipedrive_deal_id,
                                        conversation_summary=conversation_summary_text
                                    )
                                    logger.info("✅ Updated Pipedrive deal with conversation summary")
                                    
                                    # Create conversation summary in local database
                                    summary = ConversationRepository.get_conversation_summary_by_deal_id(deal.id)
                                    if summary:
                                        ConversationRepository.update_conversation_summary(
                                            instagram_user_id=to_int(summary.instagram_user_id),
                                            deal_id=to_int(deal.id),
                                            new_summary=conversation_summary_text
                                        )
                                        logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal.id)} | summary='{conversation_summary_text}'")
                                    else:
                                        ConversationRepository.create_conversation_summary(
                                            instagram_username=sender_username,
                                            instagram_user_id=to_int(user_already_present.id),
                                            deal_id=to_int(deal.id),
                                            conversation_summary=conversation_summary_text
                                        )
                                        logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present.id)}, deal_id={to_int(deal.id)} | summary='{conversation_summary_text}'")
                            
                            # Then send the greeting sequence
                            send_initial_greetings_message(sender_id, brideside_user, message_id, sender_username, access_token, brideside_user.id)
                            logger.info("Sent initial greeting message sequence to %s with extracted data stored", sender_username)
                            return True, "Processed - Greeting with data: greeting sent and data stored"
                        
                        # Regular greeting check (only if not GREETING_WITH_DATA)
                        if is_greeting_message: 
                            logger.info("Message is just a greeting - sending initial greeting sequence")
                            send_initial_greetings_message(sender_id, brideside_user, message_id, sender_username, access_token, brideside_user.id)
                            logger.info("Sent initial greeting message sequence to %s", sender_username)
                            return True, "Processed - Initial greeting message sent"
                        # Check if we should send no message (all details collected OR unrelated query)
                        if message_to_send == "NO_MESSAGE":
                            logger.info("All details collected for %s or unrelated query. No message will be sent.", sender_username)
                            
                            # Still update conversation summary in Pipedrive if there's content
                            conversation_summary_text = response.get('conversation_summary', '')
                            if conversation_summary_text:
                                update_pipedrive_deal_fields(
                                    pipedrive_deal_id,
                                    conversation_summary=conversation_summary_text
                                )
                                logger.info("✅ Updated Pipedrive deal with conversation summary only")
                            
                            return True, "Processed - No message sent"
                        
                        # Send response if it contains valid query OR structured data
                        if contains_valid_query or contains_structured_data:
                            # Get conversation summary to send to Pipedrive
                            conversation_summary_text = response.get('conversation_summary', '')
                            
                            # Handle structured data extraction and updates
                            if contains_structured_data:
                                # Update deal fields with extracted information
                                extracted_fields = {
                                    'full_name': response.get('full_name', ''),
                                    'event_type': response.get('event_type', ''),
                                    'event_date': _validate_and_format_date(response.get('event_date', '')),
                                    'venue': response.get('venue', ''),
                                    'phone_number': response.get('phone_number', '')
                                }
                                
                                # Check for changed fields (comparing with existing deal data)
                                changed_fields = _get_changed_fields_from_deal(deal, extracted_fields)
                                
                                # Also include fields that are missing (empty in deal but provided now)
                                missing_field_updates = {k: v for k, v in extracted_fields.items() 
                                                       if v and v.strip() and k in missing_fields}
                                
                                # Include any extracted fields from fallback responses (when AI fails to parse JSON)
                                fallback_extracted_fields = {k: v for k, v in extracted_fields.items() 
                                                           if v and v.strip() and k not in changed_fields and k not in missing_field_updates}
                                
                                # Combine all field updates
                                fields_to_update = {**changed_fields, **missing_field_updates, **fallback_extracted_fields}
                                
                                # Log fallback extractions
                                if fallback_extracted_fields:
                                    logger.info("🔧 Fallback extracted fields: %s", list(fallback_extracted_fields.keys()))
                                
                                # Log summary of what's happening
                                if changed_fields:
                                    logger.info("🔄 Changed fields detected: %s", list(changed_fields.keys()))
                                if missing_field_updates:
                                    logger.info("➕ New fields filled: %s", list(missing_field_updates.keys()))
                                
                                if fields_to_update:
                                    # Check if deal is valid before proceeding
                                    if deal is None:
                                        logger.error("❌ Deal is None, cannot update deal fields. Skipping update.")
                                        return False, "Failed - Deal object is None"
                                        
                                    logger.info("Updating deal %s with changed/new fields: %s", deal.id, fields_to_update)  # type: ignore
                                    
                                    # Update local database - use force update if no missing fields (user update request)
                                    if not missing_fields:  # No missing fields = user update request, overwrite existing values
                                        logger.info("🔄 Using force update for user change request")
                                        update_success = update_deal_fields_force(deal.id, **fields_to_update)  # type: ignore
                                    else:  # Missing fields = initial data collection, only fill empty fields
                                        logger.info("📝 Using regular update for data collection")
                                        update_success = update_deal_fields(deal.id, **fields_to_update)  # type: ignore
                                    
                                    if update_success:
                                        logger.info("✅ Successfully updated local deal fields")
                                        
                                        # 🔧 CRITICAL FIX: Refresh deal object from database to get latest values
                                        deal = get_deal_by_user_name(sender_username, brideside_user.id)
                                        logger.info("🔄 Refreshed deal object from database after update")
                                        
                                        # Update Pipedrive contact if name or phone is updated
                                        if 'full_name' in fields_to_update or 'phone_number' in fields_to_update:
                                            pipedrive_contact_id = get_contact_id_by_username(sender_username)
                                            if pipedrive_contact_id is not None:  # type: ignore
                                                update_pipedrive_contact_fields(
                                                    pipedrive_contact_id,
                                                    instagram_username=sender_username,
                                                    phone=fields_to_update.get('phone_number')
                                                )
                                                logger.info("✅ Updated Pipedrive contact")
                                            
                                            # 🚨 RESET CONTACT_NUMBER_ASKED FLAG
                                            if 'phone_number' in fields_to_update:
                                                logger.info("📞 Phone number provided - resetting contact_number_asked flag to False")
                                                _reset_contact_number_asked_flag(deal.id)
                                            
                                            # If event date was provided, reset the event_date_asked flag
                                            if 'event_date' in fields_to_update:
                                                logger.info("📅 Event date provided - resetting event_date_asked flag to False")
                                                _reset_event_date_asked_flag(deal.id)
                                            
                                            # If venue was provided, reset the venue_asked flag
                                            if 'venue' in fields_to_update:
                                                logger.info("🏢 Venue provided - resetting venue_asked flag to False")
                                                _reset_venue_asked_flag(deal.id)
                                            else:
                                                logger.warning("⚠️ Could not find Pipedrive contact ID for user")
                                        
                                        # Update Pipedrive deal if other fields are updated
                                        deal_fields_to_update = {k: v for k, v in fields_to_update.items() 
                                                               if k in ['event_type', 'event_date', 'venue']}
                                        if deal_fields_to_update and deal.pipedrive_deal_id is not None:
                                            update_pipedrive_deal_fields(
                                                deal.pipedrive_deal_id,  # type: ignore
                                                event_type=deal_fields_to_update.get('event_type'),
                                                event_date=deal_fields_to_update.get('event_date'),
                                                venue=deal_fields_to_update.get('venue'),
                                                conversation_summary=conversation_summary_text,
                                                full_name=fields_to_update.get('full_name'),
                                                phone=fields_to_update.get('phone_number')
                                            )
                                            logger.info("✅ Updated Pipedrive deal with fields and conversation summary")
                                        elif deal.pipedrive_deal_id is not None and conversation_summary_text:
                                            # Update only conversation summary if no other fields
                                            update_pipedrive_deal_fields(
                                                deal.pipedrive_deal_id,  # type: ignore
                                                conversation_summary=conversation_summary_text,
                                                full_name=fields_to_update.get('full_name'),
                                                phone=fields_to_update.get('phone_number')
                                            )
                                            logger.info("✅ Updated Pipedrive deal with conversation summary")
                                    else:
                                        logger.warning("⚠️ Failed to update local deal fields")
                            
                            # Update Pipedrive with conversation summary if not already done
                            if conversation_summary_text and deal.pipedrive_deal_id is not None and not contains_structured_data:
                                update_pipedrive_deal_fields(
                                    deal.pipedrive_deal_id,  # type: ignore
                                    conversation_summary=conversation_summary_text
                                )
                                logger.info("✅ Updated Pipedrive deal with conversation summary only")
                                
                                # Update or create conversation summary in DB
                                summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal))
                                if summary:
                                    ConversationRepository.update_conversation_summary(
                                        instagram_user_id=to_int(summary.instagram_user_id),
                                        deal_id=to_int(deal),
                                        new_summary=conversation_summary_text
                                    )
                                    logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                                else:
                                    ConversationRepository.create_conversation_summary(
                                        instagram_username=sender_username,
                                        instagram_user_id=to_int(user_already_present),
                                        deal_id=to_int(deal),
                                        conversation_summary=conversation_summary_text
                                    )
                                    logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present)}, deal_id={to_int(deal)} | summary='{conversation_summary_text}'")
                            
                            # Send the AI response
                            send_instagram_message(brideside_user=brideside_user, message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=message_to_send, access_token=access_token, user_id=brideside_user.id)
                            logger.info("Sent message to %s: %s", sender_username, message_to_send)
                            
                            # 🚨 FLAG SETTING LOGIC - Set flags AFTER message is sent
                            # 🚨 CONTACT NUMBER ASKED LOGIC
                            # For existing deals, set flag when asking for contact number (regardless of greeting message status)
                            if (message_to_send != "GREETING_WITH_DATA" and
                                ('phone' in message_to_send.lower() or 'contact' in message_to_send.lower() or 'number' in message_to_send.lower())):
                                if 'phone_number' in missing_fields:
                                    logger.info("📞 Asking for contact number - setting contact_number_asked flag to True")
                                    update_deal_fields(deal, contact_number_asked=True)
                                    logger.info("✅ Updated contact_number_asked flag to True for deal %s", deal)
                            
                            # 🚨 EVENT DATE ASKED LOGIC
                            if (message_to_send != "GREETING_WITH_DATA" and
                                ('event date' in message_to_send.lower() or 'date' in message_to_send.lower() or 'when' in message_to_send.lower())):
                                if 'event_date' in missing_fields:
                                    logger.info("📅 Asking for event date - setting event_date_asked flag to True")
                                    update_deal_fields(deal, event_date_asked=True)
                                    logger.info("✅ Updated event_date_asked flag to True for deal %s", deal)
                            
                            # 🚨 VENUE ASKED LOGIC
                            if (message_to_send != "GREETING_WITH_DATA" and
                                ('venue' in message_to_send.lower() or 'location' in message_to_send.lower() or 'where' in message_to_send.lower())):
                                if 'venue' in missing_fields:
                                    logger.info("🏢 Asking for venue - setting venue_asked flag to True")
                                    update_deal_fields(deal, venue_asked=True)
                                    logger.info("✅ Updated venue_asked flag to True for deal %s", deal)
                        else:
                            logger.info("No valid query or structured data detected. Not sending response.")
                            return True, "Processed - No valid query detected"
                    
                    else:
                        # Fallback - send generic message when AI response is invalid, but still try to extract basic info
                        logger.warning("Invalid response from Groq AI - using fallback response")
                        
                        # Try to extract basic information from the message even when AI fails
                        basic_extracted = ai_service._extract_basic_info(message_text, brideside_user.business_name or "The Bride Side", brideside_user.services or [])
                        
                        # Apply date validation to extracted date
                        if 'event_date' in basic_extracted and basic_extracted['event_date']:
                            basic_extracted['event_date'] = _validate_and_format_date(basic_extracted['event_date'])
                        
                        # For new users, any extracted field is an update
                        fallback_fields_to_update = {k: v for k, v in basic_extracted.items() if v and v.strip()}
                        
                        if fallback_fields_to_update:
                            logger.info("🔧 Fallback extracted fields for new user: %s", fallback_fields_to_update)
                            
                            # Update local database
                            update_success = update_deal_fields(deal_id, **fallback_fields_to_update)  # type: ignore
                            if update_success:
                                logger.info("✅ Successfully updated local deal fields from fallback")
                                
                                # Update Pipedrive contact if name or phone is provided
                                if 'full_name' in fallback_fields_to_update or 'phone_number' in fallback_fields_to_update:
                                    pipedrive_contact_id = get_contact_id_by_username(sender_username)
                                    if pipedrive_contact_id is not None:  # type: ignore
                                        update_pipedrive_contact_fields(
                                            pipedrive_contact_id,
                                            instagram_username=sender_username,
                                            phone=fallback_fields_to_update.get('phone_number')
                                        )
                                        logger.info("✅ Updated Pipedrive contact from fallback")
                                    
                                    # 🚨 RESET CONTACT_NUMBER_ASKED FLAG
                                    if 'phone_number' in fallback_fields_to_update:
                                        logger.info("📞 Phone number provided - resetting contact_number_asked flag to False")
                                        _reset_contact_number_asked_flag(deal_id)
                                    
                                    # If event date was provided, reset the event_date_asked flag
                                    if 'event_date' in fallback_fields_to_update:
                                        logger.info("📅 Event date provided - resetting event_date_asked flag to False")
                                        _reset_event_date_asked_flag(deal_id)
                                    
                                    # If venue was provided, reset the venue_asked flag
                                    if 'venue' in fallback_fields_to_update:
                                        logger.info("🏢 Venue provided - resetting venue_asked flag to False")
                                        _reset_venue_asked_flag(deal_id)
                                
                                # Update Pipedrive deal with extracted event details
                                deal_fields_to_update = {k: v for k, v in fallback_fields_to_update.items() 
                                                       if k in ['event_type', 'event_date', 'venue']}
                                if deal_fields_to_update:
                                    update_pipedrive_deal_fields(
                                        pipedrive_deal_id,
                                        event_type=deal_fields_to_update.get('event_type'),
                                        event_date=deal_fields_to_update.get('event_date'),
                                        venue=deal_fields_to_update.get('venue'),
                                        conversation_summary=f"User: {message_text}",
                                        full_name=fallback_fields_to_update.get('full_name'),
                                        phone=fallback_fields_to_update.get('phone_number')
                                    )
                                    logger.info("✅ Updated Pipedrive deal from fallback extraction")
                        
                        fallback_message = "Thank you for your message! Our team will get back to you soon. 🌸"
                        send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=fallback_message, access_token=access_token, user_id=brideside_user.id)
                        logger.info("Sent fallback message to %s: %s", sender_username, fallback_message)
                    
            else:
                deal_id = None
            
        
        return True, "Processed"
    else:
        logger.info("User %s is not present in the database. creating a new user in the instagram_user table", sender_username)

        # Create Instagram user entry
        instagram_user_id = create_instagram_user(sender_username)
        logger.info("✅ Created Instagram user for %s with ID %s.", sender_username, instagram_user_id)
        
        # Create Pipedrive contact
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        success, contact_id = create_pipedrive_contact(sender_username, sender_username, today)
        if not success:
            logger.error("❌ Failed to create Pipedrive contact for %s.", sender_username)
            return False, "Failed to create Pipedrive contact"
        
        logger.info("✅ Created Pipedrive contact for %s with ID %s.", sender_username, contact_id)
        
        create_contact_entry(sender_username, contact_id)
        
        # Check if deal already exists
        deal_already_exist = deal_exists(sender_username, brideside_user.id)
        if deal_already_exist:
            logger.info("Deal already exists for %s.", sender_username)
            return True, "Processed"
        
        # Create deal
        logger.info("Creating Pipedrive deal for %s...", sender_username)
        business_name = brideside_user.business_name
        deal_created, pipedrive_deal_id = create_pipedrive_deal(sender_username, brideside_user.organization_id, brideside_user.pipeline_id, contact_id, business_name )
        
        if not deal_created:
            logger.error("❌ Failed to create Pipedrive deal for %s.", sender_username)
            return False, "Failed to create Pipedrive deal"
        
        logger.info("✅ Created Pipedrive deal for %s with ID %s.", sender_username, pipedrive_deal_id)
        deal_id = create_deal(sender_username, brideside_user.organization_id, brideside_user.pipeline_id, brideside_user.id, pipedrive_deal_id)
        deal = get_deal_by_user_name(sender_username, brideside_user.id)  # <-- fetch the actual deal object
        # Immediately create a conversation summary entry for this deal using a valid instagram_user_id
        instagram_user_obj = is_user_present(sender_username)
        if instagram_user_obj and getattr(instagram_user_obj, 'id', None):
            ConversationRepository.create_conversation_summary(
                instagram_username=sender_username,
                instagram_user_id=instagram_user_obj.id,
                deal_id=deal_id,
                conversation_summary=""
            )
        else:
            logger.error(f"❌ Could not find Instagram user for username {sender_username} when creating conversation summary for deal {deal_id}")
        
        # First, check with AI if the message contains structured data or is just a greeting
        logger.info("Analyzing initial message from %s with AI...", sender_username)
        
        # Use AI to analyze the message and determine if it contains structured data
        # Note: For first-time users, phone_number is always missing, so AI service will be called
                    # 🚨 ESSENTIAL DETAILS RULE: No check needed here since this is a new deal with no existing required fields
        missing_fields = ['event_date', 'venue', 'phone_number']
        response = ai_service.get_response_with_json(user_message=message_text,
                                                        user_id=brideside_user.id,  # type: ignore
                                                        instagram_user_id=instagram_user_id,  # type: ignore
                                                        instagram_username=sender_username,
                                                        deal_id=deal_id,  # type: ignore
                                                        missing_fields=missing_fields,
                                                        previous_conversation_summary="")
                    
        
        logger.info("AI analysis response: %s", response)
        
        # Check if AI detected structured data in the message
        if isinstance(response, dict):
            contains_structured_data = response.get('contains_structured_data', False)
            contains_valid_query = response.get('contains_valid_query', False)
            is_greeting_message = response.get('is_greeting_message', False)
            message_to_send = response.get('message_to_be_sent', 'Thank you for your message! Our team will get back to you soon. 🌸')
            phone_number = response.get('phone_number', '').strip()
            # Initialize variables to prevent UnboundLocalError
            event_date = response.get('event_date', '').strip()
            venue = response.get('venue', '').strip()
            logger.info("is_greeting_message: %s", is_greeting_message)
            
            # 🚨 CONTACT NUMBER ASKED LOGIC
            # Check if we're asking for phone number and set the flag (but NOT for greeting messages)
            # Additional check: Don't set flag if message_to_be_sent is "GREETING_WITH_DATA" or if we're sending greeting sequence
            if (not is_greeting_message and 
                message_to_send != "GREETING_WITH_DATA" and
                ('phone' in message_to_send.lower() or 'contact' in message_to_send.lower() or 'number' in message_to_send.lower())):
                if 'phone_number' in missing_fields:
                    logger.info("📞 Asking for contact number - setting contact_number_asked flag to True")
                    # Update the contact_number_asked flag in the database
                    update_deal_fields(deal_id, contact_number_asked=True)
                    logger.info("✅ Updated contact_number_asked flag to True for deal %s", deal_id)
            
            # 🚨 CRITICAL FIX: Save extracted data BEFORE contact number check
            # This ensures that even if we're asking for contact number, we save the other extracted data
            if contains_structured_data:
                logger.info("🎯 Saving extracted structured data before contact number check")
                
                # Extract and save the structured data
                full_name = response.get('full_name', '')
                event_type = response.get('event_type', '')
                event_date = response.get('event_date', '')
                venue = response.get('venue', '')
                phone_number_extracted = response.get('phone_number', '')
                
                # Process and save the extracted data
                fields_to_update = {}
                
                if full_name:
                    fields_to_update['full_name'] = full_name
                if event_type:
                    fields_to_update['event_type'] = event_type
                if event_date:
                    fields_to_update['event_date'] = event_date
                if venue:
                    fields_to_update['venue'] = venue
                if phone_number_extracted:
                    fields_to_update['phone_number'] = phone_number_extracted
                
                # Update the deal with extracted data
                if fields_to_update:
                    update_success = update_deal_fields(deal_id, **fields_to_update)
                    if update_success:
                        logger.info("✅ Saved extracted data to deal %s: %s", deal_id, fields_to_update)
                        
                        # Update Pipedrive contact if name or phone is provided
                        if 'full_name' in fields_to_update or 'phone_number' in fields_to_update:
                            pipedrive_contact_id = get_contact_id_by_username(sender_username)
                            if pipedrive_contact_id is not None:  # type: ignore
                                update_pipedrive_contact_fields(
                                    pipedrive_contact_id,
                                    full_name=fields_to_update.get('full_name'),
                                    phone=fields_to_update.get('phone_number'),
                                    instagram_username=sender_username
                                )
                                logger.info("✅ Updated Pipedrive contact")
                            
                            # Reset contact_number_asked flag if phone number was provided
                            if 'phone_number' in fields_to_update:
                                logger.info("📞 Phone number provided - resetting contact_number_asked flag to False")
                                _reset_contact_number_asked_flag(deal_id)
                            
                            # If event date was provided, reset the event_date_asked flag
                            if 'event_date' in fields_to_update:
                                logger.info("📅 Event date provided - resetting event_date_asked flag to False")
                                _reset_event_date_asked_flag(deal_id)
                            
                            # If venue was provided, reset the venue_asked flag
                            if 'venue' in fields_to_update:
                                logger.info("🏢 Venue provided - resetting venue_asked flag to False")
                                _reset_venue_asked_flag(deal_id)
                
                # Update Pipedrive deal with conversation summary
                conversation_summary_text = response.get('conversation_summary', '')
                if conversation_summary_text:
                    deal_obj = get_deal_by_id(deal_id)
                    if deal_obj and deal_obj.pipedrive_deal_id is not None:
                        update_pipedrive_deal_fields(deal_obj.pipedrive_deal_id, conversation_summary=conversation_summary_text)
                        logger.info("✅ Updated Pipedrive deal with conversation summary")
            
            # 🚨 CONTACT NUMBER REFUSAL LOGIC
            # Check if contact_number_asked is True but user didn't provide phone number
            # Get the deal object to check the flag
            deal_obj = get_deal_by_id(deal_id)
            if deal_obj:
                contact_number_asked = getattr(deal_obj, 'contact_number_asked', False)
                logger.info("🔍 DEBUG: contact_number_asked = %s, missing_fields = %s", contact_number_asked, missing_fields)
                if contact_number_asked and 'phone_number' in missing_fields:
                    # Check if user provided phone number in this message
                    phone_number_provided = response.get('phone_number', '').strip()
                    if not phone_number_provided:
                        logger.info("🚫 User was asked for contact number but didn't provide it. No message will be sent.")
                        # Update conversation summary but don't send any message
                        conversation_summary_text = response.get('conversation_summary', '')
                        if conversation_summary_text and deal_obj.pipedrive_deal_id is not None:
                            update_pipedrive_deal_fields(deal_obj.pipedrive_deal_id, conversation_summary=conversation_summary_text)
                        return True, "Contact number requested but not provided - no message sent"

            # Check for special GREETING_WITH_DATA flag FIRST (before regular greeting check)
            if message_to_send == "GREETING_WITH_DATA":
                logger.info("Greeting with structured data detected for %s - sending static greeting + dynamic AI message AND storing extracted data", sender_username)
                # First, process and store the extracted data
                if contains_structured_data:
                    full_name = response.get('full_name', '')
                    event_type = response.get('event_type', '')
                    event_date = response.get('event_date', '')
                    venue = response.get('venue', '')
                    phone_number_extracted = response.get('phone_number', '')
                    
                    # Process and save the extracted data
                    fields_to_update = {}
                    
                    if full_name:
                        fields_to_update['full_name'] = full_name
                    if event_type:
                        fields_to_update['event_type'] = event_type
                    if event_date:
                        fields_to_update['event_date'] = event_date
                    if venue:
                        fields_to_update['venue'] = venue
                    if phone_number_extracted:
                        fields_to_update['phone_number'] = phone_number_extracted
                    
                    # Update the deal with extracted data
                    if fields_to_update:
                        update_success = update_deal_fields(deal_id, **fields_to_update)
                        if update_success:
                            logger.info("Updated deal %s with extracted data: %s", deal_id, fields_to_update)
                            
                            # Update Pipedrive contact if name or phone is provided
                            if 'full_name' in fields_to_update or 'phone_number' in fields_to_update:
                                pipedrive_contact_id = get_contact_id_by_username(sender_username)
                                if pipedrive_contact_id is not None:  # type: ignore
                                    update_pipedrive_contact_fields(
                                        pipedrive_contact_id,
                                        full_name=fields_to_update.get('full_name'),
                                        phone=fields_to_update.get('phone_number'),
                                        instagram_username=sender_username
                                    )
                                    logger.info("✅ Updated Pipedrive contact")
                                
                                # 🚨 RESET CONTACT_NUMBER_ASKED FLAG
                                if 'phone_number' in fields_to_update:
                                    logger.info("📞 Phone number provided - resetting contact_number_asked flag to False")
                                    _reset_contact_number_asked_flag(deal_id)
                                
                                # If event date was provided, reset the event_date_asked flag
                                if 'event_date' in fields_to_update:
                                    logger.info("📅 Event date provided - resetting event_date_asked flag to False")
                                    _reset_event_date_asked_flag(deal_id)
                                
                                # If venue was provided, reset the venue_asked flag
                                if 'venue' in fields_to_update:
                                    logger.info("🏢 Venue provided - resetting venue_asked flag to False")
                                    _reset_venue_asked_flag(deal_id)
                                
                                # 🔧 CRITICAL FIX: Recalculate missing fields after data is saved
                                updated_deal = get_deal_by_id(deal_id)
                                if updated_deal:
                                    missing_fields = _get_missing_fields_from_deal(updated_deal)
                                    logger.info("🔄 Recalculated missing fields after data save: %s", missing_fields)
                        else:
                            logger.error("Failed to update deal %s with extracted data: %s", deal_id, fields_to_update)
                
                # Then send static greeting + dynamic AI message instead of full greeting sequence
                original_message = response.get('message_to_be_sent', '')
                if original_message and original_message != "GREETING_WITH_DATA":
                    # Combine static greeting with dynamic AI message
                    # 🚨 CRITICAL FIX: Handle "Thank you. Will connect shortly!" specially to avoid double "thank you"
                    if original_message == "Thank you. Will connect shortly!":
                        combined_message = "Hello! Thanks for reaching out✨ Will connect shortly!"
                    else:
                        combined_message = f"Hello! Thanks for reaching out✨ {original_message}"
                    logger.info("📝 Using combined message: %s", combined_message)
                    
                    # Check if we're asking for contact number and set the flag
                    if 'phone_number' in missing_fields and 'contact number' in original_message.lower():
                        logger.info("📞 Asking for contact number in greeting - setting contact_number_asked flag to True")
                        update_deal_fields(deal.id, contact_number_asked=True)
                        logger.info("✅ Updated contact_number_asked flag to True for deal %s", deal.id)
                    
                    # Check if we're asking for event date and set the flag
                    if 'event_date' in missing_fields and ('event date' in original_message.lower() or 'date' in original_message.lower() or 'when' in original_message.lower()):
                        logger.info("📅 Asking for event date in greeting - setting event_date_asked flag to True")
                        update_deal_fields(deal.id, event_date_asked=True)
                        logger.info("✅ Updated event_date_asked flag to True for deal %s", deal.id)
                    
                    # Check if we're asking for venue and set the flag
                    if 'venue' in missing_fields and ('venue' in original_message.lower() or 'location' in original_message.lower() or 'where' in original_message.lower()):
                        logger.info("🏢 Asking for venue in greeting - setting venue_asked flag to True")
                        update_deal_fields(deal.id, venue_asked=True)
                        logger.info("✅ Updated venue_asked flag to True for deal %s", deal.id)
                    
                    # Send the combined message
                    send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=combined_message, access_token=access_token, user_id=brideside_user.id)
                    logger.info("Sent combined greeting + AI message to %s: %s", sender_username, combined_message)
                    
                    # 🚨 CRITICAL FIX: Update final_thank_you_sent flag if sending thank you message
                    if "Thank you. Will connect shortly!" in original_message:
                        try:
                            update_success = update_deal_fields(deal.id, final_thank_you_sent=True)
                            if update_success:
                                logger.info("✅ Updated final_thank_you_sent to True for deal %s", deal.id)
                            else:
                                logger.error("❌ Failed to update final_thank_you_sent for deal %s", deal.id)
                        except Exception as e:
                            logger.error("❌ Error updating final_thank_you_sent for deal %s: %s", deal.id, e)
                else:
                    # Fallback to regular greeting sequence if no AI message
                    send_initial_greetings_message(sender_id, brideside_user, message_id, sender_username, access_token, brideside_user.id)
                    logger.info("Sent initial greeting message sequence to %s (fallback)", sender_username)
                
                return True, "Processed - Greeting with data: combined message sent and data stored"
            
            # Regular greeting check (only if not GREETING_WITH_DATA)
            if is_greeting_message: 
                logger.info("Message is just a greeting - checking for structured data")
                
                # 🚨 CRITICAL FIX: If greeting message has structured data, save it to database
                if contains_structured_data:
                    logger.info("🎯 Greeting message with structured data detected - sending static greeting + dynamic AI message")
                    
                    # Extract and save the structured data
                    full_name = response.get('full_name', '')
                    event_type = response.get('event_type', '')
                    event_date = response.get('event_date', '')
                    venue = response.get('venue', '')
                    phone_number_extracted = response.get('phone_number', '')
                    
                    # Process and save the extracted data
                    greeting_fields_to_update = {}
                    
                    if full_name:
                        greeting_fields_to_update['full_name'] = full_name
                    if event_type:
                        greeting_fields_to_update['event_type'] = event_type
                    if event_date:
                        greeting_fields_to_update['event_date'] = event_date
                    if venue:
                        greeting_fields_to_update['venue'] = venue
                    if phone_number_extracted:
                        greeting_fields_to_update['phone_number'] = phone_number_extracted
                    
                    # Update the deal with extracted data
                    if greeting_fields_to_update:
                        update_success = update_deal_fields(deal.id, **greeting_fields_to_update)
                        if update_success:
                            logger.info("✅ Saved structured data from greeting message: %s", greeting_fields_to_update)
                            
                            # 🔧 CRITICAL FIX: Recalculate missing fields after data is saved
                            updated_deal = get_deal_by_id(deal.id)
                            if updated_deal:
                                missing_fields = _get_missing_fields_from_deal(updated_deal)
                                logger.info("🔄 Recalculated missing fields after greeting data save: %s", missing_fields)
                        else:
                            logger.error("❌ Failed to save structured data from greeting message: %s", greeting_fields_to_update)
                    
                    # Also update conversation summary in Pipedrive
                    conversation_summary_text = response.get('conversation_summary', '')
                    if conversation_summary_text:
                        update_pipedrive_deal_fields(
                            pipedrive_deal_id,
                            conversation_summary=conversation_summary_text
                        )
                        logger.info("✅ Updated Pipedrive deal with conversation summary from greeting message")
                
                    # Send static greeting + dynamic AI message instead of full greeting sequence
                    original_message = response.get('message_to_be_sent', '')
                    if original_message:
                        # Check if we're asking for contact number and set the flag
                        if 'phone_number' in missing_fields and 'contact number' in original_message.lower():
                            logger.info("📞 Asking for contact number in greeting - setting contact_number_asked flag to True")
                            update_deal_fields(deal.id, contact_number_asked=True)
                            logger.info("✅ Updated contact_number_asked flag to True for deal %s", deal.id)
                        
                        # Check if we're asking for event date and set the flag
                        if 'event_date' in missing_fields and ('event date' in original_message.lower() or 'date' in original_message.lower() or 'when' in original_message.lower()):
                            logger.info("📅 Asking for event date in greeting - setting event_date_asked flag to True")
                            update_deal_fields(deal.id, event_date_asked=True)
                            logger.info("✅ Updated event_date_asked flag to True for deal %s", deal.id)
                        
                        # Check if we're asking for venue and set the flag
                        if 'venue' in missing_fields and ('venue' in original_message.lower() or 'location' in original_message.lower() or 'where' in original_message.lower()):
                            logger.info("🏢 Asking for venue in greeting - setting venue_asked flag to True")
                            update_deal_fields(deal.id, venue_asked=True)
                            logger.info("✅ Updated venue_asked flag to True for deal %s", deal.id)
                        
                        # Combine static greeting with dynamic AI message
                        # 🚨 CRITICAL FIX: Handle "Thank you. Will connect shortly!" specially to avoid double "thank you"
                        if original_message == "Thank you. Will connect shortly!":
                            combined_message = "Hello! Thanks for reaching out✨ Will connect shortly!"
                        else:
                            # 🚨 SMART FIX: Remove fields from message that were already provided by user
                            smart_message = _smart_clean_message(original_message, missing_fields)
                            combined_message = f"Hello! Thanks for reaching out✨ {smart_message}"
                        logger.info("📝 Using combined greeting message: %s", combined_message)
                        
                        # Send the combined message
                        send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=combined_message, access_token=access_token, user_id=brideside_user.id)
                        logger.info("Sent combined greeting + AI message to %s: %s", sender_username, combined_message)
                        
                        # 🚨 CRITICAL FIX: Update final_thank_you_sent flag if sending thank you message
                        if "Thank you. Will connect shortly!" in original_message:
                            try:
                                update_success = update_deal_fields(deal.id, final_thank_you_sent=True)
                                if update_success:
                                    logger.info("✅ Updated final_thank_you_sent to True for deal %s", deal.id)
                                else:
                                    logger.error("❌ Failed to update final_thank_you_sent for deal %s", deal.id)
                            except Exception as e:
                                logger.error("❌ Error updating final_thank_you_sent for deal %s: %s", deal.id, e)
                        
                        return True, "Processed - Greeting with structured data: combined message sent"
                    else:
                        # Fallback to regular greeting sequence if no AI message
                        send_initial_greetings_message(sender_id, brideside_user, message_id, sender_username, access_token, brideside_user.id)
                        logger.info("Sent initial greeting message sequence to %s (fallback)", sender_username)
                        return True, "Processed - Initial greeting message sent (fallback)"
                else:
                    # No structured data - send regular greeting sequence
                    send_initial_greetings_message(sender_id, brideside_user, message_id, sender_username, access_token, brideside_user.id)
                    logger.info("Sent initial greeting message sequence to %s", sender_username)
                    return True, "Processed - Initial greeting message sent"
            
            # Check if we should send no message (unrelated queries)
            if message_to_send == "NO_MESSAGE":
                logger.info("Unrelated query detected for %s. No message will be sent.", sender_username)
                return True, "Processed - No message sent (unrelated query)"
            
            # 🚨 ADDITIONAL ESSENTIAL DETAILS CHECK - Only enforce for existing users, not new users
            # For new users (first message), we want to send the AI's response even if all details are collected
            # For existing users, enforce the "no message" rule to prevent spam
            if phone_number and phone_number.strip() and event_date and event_date.strip() and venue and venue.strip():
                # Check if this is a new user (no existing deal) or existing user
                existing_deal = get_deal_by_user_name(sender_username, brideside_user.id)
                if existing_deal and existing_deal.id != deal_id:
                    # This is an existing user - enforce NO_MESSAGE rule
                    logger.info("🚨 AI returned response with all essential details for existing user %s. Enforcing NO_MESSAGE rule.", sender_username)
                    return True, "Processed - No message sent (all essential details collected - AI bypass prevented)"
                else:
                    # This is a new user - allow the AI's response to be sent
                    logger.info("✅ New user %s provided all essential details. Allowing AI response to be sent.", sender_username)

            # --- CUSTOM LOGIC FOR FIRST MESSAGE ---
            if contains_structured_data:
                # Extract data from AI response
                full_name = response.get('full_name', '')
                event_type = response.get('event_type', '')
                event_date = response.get('event_date', '')
                venue = response.get('venue', '')
                phone_number_extracted = response.get('phone_number', '')
                
                # Process and save the extracted data first
                fields_to_update = {}
                
                if full_name:
                    fields_to_update['full_name'] = full_name
                if event_type:
                    fields_to_update['event_type'] = event_type
                if event_date:
                    fields_to_update['event_date'] = event_date
                if venue:
                    fields_to_update['venue'] = venue
                if phone_number_extracted:
                    fields_to_update['phone_number'] = phone_number_extracted
                
                # Update Pipedrive deal with extracted data
                if fields_to_update:
                    # Map phone_number to phone for Pipedrive API
                    pipedrive_fields = fields_to_update.copy()
                    if 'phone_number' in pipedrive_fields:
                        pipedrive_fields['phone'] = pipedrive_fields.pop('phone_number')
                    update_pipedrive_deal_fields(pipedrive_deal_id, **pipedrive_fields)
                    logger.info(f"✅ Updated Pipedrive deal {pipedrive_deal_id} with fields: {fields_to_update}")
                    
                    # Also update the local database deal with extracted fields
                    update_success = update_deal_fields(to_int(deal_id), **fields_to_update)
                    if update_success:
                        logger.info(f"✅ Updated database deal {deal_id} with fields: {fields_to_update}")
                    else:
                        logger.error(f"❌ Failed to update database deal {deal_id} with fields")
                
                # Update conversation summary
                conversation_summary_text = response.get('conversation_summary', '')
                if conversation_summary_text:
                    update_pipedrive_deal_fields(
                        pipedrive_deal_id,
                        conversation_summary=conversation_summary_text
                    )
                    logger.info("✅ Updated Pipedrive deal with conversation summary")
                    
                    # Update or create conversation summary in DB
                    summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal_id))
                    if summary:
                        # Use the new summary directly since it already contains the full conversation history
                        # The AI service already has access to the previous summary and includes it in its response
                        combined_summary = conversation_summary_text.strip()
                        ConversationRepository.update_conversation_summary(
                            instagram_user_id=to_int(summary.instagram_user_id),
                            deal_id=to_int(deal_id),
                            new_summary=combined_summary
                        )
                        logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal_id)} | summary='{combined_summary}'")
                    else:
                        ConversationRepository.create_conversation_summary(
                            instagram_username=sender_username,
                            instagram_user_id=to_int(instagram_user_id),
                            deal_id=to_int(deal_id),
                            conversation_summary=conversation_summary_text
                        )
                        logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(instagram_user_id)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                
                # 🚨 CRITICAL FIX: Handle "Thank you. Will connect shortly!" specially to avoid double "thank you" in main flow
                if message_to_send == "Thank you. Will connect shortly!":
                    # For first-time users who provide all details, add the static greeting
                    final_message = "Hello! Thanks for reaching out✨ Will connect shortly!"
                else:
                    final_message = message_to_send
                
                # Send the AI's message
                send_instagram_message(brideside_user=brideside_user, message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=final_message, access_token=access_token, user_id=brideside_user.id)
                logger.info("Sent custom first-message response to %s: %s", sender_username, final_message)
                
                # 🚨 CRITICAL FIX: Update final_thank_you_sent flag if sending thank you message
                if message_to_send == "Thank you. Will connect shortly!":
                    try:
                        update_success = update_deal_fields(to_int(deal_id), final_thank_you_sent=True)
                        if update_success:
                            logger.info("✅ Updated final_thank_you_sent to True for deal %s", deal_id)
                        else:
                            logger.error("❌ Failed to update final_thank_you_sent for deal %s", deal_id)
                    except Exception as e:
                        logger.error("❌ Error updating final_thank_you_sent for deal %s: %s", deal_id, e)
                
                return True, "Processed - Custom first message logic applied"
            # --- END CUSTOM LOGIC ---

            # Handle valid queries (service inquiries, budget, etc.)
            if contains_valid_query:
                # Extract any structured data from the response (even if contains_structured_data is false)
                full_name = response.get('full_name', '').strip()
                event_type = response.get('event_type', '').strip()
                event_date = response.get('event_date', '').strip()
                venue = response.get('venue', '').strip()
                phone_number_extracted = response.get('phone_number', '').strip()
                
                # Prepare fields to update in Pipedrive deal
                fields_to_update = {}
                if full_name:
                    fields_to_update['full_name'] = full_name
                if event_type:
                    fields_to_update['event_type'] = event_type
                if event_date:
                    fields_to_update['event_date'] = event_date
                if venue:
                    fields_to_update['venue'] = venue
                if phone_number_extracted:
                    fields_to_update['phone_number'] = phone_number_extracted
                
                # Update Pipedrive deal with extracted data
                if fields_to_update:
                    # Map phone_number to phone for Pipedrive API
                    pipedrive_fields = fields_to_update.copy()
                    if 'phone_number' in pipedrive_fields:
                        pipedrive_fields['phone'] = pipedrive_fields.pop('phone_number')
                    update_pipedrive_deal_fields(pipedrive_deal_id, **pipedrive_fields)
                    logger.info(f"✅ Updated Pipedrive deal {pipedrive_deal_id} with extracted fields: {fields_to_update}")
                    
                    # Also update the local database deal with extracted fields
                    update_success = update_deal_fields(to_int(deal_id), **fields_to_update)
                    if update_success:
                        logger.info(f"✅ Updated database deal {deal_id} with extracted fields: {fields_to_update}")
                    else:
                        logger.error(f"❌ Failed to update database deal {deal_id} with extracted fields")
                
                # Fallback extraction if AI misses details
                def fallback_extract_details(msg):
                    event_type = ''
                    event_date = ''
                    venue = ''
                    # Event type
                    if re.search(r'wedding photographer|photography', msg, re.I):
                        event_type = 'Wedding Photography'
                    elif re.search(r'bridal makeup', msg, re.I):
                        event_type = 'Bridal Makeup'
                    elif re.search(r'party makeup', msg, re.I):
                        event_type = 'Party Makeup'
                    elif re.search(r'wedding planner', msg, re.I):
                        event_type = 'Wedding Planner'
                    elif re.search(r'decor', msg, re.I):
                        event_type = 'Wedding Decor'
                    # Date
                    date_match = re.search(r'(\d{1,2}(st|nd|rd|th)?\s+\w+\s+20\d{2})', msg)
                    if date_match:
                        try:
                            from dateutil import parser as date_parser
                            event_date = date_parser.parse(date_match.group(1)).strftime('%Y-%m-%d')
                        except Exception:
                            pass
                    # Venue (look for 'in <city>' or 'at <city>')
                    venue_match = re.search(r'in ([A-Za-z ]+)', msg)
                    if venue_match:
                        venue = venue_match.group(1).strip().split()[0]
                    return event_type, event_date, venue

                # If AI missed details, use fallback
                if (not event_type or not event_date or not venue):
                    fb_event_type, fb_event_date, fb_venue = fallback_extract_details(message_text)
                    if not event_type and fb_event_type:
                        event_type = fb_event_type
                        fields_to_update['event_type'] = event_type
                    if not event_date and fb_event_date:
                        event_date = fb_event_date
                        fields_to_update['event_date'] = event_date
                    if not venue and fb_venue:
                        venue = fb_venue
                        fields_to_update['venue'] = venue
                    # If any fallback worked, set contains_structured_data to True
                    if event_type or event_date or venue:
                        contains_structured_data = True

                # Get conversation summary to send to Pipedrive
                conversation_summary_text = response.get('conversation_summary', '')
                
                # Update Pipedrive with conversation summary
                if conversation_summary_text:
                    update_pipedrive_deal_fields(
                        pipedrive_deal_id,
                        conversation_summary=conversation_summary_text
                    )
                    logger.info("✅ Updated Pipedrive deal with conversation summary")
                    
                    # Update or create conversation summary in DB
                    summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal_id))
                    if summary:
                        # Use the new summary directly since it already contains the full conversation history
                        # The AI service already has access to the previous summary and includes it in its response
                        combined_summary = conversation_summary_text.strip()
                        ConversationRepository.update_conversation_summary(
                            instagram_user_id=to_int(summary.instagram_user_id),
                            deal_id=to_int(deal_id),
                            new_summary=combined_summary
                        )
                        logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal_id)} | summary='{combined_summary}'")
                    else:
                        ConversationRepository.create_conversation_summary(
                            instagram_username=sender_username,
                            instagram_user_id=to_int(instagram_user_id),
                            deal_id=to_int(deal_id),
                            conversation_summary=conversation_summary_text
                        )
                        logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(instagram_user_id)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                
                # Send AI-generated response for valid queries
                send_instagram_message(brideside_user=brideside_user, message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=message_to_send, access_token=access_token, user_id=brideside_user.id)
                logger.info("Sent AI-generated response for valid query to %s: %s", sender_username, message_to_send)
                return True, "Processed - Valid query response sent"

            # --- FALLBACK HEURISTIC FOR DETAILS ---
            # If AI says not structured, but message contains event details, treat as details message
            # 🚨 CRITICAL FIX: Only use fallback when AI completely fails, not when it provides structured data
            
            def contains_event_details(msg):
                import re
                keywords = [
                    'wedding', 'photographer', 'photography', 'event', 'function', 'venue', 'location', 'haldi', 'reception', 'shoot', 'package', 'date', 'city', 'party', 'makeup', 'planner', 'decor', 'lucknow'
                ]
                msg_lower = msg.lower()
                if any(kw in msg_lower for kw in keywords):
                    return True
                # Simple date pattern: e.g. 25th dec, 25/12, 25-12, 2025
                if re.search(r'\b\d{1,2}(st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b', msg_lower):
                    return True
                if re.search(r'\b\d{1,2}[/-]\d{1,2}\b', msg_lower):
                    return True
                if re.search(r'\b20\d{2}\b', msg_lower):
                    return True
                return False
            
            if not contains_structured_data and not contains_valid_query and contains_event_details(message_text):
                # Try to extract as many details as possible
                basic_extracted = ai_service._extract_basic_info(message_text, brideside_user.business_name or "", brideside_user.services or [])
                # Apply date validation
                if 'event_date' in basic_extracted and basic_extracted['event_date']:
                    basic_extracted['event_date'] = _validate_and_format_date(basic_extracted['event_date'])
                # Prepare fields to update
                fallback_fields_to_update = {k: v for k, v in basic_extracted.items() if v and v.strip()}
                # Update local deal
                if fallback_fields_to_update:
                    update_success = update_deal_fields(deal_id, **fallback_fields_to_update)  # type: ignore
                    if update_success:
                        logger.info("✅ Successfully updated local deal fields from fallback (details-detected)")
                        # Update Pipedrive contact if name or phone is provided
                        if 'full_name' in fallback_fields_to_update or 'phone_number' in fallback_fields_to_update:
                            pipedrive_contact_id = get_contact_id_by_username(sender_username)
                            if pipedrive_contact_id is not None:  # type: ignore
                                update_pipedrive_contact_fields(
                                    pipedrive_contact_id,
                                    instagram_username=sender_username,
                                    phone=fallback_fields_to_update.get('phone_number')
                                )
                                logger.info("✅ Updated Pipedrive contact from fallback (details-detected)")
                            
                            # 🚨 RESET CONTACT_NUMBER_ASKED FLAG
                            if 'phone_number' in fallback_fields_to_update:
                                logger.info("📞 Phone number provided - resetting contact_number_asked flag to False")
                                _reset_contact_number_asked_flag(deal_id)
                            
                            # If event date was provided, reset the event_date_asked flag
                            if 'event_date' in fallback_fields_to_update:
                                logger.info("📅 Event date provided - resetting event_date_asked flag to False")
                                _reset_event_date_asked_flag(deal_id)
                            
                            # If venue was provided, reset the venue_asked flag
                            if 'venue' in fallback_fields_to_update:
                                logger.info("🏢 Venue provided - resetting venue_asked flag to False")
                                _reset_venue_asked_flag(deal_id)
                        # Update Pipedrive deal with extracted event details
                        deal_fields_to_update = {k: v for k, v in fallback_fields_to_update.items() 
                                               if k in ['event_type', 'event_date', 'venue']}
                        if deal_fields_to_update:
                            update_pipedrive_deal_fields(
                                pipedrive_deal_id,
                                event_type=deal_fields_to_update.get('event_type'),
                                event_date=deal_fields_to_update.get('event_date'),
                                venue=deal_fields_to_update.get('venue'),
                                conversation_summary=f"User: {message_text}",
                                full_name=fallback_fields_to_update.get('full_name'),
                                phone=fallback_fields_to_update.get('phone_number')
                            )
                            logger.info("✅ Updated Pipedrive deal from fallback extraction (details-detected)")
                        # Update conversation summary
                        summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal_id))
                        conversation_summary_text = f"User: {message_text}"
                        if summary:
                            ConversationRepository.update_conversation_summary(
                                instagram_user_id=to_int(summary.instagram_user_id),
                                deal_id=to_int(deal_id),
                                new_summary=conversation_summary_text
                            )
                            logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                        else:
                            ConversationRepository.create_conversation_summary(
                                instagram_username=sender_username,
                                instagram_user_id=to_int(user_already_present) if 'user_already_present' in locals() else 0,
                                deal_id=to_int(deal_id),
                                conversation_summary=conversation_summary_text
                            )
                            logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present) if 'user_already_present' in locals() else 0}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                # Now send the phone number request or thank you message
                if not phone_number:
                    message_to_send = "Thank you for sharing your details! Could you please provide your phone number so we can reach out and help you better?"
                else:
                    message_to_send = "Thank you for sharing the details, our team will reach out to you soon for the further conversation."
                send_instagram_message(brideside_user=brideside_user, message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=message_to_send, access_token=access_token, user_id=brideside_user.id)
                logger.info("Sent fallback details-detected response to %s: %s", sender_username, message_to_send)
                return True, "Processed - Fallback details logic applied"
            # --- END FALLBACK HEURISTIC ---

            # Check if we should send no message (all details collected)
            if message_to_send == "NO_MESSAGE":
                logger.info("All details collected for %s. No message will be sent.", sender_username)
                
                # Still update conversation summary in Pipedrive
                conversation_summary_text = response.get('conversation_summary', '')
                if conversation_summary_text:
                    update_pipedrive_deal_fields(
                        pipedrive_deal_id,
                        conversation_summary=conversation_summary_text
                    )
                    logger.info("✅ Updated Pipedrive deal with conversation summary only")
                    # Update or create conversation summary in DB
                    summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal_id))
                    if summary:
                        ConversationRepository.update_conversation_summary(
                            instagram_user_id=to_int(summary.instagram_user_id),
                            deal_id=to_int(deal_id),
                            new_summary=conversation_summary_text
                        )
                        logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                    else:
                        ConversationRepository.create_conversation_summary(
                            instagram_username=sender_username,
                            instagram_user_id=to_int(user_already_present),
                            deal_id=to_int(deal_id),
                            conversation_summary=conversation_summary_text
                        )
                        logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                
                return True, "Processed - No message sent (all details collected)"
            
            # Get conversation summary to send to Pipedrive
            conversation_summary_text = response.get('conversation_summary', '')
            
            if contains_structured_data:
                # Extract and update fields for both existing and new users with structured data
                extracted_fields = {
                    'full_name': response.get('full_name', ''),
                    'event_type': response.get('event_type', ''),
                    'event_date': _validate_and_format_date(response.get('event_date', '')),
                    'venue': response.get('venue', ''),
                    'phone_number': response.get('phone_number', '')
                }
                
                # For new users, all non-empty fields are considered updates
                fields_to_update = {k: v for k, v in extracted_fields.items() if v and v.strip()}
                
                if fields_to_update:
                    logger.info("Message contains structured data: %s", fields_to_update)
                    
                    # Update local database
                    update_success = update_deal_fields(deal_id, **fields_to_update)  # type: ignore
                    if update_success:
                        logger.info("✅ Successfully updated local deal fields")
                        
                        # Update Pipedrive contact if name or phone is provided
                        if 'full_name' in fields_to_update or 'phone_number' in fields_to_update:
                            pipedrive_contact_id = get_contact_id_by_username(sender_username)
                            if pipedrive_contact_id is not None:  # type: ignore
                                update_pipedrive_contact_fields(
                                    pipedrive_contact_id,
                                    full_name=fields_to_update.get('full_name'),
                                    phone=fields_to_update.get('phone_number'),
                                    instagram_username=sender_username
                                )
                                logger.info("✅ Updated Pipedrive contact")
                            
                            # 🚨 RESET CONTACT_NUMBER_ASKED FLAG
                            if 'phone_number' in fields_to_update:
                                logger.info("📞 Phone number provided - resetting contact_number_asked flag to False")
                                _reset_contact_number_asked_flag(deal_id)
                            
                            # If event date was provided, reset the event_date_asked flag
                            if 'event_date' in fields_to_update:
                                logger.info("📅 Event date provided - resetting event_date_asked flag to False")
                                _reset_event_date_asked_flag(deal_id)
                            
                            # If venue was provided, reset the venue_asked flag
                            if 'venue' in fields_to_update:
                                logger.info("🏢 Venue provided - resetting venue_asked flag to False")
                                _reset_venue_asked_flag(deal_id)
                        
                        # Update Pipedrive deal with extracted event details AND conversation summary
                        deal_fields_to_update = {k: v for k, v in fields_to_update.items() 
                                               if k in ['event_type', 'event_date', 'venue']}
                        if deal_fields_to_update:
                            update_pipedrive_deal_fields(
                                pipedrive_deal_id,
                                event_type=deal_fields_to_update.get('event_type'),
                                event_date=deal_fields_to_update.get('event_date'),
                                venue=deal_fields_to_update.get('venue'),
                                conversation_summary=conversation_summary_text
                            )
                            logger.info("✅ Updated Pipedrive deal with fields and conversation summary")
                            # Update or create conversation summary in DB
                            summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal_id))
                            if summary:
                                ConversationRepository.update_conversation_summary(
                                    instagram_user_id=to_int(summary.instagram_user_id),
                                    deal_id=to_int(deal_id),
                                    new_summary=conversation_summary_text
                                )
                                logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                            else:
                                ConversationRepository.create_conversation_summary(
                                    instagram_username=sender_username,
                                    instagram_user_id=to_int(user_already_present),
                                    deal_id=to_int(deal_id),
                                    conversation_summary=conversation_summary_text
                                )
                                logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                        elif conversation_summary_text:
                            # Update only conversation summary if no other fields
                            update_pipedrive_deal_fields(
                                pipedrive_deal_id,
                                conversation_summary=conversation_summary_text
                            )
                            logger.info("✅ Updated Pipedrive deal with conversation summary")
                            # Update or create conversation summary in DB
                            summary = ConversationRepository.get_conversation_summary_by_deal_id(to_int(deal_id))
                            if summary:
                                ConversationRepository.update_conversation_summary(
                                    instagram_user_id=to_int(summary.instagram_user_id),
                                    deal_id=to_int(deal_id),
                                    new_summary=conversation_summary_text
                                )
                                logger.info(f"✅ Conversation summary UPDATED in DB for user_id={to_int(summary.instagram_user_id)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                            else:
                                ConversationRepository.create_conversation_summary(
                                    instagram_username=sender_username,
                                    instagram_user_id=to_int(user_already_present),
                                    deal_id=to_int(deal_id),
                                    conversation_summary=conversation_summary_text
                                )
                                logger.info(f"✅ Conversation summary ADDED to DB for user_id={to_int(user_already_present)}, deal_id={to_int(deal_id)} | summary='{conversation_summary_text}'")
                
                # Send AI-generated response
                send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=message_to_send, access_token=access_token, user_id=brideside_user.id)
                logger.info("Sent AI-generated response to %s: %s", sender_username, message_to_send)
                
            else:
                # Message is just a greeting - check for structured data
                logger.info("Message is just a greeting - checking for structured data")
                
                # 🚨 CRITICAL FIX: If greeting message has structured data, save it to database
                if contains_structured_data:
                    logger.info("🎯 Greeting message with structured data detected - sending static greeting + dynamic AI message")
                    
                    # Extract and save the structured data
                    full_name = response.get('full_name', '')
                    event_type = response.get('event_type', '')
                    event_date = response.get('event_date', '')
                    venue = response.get('venue', '')
                    phone_number_extracted = response.get('phone_number', '')
                    
                    # Process and save the extracted data
                    greeting_fields_to_update = {}
                    
                    if full_name:
                        greeting_fields_to_update['full_name'] = full_name
                    if event_type:
                        greeting_fields_to_update['event_type'] = event_type
                    if event_date:
                        greeting_fields_to_update['event_date'] = event_date
                    if venue:
                        greeting_fields_to_update['venue'] = venue
                    if phone_number_extracted:
                        greeting_fields_to_update['phone_number'] = phone_number_extracted
                    
                    # Update the deal with extracted data
                    if greeting_fields_to_update:
                        update_success = update_deal_fields(deal_id, **greeting_fields_to_update)
                        if update_success:
                            logger.info("✅ Saved structured data from greeting message: %s", greeting_fields_to_update)
                            
                            # 🔧 CRITICAL FIX: Recalculate missing fields after data is saved
                            updated_deal = get_deal_by_id(deal_id)
                            if updated_deal:
                                missing_fields = _get_missing_fields_from_deal(updated_deal)
                                logger.info("🔄 Recalculated missing fields after greeting data save: %s", missing_fields)
                        else:
                            logger.error("❌ Failed to save structured data from greeting message: %s", greeting_fields_to_update)
                    
                    # Also update conversation summary in Pipedrive
                    conversation_summary_text = response.get('conversation_summary', '')
                    if conversation_summary_text:
                        update_pipedrive_deal_fields(
                            pipedrive_deal_id,
                            conversation_summary=conversation_summary_text
                        )
                        logger.info("✅ Updated Pipedrive deal with conversation summary from greeting message")
                
                    # Send static greeting + dynamic AI message instead of full greeting sequence
                    original_message = response.get('message_to_be_sent', '')
                    if original_message:
                        # Check if we're asking for contact number and set the flag
                        if 'phone_number' in missing_fields and 'contact number' in original_message.lower():
                            logger.info("📞 Asking for contact number in greeting - setting contact_number_asked flag to True")
                            update_deal_fields(deal.id, contact_number_asked=True)
                            logger.info("✅ Updated contact_number_asked flag to True for deal %s", deal.id)
                        
                        # Check if we're asking for event date and set the flag
                        if 'event_date' in missing_fields and ('event date' in original_message.lower() or 'date' in original_message.lower() or 'when' in original_message.lower()):
                            logger.info("📅 Asking for event date in greeting - setting event_date_asked flag to True")
                            update_deal_fields(deal.id, event_date_asked=True)
                            logger.info("✅ Updated event_date_asked flag to True for deal %s", deal.id)
                        
                        # Check if we're asking for venue and set the flag
                        if 'venue' in missing_fields and ('venue' in original_message.lower() or 'location' in original_message.lower() or 'where' in original_message.lower()):
                            logger.info("🏢 Asking for venue in greeting - setting venue_asked flag to True")
                            update_deal_fields(deal.id, venue_asked=True)
                            logger.info("✅ Updated venue_asked flag to True for deal %s", deal.id)
                        
                        # Combine static greeting with dynamic AI message
                        # 🚨 CRITICAL FIX: Handle "Thank you. Will connect shortly!" specially to avoid double "thank you"
                        if original_message == "Thank you. Will connect shortly!":
                            combined_message = "Hello! Thanks for reaching out✨ Will connect shortly!"
                        else:
                            # 🚨 SMART FIX: Remove fields from message that were already provided by user
                            smart_message = _smart_clean_message(original_message, missing_fields)
                            combined_message = f"Hello! Thanks for reaching out✨ {smart_message}"
                        logger.info("📝 Using combined greeting message: %s", combined_message)
                        
                        # Send the combined message
                        send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=combined_message, access_token=access_token, user_id=brideside_user.id)
                        logger.info("Sent combined greeting + AI message to %s: %s", sender_username, combined_message)
                        
                        # 🚨 CRITICAL FIX: Update final_thank_you_sent flag if sending thank you message
                        if "Thank you. Will connect shortly!" in original_message:
                            try:
                                update_success = update_deal_fields(deal.id, final_thank_you_sent=True)
                                if update_success:
                                    logger.info("✅ Updated final_thank_you_sent to True for deal %s", deal.id)
                                else:
                                    logger.error("❌ Failed to update final_thank_you_sent for deal %s", deal.id)
                            except Exception as e:
                                logger.error("❌ Error updating final_thank_you_sent for deal %s: %s", deal.id, e)
                    else:
                        # Fallback to regular greeting sequence if no AI message
                        send_initial_greetings_message(sender_id, brideside_user, message_id, sender_username, access_token, brideside_user.id)
                        logger.info("Sent initial greeting message sequence to %s (fallback)", sender_username)
                else:
                    # No structured data - send regular greeting sequence
                    send_initial_greetings_message(sender_id, brideside_user, message_id, sender_username, access_token, brideside_user.id)
                    logger.info("Sent initial greeting message sequence to %s", sender_username)
        else:
            # Fallback - send generic message when AI response is invalid, but still try to extract basic info
            logger.warning("Invalid response from AI - using fallback response")
            
            # Try to extract basic information from the message even when AI fails
            basic_extracted = ai_service._extract_basic_info(message_text, brideside_user.business_name or "", brideside_user.services or [])
            
            # Apply date validation to extracted date
            if 'event_date' in basic_extracted and basic_extracted['event_date']:
                basic_extracted['event_date'] = _validate_and_format_date(basic_extracted['event_date'])
            
            # For new users, any extracted field is an update
            fallback_fields_to_update = {k: v for k, v in basic_extracted.items() if v and v.strip()}
            
            if fallback_fields_to_update:
                logger.info("🔧 Fallback extracted fields for new user: %s", fallback_fields_to_update)
                
                # Update local database
                update_success = update_deal_fields(deal_id, **fallback_fields_to_update)  # type: ignore
                if update_success:
                    logger.info("✅ Successfully updated local deal fields from fallback")
                    
                    # Update Pipedrive contact if name or phone is provided
                    if 'full_name' in fallback_fields_to_update or 'phone_number' in fallback_fields_to_update:
                        pipedrive_contact_id = get_contact_id_by_username(sender_username)
                        if pipedrive_contact_id is not None:  # type: ignore
                            update_pipedrive_contact_fields(
                                pipedrive_contact_id,
                                instagram_username=sender_username,
                                phone=fallback_fields_to_update.get('phone_number')
                            )
                            logger.info("✅ Updated Pipedrive contact from fallback")
                        
                        # 🚨 RESET CONTACT_NUMBER_ASKED FLAG
                        if 'phone_number' in fallback_fields_to_update:
                            logger.info("📞 Phone number provided - resetting contact_number_asked flag to False")
                            _reset_contact_number_asked_flag(deal_id)
                        
                        # If event date was provided, reset the event_date_asked flag
                        if 'event_date' in fallback_fields_to_update:
                            logger.info("📅 Event date provided - resetting event_date_asked flag to False")
                            _reset_event_date_asked_flag(deal_id)
                        
                        # If venue was provided, reset the venue_asked flag
                        if 'venue' in fallback_fields_to_update:
                            logger.info("🏢 Venue provided - resetting venue_asked flag to False")
                            _reset_venue_asked_flag(deal_id)
                    
                    # Update Pipedrive deal with extracted event details
                    deal_fields_to_update = {k: v for k, v in fallback_fields_to_update.items() 
                                           if k in ['event_type', 'event_date', 'venue']}
                    if deal_fields_to_update:
                        update_pipedrive_deal_fields(
                            pipedrive_deal_id,
                            event_type=deal_fields_to_update.get('event_type'),
                            event_date=deal_fields_to_update.get('event_date'),
                            venue=deal_fields_to_update.get('venue'),
                            conversation_summary=f"User: {message_text}",
                            full_name=fallback_fields_to_update.get('full_name'),
                            phone=fallback_fields_to_update.get('phone_number')
                        )
                        logger.info("✅ Updated Pipedrive deal from fallback extraction")
            
            fallback_message = "Thank you for your message! Our team will get back to you soon. 🌸"
            send_instagram_message(brideside_user=brideside_user,message_id=message_id, sender_username=sender_username, sender_id=sender_id, message=fallback_message, access_token=access_token, user_id=brideside_user.id)
            logger.info("Sent fallback message to %s: %s", sender_username, fallback_message)
    
    return True, "Processed"


def _extract_messaging_events(data: dict) -> list:
    """Extract messaging events from webhook data."""
    try:
        messaging_events = []
        entries = data.get("entry", [])
        
        for entry in entries:
            messaging = entry.get("messaging", [])
            for event in messaging:
                # Only include events with actual messages (not read receipts, etc.)
                if "message" in event and event["message"].get("text"):
                    messaging_events.append(event)
        
        return messaging_events
    except Exception as e:
        logger.error("❌ Error extracting messaging events: %s", e)
        return []


def _handle_post_request() -> tuple[str, int]:
    """Handle POST requests for webhook processing."""
    data = request.get_json()
    logger.info("Received webhook data:")
    logger.info("data: %s", json.dumps(data, indent=2))
    
    # Validate webhook data
    is_valid, error_msg = _validate_webhook_data(data)
    if not is_valid:
        logger.info(f"{error_msg} in webhook data")
        return error_msg, 200
    
    
    
    # Extract messaging event
    entry = data.get("entry", [])[0]
    messaging_event = entry["messaging"][0]
    
    sender_id = messaging_event["sender"]["id"]
    recipient_id = messaging_event["recipient"]["id"]
    message = messaging_event.get("message", {})
    message_text = message.get("text", "").strip()
    message_id = message.get("mid", "")
    
    logger.info("sender_id: %s", sender_id)
    logger.info("recipient_id: %s", recipient_id)
    logger.info("message_text: %s", message_text)
    logger.info("message_id: %s", message_id)
    
    # Check if message should be skipped
    should_skip, skip_reason = _should_skip_message(sender_id, recipient_id, message_text, message)
    if should_skip:
        logger.info(f"🛑 {skip_reason}. Skipping.")
        return skip_reason, 200
    
    logger.info("✅ Valid conversation. Proceeding...")
    
    # 🚨 CRITICAL FIX: Check for message deduplication FIRST, before any other processing
    if message_id and is_message_processed(message_id):
        logger.info("🔄 Message %s already processed. Skipping duplicate.", message_id)
        return "Message already processed", 200
    
   
    
    # Get brideside user by Instagram account ID (recipient_id)
    brideside_user: BridesideUser = get_brideside_user_by_ig_account_id(recipient_id) # type: ignore
    
     # Mark message as processed
   
            
    if brideside_user:
        logger.info("User ID: %s, Organization ID: %s, Pipeline ID: %s", brideside_user.id, brideside_user.organization_id, brideside_user.pipeline_id)
        logger.info("Instagram Account ID: %s", brideside_user.ig_account_id)
        
        # Get usernames using the user's access token
        brideside_username = get_instagram_username(recipient_id, brideside_user.access_token, brideside_user.id)
        sender_username = get_instagram_username(sender_id, brideside_user.access_token, brideside_user.id)
        if message_id:
            # TODO: Pass the actual reply sent to the user as message_reply
            mark_message_as_processed(message_id, message_text, "", brideside_user.id, sender_username)
            logger.info("✅ Marked message %s as processed", message_id)
        logger.info("Recipient username: %s", brideside_username)
        logger.info("Sender username: %s", sender_username)
    else:
        logger.error("No brideside user found for Instagram account ID: %s", recipient_id)
        return "No brideside user found", 400
    
    
    # Handle user message flow
    success, result_msg = _handle_user_message_flow(message_text, sender_username, brideside_user, recipient_id, sender_id, message_id)
    if not success:
        return result_msg, 500
    
    # Occasionally clean up old processed messages (every 100th message)
    import random
    if random.randint(1, 100) == 1:
        cleanup_old_processed_messages(days_old=2)
    
    return result_msg, 200


def handle_webhook() -> tuple[str, int]:
    """Main webhook handler function."""
    try:
        logger.info("Your message")
        
        if request.method == "GET":
            return _handle_get_request()
        
        if request.method == "POST":
            return _handle_post_request()
        
        # Default return for unhandled HTTP methods
        return "Method not allowed", 405

    except KeyError as e:
        logger.error("❌ KeyError: %s", e)
        logger.info("🔎 Raw data: %s", request.get_json())
        return "Missing required field", 400

    except Exception as e:
        logger.error("❌ Unexpected Exception: %s", e)
        traceback.print_exc()
        return "Internal Server Error", 500


def to_int(val):
    # Handles SQLAlchemy columns, None, and plain ints
    if hasattr(val, 'id'):
        return int(val.id)
    try:
        return int(val)
    except Exception:
        return 0
