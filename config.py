import os
from dotenv import load_dotenv

load_dotenv()

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

PIPEDRIVE_API_TOKEN = os.getenv("PIPEDRIVE_API_TOKEN")
PIPEDRIVE_BASE_URL = os.getenv("PIPEDRIVE_BASE_URL")

# CRM Backend Configuration
CRM_BACKEND_URL = os.getenv("CRM_BACKEND_URL", "http://localhost:8080")
CRM_AUTH_TOKEN = os.getenv("CRM_AUTH_TOKEN", None)  # JWT token for authentication (if needed)

# Pipedrive Field Mapping Configuration
PIPEDRIVE_CONTACT_FIELDS = {
    'instagram_id': os.getenv("PIPEDRIVE_CONTACT_INSTAGRAM_ID_FIELD", "fc676a7dca016b580a8294cd964d767070f21dbd"),
    'lead_date': os.getenv("PIPEDRIVE_CONTACT_LEAD_DATE_FIELD", "1af649fe4605fd030d8c23f64a938292c4b92a7a")
}

PIPEDRIVE_DEAL_FIELDS = {
    'event_type': os.getenv("PIPEDRIVE_DEAL_EVENT_TYPE_FIELD", "accd9fb1f4d3f8908a76936061144431b98352e6"),
    'event_date': os.getenv("PIPEDRIVE_DEAL_EVENT_DATE_FIELD", "7b61d5c385508aa4cef1a30d7c3b350209670f39"),
    'venue': os.getenv("PIPEDRIVE_DEAL_VENUE_FIELD", "477fb2ebb13a363c7bf614255f42c8133c9f2447"),
    'conversation_summary': os.getenv("PIPEDRIVE_DEAL_CONVERSATION_SUMMARY_FIELD", "54c12fb281506d1590f9e61ca70448c306f63f33"),
    'full_name': os.getenv("PIPEDRIVE_DEAL_FULL_NAME_FIELD", "84ab8ec8732455ab7cf75f5661f2c027c7b1e5cd"),
    'phone': os.getenv("PIPEDRIVE_DEAL_PHONE_FIELD", "8c484975a8342d3093277bc7f47f274c56c124cb")
}

DB_CONFIG = {
    'host': os.getenv("DB_HOST", "thebrideside.mysql.database.azure.com:3306"),
    'database': os.getenv("DB_DATABASE", "thebrideside"),
    'user': os.getenv("DB_USER", "thebrideside"),
    'password': os.getenv("DB_PASSWORD", "TheBride@260799"),
    'charset': os.getenv("DB_CHARSET", "utf8mb4"),
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Venue → City enrichment (optional)
ENABLE_VENUE_CITY_LOOKUP = os.getenv("ENABLE_VENUE_CITY_LOOKUP", "true").strip().lower() in ("1", "true", "yes", "y")
NOMINATIM_BASE_URL = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org").rstrip("/")

GREETING_TEMPLATES = [
    'Hi there! ✨',
    'Hope you are doing good!',
    (
        "Welcome to The Bride Side — your one-stop destination for wedding photography, "
        "makeup, planning and decor services.\n"
        "Could you please tell us what you’re looking for?\n \n"
        "• Wedding Photography / Pre-wedding Photoshoot\n"
        "• Bridal Makeup / Party Makeup\n"
        "• Wedding Planner\n"
        "• Wedding Decor"
    )]

