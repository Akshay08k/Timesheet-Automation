# DevTimesheet Setup & Local Deployment Guide

## Prerequisites

1. **Python 3.11+**
2. **MongoDB Connection** (MongoDB Atlas URI pasted into `MONGODB_URI` in `.env`, or local MongoDB)
3. **Node.js 18+** & npm
4. **Google Gemini API Key** (from Google AI Studio)
5. **Azure DevOps Personal Access Tokens**:
   - **Client PAT**: Read scope for Code (commits/branches), Pull Requests, and Work Items.
   - **Rysun PAT**: Read & Write scope for Work Items.

---

## 1. Backend Setup

```bash
# In repository root
python -m pip install -r backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MONGODB_URI, GEMINI_API_KEY, and SECRET_KEY
```

### MongoDB Configuration & Encryption

In `.env`:
```env
# MongoDB Connection String (Atlas or local)
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=devtimesheet

# Master key for AES-256-GCM encryption of Azure DevOps PATs and credentials at rest
# (Automatically derived from SECRET_KEY if omitted, or a 32-byte base64 encoded key)
PAT_ENCRYPTION_KEY=
SECRET_KEY=your_secure_random_jwt_secret_key_min_32_characters
```

> **Security Note:** All Azure DevOps Personal Access Tokens (PATs) and credentials are encrypted at rest in MongoDB using AES-256-GCM with unique 96-bit nonces. Passwords are salted and hashed using bcrypt (12 rounds). Sensitive credentials are never returned in plaintext to the frontend or exposed over the API.

```bash
# Run tests
python -m pytest -v backend/tests

# Start backend server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
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

1. Open `http://localhost:5173` in your browser.
2. Register a new user account. The first registered user automatically receives admin privileges.
3. Log in with your new credentials.
4. Click **Connections** in the navigation bar to configure:
   - **Client Azure DevOps**: Organization URL + PAT.
   - **Rysun Azure DevOps**: Organization URL + PAT.
5. Once validated, your PAT is encrypted with AES-256-GCM and stored securely in MongoDB.
