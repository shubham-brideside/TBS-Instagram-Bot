import requests
from config import PIPEDRIVE_API_TOKEN, PIPEDRIVE_BASE_URL, PIPEDRIVE_CONTACT_FIELDS, PIPEDRIVE_DEAL_FIELDS
from utils.logger import logger  # <-- Add this import


def create_pipedrive_contact(username, instagram_username=None, lead_date=None):
    url = f"{PIPEDRIVE_BASE_URL}/v1/persons?api_token={PIPEDRIVE_API_TOKEN}"
    payload = {"name": username, "visible_to": 3}
    
    # Add Instagram_Id custom field with username if provided
    if instagram_username:
        payload[PIPEDRIVE_CONTACT_FIELDS['instagram_id']] = instagram_username
        payload[PIPEDRIVE_CONTACT_FIELDS['lead_date']] = lead_date
    
    
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        contact_id = response.json()["data"]["id"]
        logger.info(f"Created Pipedrive contact: {username} (ID: {contact_id}) with Instagram Username: {instagram_username}")
        return True, contact_id
    logger.error(f"Failed to create Pipedrive contact: {response.text}")
    return False, None


def update_pipedrive_contact_fields(contact_id, phone=None, instagram_username=None):
    """
    Update Pipedrive contact fields (phone and Instagram username only).
    Note: Contact name is kept as Instagram username and not updated.
    """
    url = f"{PIPEDRIVE_BASE_URL}/v1/persons/{contact_id}?api_token={PIPEDRIVE_API_TOKEN}"
    payload = {}
    if phone:
        payload["phone"] = phone
    if instagram_username:
        payload[PIPEDRIVE_CONTACT_FIELDS['instagram_id']] = instagram_username
    if not payload:
        return
    response = requests.put(url, json=payload)
    if response.status_code == 200:
        print("✅ Updated Pipedrive contact fields")
    else:
        print(f"❌ Failed to update Pipedrive contact: {response.text}")


def update_pipedrive_deal_fields(deal_id, event_type=None, event_date=None, venue=None, conversation_summary=None, full_name=None, phone=None):
    """Update Pipedrive deal fields with extracted information."""
    url = f"{PIPEDRIVE_BASE_URL}/v1/deals/{deal_id}?api_token={PIPEDRIVE_API_TOKEN}"
    payload = {}
    
    # Map fields to Pipedrive custom fields using configurable field mappings
    if event_type:
        payload[PIPEDRIVE_DEAL_FIELDS['event_type']] = event_type
    if event_date:
        payload[PIPEDRIVE_DEAL_FIELDS['event_date']] = event_date
    if venue:
        payload[PIPEDRIVE_DEAL_FIELDS['venue']] = venue
    if conversation_summary:
        payload[PIPEDRIVE_DEAL_FIELDS['conversation_summary']] = conversation_summary
    if full_name:
        payload[PIPEDRIVE_DEAL_FIELDS['full_name']] = full_name
    if phone:
        payload[PIPEDRIVE_DEAL_FIELDS['phone']] = phone
    
    if not payload:
        logger.info("No fields to update in Pipedrive deal")
        return True
    
    try:
        logger.info(f"Updating Pipedrive deal {deal_id} at URL: {url}")
        logger.info(f"Payload being sent: {payload}")
        response = requests.put(url, json=payload)
        if response.status_code != 200:
            logger.error(f"❌ Failed to update Pipedrive deal {deal_id}: {response.status_code} {response.text}")
            logger.error(f"Payload was: {payload}")
            return False
        logger.info(f"✅ Updated Pipedrive deal {deal_id} with fields: {list(payload.keys())}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Exception while updating Pipedrive deal {deal_id}: {e}")
        return False


def create_pipedrive_deal(username, organization_id, pipeline_id, contact_id, business_name=None):
    url = f"{PIPEDRIVE_BASE_URL}/v1/deals?api_token={PIPEDRIVE_API_TOKEN}"
    payload = {
        "title": username + "  " + business_name +" deal",
        "org_id": organization_id,
        "pipeline_id": pipeline_id,
        "person_id": contact_id
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # raise exception for HTTP errors

        deal_data = response.json()
        pipedrive_deal_id = deal_data["data"]["id"]

        logger.info(f"Created Pipedrive deal: {pipedrive_deal_id}")
        return True, pipedrive_deal_id

    except requests.exceptions.RequestException as req_err:
        logger.error(f"HTTP request error while creating deal: {req_err}")
    except (KeyError, TypeError, ValueError) as parse_err:
        logger.error(f"Error parsing response: {parse_err}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    return False, None


def user_exists(username):
    url = f"{PIPEDRIVE_BASE_URL}/v1/persons/find?api_token={PIPEDRIVE_API_TOKEN}"
    params = {"term": username}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        user = data["data"]

        if user:
            logger.info(f"User exists: {user}")
            return user  # This returns True if user exists, otherwise False
        else:
            logger.error("User does not exist")
    else:
        logger.error(f"Failed to check user existence: {response.text}")

    return False

