# DevTimesheet Setup & Local Deployment Guide

## Prerequisites

1. **Python 3.11+** (Tested and compatible with Python 3.14)
2. **Node.js 18+** & npm
3. **Google Gemini API Key** (from Google AI Studio)
4. **Azure DevOps Personal Access Tokens**:
   - **Client PAT**: Read scope for Code (commits/branches), Pull Requests, and Work Items.
   - **Rysun PAT**: Read & Write scope for Work Items.

---

## 1. Backend Setup

```bash
# In repository root
py -m venv backend/.venv
.\backend\.venv\Scripts\pip install -r backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and secure PAT_ENCRYPTION_KEY / SECRET_KEY

# Run tests
.\backend\.venv\Scripts\python.exe -m pytest -v backend/tests

# Start backend server
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend will be available at: `http://127.0.0.1:8000`  
Swagger API Documentation: `http://127.0.0.1:8000/docs`

---

## 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: `http://localhost:5173`

---

## 3. First-Time User Onboarding

1. Open `http://localhost:5173`.
2. Register your user account (the first registered user is assigned Administrator privileges).
3. Navigate to **Connections**:
   - Provide your **Client Azure DevOps Organization URL** and **PAT**.
   - Provide your **Rysun Azure DevOps Organization URL** and **PAT**.
   - Click **Validate & Save**.
4. Navigate to **Weekly Timesheet**:
   - Select the current Monday--Friday week.
   - Click **Sync Client Activity** to fetch commits, PRs, and work items.
   - Click **Generate Summaries** to run the **Google Gemini API** summary analysis on your commits.
   - Review and edit your summaries, log any manual non-code activities (meetings, reviews), and confirm hours.
   - Click **Review & Submit to Rysun**.
