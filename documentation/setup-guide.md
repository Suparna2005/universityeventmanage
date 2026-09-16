# Day 1 Setup

## Required software

- Python 3.12+
- Node.js 20+
- PostgreSQL 14+
- pgAdmin 4
- VS Code

## Local SQLite database

SQLite is the default development database. It is created as `backend/university_event.db` when the synthetic seed script runs, so no database server or password is required.

```powershell
cd backend
python scripts/seed_data.py
```

This creates the tables and safe synthetic users, students, and event data.

## PostgreSQL database (optional)

Run this in pgAdmin Query Tool or `psql`:

```sql
CREATE DATABASE university_event_db;
```

Update `backend/.env` with the PostgreSQL password and set:

```env
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@localhost:5432/university_event_db
```

The file is ignored by Git and must never be committed. SQLite remains the recommended Day 1 option.

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

When the configured database is available, `/api/health/database` returns:

```json
{
  "status": "success",
  "message": "PostgreSQL is connected"
}
```

For SQLite, the same endpoint confirms that the configured database is connected; the message remains compatible with the Day 1 API contract.

## Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The system signal panel displays the PostgreSQL connection state.
