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
    SEQUENTIAL_PIPELINE_ORG_IDS,
    SEQUENTIAL_PIPELINE_PAIRS,
    SEQUENTIAL_PIPELINE_VENDOR_IDS,
)
from utils.logger import logger  # noqa: E402

_sequential_on = bool(SEQUENTIAL_PIPELINE_PAIRS) or bool(SEQUENTIAL_PIPELINE_ORG_IDS)
if _sequential_on:
    logger.info(
        "Sequential pipeline: enabled | PAIRS=%s | ORG_IDS=%s | VENDOR_FILTER=%s",
        sorted(SEQUENTIAL_PIPELINE_PAIRS) if SEQUENTIAL_PIPELINE_PAIRS else None,
        sorted(SEQUENTIAL_PIPELINE_ORG_IDS) if SEQUENTIAL_PIPELINE_ORG_IDS else None,
        sorted(SEQUENTIAL_PIPELINE_VENDOR_IDS) if SEQUENTIAL_PIPELINE_VENDOR_IDS else None,
    )
else:
    logger.warning(
        "Sequential pipeline: DISABLED — set TBS_SEQUENTIAL_PIPELINE_PAIRS (e.g. 45:27) or "
        "TBS_SEQUENTIAL_PIPELINE_ORG_IDS in Azure Application Settings. "
        "Otherwise every new deal uses brideside_vendors.pipeline_id only."
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
