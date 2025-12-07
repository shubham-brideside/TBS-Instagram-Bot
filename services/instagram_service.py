import requests
from config import ACCESS_TOKEN, GREETING_TEMPLATES
from datetime import datetime, timezone, timedelta
from time import sleep
from models.brideside_vendor import BridesideVendor
from models.processed_message import ProcessedMessage
from repository.conversation_repository import ConversationRepository
from repository.processed_message_repository import mark_message_as_processed
from utils.logger import logger
from typing import Optional
from repository.greeting_template_repository import get_greeting_templates_by_user_id



def _handle_token_refresh_and_retry(response, user_id: int, current_token: str, retry_function, *args, **kwargs):
    """
    Handle token refresh and retry the original request
    
    Args:
        response: Failed response from Instagram API
        user_id: Brideside user ID
        current_token: Current access token
        retry_function: Function to retry after token refresh
        *args, **kwargs: Arguments to pass to retry function
        
    Returns:
        Result of retry function or None if refresh failed
    """
    try:
        from services.token_refresh_service import token_refresh_service
        
        # Check if token refresh is needed
        new_token = token_refresh_service.handle_token_refresh_if_needed(
            response.text, user_id, current_token
        )
        
        if new_token:
            # Update the access_token in kwargs for retry
            kwargs['access_token'] = new_token
            logger.info(f"🔄 Retrying request with refreshed token for user {user_id}")
            return retry_function(*args, **kwargs)
        else:
            logger.error(f"❌ Token refresh failed or not needed for user {user_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error during token refresh handling: {e}")
        return None


def send_instagram_message(sender_id, message, brideside_user: BridesideVendor, message_id, sender_username, access_token=None, user_id=None):
    """Send Instagram message using provided access token or fallback to global config"""
    try:
        # Use provided access token or fallback to global config
        token = access_token or ACCESS_TOKEN
        
        url = f"https://graph.instagram.com/v23.0/{brideside_user.ig_account_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "recipient": {"id": sender_id},
            "message": {"text": message}
        }

        logger.info(f"Sending message to user {sender_id}: {message}")
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            logger.info("Message sent successfully!")
            if message_id:
                success = mark_message_as_processed(message_id, message, message, brideside_user.id, instagram_username = sender_username)
                if success:
                    logger.info("✅ Marked message %s as processed", message_id)
                else:
                    logger.info("ℹ️ Message %s was already processed (race condition)", message_id)
           
            return True
        else:
            logger.error(f"Failed to send message: {response.status_code}")
            logger.error(f"Error response: {response.text}")
            
            # Try token refresh if user_id is provided and we have a specific token
            if user_id and access_token and response.status_code in [401, 403]:
                logger.info("🔄 Attempting token refresh for send_instagram_message")
                result = _handle_token_refresh_and_retry(
                    response, user_id, access_token, send_instagram_message,
                    brideside_user.id, sender_id, message
                )
                return result if result is not None else False
            
            return False
            
    except Exception as e:
        logger.error(f"Exception sending message: {e}")
        return False


def get_instagram_username(user_id, access_token=None, brideside_user_id=None):
    """Get Instagram username using provided access token or fallback to global config"""
    # Use provided access token or fallback to global config
    token = access_token or ACCESS_TOKEN
    
    url = f"https://graph.instagram.com/v2.0/{user_id}?fields=username&access_token={token}"
    response = requests.get(url)
    
    if response.status_code == 200:
        try:
            data = response.json()
            if "error" in data:
                # Check if it's a token expiration error
                error_info = data["error"]
                if error_info.get("code") == 190 or "expired" in error_info.get("message", "").lower():
                    logger.error(f"Token expired for {user_id}: {response.text}")
                    
                    # Try token refresh if brideside_user_id is provided and we have a specific token
                    if brideside_user_id and access_token:
                        logger.info("🔄 Attempting token refresh for get_instagram_username")
                        result = _handle_token_refresh_and_retry(
                            response, brideside_user_id, access_token, get_instagram_username,
                            user_id, access_token, brideside_user_id
                        )
                        return result if result is not None else None
                else:
                    logger.error(f"API error for {user_id}: {response.text}")
                return None
            else:
                return data.get("username", "User")
        except Exception as e:
            logger.error(f"Error parsing response for {user_id}: {e}")
            return None
    else:
        logger.error(f"Failed to get username for {user_id}: {response.status_code} - {response.text}")
        
        # Check if it's a token expiration error even with non-200 status codes
        try:
            data = response.json()
            if "error" in data:
                error_info = data["error"]
                if error_info.get("code") == 190 or "expired" in error_info.get("message", "").lower():
                    logger.error(f"Token expired for {user_id}: {response.text}")
                    
                    # Try token refresh if brideside_user_id is provided and we have a specific token
                    if brideside_user_id and access_token:
                        logger.info("🔄 Attempting token refresh for get_instagram_username")
                        result = _handle_token_refresh_and_retry(
                            response, brideside_user_id, access_token, get_instagram_username,
                            user_id, access_token, brideside_user_id
                        )
                        return result if result is not None else None
        except:
            pass  # If JSON parsing fails, continue with normal error handling
        
        # Try token refresh if brideside_user_id is provided and we have a specific token
        if brideside_user_id and access_token and response.status_code in [400, 401, 403]:
            logger.info("🔄 Attempting token refresh for get_instagram_username")
            result = _handle_token_refresh_and_retry(
                response, brideside_user_id, access_token, get_instagram_username,
                user_id, access_token, brideside_user_id
            )
            return result if result is not None else None


def checkIfUserIsAlreadyContactedOrFriend(user_id, access_token=None, brideside_user_id=None):
    """Check if user is already contacted using provided access token or fallback to global config"""
    # Use provided access token or fallback to global config
    token = access_token or ACCESS_TOKEN
    
    url = f"https://graph.instagram.com/v23.0/me/conversations?user_id={user_id}&access_token={token}&fields=particants,messages{{created_time,message,from}}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        # Check if response contains an error (like expired token)
        if "error" in data:
            error_info = data["error"]
            if error_info.get("code") == 190 or "expired" in error_info.get("message", "").lower():
                logger.error(f"Token expired for {user_id}: {response.text}")
                
                # Try token refresh if brideside_user_id is provided and we have a specific token
                if brideside_user_id and access_token:
                    logger.info("🔄 Attempting token refresh for checkIfUserIsAlreadyContactedOrFriend")
                    result = _handle_token_refresh_and_retry(
                        response, brideside_user_id, access_token, checkIfUserIsAlreadyContactedOrFriend,
                        user_id, access_token, brideside_user_id
                    )
                    return result if result is not None else False
            else:
                logger.error(f"API error for {user_id}: {response.text}")
            return False
        
        try:
            messages = data['data'][0]['messages']['data']
            if not messages:
                 # Check if the last message was sent today
                logger.info("No Previous Conversations found for ",user_id)
                return False  # No messages found
            
            # Get last message's created_time
            last_created_time_str = messages[-1]['created_time']
            
            # Convert to datetime object (UTC)
            last_created_time = datetime.strptime(last_created_time_str, "%Y-%m-%dT%H:%M:%S%z")
            last_created_date = last_created_time.date()

            # Get current UTC date
            # today_utc = datetime.now(timezone.utc).date()
            
            # Date 5 days ago from today
            # change the date range based on the last conversation if you want to send a message to the user
            five_days_ago = (datetime.now(timezone.utc) - timedelta(days=100)).date()

            # Check if the last message is from yesterday or earlier
            return last_created_date < five_days_ago

        except Exception as e:
            logger.error("Error checking date:", e)
            return False
    else:
        logger.error(f"Failed to check if user is contacted: {response.text}")
        
        # Check if it's a token expiration error even with non-200 status codes
        try:
            data = response.json()
            if "error" in data:
                error_info = data["error"]
                if error_info.get("code") == 190 or "expired" in error_info.get("message", "").lower():
                    logger.error(f"Token expired for {user_id}: {response.text}")
                    
                    # Try token refresh if brideside_user_id is provided and we have a specific token
                    if brideside_user_id and access_token:
                        logger.info("🔄 Attempting token refresh for checkIfUserIsAlreadyContactedOrFriend")
                        result = _handle_token_refresh_and_retry(
                            response, brideside_user_id, access_token, checkIfUserIsAlreadyContactedOrFriend,
                            user_id, access_token, brideside_user_id
                        )
                        return result if result is not None else False
        except:
            pass  # If JSON parsing fails, continue with normal error handling
        
        # Try token refresh if brideside_user_id is provided and we have a specific token
        if brideside_user_id and access_token and response.status_code in [400, 401, 403]:
            logger.info("🔄 Attempting token refresh for checkIfUserIsAlreadyContactedOrFriend")
            result = _handle_token_refresh_and_retry(
                response, brideside_user_id, access_token, checkIfUserIsAlreadyContactedOrFriend,
                user_id, access_token, brideside_user_id
            )
            return result if result is not None else False
        
        return False


def send_initial_greetings_message(sender_id, brideside_user: BridesideVendor, message_id: str, instagram_username, access_token=None, user_id=None):
    """Send initial greetings message dynamically from DB, or fallback to static list"""

    # Try fetching templates from DB
    greeting_templates = get_greeting_templates_by_user_id(brideside_user.id)

    # Fallback if DB returns empty
    if not greeting_templates:
        greeting_templates = [
            'Hi there! ✨',
            'Hope you are doing good!',
            (
                "Welcome to The Bride Side — your one-stop destination for wedding photography, "
                "makeup, planning and decor services.\n"
                "Could you please tell us what you’re looking for?\n\n"
                "• Wedding Photography / Pre-wedding Photoshoot\n"
                "• Bridal Makeup / Party Makeup\n"
                "• Wedding Planner\n"
                "• Wedding Decor"
            )
        ]

    conversation_summary = ""

    for idx, message_reply in enumerate(greeting_templates, 1):
        conversation_summary += message_reply + "\n"
        success = send_instagram_message(
            sender_id, message_reply, brideside_user,
            message_id, instagram_username, access_token, user_id
        )
        if not success:
            logger.error(f"Failed to send step {idx} of initial greeting to user {sender_id}")
            return False

        logger.info(f"Step {idx} of initial greeting sent to user {sender_id}")
        sleep(1 * (idx + 1))

    logger.info(f"Initial message sequence sent to user {sender_id}")
    return True

