import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

from flask import Flask
from services.webhook_service import handle_webhook
from services.ai_service_factory import AIServiceFactory
import os

app = Flask(__name__)



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
