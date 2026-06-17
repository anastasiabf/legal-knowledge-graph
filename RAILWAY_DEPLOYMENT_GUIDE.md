# Railway Deployment Guide - LegalKG

Comprehensive guide for deploying LegalKG on Railway with Neo4j Aura.

## Overview

LegalKG requires:
- **FastAPI Backend** → Deployed on Railway ☁️
- **Neo4j Database** → Deployed on Neo4j Aura ☁️ (managed service)

This setup eliminates the need to manage servers - both services are cloud-managed.

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Your Users' Browsers            │
└────────────────┬────────────────────────┘
                 │ HTTPS
┌────────────────▼────────────────────────┐
│    Railway (FastAPI LegalKG API)        │
│  https://your-app-XXXXX.railway.app    │
└────────────────┬────────────────────────┘
                 │ Bolt Protocol
┌────────────────▼────────────────────────┐
│   Neo4j Aura (Managed Graph DB)         │
│   bolt://xxxxx.neo4j.io:7687            │
└─────────────────────────────────────────┘
```

---

## Step 1: Setup Neo4j Aura

### Why Neo4j Aura?
- **No maintenance** - Auto-scaling, backups, updates
- **Free tier** - $0/month for up to 100K nodes
- **Enterprise features** - Paid upgrades available
- **Easy credentials** - Simple connection strings

### Create Instance:

1. **Visit Neo4j Aura**: https://neo4j.com/cloud/aura
2. **Create Free Account** (if needed)
3. **Create New Database**:
   - Name: `legalkg` (or any name)
   - Version: Latest stable (5.15+)
   - Tier: Free ($0/month)
4. **Wait for Deployment** (usually < 2 minutes)
5. **Download Credentials**:
   - Click "Copy Credentials" or view them
   - Save to safe place - you'll need them

**Example Credentials:**
```
NEO4J_URI: bolt://abc123def456.neo4j.io:7687
NEO4J_USER: neo4j
NEO4J_PASSWORD: ABC123_SecurePassword_XYZ789
```

**⚠️ Important**: These credentials let anyone access your database. Store them securely!

---

## Step 2: Push Code to GitHub

```bash
cd legal-kg

# Ensure all files are committed
git add .
git commit -m "Add Railway deployment files"
git push origin main
```

**Files Required** (already included):
- `Procfile` - Tells Railway how to start app
- `railway.json` - Environment variable definitions
- `requirements.txt` - Python dependencies
- `api/main.py` - FastAPI entry point

---

## Step 3: Deploy on Railway

### Connect GitHub

1. Go to https://railway.app
2. Sign up with GitHub (or login)
3. Click **"+ New Project"**
4. Select **"Deploy from GitHub"**
5. Authorize Railway to access your repos
6. Select your `legal-kg` repository
7. Click **"Deploy"** ✨

Railway will:
- Detect Python project (via `requirements.txt`)
- Build Docker image
- Install dependencies
- Assign public URL
- Start application

---

## Step 4: Configure Environment Variables

Once deployed, Railway needs your database credentials:

### In Railway Dashboard:

1. Click on your **Project**
2. Go to **"Variables"** tab
3. Add the following (copy from Neo4j Aura):

**Required Variables:**

| Variable | Value | Example |
|----------|-------|---------|
| `NEO4J_URI` | Connection string from Aura | `bolt://abc123.neo4j.io:7687` |
| `NEO4J_USER` | Usually "neo4j" | `neo4j` |
| `NEO4J_PASSWORD` | Your Aura password | `ABC123...` |
| `GOOGLE_GEMINI_API_KEY` | From makersuite.google.com | Your API key |

**Optional Variables:**

| Variable | Value | Example |
|----------|-------|---------|
| `OPENAI_API_KEY` | For embeddings (optional) | Your OpenAI key |
| `DEBUG` | Set to "False" for production | `False` |

### Setting Variables:

1. Click **"+ New Variable"**
2. Enter **Key** (e.g., `NEO4J_URI`)
3. Enter **Value** (e.g., `bolt://abc123.neo4j.io:7687`)
4. **Check "Encrypt"** for sensitive data 🔐
5. Click **"Save"**
6. Repeat for all variables

### Auto-Redeploy:

After saving variables, Railway automatically:
- Reconfigures application
- Restarts service
- Reapplies new credentials

---

## Step 5: Test Your Deployment

### Check Logs:

```
Railway Dashboard → Project → Deployments → View Logs
```

Look for:
- ✅ `Application startup complete`
- ✅ `Neo4j connection successful`
- ❌ Any error messages

### Test API:

1. Get your public URL from Railway dashboard
2. Visit: `https://your-app-XXXXX.railway.app/docs`
3. You should see Swagger UI with all endpoints
4. Try **"Try it out"** on `/health` endpoint
5. Should return `{"status": "ok"}`

---

## Managing Your Deployment

### View Live Logs

```
Railway Dashboard → Deployments → View Logs
```

Useful for debugging issues in production.

### Update Code

Every time you push to GitHub:
```bash
git push origin main
```

Railway automatically:
- Pulls new code
- Rebuilds
- Redeploys
- Restarts app

### Change Environment Variables

```
Railway Dashboard → Variables → Edit → Save
```

App auto-restarts with new values.

### Scale Resources

```
Railway Dashboard → Settings → Change instance type
```

Options:
- Free tier: $5/month credit
- Paid tiers: $0.50/GB RAM/month

---

## Monitoring & Maintenance

### Health Check Endpoint:

```bash
curl https://your-app-XXXXX.railway.app/health
```

Response:
```json
{
  "status": "ok",
  "neo4j": "connected",
  "timestamp": "2024-06-17T10:00:00Z"
}
```

### Check Database Connection:

```
Railway Dashboard → Deployments → View Logs
```

Look for Neo4j connection messages.

### Backup Data:

Neo4j Aura handles backups automatically. Additionally:

1. Export from Neo4j console:
```cypher
CALL db.backup.export.full("/path/to/backup")
```

2. Or use Neo4j browser to dump data

---

## Troubleshooting

### App Crashes Immediately

**Symptom**: App shown as "crashed" in Railway dashboard

**Solution**:
1. Check **Logs** for error messages
2. Verify all `NEO4J_*` variables are set
3. Verify Neo4j instance is running in Aura
4. Check that credentials are correct

### "Connection refused" Error

**Symptom**: `NEO4J connection failed`

**Solution**:
1. Verify `NEO4J_URI` format: `bolt://xxxxx.neo4j.io:7687`
2. Check `NEO4J_PASSWORD` is correct
3. Ensure Neo4j instance is **"Running"** (not paused) in Aura
4. Try pinging Neo4j browser: `https://xxxxx.neo4j.io`

### API Returns 500 Errors

**Symptom**: `/docs` page shows errors

**Solution**:
1. Check **Logs** for stack traces
2. Verify all API keys are set (`GOOGLE_GEMINI_API_KEY`, etc.)
3. Check Neo4j connectivity
4. Look for timeout issues with external APIs

### Slow Response Times

**Symptom**: API requests take > 5 seconds

**Solution**:
1. Check network between Railway and Neo4j (usually fine)
2. Upgrade Railway instance to more memory
3. Optimize Cypher queries in your code
4. Check Neo4j browser for slow queries: `CALL db.stats.retrieve()`

---

## Costs

### Completely Free Option:
- **Railway**: Free tier ($5/month credit = ~8 hours)
- **Neo4j Aura**: Free tier ($0, up to 100K nodes)
- **Total**: $0/month (for testing/development)

### Small Production:
- **Railway**: Paid tier ($0.50/GB RAM/month)
  - 1GB RAM = ~$0.50/month = $6/year
- **Neo4j Aura**: Free tier ($0)
- **Total**: ~$6/year

### Medium Production:
- **Railway**: 2GB RAM = $1/month = $12/year
- **Neo4j Aura**: Paid tier ($29/month+)
- **Total**: $29+/month

---

## Advanced Configuration

### Rate Limiting:

See `api/middleware.py` for rate limiting configuration.

### CORS Configuration:

In `api/main.py`, adjust CORS to restrict origins:
```python
allow_origins=["https://yourdomain.com"]
```

### Database Connection Pooling:

In `graph/neo4j_client.py`, configure pool size for better performance.

---

## Rollback & Recovery

### Rollback to Previous Deployment:

```
Railway Dashboard → Deployments → Select previous → "Redeploy"
```

### Restore Database:

Neo4j Aura keeps 7-day backup history. Contact Neo4j support for recovery.

---

## Next Steps

1. ✅ Create Neo4j Aura instance
2. ✅ Save credentials
3. ✅ Push code to GitHub
4. ✅ Deploy on Railway
5. ✅ Configure environment variables
6. ✅ Test health endpoint
7. ✅ Monitor logs
8. ✅ Set up custom domain (optional)

---

## Quick Reference

| Task | Where |
|------|-------|
| View logs | Railway → Deployments → View Logs |
| Add env vars | Railway → Variables |
| Redeploy | Push to GitHub (automatic) or Railway → Deployments |
| Check Neo4j | Neo4j Aura → Browser |
| View API docs | https://your-app-XXXXX.railway.app/docs |
| Health check | https://your-app-XXXXX.railway.app/health |

---

**Happy deploying! 🚀**
