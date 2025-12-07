# Azure Deployment Guide - Instagram Bot

Deploy your Instagram Bot to Azure with automatic HTTPS and autoscaling.

## 🚀 Azure App Service Deployment (Recommended)

### Prerequisites
- Azure account with active subscription
- Azure CLI installed
- GitHub repository

### Step 1: Create Azure App Service

#### Option A: Using Azure CLI
```bash
# Login to Azure
az login

# Create resource group (cost-optimized region)
az group create --name instagram-bot-rg --location "South Central US"

# Create App Service plan (cost-optimized)
az appservice plan create \
  --name instagram-bot-plan \
  --resource-group instagram-bot-rg \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --name your-instagram-bot-app \
  --resource-group instagram-bot-rg \
  --plan instagram-bot-plan \
  --runtime "PYTHON|3.12"

# Enable HTTPS only
az webapp update \
  --name your-instagram-bot-app \
  --resource-group instagram-bot-rg \
  --https-only true
```

#### Option B: Using Azure Portal
1. Go to [Azure Portal](https://portal.azure.com)
2. Create new **Web App**
3. Choose **Python 3.12** runtime
4. Select **Basic B1** for cost optimization (or **Standard S1** if autoscaling needed)
5. Choose **South Central US** region for lower costs
6. Enable **HTTPS Only**

### Step 2: Configure Environment Variables

```bash
# Set environment variables
az webapp config appsettings set \
  --name your-instagram-bot-app \
  --resource-group instagram-bot-rg \
  --settings \
    ENVIRONMENT=production \
    ACCESS_TOKEN="your-token" \
    IG_ACCOUNT_ID="your-id" \
    VERIFY_TOKEN="your-verify-token" \
    GROQ_API_KEY="your-groq-key" \
    PIPEDRIVE_API_TOKEN="your-pipedrive-token" \
    DB_HOST="your-db-host" \
    DB_DATABASE="your-db-name" \
    DB_USER="your-db-user" \
    DB_PASSWORD="your-db-password"
```

### Step 3: Deploy Application

#### Option A: GitHub Actions (Recommended)
1. Push your code to GitHub
2. Go to Azure Portal → Your App Service → Deployment Center
3. Choose **GitHub** as source
4. Select your repository and branch
5. Azure will automatically create a workflow file

#### Option B: Direct Deployment
```bash
# Deploy from local directory
az webapp deployment source config-zip \
  --name your-instagram-bot-app \
  --resource-group instagram-bot-rg \
  --src app.zip
```

### Step 4: Configure Autoscaling (Optional - Standard tier only)

**For Basic B1 (Cost-Optimized)**: Manual scaling only
```bash
# Scale up manually when needed
az appservice plan update \
  --name instagram-bot-plan \
  --resource-group instagram-bot-rg \
  --sku B2  # Scale to B2 when more resources needed
```

**For Standard S1 (Auto-scaling)**: If you upgrade later
```bash
# Enable autoscaling
az monitor autoscale create \
  --resource-group instagram-bot-rg \
  --resource your-instagram-bot-app \
  --resource-type Microsoft.Web/sites \
  --name instagram-bot-autoscale \
  --min-count 1 \
  --max-count 5 \
  --count 1

# Add CPU scaling rule
az monitor autoscale rule create \
  --resource-group instagram-bot-rg \
  --autoscale-name instagram-bot-autoscale \
  --condition "Percentage CPU > 80 avg 10m" \
  --scale out 1

az monitor autoscale rule create \
  --resource-group instagram-bot-rg \
  --autoscale-name instagram-bot-autoscale \
  --condition "Percentage CPU < 20 avg 15m" \
  --scale in 1
```

### Step 5: Set Up Custom Domain & SSL (Optional)

```bash
# Add custom domain
az webapp config hostname add \
  --webapp-name your-instagram-bot-app \
  --resource-group instagram-bot-rg \
  --hostname yourdomain.com

# Bind SSL certificate (managed certificate)
az webapp config ssl bind \
  --name your-instagram-bot-app \
  --resource-group instagram-bot-rg \
  --certificate-type SNI \
  --hostname yourdomain.com
```

## 🔧 Alternative: Azure Container Instances

### Create Container Deployment
```bash
# Create container group
az container create \
  --resource-group instagram-bot-rg \
  --name instagram-bot-container \
  --image your-registry/instagram-bot:latest \
  --cpu 1 \
  --memory 1.5 \
  --ports 80 443 \
  --environment-variables \
    ENVIRONMENT=production \
    ACCESS_TOKEN="your-token" \
  --secure-environment-variables \
    DB_PASSWORD="your-db-password"
```

## 📊 Monitoring & Scaling

### Application Insights
```bash
# Create Application Insights
az monitor app-insights component create \
  --app instagram-bot-insights \
  --location eastus \
  --resource-group instagram-bot-rg

# Connect to Web App
az webapp config appsettings set \
  --name your-instagram-bot-app \
  --resource-group instagram-bot-rg \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="your-key"
```

### Scaling Metrics
- **CPU Percentage**: Scale out when > 70%, scale in when < 30%
- **Memory Percentage**: Scale out when > 80%
- **HTTP Queue Length**: Scale out when > 100 requests
- **Response Time**: Scale out when > 5 seconds

## 🌐 DNS and Domain Setup

### Point Domain to Azure
1. Get your app URL: `your-instagram-bot-app.azurewebsites.net`
2. Create CNAME record: `www.yourdomain.com` → `your-instagram-bot-app.azurewebsites.net`
3. Add custom domain in Azure Portal
4. Enable managed SSL certificate

## 🔒 Security Best Practices

### Network Security
```bash
# Restrict access to specific IPs (optional)
az webapp config access-restriction add \
  --name your-instagram-bot-app \
  --resource-group instagram-bot-rg \
  --rule-name "Allow-Instagram" \
  --action Allow \
  --ip-address 173.252.88.0/24
```

### Key Vault Integration
```bash
# Create Key Vault
az keyvault create \
  --name instagram-bot-vault \
  --resource-group instagram-bot-rg \
  --location eastus

# Store secrets
az keyvault secret set \
  --vault-name instagram-bot-vault \
  --name "ACCESS-TOKEN" \
  --value "your-token"
```

## 📈 Cost Optimization

### Pricing Tiers (Monthly estimates)
- **Free (F1)**: $0 - Development only, no custom domains, no HTTPS
- **Shared (D1)**: ~$10 - Basic apps, shared resources, limited HTTPS
- **Basic (B1)**: ~$55 - **RECOMMENDED** - Dedicated resources, custom domains, SSL
- **Basic (B2)**: ~$110 - More CPU/memory than B1
- **Standard (S1)**: ~$73 - Autoscaling, staging slots
- **Premium (P1)**: ~$146 - Advanced features, better performance

### Cost-Saving Tips
1. **Use Basic B1** for most Instagram bots (~$55/month)
2. **Choose South Central US** region (cheapest)
3. **Scale manually** instead of auto-scaling initially
4. **Monitor usage** with Azure Cost Management
5. **Use reserved instances** (1-year commitment = 20% discount)
6. **Stop app during maintenance** windows if possible

### Regional Pricing (B1 Basic)
- **South Central US**: ~$55/month (cheapest)
- **Central US**: ~$55/month
- **East US 2**: ~$59/month
- **West US 2**: ~$59/month
- **North Europe**: ~$61/month
- **Southeast Asia**: ~$58/month

## 🚀 Final Steps

1. **Update Instagram Webhook URL**: `https://your-instagram-bot-app.azurewebsites.net/webhook`
2. **Test endpoints**:
   - `https://your-instagram-bot-app.azurewebsites.net/`
   - `https://your-instagram-bot-app.azurewebsites.net/webhook`
3. **Monitor performance** in Azure Portal
4. **Set up alerts** for scaling events and errors

## 📞 Support

- **Azure Documentation**: https://docs.microsoft.com/en-us/azure/app-service/
- **Pricing Calculator**: https://azure.microsoft.com/en-us/pricing/calculator/
- **Support Plans**: https://azure.microsoft.com/en-us/support/plans/

Your Instagram Bot is now deployed with:
✅ **Automatic HTTPS**
✅ **Autoscaling (1-10 instances)**
✅ **99.95% SLA**
✅ **Integrated monitoring**
✅ **Zero server management** 