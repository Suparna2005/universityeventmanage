from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.database import check_database_connection

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("https://university-event-platform.vercel.app")


@app.get("/api/health")
def health() -> dict[str, str]:
    try:
        check_database_connection()
    except SQLAlchemyError:
        return {"status": "degraded", "database": "unavailable"}
    return {"status": "ok", "database": "connected"}


@app.get("/api/health/database")
def database_health() -> JSONResponse:
    try:
        check_database_connection()
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "PostgreSQL is unavailable"},
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "SQLite is connected" if settings.database_url.startswith("sqlite") else "PostgreSQL is connected",
        },
    )


from app.api import router

app.include_router(router)
