# DevTimesheet Architecture & Gemini AI Integration

## 1. High-Level Flow

```
[ Developer Browser / React Frontend ]
                 │ (JWT Auth, no credentials stored in browser)
                 ▼
     [ FastAPI Backend (Port 8000) ]
        │                       │
        │ AES-256-GCM           │ Low temp (0.2)
        ▼                       ▼
 [ SQLite Database ]    [ Google Gemini API ]
 (data/devtimesheet.db)  (gemini-2.5-flash)
        ▲                       ▲
        │                       │
 [ Client Azure DevOps ]  [ Rysun Azure DevOps ]
 (Commits, PRs, Tasks)    (Resource Timesheet WIT)
```

## 2. Gemini API Daily Summarization Workflow

1. **Activity Retrieval**: Backend fetches the authenticated developer's Git commits, Pull Requests, reviews, and work items from Client Azure DevOps.
2. **Context Filtering & Sanitization**:
   - Commits are grouped by repository and branch.
   - Conventional commit prefixes (`feat:`, `fix:`, `chore:`, etc.) are parsed.
   - Raw source code diffs and sensitive credentials are completely excluded.
3. **Prompt Construction**:
   - Explicit system instructions enforce strict factual grounding: the model must only summarize tasks directly evidenced by commit messages.
   - Temperature is locked to `0.2`.
   - Never infers working hours.
4. **Structured Schema Output**:
   - Response uses Pydantic schema `GeminiDailySummaryOutput`.
   - Returns concise client-ready summary, detailed bullet points, supporting commit SHAs, PR IDs, and suggested project classification.
5. **Human Control & Audit Trail**:
   - Output is saved as a draft with version 1.
   - User can modify text, add non-code activities (meetings, debugging), or regenerate.
   - Manual edits create new versions without overwriting history.

## 3. Security Principles

- **PAT Security**: Azure DevOps PATs are encrypted at rest using AES-256-GCM with a master key stored in environment configuration. They are never returned to the frontend or sent to the Gemini API.
- **Multi-user Isolation**: All database queries and operations enforce strict `user_id` filtering.
- **Idempotency**: Rysun work items are verified via WIQL query prior to submission to prevent duplicate entries.
