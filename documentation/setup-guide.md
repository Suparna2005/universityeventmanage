# Day 1 Setup

## Required software

- Python 3.12+
- Node.js 20+
- PostgreSQL 14+
- pgAdmin 4
- VS Code

## PostgreSQL database

Run this in pgAdmin Query Tool or `psql`:

```sql
CREATE DATABASE university_event_db;
```

Update `backend/.env` with the PostgreSQL password. The file is ignored by Git and must never be committed.

## Start the backend

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Check:

- http://localhost:8000/api/health
- http://localhost:8000/api/health/database
- http://localhost:8000/docs

When PostgreSQL is running and the credentials are correct, `/api/health/database` returns:

```json
{
  "status": "success",
  "message": "PostgreSQL is connected"
}
```

## Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The system signal panel displays the PostgreSQL connection state.
