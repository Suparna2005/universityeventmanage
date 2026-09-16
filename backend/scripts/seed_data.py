from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models import Event, User
from app.core.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    roles = [("admin@example.test", "Test Administrator", "administrator"), ("coordinator@example.test", "Test Coordinator", "coordinator"), ("faculty@example.test", "Faculty Mentor", "faculty_mentor"), ("finance@example.test", "Finance Officer", "finance_officer")]
    for email, name, role in roles:
        if not db.query(User).filter_by(email=email).first():
            db.add(User(email=email, full_name=name, password_hash=hash_password("ChangeMe123!"), role=role))
    for index in range(1, 51):
        email = f"student{index:02d}@example.test"
        if not db.query(User).filter_by(email=email).first():
            db.add(User(email=email, full_name=f"Test Student {index:02d}", student_number=f"TEST-{index:04d}", password_hash=hash_password("ChangeMe123!"), role="student"))
    db.commit()
    coordinator = db.query(User).filter_by(email="coordinator@example.test").first()
    if not db.query(Event).filter_by(title="Synthetic University Test Event").first():
        db.add(Event(title="Synthetic University Test Event", description="Safe synthetic acceptance-test event.", event_type="workshop", starts_at=datetime.utcnow() + timedelta(days=7), ends_at=datetime.utcnow() + timedelta(days=7, hours=2), capacity=50, status="published", created_by=coordinator.id))
        db.commit()
finally:
    db.close()
print("Seeded synthetic roles, 50 students, and a capacity-50 event.")
