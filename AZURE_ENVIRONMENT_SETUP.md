# Azure Environment Variables Setup Guide

## 🎯 Overview
This guide will help you set up all the required environment variables for your Instagram Bot in Azure App Service.

## 🚀 Quick Setup (Recommended)

### Option 1: Automated Script
Run the PowerShell script to set up all environment variables automatically:

```powershell
.\azure-env-setup.ps1
```

**Prerequisites:**
- Azure CLI installed and logged in
- PowerShell 5.0 or later

---

## 🛠️ Manual Setup (Azure Portal)

### Step 1: Access Azure Portal
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your App Service: **brideside-lead-automation**
3. In the left sidebar, click **"Configuration"**
4. Select **"Application settings"** tab

### Step 2: Add Environment Variables
Click **"New application setting"** for each variable below:

#### Core Application Settings
| Name | Value |
|------|-------|
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |
| `PYTHONPATH` | `/site/wwwroot` |

#### Instagram API Configuration
| Name | Value | Description |
|------|-------|-------------|
| `ACCESS_TOKEN` | `your_instagram_access_token` | Instagram Graph API Access Token |
| `IG_ACCOUNT_ID` | `your_instagram_account_id` | Instagram Business Account ID |
| `VERIFY_TOKEN` | `your_webhook_verification_token` | Webhook verification token (any secret string) |

#### Groq AI Configuration
| Name | Value | Description |
|------|-------|-------------|
| `GROQ_API_KEY` | `your_groq_api_key` | Groq API Key for AI responses |
| `GROQ_MODEL` | `llama3-8b-8192` | Groq AI model to use |

#### Pipedrive CRM Configuration
| Name | Value | Description |
|------|-------|-------------|
| `PIPEDRIVE_API_TOKEN` | `your_pipedrive_api_token` | Pipedrive API Token |
| `PIPEDRIVE_BASE_URL` | `https://yourcompany.pipedrive.com` | Your Pipedrive base URL |

#### Database Configuration
| Name | Value | Description |
|------|-------|-------------|
| `DB_HOST` | `your_database_host` | Database server hostname |
| `DB_DATABASE` | `your_database_name` | Database name |
| `DB_USER` | `your_database_user` | Database username |
| `DB_PASSWORD` | `your_database_password` | Database password |
| `DB_CHARSET` | `utf8mb4` | Database character set |

#### Pipedrive Field Mapping (Optional)
These are pre-configured with your current field IDs. Only change if needed:

| Name | Value |
|------|-------|
| `PIPEDRIVE_CONTACT_INSTAGRAM_USERNAME_FIELD` | `18357eccb1e4d151b5dd28c69fd71a46a7bce973` |
| `PIPEDRIVE_DEAL_EVENT_TYPE_FIELD` | `33be05e5ce4039a0019fac9341f93e55f651613b` |
| `PIPEDRIVE_DEAL_EVENT_DATE_FIELD` | `df4c9016566220a8b31b23daf8658ebf868fa703` |
| `PIPEDRIVE_DEAL_VENUE_FIELD` | `202deab858d537436beba56583230b4a5bd61d47` |
| `PIPEDRIVE_DEAL_CONVERSATION_SUMMARY_FIELD` | `ba18d7941a996507ba15002f058fb91e2517874b` |

### Step 3: Save and Restart
1. Click **"Save"** after adding all variables
2. Click **"Continue"** to confirm
3. The app will automatically restart

---

## 📋 Where to Find Your Credentials

### Instagram API Credentials
- **ACCESS_TOKEN**: Meta Developer Console > Your App > Instagram Basic Display
- **IG_ACCOUNT_ID**: Your Instagram Business Account ID
- **VERIFY_TOKEN**: Any secret string you choose (remember it for webhook setup)

### Groq AI Credentials
- **GROQ_API_KEY**: [Groq Console](https://console.groq.com) > API Keys
- **GROQ_MODEL**: Available models: `llama3-8b-8192`, `mixtral-8x7b-32768`

### Pipedrive Credentials
- **PIPEDRIVE_API_TOKEN**: Pipedrive > Settings > API
- **PIPEDRIVE_BASE_URL**: Your Pipedrive company URL

### Database Credentials
- Use your existing database credentials
- If you don't have a database, consider Azure Database for MySQL

---

## ✅ Verification Steps

1. **Check Configuration**: Go to Azure Portal > App Service > Configuration
2. **Verify App Status**: Ensure the app is running
3. **Test Endpoints**: 
   - Health check: `https://brideside-lead-automation-f8f5asfpbeeddbcx.centralus-01.azurewebsites.net/health`
   - Webhook: `https://brideside-lead-automation-f8f5asfpbeeddbcx.centralus-01.azurewebsites.net/webhook`

---

## 🔧 Troubleshooting

### Common Issues
1. **App not starting**: Check application logs in Azure Portal
2. **Environment variables not loaded**: Ensure app restarted after adding variables
3. **Database connection failed**: Verify database credentials and network access

### Viewing Logs
```bash
# Azure CLI
az webapp log tail --resource-group brideside-lead-automation --name brideside-lead-automation

# Or in Azure Portal
App Service > Monitoring > Log stream
```

---

## 🔐 Security Best Practices

1. **Never commit credentials** to version control
2. **Use Azure Key Vault** for sensitive data in production
3. **Enable HTTPS only** (already configured)
4. **Regularly rotate API keys** and tokens
5. **Monitor application logs** for security issues

---

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Azure application logs
3. Verify all environment variables are correctly set
4. Test individual API connections (Instagram, Groq, Pipedrive, Database)

Your Instagram Bot is now ready for production! 🚀 