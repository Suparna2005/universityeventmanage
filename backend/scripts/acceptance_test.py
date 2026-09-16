"""Smoke acceptance checks for the seeded synthetic dataset.

Run after starting PostgreSQL and executing seed_data.py.
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app.models import Event, User

db = SessionLocal()
try:
    event = db.query(Event).filter_by(title="Synthetic University Test Event").first()
    students = db.query(User).filter_by(role="student").count()
    print("PASS synthetic event exists" if event else "FAIL synthetic event missing")
    print("PASS 50 synthetic students" if students == 50 else f"FAIL expected 50 students, found {students}")
finally:
    db.close()
