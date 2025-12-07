# Azure Environment Variables Setup Script for Instagram Bot
# Run this script to configure all environment variables in Azure App Service

# Azure App Service Configuration
$resourceGroup = "brideside-lead-automation"
$appName = "brideside-lead-automation"

Write-Host "Setting up environment variables for Azure App Service: $appName" -ForegroundColor Green

# Core Application Settings
Write-Host "Setting core application settings..." -ForegroundColor Yellow
az webapp config appsettings set --resource-group $resourceGroup --name $appName --settings `
    "ENVIRONMENT=production" `
    "SCM_DO_BUILD_DURING_DEPLOYMENT=true" `
    "PYTHONPATH=/site/wwwroot"

# Instagram API Configuration
Write-Host "Please provide your Instagram API credentials:" -ForegroundColor Yellow
$ACCESS_TOKEN = Read-Host "Enter your Instagram ACCESS_TOKEN"
$IG_ACCOUNT_ID = Read-Host "Enter your Instagram IG_ACCOUNT_ID"
$VERIFY_TOKEN = Read-Host "Enter your Instagram VERIFY_TOKEN"

az webapp config appsettings set --resource-group $resourceGroup --name $appName --settings `
    "ACCESS_TOKEN=$ACCESS_TOKEN" `
    "IG_ACCOUNT_ID=$IG_ACCOUNT_ID" `
    "VERIFY_TOKEN=$VERIFY_TOKEN"

# Groq AI Configuration
Write-Host "Please provide your Groq AI credentials:" -ForegroundColor Yellow
$GROQ_API_KEY = Read-Host "Enter your GROQ_API_KEY"
$GROQ_MODEL = Read-Host "Enter your GROQ_MODEL (e.g., llama3-8b-8192)"

az webapp config appsettings set --resource-group $resourceGroup --name $appName --settings `
    "GROQ_API_KEY=$GROQ_API_KEY" `
    "GROQ_MODEL=$GROQ_MODEL"

# Pipedrive CRM Configuration
Write-Host "Please provide your Pipedrive CRM credentials:" -ForegroundColor Yellow
$PIPEDRIVE_API_TOKEN = Read-Host "Enter your PIPEDRIVE_API_TOKEN"
$PIPEDRIVE_BASE_URL = Read-Host "Enter your PIPEDRIVE_BASE_URL (e.g., https://yourcompany.pipedrive.com)"

az webapp config appsettings set --resource-group $resourceGroup --name $appName --settings `
    "PIPEDRIVE_API_TOKEN=$PIPEDRIVE_API_TOKEN" `
    "PIPEDRIVE_BASE_URL=$PIPEDRIVE_BASE_URL"

# Database Configuration
Write-Host "Please provide your Database credentials:" -ForegroundColor Yellow
$DB_HOST = Read-Host "Enter your DB_HOST"
$DB_DATABASE = Read-Host "Enter your DB_DATABASE"
$DB_USER = Read-Host "Enter your DB_USER"
$DB_PASSWORD = Read-Host "Enter your DB_PASSWORD" -AsSecureString
$DB_PASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD))
$DB_CHARSET = Read-Host "Enter your DB_CHARSET (default: utf8mb4)"

if ([string]::IsNullOrEmpty($DB_CHARSET)) {
    $DB_CHARSET = "utf8mb4"
}

az webapp config appsettings set --resource-group $resourceGroup --name $appName --settings `
    "DB_HOST=$DB_HOST" `
    "DB_DATABASE=$DB_DATABASE" `
    "DB_USER=$DB_USER" `
    "DB_PASSWORD=$DB_PASSWORD_PLAIN" `
    "DB_CHARSET=$DB_CHARSET"

# Optional: Pipedrive Field Mapping (using defaults from config.py)
Write-Host "Setting up Pipedrive field mappings with defaults..." -ForegroundColor Yellow
az webapp config appsettings set --resource-group $resourceGroup --name $appName --settings `
    "PIPEDRIVE_CONTACT_INSTAGRAM_USERNAME_FIELD=f8cc78917de8bd1bd757fe8720213d518a3c6f86" `
    "PIPEDRIVE_DEAL_EVENT_TYPE_FIELD=b928fb0cfa31cdd64a657e714c6e9aea6341d01b" `
    "PIPEDRIVE_DEAL_EVENT_DATE_FIELD=9d9ca82c5b3f66b7186b4f02ceffe28e19e96f78" `
    "PIPEDRIVE_DEAL_VENUE_FIELD=4079f1903347e264de4e0b5f1ae2116b4066d04f" `
    "PIPEDRIVE_DEAL_CONVERSATION_SUMMARY_FIELD=0d65a25d3d96854f664ce03be04d46240bfb9958"

# Logging Configuration
az webapp config appsettings set --resource-group $resourceGroup --name $appName --settings `
    "LOG_LEVEL=INFO"

Write-Host "Environment variables setup completed!" -ForegroundColor Green
Write-Host "You can verify the settings in Azure Portal > App Service > Configuration" -ForegroundColor Cyan

# Restart the app to apply new settings
Write-Host "Restarting the app to apply new settings..." -ForegroundColor Yellow
az webapp restart --resource-group $resourceGroup --name $appName

Write-Host "Setup complete! Your app is ready for deployment." -ForegroundColor Green 