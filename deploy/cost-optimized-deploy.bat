@echo off
setlocal enabledelayedexpansion

rem Cost-Optimized Azure App Service Deployment
rem Basic B1 tier in South Central US for maximum cost efficiency

rem Configuration - EDIT THESE VALUES
set DOMAIN=thebrideside.in
set APP_NAME=brideside-lead-automation
set RESOURCE_GROUP=brideside-lead-automation
set LOCATION=Central US
set PRICING_TIER=B1

echo.
echo 💰 Cost-Optimized Instagram Bot Deployment
echo Region: %LOCATION% (cheapest)
echo Tier: %PRICING_TIER% (~$55/month)
echo ==================================================
echo.

echo ✅ Logging into Azure...
@REM az login
@REM if %errorlevel% neq 0 (
@REM     echo ❌ Azure login failed
@REM     pause
@REM     exit /b 1
@REM )

echo ✅ Creating resource group in %LOCATION%...
az group create --name %RESOURCE_GROUP% --location "%LOCATION%"
if %errorlevel% neq 0 (
    echo ❌ Failed to create resource group
    pause
    exit /b 1
)

echo ✅ Creating cost-optimized App Service plan...
az appservice plan create --name "%APP_NAME%-plan" --resource-group %RESOURCE_GROUP% --sku %PRICING_TIER% --is-linux
if %errorlevel% neq 0 (
    echo ❌ Failed to create App Service plan
    pause
    exit /b 1
)

echo 💰 Monthly cost estimate: ~$55 USD

echo ✅ Creating Web App...
az webapp create --name %APP_NAME% --resource-group %RESOURCE_GROUP% --plan "%APP_NAME%-plan" --runtime "PYTHON|3.12"
if %errorlevel% neq 0 (
    echo ❌ Failed to create Web App
    pause
    exit /b 1
)

echo ✅ Enabling HTTPS-only access...
az webapp update --name %APP_NAME% --resource-group %RESOURCE_GROUP% --https-only true
if %errorlevel% neq 0 (
    echo ❌ Failed to enable HTTPS
    pause
    exit /b 1
)

echo ✅ Setting up environment variables...
az webapp config appsettings set --name %APP_NAME% --resource-group %RESOURCE_GROUP% --settings ENVIRONMENT=production SCM_DO_BUILD_DURING_DEPLOYMENT=true WEBSITE_RUN_FROM_PACKAGE=1
if %errorlevel% neq 0 (
    echo ❌ Failed to set environment variables
    pause
    exit /b 1
)

echo.
echo ℹ️  Configure your API keys manually in Azure Portal:
echo ℹ️  - ACCESS_TOKEN
echo ℹ️  - IG_ACCOUNT_ID
echo ℹ️  - VERIFY_TOKEN
echo ℹ️  - GROQ_API_KEY
echo ℹ️  - PIPEDRIVE_API_TOKEN
echo ℹ️  - DB_HOST, DB_DATABASE, DB_USER, DB_PASSWORD
echo.

echo ✅ Deploying application code...
rem Create zip file using PowerShell
powershell -Command "Compress-Archive -Path . -DestinationPath app.zip -Force -Exclude '*.git*', '*__pycache__*', '*.pyc', '.env', 'venv\*', '.venv\*'"
if %errorlevel% neq 0 (
    echo ❌ Failed to create zip file
    pause
    exit /b 1
)

az webapp deployment source config-zip --name %APP_NAME% --resource-group %RESOURCE_GROUP% --src app.zip
if %errorlevel% neq 0 (
    echo ❌ Failed to deploy application
    pause
    exit /b 1
)

rem Clean up
del app.zip

rem Get app URL
for /f "tokens=*" %%i in ('az webapp show --name %APP_NAME% --resource-group %RESOURCE_GROUP% --query defaultHostName -o tsv') do set APP_URL=%%i

echo.
echo ✅ Deployment complete!
echo.
echo 🎉 Your Instagram Bot is now running!
echo ==================================================
echo App URL: https://%APP_URL%
echo Webhook URL: https://%APP_URL%/webhook
echo.
echo 💰 Cost Summary:
echo - Monthly cost: ~$55 USD (Basic B1)
echo - Region: South Central US (cheapest)
echo - SSL/HTTPS: Included free
echo - Custom domain: Supported
echo.
echo 📊 Monitoring:
echo - Azure Portal: https://portal.azure.com
echo - Resource Group: %RESOURCE_GROUP%
echo - App Service: %APP_NAME%
echo.
echo 🔧 Management Commands:
echo - Restart app: az webapp restart --name %APP_NAME% --resource-group %RESOURCE_GROUP%
echo - View logs: az webapp log tail --name %APP_NAME% --resource-group %RESOURCE_GROUP%
echo - Scale up: az appservice plan update --name %APP_NAME%-plan --resource-group %RESOURCE_GROUP% --sku B2
echo.
echo ⚠️  Next Steps:
echo 1. Configure environment variables in Azure Portal
echo 2. Update Instagram webhook URL to: https://%APP_URL%/webhook
echo 3. Test your bot functionality
echo 4. Set up monitoring and alerts
echo.
echo 💡 Cost Optimization Tips:
echo - Monitor usage in Azure Cost Management
echo - Consider reserved instances for 20% discount
echo - Stop app during maintenance windows
echo - Upgrade to B2 only when needed
echo.

pause 