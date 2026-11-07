# DevTimesheet --- Implementation Plan

## 1. Project Overview

Build **DevTimesheet**, a local-hosted, multi-user web application that
collects a developer's engineering activity from the **client Azure
DevOps organization**, uses the **Google Gemini API** to generate daily work summaries,
lets the developer review and override those summaries, and creates
individual **Resource Timesheet** work items in the separate **Rysun
Azure DevOps organization**.

The application is intended to make the Friday timesheet process
reliable and quick:

1.  Synchronize the developer's activity for Monday--Friday.
2.  Group related engineering activity by day.
3.  Generate one editable summary per day.
4.  Allow the developer to add non-code work and correct AI output.
5.  Check Rysun for existing timesheet entries.
6.  Let the developer review and approve each daily entry.
7.  Create or, with explicit confirmation, update the corresponding
    Rysun work items.

**Important:** Git activity is evidence of work, not a measurement of
hours. The application must never infer or fabricate working hours from
commit counts, PR counts, or code volume. The developer confirms hours
and non-code activities.

## 2. Confirmed Requirements

  -----------------------------------------------------------------------
  Area                                Decision
  ----------------------------------- -----------------------------------
  Application                         Browser-based web application

  Initial hosting                     Local machine / local network

  Users                               Multi-user

  Client Azure DevOps organization    Shared organization

  Rysun Azure DevOps organization     Shared organization

  Authentication to Azure DevOps      Each user supplies two PATs

  Client activity sources             Commits, pull requests, reviews,
                                      work items, branches

  Working week                        Monday--Friday

  AI summaries                        Separate daily summary

  Timesheet creation                  Five individual daily work items

  Existing records                    Review differences and ask before
                                      updating

  Manual override                     Required

  AI integration                      Google Gemini API (google-genai SDK)

  Submission                          User-reviewed; never silently
                                      auto-submit
  -----------------------------------------------------------------------

The client and Rysun organizations are separate systems and must have
separate connection configurations and credentials.

## 3. Important Scope and Persistence Decision

The product supports **MongoDB** (both MongoDB Atlas and local MongoDB instances) with **AES-256-GCM encryption at rest** for all sensitive credentials, Personal Access Tokens (PATs), and secrets.

A multi-user application that stores PATs, user settings, drafts, sync checkpoints, and submission history needs durable persistence with strict multi-user isolation. Connection strings are configured via MONGODB_URI in .env.

SQLite is used only for application state and operational records. It is
not intended to become a large analytics warehouse.

If a strictly database-free prototype is required, it may use in-memory
state, but credentials, drafts, synchronization progress, and duplicate
protection will be lost on restart. That is not acceptable for the
usable multi-user version.

## 4. Recommended Technology Stack

Use a modular monolith. Avoid microservices for the initial
implementation.

  -----------------------------------------------------------------------
  Component                           Technology
  ----------------------------------- -----------------------------------
  Frontend                            React + TypeScript

  UI components                       Tailwind CSS + shadcn/ui

  Backend                             Python + FastAPI

  Local persistence                   SQLite

  ORM / data access                   SQLAlchemy

  Schema migrations                   Alembic

  Background scheduling               APScheduler or a simple managed
                                      scheduler

  AI integration                      Google Gemini API (via google-genai SDK)

  Azure DevOps integration            Azure DevOps REST API, initially
                                      API version 7.1 where supported

  Local deployment                    Docker Compose, or a documented
                                      local Python/Node setup
  -----------------------------------------------------------------------

Keep the code structured so SQLite can later be replaced with PostgreSQL
if the deployment grows beyond a single host.

## 5. High-Level Architecture

``` text
Browser
  |
  v
React + TypeScript
  |
  v
FastAPI backend
  |
  +-- Application authentication and user isolation
  |
  +-- Client Azure DevOps connector
  |      +-- Commits
  |      +-- Pull requests
  |      +-- PR reviews and comments
  |      +-- Work items and updates
  |      +-- Branch metadata
  |
  +-- Activity normalization and correlation
  |
  +-- AI summary provider
  |
  +-- Daily summary and manual activity workflow
  |
  +-- Rysun Azure DevOps connector
         +-- Identity validation
         +-- Project / area / iteration configuration
         +-- Resource Timesheet lookup
         +-- Resource Timesheet create / update
  |
  v
SQLite local application file
```

All Azure DevOps API calls and AI API calls must be made by the backend.
Do not expose PATs or provider API keys to browser JavaScript.

## 6. User and Credential Management

### 6.1 Multi-user behavior

-   Provide application login and user-specific settings.
-   Each user configures their own Client PAT and Rysun PAT.
-   The two organizations are shared configuration, but credentials are
    per user.
-   Enforce user-level authorization on every API route and database
    query.
-   Do not allow one user to view or use another user's credentials,
    activities, drafts, or submissions.
-   Provide a clear connection status for each PAT.
-   Allow users to replace or revoke stored credentials.

For the initial local deployment, provide a controlled way to create the
first administrator and add users. The exact onboarding method can be
finalized during implementation; do not leave the application open to
anonymous users on a LAN.

### 6.2 PAT security

-   Store PATs encrypted at rest using authenticated encryption such as
    AES-256-GCM.
-   Keep the encryption key outside SQLite, in an environment variable
    or OS-protected secret store.
-   Never log PATs, authorization headers, or full credential-bearing
    request objects.
-   Never return PAT values to the frontend after they have been saved.
-   Never send PATs to the AI provider.
-   Request only the minimum Azure DevOps scopes needed:
    -   Client PAT: read access to code, pull requests, work items, and
        relevant project metadata.
    -   Rysun PAT: read access for identity/project/work-item discovery
        and work-item read/write for timesheet operations.
-   Validate each connection separately and explain which connection
    failed.

## 7. Client Azure DevOps Activity Collection

Collect activity from the shared client organization using each user's
Client PAT.

### 7.1 Required activity types

1.  **Commits**
    -   Commit ID / SHA
    -   Repository
    -   Branch, when available
    -   Author identity
    -   Author and commit dates
    -   Commit message
    -   Commit URL
2.  **Pull requests**
    -   PR ID
    -   Title and description
    -   Repository
    -   Creator
    -   Status
    -   Creation, update, and completion dates
    -   Source and target branches
    -   PR URL
    -   Associated commits, where available
3.  **Reviews and comments**
    -   Reviewer identity
    -   PR ID
    -   Review / vote / comment content where accessible
    -   Timestamp
    -   Source URL
4.  **Work items**
    -   Work item ID
    -   Title and description
    -   State
    -   Assigned user
    -   Relevant change history / updates
    -   Links to commits and PRs, where available
5.  **Branches**
    -   Repository and branch name
    -   Metadata and links to related commits
    -   Use as context, not as proof of work by itself

### 7.2 Identity attribution

-   Attribute activity to the authenticated developer using Azure DevOps
    identity identifiers where possible.
-   Do not rely only on display-name matching.
-   Support multiple identity aliases for a user if the client
    organization uses more than one identity for that person.
-   Show unattributed or ambiguous activity for review rather than
    silently assigning it.

### 7.3 Date attribution

-   Use the activity's actual event timestamp, converted to the user's
    configured timezone.
-   Distinguish author date, commit date, PR creation date, PR
    completion date, and review/comment date.
-   Do not assign an old commit to the current day merely because it was
    fetched today.
-   The default weekly range is Monday through Friday in the user's
    timezone.
-   Allow the user to select another week or date range.

### 7.4 Incremental synchronization

-   Store synchronization checkpoints per user and source.
-   Fetch only new or changed activity where the API supports it.
-   Handle pagination, rate limits, retries, and transient errors.
-   Deduplicate by stable external identifiers (for example, commit SHA,
    repository ID, PR ID, review/comment ID, and work item ID/update
    ID).
-   Preserve source URLs so users can open the original records.
-   Provide a manual "Sync now" action.
-   Show the last successful sync time and any source-specific errors.

## 8. Activity Normalization and Correlation

Do not send raw API responses directly to the AI model.

Normalize activity into a common internal representation, for example:

``` json
{
  "source_type": "commit",
  "external_id": "commit-sha-or-provider-id",
  "repository": "repository-name",
  "project": "client-project",
  "author_id": "azure-identity-id",
  "occurred_at": "ISO-8601 timestamp",
  "title": "Commit message or PR title",
  "description": "Relevant description",
  "url": "source URL",
  "related_ids": ["PR-123", "WORKITEM-456"]
}
```

### Correlation requirements

-   Group related commits under their PR where possible.
-   Associate PRs with linked work items where possible.
-   Associate reviews and comments with their PR.
-   Avoid counting one underlying change multiple times in the summary.
-   Use branches as supporting context only; branch existence or update
    alone does not prove work was performed on a given date.
-   Preserve individual source records even when they are grouped.
-   Let the user include or exclude activity from summary generation.

The system should generate a concise, factual summary of work performed,
not a list of raw commit messages.

## 9. AI Daily Summary Generation

Generate a separate summary for each working day.

### 9.1 AI input

Send only the minimum relevant, normalized activity data for that day,
such as:

-   Commit messages and links
-   PR titles, descriptions, statuses, and links
-   Review/comment summaries and links
-   Work item titles, descriptions, states, and links
-   User-entered manual activities
-   User-selected project context

Do not send PATs, credentials, unnecessary personal data, or complete
repository contents.

Do not send source code or diffs by default. If a future feature needs
code-level analysis, it must be explicitly enabled and reviewed for
privacy and data exposure.

### 9.2 AI output

For each day, return structured output containing:

-   A concise timesheet-ready task summary.
-   A list of supporting activity references.
-   Any uncertain or ambiguous statements.
-   A note when there is insufficient activity evidence.
-   Optional suggested project mapping, clearly marked as a suggestion.

The AI must not invent tasks, claim a PR was merged when it was not,
infer hours from activity counts, or claim work was completed without
evidence.

### 9.3 Human control

-   Generated summaries are drafts.
-   Users can edit, replace, shorten, or delete generated text.
-   Users can exclude incorrect activity.
-   Users can add manual activities.
-   Users can regenerate a summary after changing included activities.
-   Preserve the original AI-generated text and subsequent edited
    versions.
-   Regeneration must not silently overwrite a user's edits.
-   Show source links supporting generated statements where possible.

### 9.4 Gemini API Integration for Commit History Summarization

The application explicitly uses the **Google Gemini API** (via the official `google-genai` Python SDK) to generate daily timesheet summaries from engineering activity and Git commit history.

#### 9.4.1 Model & Configuration
- **Model**: `gemini-2.5-flash` (or `gemini-1.5-flash` as configurable fallback) for fast, low-latency, and cost-effective text generation.
- **Temperature**: `0.2` (low temperature to minimize hallucination and enforce factual grounding strictly based on commit messages).
- **Client Configuration**: Backend service `GeminiSummaryService` instantiated with `genai.Client(api_key=...)`. The API key is stored securely (environment variable or encrypted app settings) and never leaked to the client browser.

#### 9.4.2 Structured Output Schema
Gemini's structured JSON output mode (`response_mime_type="application/json"`, with Pydantic schema validation) is enforced:

```python
class DailySummaryOutput(BaseModel):
    task_summary: str = Field(
        description="A concise 1-3 sentence timesheet summary formatted for the Rysun Task Summary field."
    )
    detailed_bullets: list[str] = Field(
        description="Bullet points describing specific engineering tasks completed based on commits and PRs."
    )
    referenced_commit_shas: list[str] = Field(
        description="List of commit SHAs directly supporting this summary."
    )
    referenced_pr_ids: list[str] = Field(
        description="List of Pull Request IDs referenced."
    )
    suggested_project: Optional[str] = Field(
        default=None,
        description="Suggested project name based on repository context (e.g. VCQMS or RMA)."
    )
    ambiguities_or_notes: Optional[str] = Field(
        default=None,
        description="Flags if commit messages were vague (e.g. 'misc fix') or require human clarification."
    )
```

#### 9.4.3 Prompt Engineering & Commit Context Construction
When constructing the prompt payload for the Gemini API:
1. **Commit grouping**: Group commits under their corresponding PRs and repositories.
2. **Commit message sanitization**: Clean conventional commit prefixes (e.g., `feat:`, `fix:`, `chore:`, `refactor:`) into clear business/technical descriptions without dropping ticket identifiers.
3. **No raw diffs/code**: Send commit messages, PR titles, descriptions, and linked work item titles. Do not send source code diffs to conserve tokens and maintain strict security/privacy.
4. **Grounding instruction**:
   > "You are an assistant generating professional enterprise timesheet entries. You must strictly summarize only the work evidenced by the provided commit messages, PRs, and work items. Never invent tasks, never estimate or guess hours worked, and never claim tasks are completed if the PR or commit status is in-progress."

#### 9.4.4 Error Handling & Resilience
- **Rate limiting / Quotas**: Implement exponential backoff retry for HTTP 429 and 503 errors.
- **Offline / Fallback mode**: If the Gemini API is unreachable or times out, the backend generates a clean rule-based fallback summary (concatenating sanitized commit messages) and flags that the AI summary could not be generated so the user can easily review and edit.

## 10. Manual Activities and Overrides

Support non-code work, including:

-   Meetings
-   Client discussions
-   Team discussions
-   Debugging and investigation
-   Documentation
-   Requirement analysis
-   Support and coordination
-   Deployment or release activities
-   Other work entered by the developer

Each manual activity should have:

-   Date
-   Category
-   Description
-   Optional duration
-   Optional project
-   Optional notes

Manual activities can be added to the AI-generated daily summary. The
user can also replace the entire summary manually.

The application must distinguish AI-derived activity from manually
entered activity in the review UI.

## 11. Timesheet Configuration

Use the following initial defaults, but keep them configurable.

### 11.1 Common fields

  Field          Initial value / behavior
  -------------- -------------------------------------------------------
  Client Name    Visual Comfort and Co
  Project        Selected per day
  Date           Selected daily date
  Day            Derived from date
  PH             Public holiday flag
  Leave          Default No
  Half Day       Default No
  WFH            Default No
  Hours          Suggested default 8; developer confirms
  Task Summary   Daily AI summary, editable
  Title          `[User Name] - [Date]`
  Assigned To    Logged-in user's resolved Rysun Azure DevOps identity
  Iteration      `Rysun Project Management`

### 11.2 Project and area mapping

Initial mappings:

  ----------------------------------------------------------------------------------------
  Rysun project                       Area path
  ----------------------------------- ----------------------------------------------------
  VCC - VCQMS Enhancements and        `Rysun Project Management\VC - VCQMS`
  InspectionDB                        

  VCC - RMA Modernization             `Rysun Project Management\VCC - RMA Modernization`
  ----------------------------------------------------------------------------------------

The UI must allow project selection per day because a developer may work
on both projects during one week.

Use the configured mapping to select the corresponding area path.
Validate the project, area path, and iteration against Rysun metadata
before submission.

Do not assume the project selection or area mapping can be inferred
reliably from commits alone. AI may suggest a mapping, but the user can
override it.

### 11.3 Special-day behavior

-   Public holiday: mark PH = Yes; do not assume normal working hours.
-   Full-day leave: mark Leave = Yes.
-   Half-day leave: mark Half Day = Yes and ask the user to confirm
    hours.
-   WFH: mark WFH = Yes when selected.
-   Weekend: exclude from the default Monday--Friday timesheet.
-   No code activity: allow manual activity entry; do not fabricate a
    summary or hours.
-   Allow users to configure their timezone and holiday calendar.

## 12. Rysun Resource Timesheet Integration

The Rysun Azure DevOps organization is the destination system.

### 12.1 Discovery before implementation

The provided screenshots show the visible custom Resource Timesheet
form, but do not reveal its underlying API field reference names.

Before implementing creation, use the Rysun PAT to discover and
validate:

-   Organization and project
-   Custom work-item type name
-   Required fields
-   Field reference names
-   Field data types
-   Allowed values for picklists
-   Required title format
-   Client Name field
-   Project field
-   Date and Day fields
-   PH, Leave, Half Day, WFH fields
-   Hours field
-   Task Summary field
-   Area path
-   Iteration path
-   Assigned To behavior
-   Any required custom rules

Use Azure DevOps work-item type metadata and a safe test work item in an
approved test area. Do not guess custom field reference names.

### 12.2 User identity

-   Resolve each user's Rysun identity using Azure DevOps identity APIs
    or a validated identity lookup.
-   Store the stable identity identifier and the appropriate assignable
    identity value.
-   Do not assign by guessing or concatenating display names.
-   Validate assignment before submission.
-   If identity resolution is ambiguous, ask the user to select their
    correct Rysun account.

### 12.3 Work-item creation

Create five separate daily Resource Timesheet work items.

Each item should include:

-   Title: `[User Name] - [Date]`
-   Client Name
-   Project
-   Date
-   Day
-   PH
-   Leave
-   Half Day
-   WFH
-   Hours
-   Task Summary
-   Assigned To
-   Area path
-   Iteration path

The application must use the exact custom field reference names and
values discovered from Rysun.

### 12.4 Existing record detection and review

The selected behavior is **review before updating**.

For each user/date/project combination:

1.  Search Rysun for existing Resource Timesheet records.
2.  Compare relevant fields with the local draft.
3.  If no record exists, mark the entry as ready to create.
4.  If an identical record exists, mark it as already submitted.
5.  If a different record exists, show a field-by-field comparison.
6.  Ask the user whether to keep the existing item or update it.
7.  Never update an existing record silently.
8.  Never create a duplicate when a matching record has already been
    submitted.

Store the returned Rysun work-item ID and submission result locally.

Use an idempotency check before every create request. A local record
alone is not enough: check Rysun too, because users may have created or
changed timesheets outside this application.

### 12.5 Submission safety

-   Submission requires explicit user approval.
-   Show a preview of all five daily entries.
-   Allow submission of selected days if some days are not ready.
-   Record success/failure independently for each day.
-   If three entries succeed and two fail, do not blindly retry all
    five.
-   Provide a retry action for failed entries.
-   Preserve the Rysun work-item ID for successful entries.
-   Provide links to created work items.

## 13. Weekly Workflow and Scheduling

Default workflow:

1.  User opens DevTimesheet.
2.  Selects the Monday--Friday week.
3.  Clicks **Sync Client Activity**.
4.  The backend retrieves and normalizes activity.
5.  The AI generates five daily summaries.
6.  User reviews source activity and summaries.
7.  User adds meetings, discussions, and other non-code work.
8.  User confirms project, area, hours, PH, leave, half day, and WFH
    values.
9.  Application checks Rysun for existing Resource Timesheet records.
10. Application shows create/update/already-submitted states.
11. User reviews the five entries.
12. User explicitly approves creation or updates.
13. Backend submits each entry independently.
14. Application displays the resulting Rysun IDs and links.

### Friday automation

-   Provide a configurable Friday reminder or preparation job.
-   Synchronize activity and prepare drafts automatically if enabled.
-   Do not automatically submit timesheets.
-   Allow manual synchronization and week selection at any time.
-   Do not assume the application is running when the user is away; show
    missed or failed scheduled runs.

## 14. User Interface Requirements

Build the following screens.

### 14.1 Login and user management

-   Application login
-   Administrator-controlled initial user creation
-   User-specific settings
-   User timezone
-   Credential connection status

### 14.2 Connections

Two distinct connection cards:

**Client Azure DevOps** - Organization - PAT input - Validate
connection - Show connected identity - Show accessible projects and
repositories - Last synchronization

**Rysun Azure DevOps** - Organization - PAT input - Validate
connection - Show connected identity - Validate Resource Timesheet
work-item type - Validate project and area configuration

### 14.3 Dashboard

-   Selected week
-   Five daily status cards
-   Activity synchronization status
-   Summary generation status
-   Review completion
-   Existing timesheet warnings
-   Submission status
-   Last sync time

### 14.4 Activity Explorer

-   Group by date
-   Filter by repository, activity type, PR, work item, and author
-   Show commit/PR/review/work-item details
-   Open source records
-   Include/exclude activity
-   Display related activities together
-   Flag ambiguous attribution

### 14.5 Daily Summary Editor

-   AI-generated summary
-   Editable final summary
-   Original generated version
-   Manual activities
-   Supporting source references
-   Regenerate action
-   Hours confirmation
-   Project selection
-   Save draft

### 14.6 Weekly Timesheet Review

-   Five daily records
-   Project and area mapping
-   All custom timesheet fields
-   Existing Rysun record comparison
-   Create/update/already-submitted status
-   Per-day approval
-   Submit selected entries
-   Submission history

### 14.7 Settings

-   AI provider configuration
-   User timezone
-   Holiday calendar
-   Project/area mappings
-   Default hours
-   Friday reminder configuration
-   Credential management

## 15. Local Hosting and Multi-user Access

Initial deployment is one local host running the frontend, backend, and
SQLite file.

-   Other users can access the web application through the host's
    private LAN address if LAN access is enabled.
-   Bind to localhost by default; LAN exposure must be an explicit
    configuration.
-   Use HTTPS if credentials are submitted over a network.
-   Do not expose the application directly to the public internet.
-   Provide a backup and restore mechanism for the SQLite file and
    encryption key.
-   Restrict access to the host and its data directory.
-   Keep logs free of secrets and sensitive request headers.

If the team later needs access from outside the LAN or higher
availability, deploy to a private server and evaluate a managed
database. Keep that migration out of the initial scope.

## 16. Suggested Local Project Structure

``` text
devtimesheet/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── connections/
│   │   │   ├── activity/
│   │   │   ├── summaries/
│   │   │   ├── timesheets/
│   │   │   └── settings/
│   │   ├── api/
│   │   └── types/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── azure_client/
│   │   │   ├── azure_rysun/
│   │   │   ├── activity/
│   │   │   ├── ai/
│   │   │   └── timesheet/
│   │   ├── jobs/
│   │   ├── security/
│   │   └── config/
│   ├── tests/
│   └── pyproject.toml
├── data/
│   └── .gitkeep
├── docs/
│   ├── architecture.md
│   ├── rysun-field-mapping.md
│   └── setup.md
├── .env.example
├── docker-compose.yml
└── README.md
```

Do not commit the SQLite database, PATs, encryption keys, AI API keys,
or real user data to source control.

## 17. Implementation Phases

### Phase 0 --- Rysun and Client API discovery

-   Validate both Azure DevOps connections.
-   Confirm the correct shared organization URLs and project names.
-   Discover the Resource Timesheet work-item type.
-   Discover every required custom field and allowed value.
-   Resolve the Rysun identity format.
-   Test reading and creating a single Resource Timesheet in an approved
    test context.
-   Document exact field mappings and API behavior.

**Exit criteria:** The application can safely read client activity and
can create/read a test Resource Timesheet with correct values.

### Phase 1 --- Application foundation

-   Create frontend and backend projects.
-   Implement application authentication.
-   Implement administrator-controlled user onboarding.
-   Implement SQLite persistence.
-   Implement encrypted PAT storage.
-   Implement per-user authorization.
-   Build Client and Rysun connection validation.

**Exit criteria:** Two test users can connect separate PATs and cannot
access each other's data.

### Phase 2 --- Client activity synchronization

-   Implement commits, PRs, reviews, work items, and branch metadata
    retrieval.
-   Implement identity attribution.
-   Implement date/timezone normalization.
-   Implement pagination and incremental sync.
-   Implement deduplication and activity correlation.
-   Build Activity Explorer.

**Exit criteria:** A selected Monday--Friday period shows correctly
attributed, linked activity.

### Phase 3 --- AI summaries and manual work

-   Implement the Gemini API integration using `google-genai` SDK (`gemini-2.5-flash`).
-   Enforce structured JSON schema for timesheet summaries with referenced commit SHAs.
-   Generate one factual summary per day from commit history and normalized activities.
-   Keep source references for generated statements.
-   Implement activity inclusion/exclusion.
-   Implement manual activity entry.
-   Implement editable summaries and version history.
-   Prevent regeneration from overwriting manual edits.
-   Add explicit hours confirmation.
-   Implement offline / rule-based fallback when Gemini API is unavailable.

**Exit criteria:** A developer can produce and edit five factual daily
summaries.

### Phase 4 --- Rysun timesheet mapping

-   Implement identity lookup.
-   Implement project and area validation.
-   Implement exact custom field mapping.
-   Implement date/day and special-day handling.
-   Implement Resource Timesheet read/search.
-   Implement duplicate detection.
-   Build the weekly timesheet review screen.

**Exit criteria:** The application can accurately preview all fields for
five daily records and identify existing entries.

### Phase 5 --- Safe submission

-   Implement create requests.
-   Implement explicit update confirmation.
-   Implement per-entry status tracking.
-   Implement retry for failed entries.
-   Store returned work-item IDs.
-   Add links to Rysun records.
-   Add audit history.

**Exit criteria:** Five reviewed daily entries can be created without
accidental duplicates, and partial failures can be safely recovered.

### Phase 6 --- Friday preparation and operational hardening

-   Add Friday preparation scheduling.
-   Add reminders.
-   Add connection expiry/error warnings.
-   Add backup/restore.
-   Add API rate-limit handling.
-   Add security and multi-user isolation tests.
-   Add documentation and local deployment instructions.

**Exit criteria:** The system can reliably prepare the weekly review and
operate locally for multiple users.

## 18. Testing Requirements

Test at minimum:

-   Invalid and expired Client PAT.
-   Invalid and expired Rysun PAT.
-   Incorrect user identity.
-   Multiple users with isolated credentials.
-   Pagination and rate limits.
-   Duplicate commits and repeated syncs.
-   PRs with many commits.
-   PRs created on one day and merged on another.
-   Activity with missing or ambiguous author identity.
-   Timezone boundaries and date attribution.
-   No-code workdays.
-   Public holidays, leave, half days, and WFH.
-   AI API failure and malformed AI response.
-   AI regeneration after manual edits.
-   Existing identical timesheet.
-   Existing timesheet with changed summary.
-   Partial submission failure.
-   Retry without duplicate creation.
-   Application restart and persistence recovery.

## 19. Non-goals for the Initial Version

Do not build these unless required by actual usage:

-   Microservices
-   Kubernetes
-   PostgreSQL server
-   Public SaaS multi-tenancy
-   Automatic timesheet submission without review
-   Automatic inference of hours from Git activity
-   Automatic modification of existing Rysun records
-   Full source-code or diff ingestion by AI
-   Complex analytics and productivity scoring
-   Mobile applications

## 20. Instructions to the Implementing Agent

1.  Read this entire plan before making changes.
2.  Inspect the existing repository and its conventions before choosing
    or creating files.
3.  Do not assume custom Rysun field names. Discover and document them
    first.
4.  Do not guess Azure DevOps user identities. Resolve stable identities
    through the organization.
5.  Do not expose PATs or AI API keys to the frontend or logs.
6.  Keep all external API calls in backend services.
7.  Enforce user isolation on every user-owned record and operation.
8.  Use typed request/response schemas and validate external API
    responses.
9.  Keep Client and Rysun integrations separate.
10. Keep activity collection, correlation, AI generation, manual
    editing, and submission as separate services.
11. Preserve source activity and AI summary versions when users edit or
    regenerate summaries.
12. Never fabricate activity or working hours.
13. Require explicit human approval before creating or updating
    timesheet work items.
14. Make submission idempotent and recoverable after partial failures.
15. Add tests for critical logic and API integrations; mock external
    APIs in automated tests.
16. Implement incrementally by phase. Do not attempt to build the entire
    system in one unreviewed code-generation step.
17. Maintain a clear README with local setup, configuration, security,
    and troubleshooting instructions.
18. Update this plan or supporting documentation when a confirmed
    implementation decision changes.

## 21. Open Decisions to Confirm During Implementation

These items were not fully decided yet. Use sensible defaults, document
the choice, and ask before making decisions that affect security or
timesheet correctness.

-   Exact local hosting model: one LAN-accessible host versus one
    instance per developer.
-   User onboarding: administrator-created accounts versus another
    controlled registration process.
-   AI provider: **Confirmed** --- Google Gemini API (using `google-genai` SDK with `gemini-2.5-flash` and structured schema output).
-   Whether one developer may select different projects on different
    days (recommended: yes).
-   User timezone and holiday-calendar source.
-   Exact Client and Rysun organization URLs and project identifiers.
-   Exact Resource Timesheet work-item type and custom field reference
    names.
-   Whether Rysun allows updates to submitted/closed records and what
    permissions are required.
-   Whether client activity includes multiple repositories or projects
    for the same user.

------------------------------------------------------------------------

## Definition of Done

The initial product is complete when a user can:

1.  Sign in to DevTimesheet.
2.  Connect their own Client and Rysun PATs.
3.  Select a Monday--Friday period.
4.  Synchronize their own Client Azure DevOps commits, PRs, reviews,
    work items, and branch context.
5.  Review correctly attributed daily activity.
6.  Generate five AI summaries.
7.  Add non-code work and manually edit or replace summaries.
8.  Confirm each day's hours, project, and special-day fields.
9.  Detect existing Rysun Resource Timesheet work items.
10. Review differences and explicitly approve create/update actions.
11. Submit the five daily records and receive their Rysun work-item
    links.
12. Reopen the application later and see the saved drafts, history, and
    submission status.

**Product principle:** Automate collection and preparation; keep the
developer in control of what is reported and submitted.
