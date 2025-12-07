#!/usr/bin/env python3
"""
Simple validation script to check Pipedrive field mappings
"""

from config import PIPEDRIVE_DEAL_FIELDS, PIPEDRIVE_CONTACT_FIELDS

def validate_field_mappings():
    """Validate that all required field mappings are configured"""
    print("🔧 Pipedrive Field Mapping Validation")
    print("=" * 50)
    
    # Expected deal fields
    expected_deal_fields = [
        'event_type',
        'event_date', 
        'venue',
        'conversation_summary'
    ]
    
    # Expected contact fields  
    expected_contact_fields = [
        'instagram_username'
    ]
    
    print("\n📋 Deal Field Mappings:")
    print("-" * 30)
    
    missing_deal_fields = []
    for field in expected_deal_fields:
        if field in PIPEDRIVE_DEAL_FIELDS:
            field_id = PIPEDRIVE_DEAL_FIELDS[field]
            print(f"✅ {field}: {field_id}")
        else:
            print(f"❌ {field}: MISSING")
            missing_deal_fields.append(field)
    
    print("\n📞 Contact Field Mappings:")
    print("-" * 30)
    
    missing_contact_fields = []
    for field in expected_contact_fields:
        if field in PIPEDRIVE_CONTACT_FIELDS:
            field_id = PIPEDRIVE_CONTACT_FIELDS[field]
            print(f"✅ {field}: {field_id}")
        else:
            print(f"❌ {field}: MISSING")
            missing_contact_fields.append(field)
    
    print("\n" + "=" * 50)
    
    if missing_deal_fields or missing_contact_fields:
        print("❌ VALIDATION FAILED")
        if missing_deal_fields:
            print(f"Missing deal fields: {', '.join(missing_deal_fields)}")
        if missing_contact_fields:
            print(f"Missing contact fields: {', '.join(missing_contact_fields)}")
        return False
    else:
        print("✅ ALL FIELD MAPPINGS VALIDATED SUCCESSFULLY")
        return True

def show_current_mappings():
    """Display current field mappings from config"""
    print("\n🔍 Current Configuration:")
    print("-" * 30)
    
    print("Deal Fields:")
    for field_name, field_id in PIPEDRIVE_DEAL_FIELDS.items():
        print(f"  {field_name}: {field_id}")
    
    print("\nContact Fields:")
    for field_name, field_id in PIPEDRIVE_CONTACT_FIELDS.items():
        print(f"  {field_name}: {field_id}")

if __name__ == "__main__":
    validate_field_mappings()
    show_current_mappings() 