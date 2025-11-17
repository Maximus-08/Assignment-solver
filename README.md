# Automated Assignment Solver

A full-stack AI-powered system that automatically fetches assignments from Google Classroom, generates intelligent solutions using Google Gemini AI, and provides a modern web interface for managing and viewing assignments with detailed step-by-step explanations.

## 🏗️ System Architecture

### Three-Tier Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Browser   │─────▶│  Frontend   │─────▶│   Backend   │─────▶│   MongoDB   │
│  (React/    │◀─────│  (Next.js)  │◀─────│  (FastAPI)  │◀─────│  (Database) │
│   Next.js)  │      │             │      │             │      │             │
└─────────────┘      └─────────────┘      └──────┬──────┘      └─────────────┘
                                                  │
                                                  ▼
                                          ┌─────────────┐      ┌─────────────┐
                                          │    Agent    │─────▶│  Gemini AI  │
                                          │  (Python)   │◀─────│   (Google)  │
                                          └─────────────┘      └─────────────┘
```

### Components

1. **Frontend** (`/frontend`) - Next.js 14 + TypeScript + Tailwind CSS
   - User interface and authentication
   - Assignment viewing and management
   - Real-time solution polling and display

2. **Backend** (`/backend`) - FastAPI + MongoDB
   - RESTful API server
   - User authentication (Google OAuth + JWT)
   - Assignment and solution storage
   - Agent orchestration

3. **Agent** (`/agent`) - Python Automation Service
   - Google Classroom integration
   - Gemini AI solution generation
   - Background processing

## ✨ Features

- 🔄 **Automatic Assignment Fetching** - Syncs with Google Classroom
- 🤖 **AI Solution Generation** - Powered by Google Gemini 2.0
- 📝 **Manual Upload** - Add assignments without Google Classroom
- 🔐 **Secure Authentication** - Google OAuth 2.0
- 📊 **Detailed Solutions** - Step-by-step breakdowns with explanations
- 📎 **Attachment Support** - Handle PDFs, images, and documents
- 🔍 **Search & Filter** - Find assignments by subject or title
- 📱 **Responsive Design** - Works on desktop and mobile
- ⚡ **Real-time Updates** - Live status polling for solution generation

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **MongoDB** (local installation or MongoDB Atlas)
- **Google Cloud Project** with:
  - Google Classroom API enabled
  - Gemini API access
  - OAuth 2.0 credentials configured

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Project
   ```

2. **Install Frontend dependencies:**
   ```bash
   cd frontend
   npm install
   ```

3. **Install Backend dependencies:**
   ```bash
   cd ../backend
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

4. **Install Agent dependencies:**
   ```bash
   cd ../agent
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

### Configuration

1. **Frontend** (`frontend/.env.local`):
   ```env
   NEXTAUTH_URL=http://localhost:3000
   NEXTAUTH_SECRET=<generate-with-openssl-rand-base64-32>
   GOOGLE_CLIENT_ID=<your-google-oauth-client-id>
   GOOGLE_CLIENT_SECRET=<your-google-oauth-client-secret>
   NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
   ```

2. **Backend** (`backend/.env`):
   ```env
   MONGODB_URL=mongodb://localhost:27017
   DATABASE_NAME=assignment_solver
   SECRET_KEY=<generate-with-openssl-rand-hex-32>
   BACKEND_API_KEY=<generate-secure-api-key-for-agent>
   GOOGLE_CLIENT_ID=<same-as-frontend>
   GOOGLE_CLIENT_SECRET=<same-as-frontend>
   ```

3. **Agent** (`agent/.env`):
   ```env
   BACKEND_API_URL=http://localhost:8000
   BACKEND_API_KEY=<same-as-backend-api-key>
   GEMINI_API_KEY=<your-google-gemini-api-key>
   GEMINI_MODEL=gemini-2.0-flash
   GOOGLE_CLASSROOM_CREDENTIALS=<path-to-service-account-json>
   ```

### Running the Application

#### Option 1: All-in-One Script (Windows)
```powershell
.\start-all.ps1
```

#### Option 2: Manual Start
```bash
# Terminal 1: Backend
cd backend
.\start-dev.ps1  # Windows
# OR
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
.\start-dev.ps1  # Windows
# OR
npm run dev

# Terminal 3: Agent (runs automatically via backend, manual for testing)
cd agent
python main.py
```

#### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MongoDB**: mongodb://localhost:27017

## 📁 Project Structure

```
Project/
├── frontend/                   # Next.js 14 Web Application
│   ├── src/
│   │   ├── app/               # App Router (Next.js 13+)
│   │   │   ├── api/           # API routes (NextAuth, health checks)
│   │   │   ├── assignments/   # Assignment pages
│   │   │   ├── auth/          # Authentication pages
│   │   │   ├── upload/        # Manual upload page
│   │   │   ├── layout.tsx     # Root layout
│   │   │   └── page.tsx       # Home page
│   │   ├── components/        # React Components
│   │   │   ├── assignments/   # Assignment-related components
│   │   │   ├── layout/        # Layout components (Header, Sidebar)
│   │   │   ├── upload/        # Upload form components
│   │   │   └── ui/            # Reusable UI components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # Utilities
│   │   │   ├── api.ts         # Backend API client
│   │   │   ├── auth.ts        # NextAuth configuration
│   │   │   └── utils.ts       # Helper functions
│   │   └── types/             # TypeScript definitions
│   ├── public/                # Static assets
│   ├── .env.local             # Environment variables
│   ├── package.json           # Dependencies
│   └── start-dev.ps1          # Development startup script
│
├── backend/                    # FastAPI Server
│   ├── app/
│   │   ├── api/               # API Layer
│   │   │   └── v1/
│   │   │       ├── api.py     # Router configuration
│   │   │       └── endpoints/ # API endpoints
│   │   │           ├── assignments.py  # Assignment CRUD + internal
│   │   │           ├── solutions.py    # Solution CRUD + internal
│   │   │           └── users.py        # User management
│   │   ├── core/              # Core Configuration
│   │   │   ├── config.py      # Settings
│   │   │   ├── database.py    # MongoDB connection
│   │   │   ├── security.py    # JWT and password hashing
│   │   │   ├── oauth.py       # Google OAuth verification
│   │   │   ├── middleware.py  # Request/response middleware
│   │   │   └── logging.py     # Logging setup
│   │   ├── models/            # Data Models
│   │   │   ├── assignment.py  # Assignment schema
│   │   │   ├── solution.py    # Solution schema
│   │   │   └── user.py        # User schema
│   │   ├── repositories/      # Database Layer
│   │   │   ├── base.py        # Base repository
│   │   │   ├── assignment.py  # Assignment queries
│   │   │   ├── solution.py    # Solution queries
│   │   │   └── user.py        # User queries
│   │   ├── services/          # Business Logic
│   │   │   └── storage.py     # File storage service
│   │   └── main.py            # FastAPI app initialization
│   ├── .env                   # Environment variables
│   ├── requirements.txt       # Python dependencies
│   └── start-dev.ps1          # Development startup script
│
├── agent/                      # Automation Agent
│   ├── src/
│   │   ├── agent.py           # Main agent orchestration
│   │   ├── auth_manager.py    # Google OAuth management
│   │   ├── backend_auth.py    # Backend authentication
│   │   ├── backend_client.py  # Backend API client
│   │   ├── classroom_client.py# Google Classroom API
│   │   ├── gemini_client.py   # Gemini AI integration
│   │   ├── scheduler.py       # Cron job scheduler
│   │   ├── config.py          # Configuration
│   │   ├── models.py          # Data models
│   │   └── logging_config.py  # Logging setup
│   ├── main.py                # Agent entry point
│   ├── .env                   # Environment variables
│   ├── requirements.txt       # Python dependencies
│   └── start-dev.ps1          # Development startup script
│
├── scripts/                    # Deployment Scripts
│   ├── deploy-railway.ps1     # Railway deployment
│   ├── deploy-vercel.ps1      # Vercel deployment
│   ├── mongo-init.js          # MongoDB initialization
│   └── verify-deployment.ps1  # Deployment verification
│
├── .gitignore                 # Git ignore rules
├── docker-compose.prod.yml    # Production Docker setup
├── DEPLOYMENT.md              # Deployment guide
├── README.md                  # This file
└── start-all.ps1              # Start all services
```

## 🔑 Key Files Explained

### Frontend Files

| File | Purpose |
|------|---------|
| `src/app/layout.tsx` | Root layout with session provider |
| `src/app/page.tsx` | Home page with assignments list |
| `src/app/assignments/[id]/page.tsx` | Individual assignment detail page |
| `src/app/upload/page.tsx` | Manual assignment upload form |
| `src/lib/api.ts` | API client with authentication |
| `src/lib/auth.ts` | NextAuth configuration for Google OAuth |
| `src/components/assignments/AssignmentCard.tsx` | Assignment display card |
| `src/components/assignments/SolutionView.tsx` | Solution display with steps |
| `next.config.js` | Next.js configuration |
| `package.json` | Dependencies (Next.js, NextAuth, Tailwind) |

### Backend Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app initialization, CORS, middleware |
| `app/core/config.py` | Environment variables and settings |
| `app/core/database.py` | MongoDB connection and initialization |
| `app/core/security.py` | JWT token generation and password hashing |
| `app/core/oauth.py` | Google OAuth token verification |
| `app/api/v1/endpoints/assignments.py` | Assignment CRUD + internal agent endpoints |
| `app/api/v1/endpoints/solutions.py` | Solution CRUD + internal agent endpoints |
| `app/api/v1/endpoints/users.py` | User registration and profile |
| `app/models/assignment.py` | Assignment Pydantic models |
| `app/models/solution.py` | Solution Pydantic models |
| `app/repositories/assignment.py` | Assignment database queries |
| `requirements.txt` | Python dependencies (FastAPI, Motor, PyJWT) |

### Agent Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, starts scheduler or one-time run |
| `src/agent.py` | Main orchestration logic, fetches and processes |
| `src/classroom_client.py` | Google Classroom API integration |
| `src/gemini_client.py` | Gemini AI solution generation |
| `src/backend_client.py` | Backend API communication with X-API-Key auth |
| `src/auth_manager.py` | Google OAuth token management |
| `src/scheduler.py` | Cron job for automatic fetching |
| `src/config.py` | Environment variable loading |
| `src/models.py` | Data models (ProcessedAssignment, etc.) |
| `requirements.txt` | Python dependencies (google-api, google-generativeai) |

## 🔄 How It Works

### 1. Assignment Fetching (Automated)
```
Agent Scheduler → Google Classroom API → Fetch Assignments → Backend API → MongoDB
```
- Agent runs on schedule (e.g., every hour)
- Fetches new assignments from Google Classroom
- Stores in backend database

### 2. Assignment Fetching (Manual)
```
User → Frontend Upload Form → Backend API → MongoDB
```
- User uploads assignment details manually
- Supports file attachments (PDF, images)

### 3. Solution Generation
```
User Clicks "Solve" → Backend → Spawns Agent → Gemini AI → Solution → MongoDB → Frontend
```
1. User clicks "Solve with AI" button
2. Backend spawns agent subprocess
3. Agent fetches assignment details
4. Agent sends to Gemini AI with context
5. Gemini generates solution with steps
6. Agent uploads solution to backend
7. Frontend polls and displays result

### 4. Authentication Flow
```
User → Google OAuth → NextAuth → Backend JWT → Protected API Access
```
- Frontend uses NextAuth for Google OAuth
- Backend verifies Google token and issues JWT
- JWT used for all subsequent API requests
- Agent uses separate X-API-Key for internal endpoints

## 🔐 Security Features

- **Google OAuth 2.0** - Secure user authentication
- **JWT Tokens** - Stateless API authentication
- **API Key Authentication** - Separate key for agent-backend communication
- **CORS Protection** - Configured allowed origins
- **Input Validation** - Pydantic models validate all inputs
- **Password Hashing** - Bcrypt for password storage
- **Rate Limiting** - Prevents abuse (configurable)

## 🚢 Deployment

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

**Quick Deploy:**
```bash
# Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Railway
.\scripts\deploy-railway.ps1

# Vercel (Frontend)
.\scripts\deploy-vercel.ps1
```

### Environment Variables (Production)

Set these in your production environment:
- `MONGODB_URL` - Production MongoDB connection string
- `NEXTAUTH_URL` - Production frontend URL
- `BACKEND_API_URL` - Production backend URL
- All API keys and secrets

## 🛠️ Development Tips

### Backend Development
```bash
# Run with hot reload
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Access API docs
open http://localhost:8000/docs
```

### Frontend Development
```bash
# Run with hot reload
cd frontend
npm run dev

# Build for production
npm run build
npm start
```

### Agent Testing
```bash
# Run agent once (manual)
cd agent
python main.py

# Check logs
tail -f agent_workflow_*.log
```

## 🧪 Testing

### Manual Testing
1. Sign in with Google account
2. Upload a test assignment or sync from Classroom
3. Click "Solve with AI"
4. Wait for solution generation (15-30 seconds)
5. View detailed solution with steps

### API Testing
Use the interactive API docs at http://localhost:8000/docs

## 📊 Database Schema

### Collections

**users**
```json
{
  "_id": "ObjectId",
  "email": "string",
  "name": "string",
  "google_id": "string",
  "created_at": "datetime"
}
```

**assignments**
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "title": "string",
  "description": "string",
  "subject_area": "string",
  "status": "pending|processing|completed|failed",
  "attachments": ["array"],
  "created_at": "datetime"
}
```

**solutions**
```json
{
  "_id": "ObjectId",
  "assignment_id": "ObjectId",
  "content": "string",
  "explanation": "string",
  "step_by_step": ["array"],
  "reasoning": "string",
  "confidence_score": "float",
  "ai_model_used": "string",
  "created_at": "datetime"
}
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

This project is for educational purposes.

## 🆘 Troubleshooting

**Frontend won't connect to backend:**
- Check `NEXT_PUBLIC_BACKEND_API_URL` in `.env.local`
- Verify backend is running on port 8000

**MongoDB connection failed:**
- Ensure MongoDB is running (`mongod`)
- Check `MONGODB_URL` in backend `.env`

**Agent can't authenticate:**
- Verify `BACKEND_API_KEY` matches in backend and agent `.env`
- Check agent logs for authentication errors

**Gemini API quota exceeded:**
- Use `gemini-2.0-flash` instead of experimental models
- Check API key and quota at Google AI Studio

**Solutions not appearing:**
- Check browser console for errors
- Verify CORS configuration in backend
- Check backend logs for ObjectId serialization errors

## 📧 Support

For issues and questions, please open an issue in the repository.