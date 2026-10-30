# Deploying DevTimesheet to Vercel (Frontend + Backend)

This repository is pre-configured to deploy both the **React + TypeScript frontend** and the **FastAPI Python backend** to Vercel as a single full-stack project.

---

## 1. How It Works on Vercel

```
Incoming Request
      │
      ├── /api/* ──► Serverless Function (api/index.py ──► FastAPI backend)
      │
      └── /*     ──► Static Build Output (frontend/dist/ ──► React SPA)
```

- **Frontend**: Built using Vite (`npm run build`) and output to `frontend/dist`.
- **Backend**: Served via Vercel's native `@vercel/python` Serverless runtime using [`api/index.py`](../api/index.py), which wraps [`backend/app/main.py`](../backend/app/main.py).
- **Routing**: Configured via [`vercel.json`](../vercel.json) rewrites.

---

## 2. Step-by-Step Vercel Deployment

### Method A: Deploy via GitHub (Recommended)

1. Push this repository to GitHub:
   ```bash
   git add .
   git commit -m "Configure Vercel deployment for full-stack FE & BE"
   git push origin main
   ```
2. Go to [Vercel Dashboard](https://vercel.com/dashboard) and click **"Add New" ➔ "Project"**.
3. Import your GitHub repository.
4. Keep the default settings (Vercel will automatically read `vercel.json`).
5. Open **Environment Variables** (see below) and add the required keys.
6. Click **Deploy**.

### Method B: Deploy via Vercel CLI

```bash
# Install Vercel CLI if needed
npm install -g vercel

# Login and deploy
vercel
```

---

## 3. Required Environment Variables on Vercel

In your Vercel Project Settings ➔ **Environment Variables**, configure the following:

| Variable | Description | Example / Instructions |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API Key | Get from [Google AI Studio](https://aistudio.google.com/) |
| `SECRET_KEY` | JWT secret key (min 32 chars) | Generate with `openssl rand -hex 32` |
| `PAT_ENCRYPTION_KEY` | 32-byte base64 key for AES-256-GCM | Run: `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"` |
| `DATABASE_URL` | *(Recommended for production)* Remote Database URL | Use free Postgres from **Neon**, **Supabase**, or **Render** (`postgresql://user:pass@host/db`). If omitted, falls back to `/tmp/devtimesheet.db`. |

> [!IMPORTANT]
> **Database Persistence in Serverless**:
> Vercel functions are stateless serverless lambdas. If you don't provide a `DATABASE_URL`, the application automatically uses `/tmp/devtimesheet.db`. However, `/tmp` is wiped when serverless containers cold-start. For multi-day or team usage on Vercel, connect a free hosted PostgreSQL database (such as **Neon** or **Supabase**) by pasting the connection string into `DATABASE_URL`.
