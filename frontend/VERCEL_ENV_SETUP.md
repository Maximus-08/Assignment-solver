# Vercel Environment Variables Setup

## Required Environment Variables

Your Vercel deployment needs these environment variables:

### 1. Backend API URLs
```
NEXT_PUBLIC_BACKEND_API_URL=https://your-backend.onrender.com
BACKEND_API_URL=https://your-backend.onrender.com
```
- `NEXT_PUBLIC_BACKEND_API_URL` - Used by client-side API calls
- `BACKEND_API_URL` - Used by server-side NextAuth to sync tokens with backend

### 2. NextAuth Configuration
```
NEXTAUTH_URL=https://assignment-solver-delta.vercel.app
NEXTAUTH_SECRET=your-secret-key
```

### 3. Google OAuth
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

## How to Add in Vercel

1. Go to https://vercel.com/dashboard
2. Select your project
3. Go to **Settings** → **Environment Variables**
4. Add each variable above
5. Select **Production**, **Preview**, and **Development**
6. Click **Save**
7. **Redeploy** your application

## The 403 Error Fix

The 403 errors happen because:
1. When you log in, NextAuth tries to sync your Google token with the backend
2. It needs `BACKEND_API_URL` to know where to send the request
3. Backend returns a JWT token that's stored in your session
4. This JWT token is used for all API requests
5. **Without `BACKEND_API_URL`, no JWT token is created, so all API calls fail with 403**

## Testing

After adding the environment variables and redeploying:
1. Visit `/debug` to check if `Backend Token` shows "Present"
2. Try syncing Google Classroom
3. API calls should work now

## Current Issue

Your frontend is trying to call backend APIs but doesn't have a valid JWT token because:
- `BACKEND_API_URL` is missing from Vercel environment variables
- The auth sync during login fails silently
- Session has no `backendToken`
- All API calls return 403 Forbidden
