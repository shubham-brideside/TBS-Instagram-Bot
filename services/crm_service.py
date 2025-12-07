import requests
import os
from typing import Optional, Dict, Any, List
from datetime import date
from utils.logger import logger
from config import DB_CONFIG


class CRMService:
    """Service to interact with BridesideCRM_Backend API"""
    
    def __init__(self):
        # Get CRM backend base URL from environment or use default
        from config import CRM_BACKEND_URL, CRM_AUTH_TOKEN
        self.base_url = CRM_BACKEND_URL
        # Remove trailing slash if present
        self.base_url = self.base_url.rstrip('/')
        # JWT token for authentication (if needed)
        self.auth_token = CRM_AUTH_TOKEN
        self.headers = {
            "Content-Type": "application/json"
        }
        if self.auth_token:
            self.headers["Authorization"] = f"Bearer {self.auth_token}"
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request to CRM backend API"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=data)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"CRM API request failed: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making CRM API request: {e}")
            return None
    
    def create_person(self, name: str, instagram_id: Optional[str] = None, 
                     phone: Optional[str] = None, email: Optional[str] = None,
                     organization_id: Optional[int] = None,
                     owner_id: Optional[int] = None,
                     category_id: Optional[int] = None,
                     lead_date: Optional[date] = None,
                     source: Optional[str] = "Direct",
                     sub_source: Optional[str] = "Instagram") -> Optional[int]:
        """
        Create a person in the CRM backend.
        
        Returns:
            Person ID if successful, None otherwise
        """
        payload = {
            "name": name
        }
        
        if instagram_id:
            payload["instagramId"] = instagram_id
        if phone:
            payload["phone"] = phone
        if email:
            payload["email"] = email
        if organization_id:
            payload["organizationId"] = organization_id
        if owner_id:
            payload["ownerId"] = owner_id
        if category_id:
            payload["categoryId"] = category_id
        if lead_date:
            payload["leadDate"] = lead_date.isoformat() if isinstance(lead_date, date) else lead_date
        if source:
            payload["source"] = source
        if sub_source:
            payload["subSource"] = sub_source
        
        response = self._make_request("POST", "/api/persons", payload)
        
        if response and "id" in response:
            person_id = response["id"]
            logger.info(f"✅ Created person in CRM: {name} (ID: {person_id})")
            return person_id
        else:
            logger.error(f"❌ Failed to create person in CRM: {name}")
            return None
    
    def get_organization(self, organization_id: int) -> Optional[Dict]:
        """
        Get organization by ID from CRM backend.
        
        Returns:
            Organization data if found, None otherwise
        """
        response = self._make_request("GET", f"/api/organizations/{organization_id}")
        
        if response and "data" in response:
            return response["data"]
        elif response:
            # If response is the organization directly (not wrapped)
            return response
        return None
    
    def get_categories(self) -> Optional[List[Dict]]:
        """
        Get list of categories from CRM backend.
        
        Returns:
            List of categories if successful, None otherwise
        """
        response = self._make_request("GET", "/api/persons/categories")
        
        if response and "data" in response:
            return response["data"]
        elif isinstance(response, list):
            return response
        return None
    
    def get_pipeline_stages(self, pipeline_id: int) -> Optional[List[Dict]]:
        """
        Get list of stages for a pipeline from CRM backend.
        
        Returns:
            List of stages if successful, None otherwise
        """
        response = self._make_request("GET", f"/api/pipelines/{pipeline_id}/stages")
        
        if response and "data" in response:
            return response["data"]
        elif isinstance(response, list):
            return response
        return None
    
    def get_stage_by_name(self, pipeline_id: int, stage_name: str) -> Optional[int]:
        """
        Get stage ID by name from a pipeline.
        
        Returns:
            Stage ID if found, None otherwise
        """
        stages = self.get_pipeline_stages(pipeline_id)
        if not stages:
            return None
        
        # Search for stage by name (case-insensitive)
        for stage in stages:
            if stage.get("name", "").lower() == stage_name.lower():
                return stage.get("id")
        
        return None
    
    def update_person(self, person_id: int, instagram_id: Optional[str] = None,
                     phone: Optional[str] = None, email: Optional[str] = None) -> bool:
        """
        Update person fields in the CRM backend.
        
        Returns:
            True if successful, False otherwise
        """
        payload = {}
        
        if instagram_id is not None:
            payload["instagramId"] = instagram_id
        if phone is not None:
            payload["phone"] = phone
        if email is not None:
            payload["email"] = email
        
        if not payload:
            logger.info("No fields to update for person")
            return True
        
        response = self._make_request("PUT", f"/api/persons/{person_id}", payload)
        
        if response:
            logger.info(f"✅ Updated person {person_id} in CRM")
            return True
        else:
            logger.error(f"❌ Failed to update person {person_id} in CRM")
            return False
    
    def get_person_by_name(self, name: str) -> Optional[Dict]:
        """
        Search for a person by name in the CRM backend.
        
        Returns:
            Person data if found, None otherwise
        """
        # The API returns a Page object, so we need to check the structure
        response = self._make_request("GET", "/api/persons", {"q": name, "size": 1})
        
        if response:
            # Check if it's a Page object with content
            if "content" in response:
                persons = response["content"]
                if persons:
                    # Find exact match by name
                    for person in persons:
                        if person.get("name") == name:
                            return person
            # Check if it's a list directly
            elif isinstance(response, list):
                for person in response:
                    if person.get("name") == name:
                        return person
        
        return None
    
    def create_deal(self, name: str, person_id: int, organization_id: int, 
                   pipeline_id: int, value: float = 0.0,
                   stage_id: Optional[int] = None,
                   category_id: Optional[int] = None,
                   event_type: Optional[str] = None,
                   event_date: Optional[str] = None,
                   event_dates: Optional[List[str]] = None,
                   venue: Optional[str] = None,
                   phone_number: Optional[str] = None,
                   user_name: Optional[str] = None,
                   source: Optional[str] = "Direct",
                   sub_source: Optional[str] = "Instagram",
                   status: Optional[str] = "IN_PROGRESS") -> Optional[int]:
        """
        Create a deal in the CRM backend.
        
        Returns:
            Deal ID if successful, None otherwise
        """
        from decimal import Decimal
        
        payload = {
            "name": name,
            "personId": person_id,
            "organizationId": organization_id,
            "pipelineId": pipeline_id,
            "value": float(value),
            "source": source,
            "subSource": sub_source,
            "createdBy": "BOT"  # Mark deal as created by bot
        }
        
        if status:
            payload["status"] = status
        if stage_id:
            payload["stageId"] = stage_id
        if category_id:
            payload["categoryId"] = category_id
        if event_type:
            payload["eventType"] = event_type
        if event_date:
            payload["eventDate"] = event_date
        if event_dates:
            payload["eventDates"] = event_dates
        if venue:
            payload["venue"] = venue
        if phone_number:
            payload["phoneNumber"] = phone_number
        if user_name:
            payload["userName"] = user_name
        
        response = self._make_request("POST", "/api/deals", payload)
        
        if response and "id" in response:
            deal_id = response["id"]
            logger.info(f"✅ Created deal in CRM: {name} (ID: {deal_id})")
            return deal_id
        else:
            logger.error(f"❌ Failed to create deal in CRM: {name}")
            return None
    
    def update_deal(self, deal_id: int, event_type: Optional[str] = None,
                   event_date: Optional[str] = None,
                   venue: Optional[str] = None,
                   phone_number: Optional[str] = None,
                   user_name: Optional[str] = None,
                   conversation_summary: Optional[str] = None) -> bool:
        """
        Update deal fields in the CRM backend.
        
        Note: conversation_summary is not directly supported by the CRM backend API,
        so it will be logged but not sent to the API.
        
        Returns:
            True if successful, False otherwise
        """
        payload = {}
        
        if event_type is not None:
            payload["eventType"] = event_type
        if event_date is not None:
            payload["eventDate"] = event_date
        if venue is not None:
            payload["venue"] = venue
        if phone_number is not None:
            payload["phoneNumber"] = phone_number
        if user_name is not None:
            payload["userName"] = user_name
        
        # Note: conversation_summary is not part of the Deal DTO, so we log it but don't send it
        if conversation_summary:
            logger.info(f"Conversation summary received for deal {deal_id} (not sent to CRM API as it's not supported)")
        
        if not payload:
            logger.info("No fields to update for deal")
            return True
        
        response = self._make_request("PATCH", f"/api/deals/{deal_id}", payload)
        
        if response:
            logger.info(f"✅ Updated deal {deal_id} in CRM")
            return True
        else:
            logger.error(f"❌ Failed to update deal {deal_id} in CRM")
            return False
    
    def update_deal_stage(self, deal_id: int, stage_id: int) -> bool:
        """
        Update deal stage in the CRM backend.
        This will trigger activity creation if moving from "Lead In" to "Qualified".
        
        Returns:
            True if successful, False otherwise
        """
        payload = {
            "stageId": stage_id
        }
        
        logger.info(f"Calling backend API: PUT /api/deals/{deal_id}/stage with payload: {payload}")
        response = self._make_request("PUT", f"/api/deals/{deal_id}/stage", payload)
        
        if response:
            logger.info(f"✅ Updated deal {deal_id} stage to {stage_id} in CRM - Response: {response}")
            return True
        else:
            logger.error(f"❌ Failed to update deal {deal_id} stage in CRM - No response or error occurred")
            return False
    
    def get_stage_by_name(self, pipeline_id: int, stage_name: str) -> Optional[int]:
        """
        Get stage ID by name from a pipeline.
        
        Returns:
            Stage ID if found, None otherwise
        """
        stages = self.get_pipeline_stages(pipeline_id)
        if not stages:
            return None
        
        # Search for stage by name (case-insensitive)
        for stage in stages:
            if stage.get("name", "").lower() == stage_name.lower():
                return stage.get("id")
        
        return None


# Create a singleton instance
crm_service = CRMService()

