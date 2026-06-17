# Railway Deployment Setup - Summary

Your LegalKG API is now ready for Railway deployment! ✨

## Files Created/Modified

| File | Purpose | What Changed |
|------|---------|--------------|
| **Procfile** | ✨ NEW | Tells Railway how to start your API |
| **railway.json** | ✨ NEW | Railway configuration & environment variables |
| **RAILWAY_QUICKSTART.md** | ✨ NEW | 10-minute deployment guide (START HERE!) |
| **RAILWAY_DEPLOYMENT_GUIDE.md** | ✨ NEW | Full guide with Neo4j Aura setup details |
| **README.md** | 📝 Updated | Added quick deployment section |
| **.env.example** | 📝 Updated | Better comments for Railway setup |

---

## What You Need to Do

### 1. **Create Neo4j Aura Instance** (First time only)
```bash
# Go to https://neo4j.com/cloud/aura
# 1. Sign up (free)
# 2. Create new database (Free tier = $0)
# 3. Wait for deployment
# 4. Copy credentials:
#    - NEO4J_URI: bolt://xxxxx.neo4j.io:7687
#    - NEO4J_USER: neo4j
#    - NEO4J_PASSWORD: (your password)
```

**Save these credentials - you'll need them in Railway!**

### 2. **Commit & Push Code**
```bash
cd legal-kg
git add .
git commit -m "Add Railway deployment configuration"
git push origin main
```

### 3. **Deploy on Railway** (Open browser)
1. Go to https://railway.app
2. Click "Create New Project"
3. Select "Deploy from GitHub"
4. Choose your repository
5. Railway auto-detects Python → Click Deploy ✨

### 4. **Set Environment Variables** (In Railway Dashboard)
1. Go to Project → Variables
2. Add the credentials from Neo4j Aura:
   - `NEO4J_URI`: bolt://xxxxx.neo4j.io:7687
   - `NEO4J_USER`: neo4j
   - `NEO4J_PASSWORD`: (your password)
3. Add API keys:
   - `GOOGLE_GEMINI_API_KEY`: From https://makersuite.google.com/app/apikey
   - `OPENAI_API_KEY`: (optional) From https://platform.openai.com/api-keys
4. Check "Encrypt" for all sensitive variables
5. Save → Auto redeploy

### 5. **Done!** 🎉
Your API is live at: `https://your-app-XXXXX.railway.app/docs`

---

## Important Notes

⚠️ **Database Setup (NEW!)**
- LegalKG requires Neo4j database
- Use **Neo4j Aura** (managed, free tier available, no maintenance)
- Get connection info from Aura → set in Railway dashboard

🔐 **API Key Security**
- Always use Railway's "Encrypt" for sensitive variables
- Neo4j credentials + API keys are secrets
- Never commit .env file to GitHub

💰 **Railway Pricing**
- Free tier: $5/month credit (~8 hours)
- Paid tier: Pay-as-you-go ($0.50/GB/month)

💰 **Neo4j Aura Pricing**
- Free tier: $0/month (up to 100K nodes) ← Great for testing!
- Paid tier: $29/month+ for more capacity

---

## Quick Links

| Document | For What |
|----------|----------|
| [RAILWAY_QUICKSTART.md](RAILWAY_QUICKSTART.md) | 10-minute deploy (START HERE!) |
| [RAILWAY_DEPLOYMENT_GUIDE.md](RAILWAY_DEPLOYMENT_GUIDE.md) | Full details with troubleshooting |
| [README.md](README.md) | Project overview & local setup |
| [.env.example](.env.example) | Environment variables reference |

---

## Setup Checklist

✅ Create Neo4j Aura instance (5 min)
✅ Save Neo4j credentials
✅ Get Gemini API key
✅ Commit code
✅ Push to GitHub  
✅ Deploy on Railway
✅ Set all environment variables
✅ Access your live API

---

## What Happens Next

1. **First Deploy**: Railway builds your image & starts app (~2 min)
2. **Environment Variables Set**: App auto-restarts with DB connection
3. **Health Check**: Access `/health` endpoint to verify everything works
4. **Start Using**: Your API is ready!

---

## Troubleshooting

**"Neo4j connection failed"**
→ Check credentials from Neo4j Aura
→ Make sure `NEO4J_URI` starts with `bolt://`
→ Verify Neo4j instance is "Running" in Aura

**"Can't access API"**
→ Check Railway logs: Dashboard → Deployments → View Logs
→ Look for error messages
→ Verify all required variables are set

**"Database seems slow"**
→ Use free Neo4j tier for development
→ Upgrade to paid tier if needed for production

---

## Next: Configure Your Data

Once deployed, you can:
1. **Ingest documents**: Upload legal documents to populate graph
2. **Run RAG queries**: Ask questions about legal content
3. **Use API**: Integrate with your applications

See [README.md](README.md) for API endpoint documentation.

---

Happy deploying! 🚀

Need help? Check the full guide in [RAILWAY_DEPLOYMENT_GUIDE.md](RAILWAY_DEPLOYMENT_GUIDE.md)
