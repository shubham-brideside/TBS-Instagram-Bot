#!/usr/bin/env python3
"""
Debug script to test Pipedrive deal field mapping
"""

import requests
import json
from config import PIPEDRIVE_API_TOKEN, PIPEDRIVE_BASE_URL, PIPEDRIVE_CONTACT_FIELDS, PIPEDRIVE_DEAL_FIELDS

def test_pipedrive_connection():
    """Test basic Pipedrive API connection"""
    url = f"{PIPEDRIVE_BASE_URL}/v1/deals?api_token={PIPEDRIVE_API_TOKEN}&limit=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        print("✅ Pipedrive API connection successful")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Pipedrive API connection failed: {e}")
        return False

def get_deal_fields():
    """Get all available deal fields from Pipedrive"""
    url = f"{PIPEDRIVE_BASE_URL}/v1/dealFields?api_token={PIPEDRIVE_API_TOKEN}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        print("\n📋 Available Deal Fields:")
        print("-" * 80)
        
        for field in data.get('data', []):
            field_key = field.get('key', 'N/A')
            field_name = field.get('name', 'N/A')
            field_type = field.get('field_type', 'N/A')
            
            print(f"Key: {field_key}")
            print(f"Name: {field_name}")
            print(f"Type: {field_type}")
            print("-" * 40)
            
        return data.get('data', [])
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get deal fields: {e}")
        return []

def test_deal_update(deal_id, test_payload):
    """Test updating a deal with specific payload"""
    url = f"{PIPEDRIVE_BASE_URL}/v1/deals/{deal_id}?api_token={PIPEDRIVE_API_TOKEN}"
    
    print(f"\n🧪 Testing deal update for deal ID: {deal_id}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    
    try:
        response = requests.put(url, json=test_payload)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Deal update successful")
            return True
        else:
            print(f"❌ Deal update failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def validate_field_mappings():
    """Validate the current field mappings"""
    current_mappings = PIPEDRIVE_DEAL_FIELDS.copy()
    contact_mappings = PIPEDRIVE_CONTACT_FIELDS.copy()
    
    print("\n🔍 Current Deal Field Mappings:")
    print("-" * 70)
    
    fields = get_deal_fields()
    field_keys = [field.get('key') for field in fields]
    
    # Create a mapping of key to field info for easier lookup
    field_info = {field.get('key'): field for field in fields}
    
    for field_name, field_key in current_mappings.items():
        if field_key in field_keys:
            field_data = field_info[field_key]
            field_display_name = field_data.get('name', 'Unknown')
            field_type = field_data.get('field_type', 'Unknown')
            print(f"✅ {field_name}: {field_key}")
            print(f"   └─ Display Name: {field_display_name}")
            print(f"   └─ Type: {field_type}")
        else:
            print(f"❌ {field_name}: {field_key} (INVALID)")
        print()
    
    print("\n🔍 Current Contact Field Mappings:")
    print("-" * 70)
    
    for field_name, field_key in contact_mappings.items():
        print(f"📞 {field_name}: {field_key}")
        print(f"   └─ Note: Contact field validation requires separate API call")
        print()
    
    return current_mappings

def main():
    print("🔧 Pipedrive Deal Mapping Debug Tool")
    print("=" * 50)
    
    # Test connection
    if not test_pipedrive_connection():
        return
    
    # Get and display all deal fields
    get_deal_fields()
    
    # Validate current mappings
    validate_field_mappings()
    
    # Test with a sample deal (you'll need to provide a real deal ID)
    print("\n" + "=" * 50)
    print("To test deal updates, you need to:")
    print("1. Find a real deal ID from your Pipedrive account")
    print("2. Run: test_deal_update(DEAL_ID, {'field_key': 'test_value'})")
    print("3. Check the response for errors")

if __name__ == "__main__":
    main() 