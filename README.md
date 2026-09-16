# University Event Platform

A secure full-stack platform for university clubs, events, registrations, QR attendance, certificates, participation hours, finance, feedback, and recommendations.

## Phase 1: Foundation

### Requirements

- Python 3.12 or newer
- Node.js 20 or newer
- PostgreSQL 14 or newer

### Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The API is available at http://localhost:8000 and Swagger is at http://localhost:8000/docs.

### Frontend setup

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The frontend is available at http://localhost:5173.

### PostgreSQL

Create a database and user matching `backend/.env`, or change `DATABASE_URL` to your local PostgreSQL connection string. The health endpoint reports `degraded` until PostgreSQL is reachable.

### Checks

```powershell
# backend
cd backend
pytest

# frontend
cd frontend
npm run build
```

The remaining capabilities are implemented one phase at a time. No production secrets or personal student data belong in this repository.

## Deployment

The frontend is Vercel-ready. In Vercel, import this repository and keep the project root at the repository root; the included `vercel.json` builds `frontend` and serves its `dist` output. Set `VITE_API_URL` to the public URL of the deployed FastAPI service.

The API includes a Vercel Python entry point at `api/index.py`. Configure `DATABASE_URL`, `FRONTEND_URL`, `JWT_SECRET`, and `JWT_EXPIRE_MINUTES` as Vercel environment variables. Use a managed PostgreSQL provider for production; do not use the local development connection string.

Deployment cannot be completed from this workspace without your Vercel account/project and a hosted PostgreSQL URL. The repository contains the deployment configuration and can be deployed with the Vercel dashboard or CLI.
