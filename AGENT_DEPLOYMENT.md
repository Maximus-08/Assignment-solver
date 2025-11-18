# Agent Deployment Checklist

## ✅ Completed Steps

### 1. Agent Integration into Backend
- ✅ Copied agent source code to `backend/agent/` directory
- ✅ Updated `backend/requirements.txt` with agent dependencies:
  - `google-generativeai==0.8.3`
  - `apscheduler==3.10.4`
  - `tenacity==8.2.3`
- ✅ Updated backend code to use `backend/agent/main.py` path
- ✅ Removed dependency on separate agent venv (uses backend Python)

### 2. Fixed Assignment Sync Issue
- ✅ Added `useQueryClient` hook to assignments page
- ✅ Auto-refresh assignments list after Google Classroom sync completes
- ✅ Removed "Refresh page" message - now refreshes automatically
- ✅ Imported `assignmentKeys` to properly invalidate query cache

### 3. Configuration Files Updated
- ✅ Agent config uses environment variables properly
- ✅ `BACKEND_API_URL` defaults to `localhost:8000` (internal on Render)
- ✅ `GEMINI_API_KEY` read from environment
- ✅ `BACKEND_API_KEY` read from environment

### 4. Git Repository
- ✅ All changes committed and pushed to main branch
- ✅ Latest commits:
  - `b401447` - Fix assignment sync auto-refresh and agent deployment config
  - `877661e` - Add agent code to backend for Render deployment
  - `c9b3b61` - Fix CORS: move CORSMiddleware to last

## 🔧 Required Render Environment Variables

Add these in Render Dashboard → assignment-solver-backend → Environment:

### Critical (Agent Won't Work Without These)
```bash
GEMINI_API_KEY=<your-gemini-api-key>
```

### Already Set (Verify These)
```bash
BACKEND_API_KEY=<already-generated>
MONGODB_URL=mongodb+srv://...
SECRET_KEY=<already-generated>
GOOGLE_CLIENT_ID=<your-google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-google-oauth-client-secret>
BACKEND_CORS_ORIGINS=["https://assignment-solver-delta.vercel.app"]
```

### Optional (Have Defaults)
```bash
BACKEND_API_URL=http://localhost:8000  # Internal calls on Render
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## 🎯 How to Get Gemini API Key

1. Go to https://makersuite.google.com/app/apikey (or https://aistudio.google.com/app/apikey)
2. Click "Create API key"
3. Select a Google Cloud project (or create one)
4. Copy the API key
5. Add to Render as `GEMINI_API_KEY` environment variable

## 🔄 Deployment Flow

Once you add `GEMINI_API_KEY` to Render:

1. Render will automatically trigger a redeploy
2. Backend will install agent dependencies from `requirements.txt`
3. Agent code will be available at `backend/agent/`
4. When users click "Solve" or "Regenerate", backend spawns agent subprocess
5. Agent generates solution using Gemini AI
6. Solution is uploaded back to backend API
7. Frontend shows solution status updates

## 🧪 Testing After Deployment

1. **Test CORS** (should already work after previous fix):
   - Visit https://assignment-solver-delta.vercel.app
   - Check browser console for CORS errors
   - Should see successful API calls

2. **Test Google OAuth**:
   - Click "Sign in with Google"
   - Should redirect and authenticate successfully
   - Check that user email appears in header

3. **Test Assignment Sync**:
   - Click "Sync Google Classroom" button
   - Should see "Synced X new assignments" message
   - Assignments should appear automatically (no manual refresh needed)

4. **Test Solution Generation**:
   - Click on an assignment
   - Click "Solve Assignment" button
   - Status should change to "Processing..."
   - After 30-60 seconds, solution should appear
   - Verify solution has:
     - Step-by-step breakdown
     - Detailed explanation
     - Final answer
     - Confidence score

5. **Test Regenerate**:
   - Click "Regenerate Solution" on existing solution
   - Old solution should be deleted
   - New solution should be generated
   - Should be different from previous solution

## 🐛 Troubleshooting

### Agent Not Working
- Check Render logs for error messages
- Verify `GEMINI_API_KEY` is set correctly
- Ensure backend redeployed after adding env var
- Check if Gemini API quota is exceeded

### Assignments Not Syncing
- Verify user has signed in with Google
- Check Google OAuth tokens are stored in database
- Verify Google Classroom API is enabled in Google Cloud Console
- Check Render logs for Google API errors

### Solutions Not Generating
- Check if assignment status is stuck on "processing"
- Look for agent subprocess errors in Render logs
- Verify `BACKEND_API_KEY` matches between backend and agent
- Check if Gemini API is responding (might be rate limited)

## 📊 Monitor Agent Activity

In Render logs, search for:
- `"Starting agent for assignment"` - Agent triggered
- `"Agent completed successfully"` - Solution generated
- `"Agent failed"` - Error occurred
- `"GEMINI_API_KEY not found"` - Missing API key
- `"Failed to generate solution"` - Gemini API error

## ✨ Next Steps

1. Add `GEMINI_API_KEY` to Render environment variables
2. Wait for automatic redeploy (2-3 minutes)
3. Test full workflow on production site
4. If issues, check Render logs and report errors
