# Railway Deployment - Quick Start

Deploy LegalKG Knowledge Graph API to Railway in 10 minutes.

## Prerequisites

- GitHub account with your repo
- Google Gemini API key from [makersuite.google.com](https://makersuite.google.com/app/apikey)
- **Neo4j Aura account** (for managed Neo4j database)

## 1. Setup Neo4j Aura (First Time Only)

Neo4j Aura is the easiest way to run Neo4j without managing servers.

### Create Neo4j Instance:

1. Go to https://neo4j.com/cloud/aura
2. Sign up (free account)
3. Click **"Create Database"**
4. Choose **"Free tier"** ($0/month)
5. Wait for instance to deploy
6. Click **"Copy Connection Details"** → You'll get:
   - `NEO4J_URI`: bolt://xxx.xxx.neo4j.io:7687
   - `NEO4J_USER`: neo4j
   - `NEO4J_PASSWORD`: your_secure_password

**Save these credentials** - you'll need them in Railway dashboard.

---

## 2. Prepare Your Repository

```bash
# Make sure all changes are committed and pushed
git add .
git commit -m "Ready for Railway deployment"
git push origin main
```

---

## 3. Deploy on Railway

1. Go to https://railway.app
2. Click **"Create New Project"**
3. Select **"Deploy from GitHub"**
4. Login with GitHub and select your repository
5. Railway auto-detects Python project
6. Click **"Deploy"** ✨

---

## 4. Set Environment Variables (Critical!)

In Railway dashboard:

1. Go to your **Project**
2. Click **"Variables"** tab
3. Add the following variables from your Neo4j Aura credentials:

| Key | Value | Example |
|-----|-------|---------|
| `NEO4J_URI` | From Neo4j Aura | `bolt://xxxxxxx.neo4j.io:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | Your secure password |
| `GOOGLE_GEMINI_API_KEY` | From makersuite.google.com | Your API key |
| `OPENAI_API_KEY` | (Optional) From openai.com | Your API key (if using) |

4. Check **"Encrypt"** for all sensitive variables
5. Save changes → Railway auto-redeploys! 🔄

---

## 5. Your App is Live! 🚀

Railway will automatically:
- Assign you a public URL: `https://your-app-XXXXX.railway.app`
- Start the FastAPI server
- Keep it running 24/7

Access your app:
- **API Docs**: https://your-app-XXXXX.railway.app/docs
- **Health Check**: https://your-app-XXXXX.railway.app/health
- **Chat API**: https://your-app-XXXXX.railway.app/api/chat

---

## 6. Automatic Updates

Every time you push to GitHub:
```bash
git push origin main
```

Railway automatically rebuilds and redeploys! 🔄

---

## Database Management

### Access Neo4j Browser:

1. From Neo4j Aura dashboard
2. Click on your database → **"Open in Browser"**
3. Login with credentials you set
4. Execute Cypher queries to manage your knowledge graph

### Backup Your Data:

Neo4j Aura provides automatic backups. In Neo4j console:
```cypher
CALL db.backup.export.full("/path/to/backup")
```

---

## Pricing

| Component | Cost |
|-----------|------|
| **Railway (API)** | Free tier: $5/month credit |
| **Neo4j Aura** | Free tier: $0/month (up to 100K nodes) |
| **Total** | Can be completely free! |

---

## Common Issues

### "Neo4j connection failed"
→ Check your `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
→ Verify they match exactly from Neo4j Aura
→ Make sure credentials are encrypted in Railway

### "App keeps crashing"
→ Check **Logs** tab in Railway dashboard
→ Verify all required API keys are set
→ Look for connection timeouts

### "How to view logs?"
→ Railway Dashboard → Project → Deployments → View Logs

### "Need to scale or increase resources?"
→ Railway Dashboard → Settings → Change tier (starts at $0.50/month)

---

## Need Help?

- **Railway Docs**: https://docs.railway.app
- **Neo4j Aura Docs**: https://neo4j.com/docs/aura
- **FastAPI Docs**: https://fastapi.tiangolo.com

---

## Next Steps

✅ Create Neo4j Aura instance
✅ Get credentials from Aura
✅ Commit code & push to GitHub
✅ Deploy on Railway
✅ Set all environment variables
✅ Access your live API

Happy deploying! 🎉
