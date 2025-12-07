#!/bin/bash

# Instagram Bot HTTPS Deployment Script
# Customize the variables below for your setup

# Configuration Variables - EDIT THESE
DOMAIN="thebrideside.in"
EMAIL="sahil@thebrideside.in"
APP_DIR="/var/www/brideside-instagram-bot"
SERVICE_NAME="brideside-instagram-bot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Instagram Bot HTTPS Deployment Script${NC}"
echo "==============================================="

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
print_status "Installing required packages..."
sudo apt install -y nginx python3-pip python3-venv git curl

# Create application directory
print_status "Setting up application directory..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Navigate to app directory
cd $APP_DIR

# Set up virtual environment
print_status "Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirement.txt

# Set up environment variables
print_status "Setting up environment variables..."
if [ ! -f .env ]; then
    cp env.example .env
    print_warning "Please edit .env file with your configuration"
    print_warning "Make sure to set ENVIRONMENT=production"
fi

# Set up SSL certificates
print_status "Setting up SSL certificates..."
if ! command -v certbot &> /dev/null; then
    sudo apt install -y certbot python3-certbot-nginx
fi

# Generate SSL certificates
print_status "Generating SSL certificates for $DOMAIN..."
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email $EMAIL

# Generate dhparam for security
if [ ! -f /etc/nginx/dhparam.pem ]; then
    print_status "Generating dhparam for enhanced security..."
    sudo openssl dhparam -out /etc/nginx/dhparam.pem 2048
fi

# Configure Nginx
print_status "Configuring Nginx..."
sudo cp deploy/nginx.conf /etc/nginx/sites-available/$SERVICE_NAME

# Replace placeholder domain in nginx config
sudo sed -i "s/yourdomain.com/$DOMAIN/g" /etc/nginx/sites-available/$SERVICE_NAME
sudo sed -i "s|/path/to/your/app|$APP_DIR|g" /etc/nginx/sites-available/$SERVICE_NAME

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
sudo nginx -t

if [ $? -eq 0 ]; then
    print_status "Nginx configuration is valid"
    sudo systemctl reload nginx
else
    print_error "Nginx configuration has errors"
    exit 1
fi

# Set up systemd service
print_status "Setting up systemd service..."
sudo cp deploy/$SERVICE_NAME.service /etc/systemd/system/

# Replace placeholder paths in service file
sudo sed -i "s|/path/to/your/app|$APP_DIR|g" /etc/systemd/system/$SERVICE_NAME.service

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# Set up SSL certificate auto-renewal
print_status "Setting up SSL certificate auto-renewal..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Check service status
print_status "Checking service status..."
sleep 5

if sudo systemctl is-active --quiet $SERVICE_NAME; then
    print_status "Service is running successfully"
else
    print_error "Service failed to start"
    sudo systemctl status $SERVICE_NAME
    exit 1
fi

# Test endpoints
print_status "Testing deployment..."
echo "Testing HTTP to HTTPS redirect..."
curl -I -L http://$DOMAIN

echo -e "\nTesting HTTPS endpoint..."
curl -I https://$DOMAIN

echo -e "\nTesting webhook endpoint..."
curl -I https://$DOMAIN/webhook

# Final instructions
echo -e "\n${GREEN}🎉 Deployment Complete!${NC}"
echo "==============================================="
echo -e "${GREEN}✅ Your Instagram Bot is now running with HTTPS!${NC}"
echo ""
echo "Next steps:"
echo "1. Update your Instagram webhook URL to: https://$DOMAIN/webhook"
echo "2. Test your webhook integration"
echo "3. Monitor the application logs:"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Useful commands:"
echo "- Restart service: sudo systemctl restart $SERVICE_NAME"
echo "- Check status: sudo systemctl status $SERVICE_NAME"
echo "- View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "- Test SSL: openssl s_client -connect $DOMAIN:443 -servername $DOMAIN"
echo ""
echo -e "${YELLOW}⚠️  Remember to:${NC}"
echo "- Configure your .env file with production values"
echo "- Set up database backups"
echo "- Configure monitoring and alerting"
echo "- Set up a firewall (UFW recommended)" 