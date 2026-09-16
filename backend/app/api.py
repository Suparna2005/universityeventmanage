from datetime import datetime
from io import BytesIO
from secrets import token_urlsafe
from uuid import uuid4

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import create_token, current_user, hash_password, require_roles, verify_password
from app.database import get_db
from app.models import Attendance, Budget, Certificate, Event, Expense, Feedback, Participation, Registration, Ticket, User

router = APIRouter(prefix="/api")


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=160)
    student_number: str | None = None
    department: str | None = None
    semester: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class EventIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    event_type: str = "seminar"
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(gt=0)


class EventOut(EventIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=4000)


class BudgetIn(BaseModel):
    amount: float = Field(gt=0)


class ExpenseIn(BaseModel):
    amount: float = Field(gt=0)
    description: str = Field(min_length=2, max_length=255)


def sentiment(comment: str, rating: int) -> str:
    positive = {"good", "great", "excellent", "enjoyed", "helpful", "amazing"}
    negative = {"bad", "poor", "boring", "late", "waste", "difficult"}
    words = set(comment.lower().split())
    score = len(words & positive) - len(words & negative) + (rating - 3)
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


@router.post("/auth/register", status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> dict:
    user = User(**payload.model_dump(exclude={"password"}), password_hash=hash_password(payload.password), role="student")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email or student number already exists")
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"id": user.id, "full_name": user.full_name, "role": user.role}}


@router.get("/auth/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "student_number": user.student_number}


@router.post("/events", response_model=EventOut, status_code=201)
def create_event(payload: EventIn, user: User = Depends(require_roles("administrator", "coordinator")), db: Session = Depends(get_db)) -> Event:
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Event end must be after its start")
    event = Event(**payload.model_dump(), created_by=user.id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/events", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)) -> list[Event]:
    return list(db.scalars(select(Event).where(Event.status == "published").order_by(Event.starts_at)))


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/events/{event_id}", response_model=EventOut)
def update_event(event_id: int, payload: EventIn, user: User = Depends(require_roles("administrator", "coordinator")), db: Session = Depends(get_db)) -> Event:
    event = db.get(Event, event_id)
    if not event or (user.role != "administrator" and event.created_by != user.id):
        raise HTTPException(status_code=404, detail="Event not found")
    for key, value in payload.model_dump().items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


@router.post("/events/{event_id}/publish", response_model=EventOut)
def publish_event(event_id: int, user: User = Depends(require_roles("administrator", "faculty_mentor")), db: Session = Depends(get_db)) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = "published"
    db.commit()
    db.refresh(event)
    return event


@router.post("/events/{event_id}/complete", response_model=EventOut)
def complete_event(event_id: int, user: User = Depends(require_roles("administrator", "coordinator")), db: Session = Depends(get_db)) -> Event:
    event = db.get(Event, event_id)
    if not event or (user.role != "administrator" and event.created_by != user.id):
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = "completed"
    db.commit()
    db.refresh(event)
    return event


@router.post("/events/{event_id}/register", status_code=201)
def register_for_event(event_id: int, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)) -> dict:
    event = db.get(Event, event_id)
    if not event or event.status != "published":
        raise HTTPException(status_code=400, detail="Event is not open for registration")
    if db.scalar(select(Registration).where(Registration.event_id == event_id, Registration.student_id == user.id)):
        raise HTTPException(status_code=409, detail="Already registered")
    count = db.scalar(select(func.count()).select_from(Registration).where(Registration.event_id == event_id, Registration.status == "registered")) or 0
    if count >= event.capacity:
        raise HTTPException(status_code=409, detail="Event capacity is full")
    registration = Registration(event_id=event_id, student_id=user.id)
    db.add(registration)
    db.flush()
    ticket = Ticket(registration_id=registration.id, token=token_urlsafe(32))
    db.add(ticket)
    db.commit()
    return {"registration_id": registration.id, "ticket_id": ticket.id, "token": ticket.token}


@router.get("/students/me/registrations")
def my_registrations(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Registration, Event).join(Event, Event.id == Registration.event_id).where(Registration.student_id == user.id)).all()
    return [{"registration_id": r.id, "event_id": event.id, "title": event.title, "status": r.status} for r, event in rows]


@router.get("/tickets/{ticket_id}/qr")
def ticket_qr(ticket_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    ticket = db.get(Ticket, ticket_id)
    registration = db.get(Registration, ticket.registration_id) if ticket else None
    if not ticket or not registration or registration.student_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    image = qrcode.make(ticket.token)
    output = BytesIO()
    image.save(output, format="PNG")
    return Response(output.getvalue(), media_type="image/png")


@router.post("/attendance/check-in")
def check_in(token: str, event_id: int, user: User = Depends(require_roles("administrator", "coordinator")), db: Session = Depends(get_db)) -> dict:
    ticket = db.scalar(select(Ticket).where(Ticket.token == token))
    if not ticket or ticket.status != "active":
        raise HTTPException(status_code=400, detail="Invalid or cancelled ticket")
    registration = db.get(Registration, ticket.registration_id)
    if not registration or registration.event_id != event_id:
        raise HTTPException(status_code=400, detail="Ticket belongs to another event")
    if db.scalar(select(Attendance).where(Attendance.event_id == event_id, Attendance.student_id == registration.student_id)):
        raise HTTPException(status_code=409, detail="Duplicate check-in")
    attendance = Attendance(event_id=event_id, student_id=registration.student_id, ticket_id=ticket.id)
    db.add(attendance)
    db.commit()
    return {"result": "checked_in", "attendance_id": attendance.id, "checked_in_at": attendance.checked_in_at}


@router.get("/events/{event_id}/attendance/summary")
def attendance_summary(event_id: int, user: User = Depends(require_roles("administrator", "coordinator", "faculty_mentor")), db: Session = Depends(get_db)) -> dict:
    total = db.scalar(select(func.count()).select_from(Registration).where(Registration.event_id == event_id)) or 0
    attended = db.scalar(select(func.count()).select_from(Attendance).where(Attendance.event_id == event_id)) or 0
    return {"event_id": event_id, "registered": total, "attended": attended, "absent": total - attended}


@router.get("/admin/events/{event_id}/participants")
def participants(event_id: int, user: User = Depends(require_roles("administrator", "coordinator", "faculty_mentor")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Registration, User).join(User, User.id == Registration.student_id).where(Registration.event_id == event_id)).all()
    return [{"student_name": student.full_name, "student_number": student.student_number, "department": student.department, "semester": student.semester, "registration_status": registration.status, "attendance_status": "present" if db.scalar(select(Attendance).where(Attendance.event_id == event_id, Attendance.student_id == student.id)) else "absent"} for registration, student in rows]


@router.post("/attendance/manual-check-in")
def manual_check_in(event_id: int, student_id: int, user: User = Depends(require_roles("administrator", "coordinator")), db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(Attendance).where(Attendance.event_id == event_id, Attendance.student_id == student_id)):
        raise HTTPException(status_code=409, detail="Duplicate check-in")
    if not db.scalar(select(Registration).where(Registration.event_id == event_id, Registration.student_id == student_id)):
        raise HTTPException(status_code=400, detail="Student is not registered for this event")
    row = Attendance(event_id=event_id, student_id=student_id, method="manual")
    db.add(row)
    db.commit()
    return {"result": "checked_in", "attendance_id": row.id}


@router.post("/events/{event_id}/certificates/generate")
def generate_certificates(event_id: int, user: User = Depends(require_roles("administrator", "coordinator")), db: Session = Depends(get_db)) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = "completed"
    attended = db.scalars(select(Attendance).where(Attendance.event_id == event_id)).all()
    created = 0
    for row in attended:
        exists = db.scalar(select(Certificate).where(Certificate.event_id == event_id, Certificate.student_id == row.student_id))
        if not exists:
            db.add(Certificate(event_id=event_id, student_id=row.student_id, certificate_number=f"UEP-{event_id}-{uuid4().hex[:12].upper()}"))
            db.add(Participation(event_id=event_id, student_id=row.student_id, hours=max((event.ends_at - event.starts_at).total_seconds() / 3600, 0)))
            created += 1
    db.commit()
    return {"generated": created}


@router.get("/students/me/certificates")
def my_certificates(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Certificate, Event).join(Event, Event.id == Certificate.event_id).where(Certificate.student_id == user.id)).all()
    return [{"certificate_number": c.certificate_number, "event": event.title, "created_at": c.created_at} for c, event in rows]


@router.get("/certificates/{certificate_number}/verify")
def verify_certificate(certificate_number: str, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(Certificate).where(Certificate.certificate_number == certificate_number))
    if not row:
        raise HTTPException(status_code=404, detail="Certificate not found")
    event = db.get(Event, row.event_id)
    student = db.get(User, row.student_id)
    return {"valid": True, "certificate_number": row.certificate_number, "student_name": student.full_name, "event": event.title, "issued_at": row.created_at}


@router.get("/students/me/participation-hours")
def my_hours(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)) -> dict:
    total = db.scalar(select(func.coalesce(func.sum(Participation.hours), 0)).where(Participation.student_id == user.id)) or 0
    return {"hours": float(total)}


@router.post("/events/{event_id}/budget", status_code=201, response_model=None)
def create_budget(event_id: int, payload: BudgetIn, user: User = Depends(require_roles("coordinator")), db: Session = Depends(get_db)) -> Budget:
    budget = Budget(event_id=event_id, amount=payload.amount)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.post("/budgets/{budget_id}/approve")
def approve_budget(budget_id: int, user: User = Depends(require_roles("finance_officer", "administrator")), db: Session = Depends(get_db)) -> dict:
    budget = db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    budget.status = "approved"
    db.commit()
    return {"status": budget.status}


@router.post("/budgets/{budget_id}/expenses", status_code=201, response_model=None)
def add_expense(budget_id: int, payload: ExpenseIn, user: User = Depends(require_roles("coordinator")), db: Session = Depends(get_db)) -> Expense:
    budget = db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    expense = Expense(event_id=budget.event_id, submitted_by=user.id, amount=payload.amount, description=payload.description)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.post("/events/{event_id}/feedback", status_code=201, response_model=None)
def add_feedback(event_id: int, payload: FeedbackIn, user: User = Depends(require_roles("student")), db: Session = Depends(get_db)) -> Feedback:
    feedback = Feedback(event_id=event_id, student_id=user.id, rating=payload.rating, comment=payload.comment, sentiment=sentiment(payload.comment, payload.rating))
    db.add(feedback)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Feedback already submitted")
    db.refresh(feedback)
    return feedback


@router.get("/students/me/recommendations")
def recommendations(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)) -> list[dict]:
    events = db.scalars(select(Event).where(Event.status == "published").order_by(Event.starts_at)).all()
    return [{"event_id": event.id, "title": event.title, "score": 50, "explanation": "Recommended from currently published university events."} for event in events]


@router.get("/admin/reports/events")
def event_report(user: User = Depends(require_roles("administrator")), db: Session = Depends(get_db)) -> dict:
    return {"events": db.scalar(select(func.count()).select_from(Event)) or 0, "published": db.scalar(select(func.count()).select_from(Event).where(Event.status == "published")) or 0, "completed": db.scalar(select(func.count()).select_from(Event).where(Event.status == "completed")) or 0}


@router.get("/admin/reports/attendance")
def attendance_report(user: User = Depends(require_roles("administrator")), db: Session = Depends(get_db)) -> dict:
    return {"registrations": db.scalar(select(func.count()).select_from(Registration)) or 0, "attendance": db.scalar(select(func.count()).select_from(Attendance)) or 0}


@router.get("/admin/reports/participation")
def participation_report(user: User = Depends(require_roles("administrator")), db: Session = Depends(get_db)) -> dict:
    total = db.scalar(select(func.coalesce(func.sum(Participation.hours), 0))) or 0
    return {"ledger_entries": db.scalar(select(func.count()).select_from(Participation)) or 0, "hours": float(total)}


