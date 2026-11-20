# Public portfolio and owner workspace

The website separates public fictional inputs from private owner data. `/demo` is open to everyone and reads curated fictional fixtures (`frontend/src/data/examples.v1.json` for records and `frontend/src/tourData.ts` for the guided simulation). The recorded experience does not query the workspace API, invoke a model, or save visitor submissions. The optional [live tour](22-public-live-demo.md) uses a separate fixed-input public API and real model calls, with a shared daily allowance; it never queries workspace records. All public student emails use the reserved `example.test` domain. Recorded drafts and simulated booking outcomes are labelled as illustrations; live drafts are generated only on request. The guided tour described below allows temporary browser-only edits without changing the published records.

`/workspace` uses the running backend after Google owner sign-in. It provides record inspection, email simulation, and draft review. Public examples never update when workspace records change. Existing bearer-authenticated administration clients continue to work.

## Build and run locally

Use Node.js 22.12 or newer and npm. From the repository root:

```sh
cd frontend
npm ci
npm run build
```

Use the root README to set up PostgreSQL and the backend. From `backend/`:

```sh
uv sync --frozen
uv run --env-file .env.example uvicorn studio_copilot.api.app:app --host 127.0.0.1 --port 8000
```

Open `http://localhost:8000`. FastAPI serves the compiled frontend and the API from one origin. Build before starting the server so its asset directory is mounted. Rebuild and restart after frontend changes. `frontend/dist/` is ignored build output; include it when packaging an application image. `WEBSITE_DIST` can point to an absolute build directory when the backend is packaged separately.

The public site works without Google or OpenAI configuration. Backend startup still requires the existing `DATABASE_URL` and `ADMIN_API_TOKEN`. Owner generation requires OpenAI configuration, application migrations, and explicit LangGraph checkpoint provisioning as described in the agent guide.

For frontend development, `npm run dev` starts Vite on its printed local origin and proxies `/api` and `/auth` to port 8000. When testing Google login through Vite, set `PUBLIC_BASE_URL` and the Google callback to that browser origin, and use that exact origin in the browser.

## Configure owner Google sign-in

Create a Google OAuth web application with the exact authorized redirect URI:

```text
http://localhost:8000/auth/callback
```

For a hosted instance use `https://YOUR-DOMAIN/auth/callback`. Configure Google's consent screen and test users as required for the OAuth application's publishing state. Owner sign-in requests only `openid email profile`; it grants no Gmail or inbox access.

Put these settings in an ignored `backend/.env` or the host's secret configuration:

```text
PUBLIC_BASE_URL=http://localhost:8000
OWNER_EMAIL=your-google-email@example.com
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
SESSION_SECRET=your-stable-random-secret-of-at-least-32-characters
```

Generate a private random signing secret with `uv run python -c 'import secrets; print(secrets.token_urlsafe(48))'` and store it privately. All replicas must share the same secret. Rotate it to invalidate existing sessions. Never put Google secrets, the admin token, or the OpenAI key in frontend environment variables or example JSON.

Start the backend with `--env-file .env` and open `/workspace`. Google must return a verified email matching `OWNER_EMAIL` exactly after case normalization. The server uses Authlib's authorization-code/OpenID Connect validation, OAuth state, nonce, and PKCE. Signed sessions expire after eight hours. The cookie is HttpOnly and SameSite=Lax, and is Secure on HTTPS. Google provider tokens are not retained in the session. Session contents are signed rather than encrypted; they contain only owner identity, expiry, and a CSRF token.

Owner browser sessions can read studio records and submit explicit agent actions: incoming email, run start, review, and retry. Other administration writes are denied even if manually requested. Browser writes require a matching CSRF token and exact configured Origin. The admin bearer credential retains its existing administration scope and is never sent to the frontend.

## Review and recovery

- Approval submits the final edited response and the displayed revision through the existing review API. A validated proposal is booked atomically with the reviewed response. No email is sent and regular enrolments remain unchanged.
- A 409 preserves local edits. The reviewer can inspect the refreshed state and explicitly load the newest draft. Navigation warns before discarding local edits.
- Active processing and finalization states refresh every five seconds. HTTP 200 with `status=failed` is displayed as failure. A stored `approved_response_id` remains visible when memory reconciliation needs recovery.
- Email simulation is persistent and can call the paid model. An unknown sender gets a placeholder student. Repeating intake creates a new email; the browser disables duplicate clicks and never automatically resubmits after an interruption. Inspect the queue before trying again.
- The local seed contains future-dated February 2027 emails. Before then, use a fresh fictional sender for owner intake; the service rejects intake older than the latest conversation email.
- Student profiles show current enrolments, with full history in a collapsed disclosure. Public examples use 11 February 2027; the workspace uses the current date. Confirmed sessions combines scheduled classes covered by non-cancelled dated enrolments and approved makeup bookings, sorted chronologically and shown once per session. Regular sessions must fall within both the enrolment and term dates, using the studio location timezone. A 12-session term displays all 12 scheduled sessions without creating duplicate booking records. Independent session student lists determine capacity.

The new `GET /api/v1/agent-runs` endpoint accepts `status`, `student_id`, `conversation_id`, `q`, `limit`, and `offset`. Search matches student name/email. Ordering is descending creation time followed by ID, including ties. The response uses the existing paginated envelope and includes student identity, status, revision, request summary, safe error, and links to the run/conversation. Full interpretations and evidence remain on the run-detail endpoint.

## Verification

Backend checks, from `backend/`, use a dedicated `_test` PostgreSQL database:

```sh
uv run --env-file .env.example pytest
uv run ruff check .
uv run ruff format --check .
```

Website tests require the built FastAPI app running. From `frontend/`:

```sh
npm exec playwright install chromium
WEBSITE_TEST_URL=http://localhost:8000 npm test
```

To use an already installed Chrome instead, set `PLAYWRIGHT_CHANNEL=chrome`. Without `WEBSITE_TEST_URL`, tests target `http://127.0.0.1:8010`. The suite covers desktop/mobile public navigation, linked historical records, responsive width, keyboard entry, owner access, edited approval, stale-review text preservation, and interrupted-intake recovery. Owner UI tests intercept requests with fictional responses; backend tests cover server authentication, CSRF, permission boundaries, queue queries, and the real workflow separately. Tests do not contact Google or call a paid model.

The schema manifest in `frontend/src/data/schema.v1.json` is checked against SQLAlchemy table names, fields, and foreign keys. Fixture tests verify foreign-key consistency, source message kinds, example identities, and required scenarios.

## Prepare for hosting

Package the frontend build with the FastAPI application and use one public HTTPS origin. Terminate TLS at the host or a trusted reverse proxy, configure `PUBLIC_BASE_URL` to that exact origin, register its Google callback, and keep secrets in server configuration. Keep PostgreSQL private. Run application migrations and checkpoint setup as explicit deployment steps, then start the app; startup does not migrate tables.

Hosting/provider selection, remote provisioning, live inbox integration, public AI generation, studio administration forms, and permanent reviewer audit history remain future work. No remote deployment is performed by this increment. Real Google credentials and a manual owner login are required to confirm OAuth operation for a deployed instance.

## Owner login for the current port-8010 preview

There is no pre-created owner password. Configure a Google OAuth **Web application** client with the exact authorized redirect URI `http://127.0.0.1:8010/auth/callback`. If the OAuth app is in testing, add your Google account as a test user. See [Google’s server-side OAuth setup](https://developers.google.com/identity/protocols/oauth2/web-server).

Set these values locally in the ignored `backend/.env`, alongside existing database/admin/model settings:

```text
PUBLIC_BASE_URL=http://127.0.0.1:8010
OWNER_EMAIL=your-google-email@example.com
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
SESSION_SECRET=your-private-random-secret-at-least-32-characters
```

Generate the signing secret privately with `uv run python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Keep credentials local rather than pasting them into chat.

Restart from `backend/` with `uv run --env-file .env uvicorn studio_copilot.api.app:app --host 127.0.0.1 --port 8010`. Open `http://127.0.0.1:8010/workspace`, choose **Continue with Google**, and use the account matching `OWNER_EMAIL`. Use one exact origin consistently: `localhost` and `127.0.0.1` differ.

## Booking confirmation on approval

A teacher-facing draft may say “Thanks for letting me know. I’ve booked Thursday 11 February for you.” Its **Proposed class booking** panel makes clear that no seat is reserved before approval. **Approve and book class** commits that reservation and the response together or reports a conflict. **Booking confirmed** then appears in the review and the booking is visible on the student profile and session view. Public examples use predefined fictional records and cannot book anything.

Apply the additive migration with `uv run --env-file .env alembic upgrade head` before using the updated owner workspace. Existing drafts without a proposal remain response-only; request a revision or generate a new run to obtain a proposed booking.

## Makeup validation settings

The backend reads the absence-notice timing and class-level order from `STUDIO_POLICY_PATH` (default: `backend/policies/studio.yaml` when running from `backend/`). New AI runs retain a snapshot of these settings, and existing reviews keep their original snapshots. Manage reference material through **Studio knowledge → Documents** and enable documents before using them for answers. The former Rules links redirect to Documents.

Authenticated `GET /api/v1/policy` and `PUT /api/v1/policy` remain available for compatibility. The explanation field in older configuration is excluded from new runs and removed when settings are saved. Browser writes require the owner session, same-origin request, and CSRF token.

## Database browser

The **Database** page lists all nine application tables with record counts. Select a table to inspect every stored column, including IDs, timestamps, message ownership, and full JSON fields. Rows paginate in creation-time/ID order, with 20, 50, or 100 rows per page. The grid scrolls horizontally on narrow screens, and JSON cells expand for inspection. Refresh the database to reload table counts and records, or refresh an individual table.

`/demo/database` uses only the curated fictional fixture. `/workspace/database` reads the authenticated `GET /api/v1/database` catalog and `GET /api/v1/database/{table_name}?limit=20&offset=0` records. These read-only endpoints use the existing owner/bearer access checks and expose only mapped application tables. LangGraph checkpoint and database infrastructure tables remain outside the studio record browser.

## Independent session students

Class sessions store a `students` UUID list, displayed as student names linking to profiles. The timetable shows one session roster; student confirmed attendance uses only explicit session membership. Enrolment changes never rewrite these lists. New sessions begin empty unless students are supplied. `POST /api/v1/sessions` and `PATCH /api/v1/sessions/{id}` accept `students: [student UUID, ...]`. Unknown students, duplicate assignments, and capacity overflow are rejected.

Apply migration `b7e2190c4a63` before starting this version. It copies existing dated regular rosters and approved makeup participants, deduplicates them, then removes the separate booking table and `/bookings` API. Approval adds the student and saves the teacher response atomically; no email is sent. The migration has no lossless downgrade for independent assignments.

## Public guided simulation

The homepage primary action opens `/demo/tour?mode=live`; the tour defaults to live mode and has no visible mode toggle. The recorded test route is `/demo/tour?mode=recorded`. The following describes recorded mode; see [live mode](22-public-live-demo.md) for click-triggered generation and quota behavior. Select `?scenario=booking` (the default, including unknown values) or `?scenario=document` to share a scenario. Both follow Email → Evidence → Teacher review → Confirmation. All content is fictional and curated; the tour makes no API/auth or model requests and sends no email. The existing record browser remains read-only.

The booking example reuses Alex's Thursday-to-Saturday correction, displays prerecorded eligibility checks, and lets a visitor edit and simulate approval. The document example uses a saved clothing-policy revision with an exact highlighted citation. Its missing trial fee requires a teacher answer or deferral and an explicit Update draft before simulated approval. Updating uses a deterministic template and replaces direct response edits; arbitrary final edits are retained verbatim without AI validation. Blank responses cannot be approved.

State is held in a tour-scoped React provider. Back/Next retains edits and decisions. Scenario changes, leaving the tour and reload discard them; there is no reset button. Simulated reservations and approved text never modify the shared public fixtures or workspace records. The public navigation label is Email walkthrough; the existing `/demo/test-email` URL and owner Test email label are retained. Homepage engineering links point to the repository, architecture and dated integrated evaluation, including its hold recommendation and synthetic/AI-review limitations.

`frontend/tests/tour.spec.ts` covers both journeys on desktop/mobile, decision and empty-response gates, literal teacher input, exact source previews, keyboard/focus and state lifecycle. Request interception verifies zero API/auth access and profile comparisons check that published fixtures remain unchanged.

The final step is **Confirmation**. Booking approval shows **Class booked**, a Simulation badge, the class details and a before/after session roster. Remaining places derive from fixture capacity and membership; Alex is added once. The collapsed **View saved record** disclosure represents `class_sessions.students` as student UUIDs, matching the real model rather than inventing booking rows. The real workflow commits this roster update and the reviewed response together in PostgreSQL; the tour does not write to PostgreSQL. A separate collapsed **Approved response** shows the exact approved snapshot, and **Email not sent** remains a distinct delivery status. Information enquiries show **Response approved** without a booking or roster section. **Back to review** preserves edits; reapproval replaces the confirmation snapshot. Leaving, switching scenarios or reloading clears it.

Teacher-facing approval and simulation notices stay outside the student email. The public and owner adapters share the same first-person teacher-voice instruction; scenario inputs and orchestration remain separate. Step headings and source previews still receive programmatic focus for accessibility, without a visible outline; interactive controls retain their keyboard focus indicators.


## Custom email and review presentation

The public Email walkthrough at `/demo/test-email` now lets visitors select a fictional student and freely write an email up to 2,000 characters, then run the isolated AI simulation. It displays the inferred workflow, editable draft, source evidence and missing facts inline. It does not create an owner conversation or write bookings. Workspace Test email retains its existing authenticated intake behavior.

Makeup booking and Document enquiry use an accessible tablist, selected tab and associated panel, with roving keyboard focus. Live mode is the default; the visible Use live AI/Use recorded demo controls have been removed.

Current response presents booking proposals in a dedicated card: state badge, class heading, labeled date/time/location, then a separate approval/capacity note and session-student link. Confirmed bookings use the same hierarchy with a confirmed state and no pending-reservation note. Only presentation changes; approval semantics and permissions remain unchanged.
