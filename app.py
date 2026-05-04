import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

from flask import Flask
from services.webhook_service import handle_webhook
from services.ai_service_factory import AIServiceFactory
import os

app = Flask(__name__)

# One-time log so production (Azure) shows whether sequential pipeline env is loaded (.env is not deployed).
from config import (  # noqa: E402
    HUB_MIRROR_ORGANIZATION_ID,
    INSTAGRAM_PIPELINE_ROTATION_ORG_ID,
    MIRROR_DEAL_ORG_ID,
    MIRROR_DEAL_VENDOR_USERNAMES,
    SEQUENTIAL_PIPELINE_ORG_IDS,
    SEQUENTIAL_PIPELINE_PAIRS,
    SEQUENTIAL_PIPELINE_VENDOR_IDS,
)
from utils.logger import logger  # noqa: E402

if INSTAGRAM_PIPELINE_ROTATION_ORG_ID is not None:
    logger.info(
        "Instagram primary pipeline rotation: ON for organization_id=%s only | PAIRS=%s | ORG_IDS=%s | VENDOR_FILTER=%s",
        INSTAGRAM_PIPELINE_ROTATION_ORG_ID,
        sorted(SEQUENTIAL_PIPELINE_PAIRS) if SEQUENTIAL_PIPELINE_PAIRS else None,
        sorted(SEQUENTIAL_PIPELINE_ORG_IDS) if SEQUENTIAL_PIPELINE_ORG_IDS else None,
        sorted(SEQUENTIAL_PIPELINE_VENDOR_IDS) if SEQUENTIAL_PIPELINE_VENDOR_IDS else None,
    )
else:
    logger.info(
        "Instagram primary pipeline rotation: OFF — all vendors use brideside_vendors.pipeline_id. "
        "Hub mirror round-robin is separate (org %s).",
        HUB_MIRROR_ORGANIZATION_ID,
    )

if MIRROR_DEAL_ORG_ID is not None:
    logger.info(
        "Mirror hub deals: enabled | org_id=%s | vendor_usernames=%s",
        MIRROR_DEAL_ORG_ID,
        sorted(MIRROR_DEAL_VENDOR_USERNAMES),
    )
else:
    logger.info(
        "Mirror hub deals: disabled (set TBS_MIRROR_DEAL_ORG_ID=%s to enable)",
        HUB_MIRROR_ORGANIZATION_ID,
    )


# Add security headers for production
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if os.getenv('ENVIRONMENT') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/privacy_policy")
def privacy_policy():
    return "<p>Hello, World!</p>"


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    return handle_webhook()

if __name__ == "__main__":
    logging.info("🚀 Starting Instagram Bot...")
    is_production = os.getenv('ENVIRONMENT') == 'production'
    # Check environment for production/development mode
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=not is_production)
