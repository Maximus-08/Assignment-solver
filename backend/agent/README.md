# Assignment Solver Agent

This agent is integrated into the backend and automatically generates solutions for assignments using Google Gemini AI.

## How It Works

1. **Triggered by Backend**: When a user clicks "Solve" or "Regenerate" on an assignment, the backend spawns this agent as a subprocess
2. **Fetches Assignment**: Agent retrieves the assignment details from the backend API
3. **Generates Solution**: Uses Google Gemini AI to create detailed solutions with explanations
4. **Uploads Result**: Posts the solution back to the backend API

## Required Environment Variables

These should be set in your Render backend deployment:

```bash
# Google Gemini AI API Key (required)
GEMINI_API_KEY=your_gemini_api_key_here

# Backend API authentication (already set)
BACKEND_API_KEY=your_backend_api_key

# Backend URL (auto-set by Render, use localhost for internal calls)
BACKEND_API_URL=http://localhost:8000
```

## Running Locally

The agent is automatically invoked by the backend. To test manually:

```bash
cd backend
python agent/main.py --assignment-id <assignment_id> --user-id <user_id>
```

## Deployment

The agent is bundled with the backend deployment and requires no separate setup. Just ensure `GEMINI_API_KEY` is set in Render environment variables.
