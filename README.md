# Pujo Path

Pujo Path is a responsive Kolkata Durga Puja guide for curated North and South Kolkata pandal routes. Visitors can begin without creating an account, follow the configured stop order, and resume a journey using a signed guest session.

## Run locally

### Backend

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`, with interactive documentation at `/docs`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` when the API is not running at `http://localhost:8000/api`.

### Production hosting

The repository includes a root `vercel.json` that deploys the Vite frontend and
FastAPI backend as two Vercel services on one domain. Deploy from the repository
root, not from `frontend` or `backend`:

```powershell
vercel --prod
```

Configure these Vercel environment variables for the **backend** service before
deploying:

- `SECRET_KEY`: a new random value of at least 32 characters
- `ADMIN_EMAIL`: the production admin email
- `ADMIN_PASSWORD`: the production admin password
- `DATABASE_URL`: a hosted database URL (PostgreSQL is recommended)
- `CORS_ORIGINS`: the exact frontend origin, such as `https://pujo.example.com`

Do not use the development `.env` values in production. Vercel's filesystem is
ephemeral and should not be used for a writable production SQLite database.

Build the frontend with the public API URL:

```powershell
cd frontend
$env:VITE_API_URL="https://api.example.com/api"
npm run build
```

For the same-domain Vercel deployment, omit `VITE_API_URL` (or leave it blank);
the built frontend will call `/api`. If the API is hosted on a different
domain, set `VITE_API_URL` on the **frontend** service to the full URL ending
in `/api`, then redeploy the frontend.
Set the backend `CORS_ORIGINS` environment variable to the exact public frontend origin
(for example, `https://pujo.example.com`) when the frontend and API use different domains.
Serve the SPA fallback (`index.html`) for unknown frontend routes and expose HTTPS URLs
for both services.

## Google Maps

Every journey stop includes Google Maps search and walking-directions links generated from the curated pandal name and address. This works without an API key. The supplied PDFs did not contain verified coordinates, so the imported routes intentionally use searchable area addresses and leave coordinates unset rather than inventing them.

For a future interactive Google Maps JavaScript map, add a restricted browser key as `VITE_GOOGLE_MAPS_API_KEY` in `frontend/.env`. Restrict that key by HTTP referrer and enable only the APIs required by the map implementation.

## Journey access

The visitor experience is frictionless: the frontend obtains a signed guest-session token once and stores it locally. Journey mutations still validate that the token owns the requested journey, so changing a journey ID cannot expose or alter another visitor's progress. Account login and registration are available for visitors who want server-backed identity.

Admin route validation/import endpoints require an authenticated admin:

- `POST /api/admin/routes/validate`
- `POST /api/admin/routes/import`

Use `dry_run: true` to validate and preview route data before importing. Production deployments should replace the development secret and admin credentials in environment configuration.
