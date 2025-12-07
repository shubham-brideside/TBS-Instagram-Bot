#!/bin/bash

# SSL Setup Script for Instagram Bot
# Replace 'yourdomain.com' with your actual domain

DOMAIN="yourdomain.com"
EMAIL="your-email@example.com"

echo "🔒 Setting up SSL certificates for $DOMAIN"

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo apt update
    sudo apt install certbot python3-certbot-nginx -y
fi

# Generate SSL certificates
echo "Generating SSL certificates..."
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email $EMAIL

# Generate dhparam for better security
if [ ! -f /etc/nginx/dhparam.pem ]; then
    echo "Generating dhparam..."
    sudo openssl dhparam -out /etc/nginx/dhparam.pem 2048
fi

# Set up auto-renewal
echo "Setting up auto-renewal..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

echo "✅ SSL setup complete!"
echo "Your certificates are located at: /etc/letsencrypt/live/$DOMAIN/"
echo "Auto-renewal is set up and will run twice daily." 