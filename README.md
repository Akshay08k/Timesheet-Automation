# DevTimesheet ⏱️🤖

**DevTimesheet** is an enterprise-grade engineering timesheet automation platform. It seamlessly extracts daily engineering activities (Git commits, Pull Requests, code reviews, and linked work items) from a **Client Azure DevOps organization (`ClientCompany`)**, leverages **Google Gemini AI** to produce professional daily summaries formatted in clean **README (Markdown) format** with point-wise bullet items, and creates or updates **Resource Timesheet** work items in your company's **Azure DevOps organization (`MyCompany`)**.

---

## ✨ Key Features & Capabilities

- **Lightweight Google Gemini AI Summarization**:
  - Automatically turns complex Git commits and PRs into an executive 1–2 sentence overview followed by distinct, actionable bullet items (`- `).
  - Strictly grounded in verified activities with low temperature (`0.2`) to prevent AI hallucinations.
  - Generates timesheet entries in **README (CommonMark / GFM)** format directly supported by Azure DevOps work items.
- **Batch Week Generation**:
  - Generates the entire 5-day Monday–Friday timesheet schedule in a single, high-performance backend workflow.
- **High-Performance MongoDB Persistence**:
  - Built with MongoDB Atlas / local MongoDB with connection pooling, automatic index creation, and atomic sequence counters.
  - Multi-user isolation across all collections (`user_id` enforced on every query).
- **Two-Way Idempotent Sync with MyCompany Azure DevOps**:
  - Queries existing timesheets via WIQL to prevent accidental duplicates.
  - Allows 1-click **Update in MyCompany** to refresh previously submitted timesheets with updated descriptions or hours.
- **Optimistic UI with Debounced Persistence**:
  - Instantaneous, zero-lag editing in the timesheet review interface with automatic 400ms debouncing before saving to the server.
- **Zero-Leak Enterprise Security**:
  - Personal Access Tokens (PATs) and credentials are encrypted at rest using **AES-256-GCM** with unique 96-bit nonces.
  - User passwords are protected with **bcrypt** (12 rounds).
  - Tokens and raw diffs are never exposed in API responses or sent to external AI providers.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│         Developer Web App (React 19 + Tailwind)        │
└───────────────────────────┬────────────────────────────┘
                            │ (JWT Bearer Token)
                            ▼
┌────────────────────────────────────────────────────────┐
│           FastAPI Backend Service (Port 8000)          │
│                                                        │
│  ├── Security: AES-256-GCM Credential Encryption       │
│  ├── AI Service: Google Gemini API (Structured Output) │
│  ├── Client Connector: Repositories, Commits, PRs      │
│  └── MyCompany Connector: Resource Timesheets (REST)   │
└─────────────────────┬───────────────────────┬──────────┘
                      │                       │
                      ▼                       ▼
          ┌───────────────────────┐ ┌───────────────────┐
          │  MongoDB Database     │ │  Google Gemini    │
          │  (Atlas / Local)      │ │  Flash Models     │
          └───────────────────────┘ └───────────────────┘
                      ▲                       ▲
                      │                       │
          ┌───────────┴───────────┐ ┌─────────┴─────────┐
          │ Client Azure DevOps   │ │ MyCompany DevOps  │
          │ (ClientCompany)       │ │ (MyCompany)       │
          └───────────────────────┘ └───────────────────┘
```

---

## ⚡ Performance Optimizations

1. **In-Memory External ID Set Lookups**:
   - Pre-fetches all existing external IDs for the authenticated developer into an in-memory set in a single fast query.
   - Eliminates hundreds of sequential round trips to remote databases during client activity synchronization.
2. **MongoDB Compound Indexes**:
   - `("user_id", 1), ("date_str", 1), ("is_excluded", 1)` for instant daily activity grouping.
   - `("user_id", 1), ("date_str", 1)` for atomic timesheet draft resolution.
3. **Single Round-Trip Batch Operations**:
   - All 5 weekdays (Monday through Friday) are resolved in 1 single database batch query (`$in: [cur_date_strs]`).
4. **Lightweight AI Payload**:
   - Strips code diffs and non-essential metadata, transmitting high-signal activity items (type, title, linked PRs/work items) for rapid model generation and reduced token consumption.

---

## 🚀 Quick Start Guide

### 1. Prerequisites

- **Python 3.11+**
- **Node.js 18+** & npm
- **MongoDB Connection** (MongoDB Atlas or local MongoDB)
- **Google Gemini API Key** (from Google AI Studio)

### 2. Backend Setup

```powershell
# Navigate to project root
cd "d:\Projects\Timesheet Automation"

# Install backend dependencies
python -m pip install -r backend/requirements.txt

# Create .env from template
cp .env.example .env
```

Configure your `.env` file:
```env
# Application Settings
APP_ENV=development
HOST=127.0.0.1
PORT=8000
DEBUG=True

# Security
SECRET_KEY=your_secure_random_jwt_secret_key_min_32_characters
PAT_ENCRYPTION_KEY=  # Optional: automatically derived from SECRET_KEY

# Database
MONGODB_URI="mongodb+srv://<user>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority"
MONGODB_DB_NAME=devtimesheet

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Default Organization Settings
DEFAULT_CLIENT_ORG_URL=https://dev.azure.com/ClientCompany
DEFAULT_MYCOMPANY_ORG_URL=https://dev.azure.com/MyCompany
DEFAULT_CLIENT_NAME=ClientCompany
DEFAULT_PROJECT_NAME=ClientCompany - Core Enhancements
DEFAULT_ITERATION=MyCompany Project Management
DEFAULT_AREA_PATH=MyCompany Project Management\ClientCompany
```

Run unit tests:
```powershell
python -m pytest backend/tests
```

Start the FastAPI application:
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`

---

### 3. Frontend Setup

```powershell
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Run frontend in development mode
npm run dev
```

Frontend application will be running at: `http://localhost:5173`

---

## 📋 Standard API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register new user account (first user becomes Admin) |
| `POST` | `/api/auth/token` | Authenticate and obtain JWT Bearer Token |
| `GET` | `/api/auth/me` | Fetch current user profile |
| `GET` | `/api/credentials` | List configured Azure DevOps connections |
| `POST` | `/api/credentials` | Validate & store encrypted PAT credentials |
| `DELETE`| `/api/credentials/{provider}`| Revoke stored credentials (`client` / `mycompany`) |
| `GET` | `/api/activities` | List engineering activities with date/type filters |
| `POST` | `/api/activities/sync` | Sync Git commits & PRs from Client Azure DevOps |
| `PATCH`| `/api/activities/{id}/toggle-exclude` | Exclude/include specific activity from AI summaries |
| `POST` | `/api/summaries/generate` | Generate AI summary for a single day |
| `POST` | `/api/summaries/generate-week` | Generate AI summaries for all 5 weekdays in 1 call |
| `GET` | `/api/timesheets/week/{monday}`| Retrieve weekly review entries with remote status |
| `PATCH`| `/api/timesheets/drafts/{id}` | Update draft fields (debounced autosave) |
| `POST` | `/api/timesheets/submit-day` | Submit / update single day timesheet to MyCompany ADO |
| `POST` | `/api/timesheets/submit-week` | Submit approved timesheets for the entire week |

---

## 🔒 Security Best Practices

1. **PAT Encryption**: PAT tokens are never stored in plaintext and never transmitted to the browser or AI prompts.
2. **Environment Isolation**: Default placeholders `ClientCompany` and `MyCompany` prevent accidental exposure of corporate identities or client project metadata.
3. **Repository Logs**: Sync logs are written to `fetchClientLogs.txt` which is ignored in `.gitignore` to prevent secret leakage.
