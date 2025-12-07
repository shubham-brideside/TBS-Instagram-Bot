import requests
from typing import Optional, Tuple
from utils.logger import logger
from repository.brideside_vendor_repository import update_brideside_vendor_access_token


class TokenRefreshService:
    """Service to handle Instagram access token refresh"""
    
    @staticmethod
    def refresh_access_token(current_access_token: str, user_id: int) -> Optional[str]:
        """
        Refresh Instagram access token and update in database
        
        Args:
            current_access_token: Current access token to refresh
            user_id: Brideside user ID to update in database
            
        Returns:
            New access token if successful, None if failed
        """
        try:
            # Make API call to refresh token
            refresh_url = "https://graph.instagram.com/refresh_access_token"
            params = {
                "grant_type": "ig_refresh_token",
                "access_token": current_access_token
            }
            
            logger.info(f"Refreshing access token for user {user_id}")
            response = requests.get(refresh_url, params=params)
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get("access_token")
                token_type = token_data.get("token_type")
                expires_in = token_data.get("expires_in")
                
                logger.info(f"✅ Successfully refreshed token for user {user_id}")
                logger.info(f"Token type: {token_type}, Expires in: {expires_in} seconds")
                
                # Update token in database
                update_success = update_brideside_vendor_access_token(user_id, new_access_token)
                if update_success:
                    logger.info(f"✅ Updated access token in database for user {user_id}")
                    return new_access_token
                else:
                    logger.error(f"❌ Failed to update access token in database for user {user_id}")
                    return None
                    
            else:
                logger.error(f"❌ Failed to refresh token for user {user_id}: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Exception during token refresh for user {user_id}: {e}")
            return None
    
    @staticmethod
    def is_token_expired_error(error_response: dict) -> bool:
        """
        Check if the error response indicates an expired token
        
        Args:
            error_response: Error response from Instagram API
            
        Returns:
            True if token is expired, False otherwise
        """
        try:
            if "error" in error_response:
                error_info = error_response["error"]
                
                # Check for common expired token error codes/messages
                error_code = error_info.get("code")
                error_message = error_info.get("message", "").lower()
                error_type = error_info.get("type", "").lower()
                
                # Instagram expired token indicators
                expired_indicators = [
                    "expired",
                    "invalid_token",
                    "access token has expired",
                    "token has expired",
                    "oauth exception"
                ]
                
                # Check error code (190 is common for expired tokens)
                if error_code in [190, 102]:
                    return True
                
                # Check error message and type
                for indicator in expired_indicators:
                    if indicator in error_message or indicator in error_type:
                        return True
                        
            return False
            
        except Exception as e:
            logger.error(f"Error checking token expiration: {e}")
            return False
    
    @staticmethod
    def handle_token_refresh_if_needed(response_text: str, user_id: int, current_token: str) -> Optional[str]:
        """
        Check if API response indicates expired token and refresh if needed
        
        Args:
            response_text: Raw response text from Instagram API
            user_id: Brideside user ID
            current_token: Current access token
            
        Returns:
            New access token if refreshed, None if no refresh needed or failed
        """
        try:
            import json
            response_data = json.loads(response_text)
            
            if TokenRefreshService.is_token_expired_error(response_data):
                logger.info(f"🔄 Detected expired token for user {user_id}, attempting refresh...")
                return TokenRefreshService.refresh_access_token(current_token, user_id)
                
            return None
            
        except json.JSONDecodeError:
            # If response is not JSON, it's likely not an error response
            return None
        except Exception as e:
            logger.error(f"Error handling token refresh: {e}")
            return None


# Create a singleton instance
token_refresh_service = TokenRefreshService() 