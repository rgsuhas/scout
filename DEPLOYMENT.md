# Scout API - Deployment Guide

Scout is an AI-powered roadmap generation service that can be deployed as a standalone API.

## Quick Deploy to Render

### Option 1: Deploy via render.yaml (Recommended)

1. **Push code to GitHub** (already done)

2. **Create New Web Service on Render**
   - Go to https://render.com/dashboard
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository: `https://github.com/rgsuhas/scout`
   - Render will auto-detect `render.yaml`

3. **Set Environment Variables** (in Render Dashboard)
   ```
   GOOGLE_API_KEY=your-google-gemini-api-key
   FRONTEND_URL=https://your-frontend.vercel.app
   ```

4. **Deploy!**
   - Render will automatically build and deploy
   - Your API will be available at: `https://scout.onrender.com` (or your chosen name)

### Option 2: Manual Docker Deployment

1. **Create New Web Service**
   - Go to https://render.com/dashboard
   - Click "New +" → "Web Service"
   - Connect repository: `https://github.com/rgsuhas/scout`

2. **Configure Service**
   ```
   Name: scout-api
   Region: Oregon (or closest to you)
   Branch: main
   Runtime: Docker
   Dockerfile Path: ./Dockerfile
   Docker Context: .
   Plan: Free
   ```

3. **Add Environment Variables**
   ```
   SERVICE_NAME=scout-api
   SERVICE_VERSION=1.0.0
   PORT=8003
   ENVIRONMENT=production
   LOG_LEVEL=info

   AI_PROVIDER=google
   GOOGLE_API_KEY=your-api-key-here
   GOOGLE_MODEL=gemini-2.5-flash
   AI_MAX_TOKENS=65536
   AI_TEMPERATURE=0.7
   AI_TIMEOUT=60

   FRONTEND_URL=https://your-frontend.vercel.app
   DEBUG=false
   RELOAD=false
   ```

4. **Deploy**

---

## API Endpoints

Once deployed, your Scout API will have these endpoints:

### Health Check
```bash
GET https://scout-api.onrender.com/health
```

### Generate Roadmap
```bash
POST https://scout-api.onrender.com/api/v1/roadmap/generate

Body:
{
  "user_goal": "Full Stack Developer",
  "user_skills": [
    {"skill": "JavaScript", "score": 7, "level": "intermediate"}
  ],
  "experience_level": "intermediate",
  "preferences": {
    "learning_style": "hands-on",
    "time_commitment_hours_per_week": 10
  }
}
```

### API Documentation
```bash
GET https://scout-api.onrender.com/docs
```
(Only available in development/staging, disabled in production for security)

---

## Testing Your Deployment

1. **Health Check**
   ```bash
   curl https://scout-api.onrender.com/health
   ```
   Should return:
   ```json
   {
     "status": "healthy",
     "provider": "google",
     "model": "gemini-2.5-flash"
   }
   ```

2. **Generate Test Roadmap**
   ```bash
   curl -X POST https://scout-api.onrender.com/api/v1/roadmap/generate \
     -H "Content-Type: application/json" \
     -d '{
       "user_goal": "Learn Python",
       "user_skills": [],
       "experience_level": "beginner",
       "preferences": {
         "learning_style": "hands-on",
         "time_commitment_hours_per_week": 5
       }
     }'
   ```

---

## Integration with Backend

Update your backend to use Scout API instead of direct Gemini integration:

1. **Add Scout URL to backend .env**
   ```
   SCOUT_API_URL=https://scout-api.onrender.com
   ```

2. **Update backend to call Scout API** (optional)
   - Replace direct Gemini calls with HTTP requests to Scout
   - Scout handles all AI provider logic

---

## Local Development

Run Scout locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY=your-key
export AI_PROVIDER=google

# Run with uvicorn
python -m uvicorn src.main:app --reload --port 8003
```

Or use Docker:

```bash
# Build image
docker build -t scout-api .

# Run container
docker run -p 8003:8003 \
  -e GOOGLE_API_KEY=your-key \
  -e AI_PROVIDER=google \
  scout-api
```

Access at: http://localhost:8003

---

## CORS Configuration

Scout is configured to allow requests from:
- `localhost:*` (all localhost ports)
- All Vercel deployments (`*.vercel.app`)
- All Render deployments (`*.onrender.com`)
- Custom `FRONTEND_URL` from environment

No additional CORS configuration needed!

---

## Monitoring

### Render Dashboard
- View logs in real-time
- Monitor service health
- Check resource usage

### Health Check Endpoint
```bash
curl https://scout-api.onrender.com/health
```

### Logs
```bash
# View logs in Render dashboard
# Or use Render CLI
render logs -s scout-api
```

---

## Troubleshooting

### Service Not Starting
1. Check environment variables in Render dashboard
2. Verify `GOOGLE_API_KEY` is set correctly
3. Check logs for startup errors

### CORS Errors
1. Verify `FRONTEND_URL` is set
2. Check frontend is using correct Scout URL
3. Ensure using HTTPS in production

### API Timeout
1. Increase `AI_TIMEOUT` environment variable
2. Check Gemini API rate limits
3. Monitor Render service health

---

## Cost

**Render Free Tier:**
- ✅ 750 hours/month (always-on)
- ✅ Auto-sleep after 15min inactivity
- ✅ Cold start: ~30-60 seconds
- ✅ Good for development/low-traffic

**Gemini API Free Tier:**
- ✅ 60 requests/minute
- ✅ 1500 requests/day
- ✅ Free with usage limits

---

## Production Checklist

- [ ] `GOOGLE_API_KEY` set in Render dashboard
- [ ] `FRONTEND_URL` set to production frontend URL
- [ ] `ENVIRONMENT=production` set
- [ ] `DEBUG=false` and `RELOAD=false` set
- [ ] Health check endpoint responding
- [ ] Test roadmap generation working
- [ ] CORS configured for frontend domain
- [ ] Monitoring/alerts set up (optional)

---

## Support

- Documentation: See README.md
- API Docs: https://scout-api.onrender.com/docs (dev only)
- GitHub: https://github.com/rgsuhas/scout
