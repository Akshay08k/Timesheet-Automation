# DevTimesheet ⏱️🤖

**DevTimesheet** is a local-first, multi-user engineering timesheet automation platform. It synchronizes a developer's activity (Git commits, Pull Requests, reviews, work items) from the **Client Azure DevOps organization**, uses the **Google Gemini API** (`gemini-2.5-flash`) to generate structured daily summaries grounded strictly in commit history, and creates/updates **Resource Timesheet** work items in the **Rysun Azure DevOps organization** after developer review.

---

## ✨ Features

- **Google Gemini API Summarization**: Generates professional 1-3 sentence task summaries and actionable work bullets from Git commits with zero hallucinations, strict grounding, and low temperature (`0.2`).
- **Activity Correlation**: Groups commits under their respective Pull Requests and branches; supports excluding non-relevant commits.
- **Manual Work Logger**: Easily logs non-code activities like client meetings, architectural discussions, debugging, and code reviews.
- **Rysun Azure DevOps Integration**: Idempotently detects existing timesheets via WIQL to prevent duplicates and submits verified 5-day Monday--Friday timesheet records.
- **Enterprise Security**:
  - Personal Access Tokens (PATs) are encrypted at rest using **AES-256-GCM**.
  - PATs and raw source code diffs are never sent to the Gemini API or browser client.
  - Multi-user isolation across all routes and database queries.
- **Local-First Persistence**: Lightweight embedded SQLite database (`data/devtimesheet.db`) requiring no separate database server.

---

## 🏗️ Architecture

```
Browser (React + TypeScript + Tailwind)
   │
   ▼ (JWT Session)
FastAPI Backend (Port 8000)
   ├── Security: AES-256-GCM PAT Encryption
   ├── Persistence: SQLite via SQLAlchemy
   ├── Google Gemini API: Structured commit summarization
   ├── Client ADO Connector: Commits, PRs, branches, reviews
   └── Rysun ADO Connector: Resource Timesheet discovery & patch
```

---

## 🚀 Quick Start

### 1. Backend Setup

```powershell
# Navigate to project root
cd "d:\TimeSheet Automation"

# Initialize virtual environment (Python 3.11+)
py -m venv backend\.venv
.\backend\.venv\Scripts\pip install -r backend\requirements.txt

# Configure environment variables
# Copy .env.example to .env and configure GEMINI_API_KEY
cp .env.example .env

# Run automated test suite
.\backend\.venv\Scripts\python.exe -m pytest -v backend\tests

# Start FastAPI server
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

FastAPI will be available at: [http://127.0.0.1:8000](http://127.0.0.1:8000)  
Interactive OpenAPI / Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Frontend will be available at: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Testing

Run backend tests covering AES-256-GCM encryption, JWT authentication, Gemini API commit summarization, and draft creation:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v backend\tests
```

Build and test frontend TypeScript compilation:

```powershell
cd frontend
npm run build
```

---

## 📖 Documentation

- [plan.md](plan.md): Full product specification and phased delivery roadmap.
- [docs/architecture.md](docs/architecture.md): Architectural flow and Gemini AI prompt engineering details.
- [docs/vercel-deployment.md](docs/vercel-deployment.md): Step-by-step guide for full-stack deployment on Vercel.
- [docs/rysun-field-mapping.md](docs/rysun-field-mapping.md): Field reference names and WIQL queries for Rysun Resource Timesheet work items.
- [docs/setup.md](docs/setup.md): Complete setup and deployment guide.
