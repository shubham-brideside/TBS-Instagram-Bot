# HTTPS Deployment Guide for Instagram Bot

This guide will help you deploy your Instagram Bot Flask application with HTTPS support.

## Prerequisites

1. A domain name pointing to your server
2. A server with Ubuntu/Debian (VPS or dedicated server)
3. SSH access to your server
4. Basic knowledge of command line

## Quick Setup

### 1. Update Your Environment Variables

Add these to your `.env` file:
```
ENVIRONMENT=production
```

### 2. Install Dependencies

```bash
# Update your virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirement.txt
```

## Deployment Options

### Option A: VPS/Server Deployment (Recommended)

#### Step 1: Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install nginx python3-pip python3-venv git -y

# Create application directory
sudo mkdir -p /var/www/instagram-bot
sudo chown $USER:$USER /var/www/instagram-bot
```

#### Step 2: Deploy Application
```bash
# Clone your repository
cd /var/www/instagram-bot
git clone <your-repository-url> .

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirement.txt
```

#### Step 3: Configure Environment
```bash
# Copy environment file
cp env.example .env

# Edit environment variables
nano .env
```

Make sure to set:
- `ENVIRONMENT=production`
- All your API keys and database credentials
- Database connection details

#### Step 4: Set Up SSL Certificates
```bash
# Make the setup script executable
chmod +x deploy/setup_ssl.sh

# Edit the script with your domain and email
nano deploy/setup_ssl.sh

# Run the SSL setup
./deploy/setup_ssl.sh
```

#### Step 5: Configure Nginx
```bash
# Copy nginx configuration
sudo cp deploy/nginx.conf /etc/nginx/sites-available/instagram-bot

# Edit with your domain name
sudo nano /etc/nginx/sites-available/instagram-bot

# Enable the site
sudo ln -s /etc/nginx/sites-available/instagram-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### Step 6: Set Up System Service
```bash
# Copy service file
sudo cp deploy/instagram-bot.service /etc/systemd/system/

# Edit paths in the service file
sudo nano /etc/systemd/system/instagram-bot.service

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable instagram-bot
sudo systemctl start instagram-bot
```

#### Step 7: Test Deployment
```bash
# Check service status
sudo systemctl status instagram-bot

# Check nginx status
sudo systemctl status nginx

# Test your endpoints
curl -I https://yourdomain.com
curl -I https://yourdomain.com/webhook
```

### Option B: Shared Hosting (cPanel)

If you're using shared hosting with cPanel:

1. **Upload Files**: Upload all your files to your domain's public_html directory
2. **Python App**: Use cPanel's Python App feature to create a Python application
3. **SSL**: Enable SSL in cPanel (usually free with Let's Encrypt)
4. **Environment Variables**: Set environment variables in cPanel
5. **Startup File**: Use `wsgi.py` as your startup file

### Option C: Cloud Platforms

#### Heroku
```bash
# Install Heroku CLI
# Create Procfile
echo "web: gunicorn wsgi:app" > Procfile

# Deploy
heroku create your-app-name
git push heroku master
```

#### DigitalOcean App Platform
1. Connect your GitHub repository
2. Set environment variables
3. Deploy (HTTPS is automatic)

## Important Configuration Updates

### 1. Update Instagram Webhook URL

After deployment, update your Instagram webhook URL to:
```
https://yourdomain.com/webhook
```

### 2. Update Database Connection

Make sure your database is accessible from your server and update the connection details in your `.env` file.

### 3. Test Webhook

Test your webhook using:
```bash
curl -X POST https://yourdomain.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

## Monitoring and Maintenance

### View Logs
```bash
# Application logs
sudo journalctl -u instagram-bot -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Update Application
```bash
cd /var/www/instagram-bot
git pull origin master
source .venv/bin/activate
pip install -r requirement.txt
sudo systemctl restart instagram-bot
```

### SSL Certificate Renewal
Certificates will auto-renew, but you can test renewal:
```bash
sudo certbot renew --dry-run
```

## Security Best Practices

1. **Firewall**: Enable UFW and allow only necessary ports
2. **User Permissions**: Run the application as a non-root user
3. **Environment Variables**: Never commit sensitive data to git
4. **Regular Updates**: Keep your system and packages updated
5. **Backup**: Regular database and application backups

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**: Check if your Flask app is running
2. **SSL Certificate Issues**: Verify domain DNS and certificate paths
3. **Permission Denied**: Check file permissions and ownership
4. **Database Connection**: Verify database credentials and network access

### Debug Commands
```bash
# Check if app is running
sudo systemctl status instagram-bot

# Check nginx configuration
sudo nginx -t

# Test SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

## Next Steps

1. Set up monitoring (like New Relic or DataDog)
2. Configure automated backups
3. Set up CI/CD pipeline for automatic deployments
4. Add rate limiting and security middleware
5. Configure log rotation

For support, check the application logs and verify all configuration files are correctly set up with your specific domain and paths. 