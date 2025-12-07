import os
import logging
from app import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Get port from environment variable or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    # Check if we're in production
    is_production = os.getenv('ENVIRONMENT') == 'production'
    
    logger.info("🚀 Starting Instagram Bot...")
    logger.info(f"Environment: {'Production' if is_production else 'Development'}")
    logger.info(f"Port: {port}")
    
    # Use Flask server (Gunicorn handled by Docker in production)
    app.run(host='0.0.0.0', port=port, debug=not is_production) 