---
name: run-dance-studio-app
description: Start the Dance Studio Copilot frontend and backend locally and report their URLs and startup blockers.
---

# Run Dance Studio App

Start the app from this repository and leave its services running. Preserve the existing environment and database data.

1. Select `backend/.env` if present, otherwise `backend/.env.example`. Determine the effective `PUBLIC_BASE_URL`, `DATABASE_URL`, and `WEBSITE_DIST` from the environment that will launch the backend: variables already exported in that environment take precedence over the selected file when using `uv run --env-file`. Do not print secrets. Google sign-in and owner writes require the browser's exact configured origin, including scheme, hostname and port. The Google callback must be registered as `<PUBLIC_BASE_URL>/auth/callback`.
2. Check the configured database and existing listeners before starting services. Reuse a running backend only after identifying it as this checkout, checking its health, and establishing that its effective `PUBLIC_BASE_URL`, `DATABASE_URL`, and `WEBSITE_DIST` match the intended configuration. Compare settings without revealing secrets. If its configuration cannot be established, report the blocker rather than assuming it matches. If the configured database is the local Compose database and it is unavailable, start it with `docker compose up -d --wait db` from the repository root. Do not reset its data or start Compose as a substitute for a different configured database.
3. For a local HTTP origin on port 8000, install missing or incomplete frontend dependencies with `npm ci` and build with `npm run build` from `frontend/` **before starting the backend**. FastAPI mounts static assets at startup. If `WEBSITE_DIST` points elsewhere, ensure the build is available there or report the configuration conflict. If reusing an already running backend, verify it serves the built assets; if it cannot be restarted with its existing configuration, report the blocker. The project requires Node.js 22.12 or newer.
4. Start the backend in a persistent terminal from `backend/`, using the selected environment file and the same inherited environment inspected above:

   ```sh
   uv run --env-file .env uvicorn studio_copilot.api.app:app --host 127.0.0.1 --port 8000
   ```

   Replace `.env` with `.env.example` when appropriate. If port 8000 is occupied by another service, report the conflict instead of stopping it or silently changing the backend port: the frontend proxy targets port 8000.
5. Serve the frontend at the exact configured origin:

   - For an HTTP origin on `localhost` or `127.0.0.1` with a port other than 8000, start Vite in a separate persistent terminal from `frontend/` with `npm run dev -- --host <hostname> --port <port> --strictPort`. Use the hostname and port from `PUBLIC_BASE_URL`. If the port is occupied, identify the listener and report the conflict unless it is this app's frontend.
   - For the local HTTP origin on port 8000, use the built frontend served by the backend. This supports the example configuration, `http://localhost:8000`.
   - If the configured origin cannot be served by these local commands, explain the conflict and the configuration needed; do not silently use a different origin or modify Google or environment settings.

   For Vite, install missing or incomplete frontend dependencies with `npm ci` from `frontend/` first. Vite proxies `/auth` and `/api` to the backend on port 8000.
6. Check `http://127.0.0.1:8000/health`, load the frontend at the exact configured origin, verify its assets load, and check `/auth/me` through that origin. A healthy endpoint and `login_available: true` confirm the local service is ready for a login attempt; they do not prove Google sign-in succeeds.
7. Report the portal URL, backend URL, whether the local database was started, and any concrete blocker. Keep the app running.

Do not seed demo data, run migrations, or configure the AI agent merely to start the app. If required setup is missing, report the blocker and the setup needed.
