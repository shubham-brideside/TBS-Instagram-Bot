#!/bin/bash

# Azure App Service startup script
echo "Starting Instagram Bot Application..."

# Set environment variables
export ENVIRONMENT=production

# Run database migrations if needed
# python -m alembic upgrade head

# Start the application
python main.py 