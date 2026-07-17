"""
PropertyHub — Backend MVP
--------------------------
FastAPI + SQLAlchemy + SQLite (swap DATABASE_URL for Postgres in production).

Run locally:
    pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] pydantic[email] python-multipart
    uvicorn main:app --reload

MVP scope covered:
1. Landlord: create property/unit, invite tenant, basic dashboard stats
2. Tenant: accept invite, view lease, submit maintenance request
3. Rights Center: pick state, browse rights summary, generate one letter type
4. Basic messaging between landlord and tenant

NOTE: This is a single-file MVP for speed of iteration. As the app grows,
split into routers/models/schemas/services packages.
"""

import os
import enum
import uuid
import secrets
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Enum, Text
)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr, field_validator

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./propertyhub.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

LEGAL_DISCLAIMER = (
    "This tool provides general information about tenant rights, not legal "
    "advice. Laws vary by city/county and change over time. For an active "
    "dispute, contact a local tenant union or a legal aid organization in "
    "your area."
)

# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    landlord = "landlord"
    tenant = "tenant"


class MaintenanceStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    properties = relationship("Property", back_populates="landlord")
    leases = relationship("Lease", back_populates="tenant")


class Property(Base):
    __tablename__ = "properties"
    id = Column(Integer, primary_key=True, index=True)
    landlord_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    address_line1 = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)  # 2-letter code, drives Rights Center lookups
    zip_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    landlord = relationship("User", back_populates="properties")
    units = relationship("Unit", back_populates="property", cascade="all, delete-orphan")


class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    unit_label = Column(String, nullable=False)  # e.g. "Unit 2B"
    bedrooms = Column(Integer, default=1)
    bathrooms = Column(Float, default=1.0)
    rent_amount = Column(Float, nullable=False)

    property = relationship("Property", back_populates="units")
    leases = relationship("Lease", back_populates="unit")


class Lease(Base):
    __tablename__ = "leases"
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null until invite accepted
    rent_amount = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    security_deposit = Column(Float, default=0.0)
    document_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    unit = relationship("Unit", back_populates="leases")
    tenant = relationship("User", back_populates="leases")
    payments = relationship("Payment", back_populates="lease", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    is_late = Column(Boolean, default=False)

    lease = relationship("Lease", back_populates="payments")


class Invite(Base):
    __tablename__ = "invites"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, default=lambda: secrets.token_urlsafe(24))
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=True)
    invited_email = Column(String, nullable=False)
    accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    photo_url = Column(String, nullable=True)
    status = Column(Enum(MaintenanceStatus), default=MaintenanceStatus.open)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Static legal-facts store (structured data, NOT AI-generated)
# This is a small illustrative seed. In production this table should be
# maintained/reviewed by someone with legal expertise per jurisdiction.
# ---------------------------------------------------------------------------

STATE_RIGHTS_DATA = {
    "CA": {
        "state_name": "California",
        "security_deposit_limit": "Max 2 months' rent (unfurnished) or 3 months' (furnished).",
        "late_fee_rules": "Must be a 'reasonable' pre-estimate of actual damages; flat arbitrary fees can be challenged.",
        "notice_to_enter": "24 hours written notice generally required, except emergencies.",
        "rent_increase_notice": "30 days' notice for increases under 10%; 90 days if over 10% in 12 months.",
        "required_disclosures": ["Lead paint (pre-1978)", "Bed bug history", "Shared utility arrangements"],
    },
    "NY": {
        "state_name": "New York",
        "security_deposit_limit": "Max 1 month's rent.",
        "late_fee_rules": "Capped at $50 or 5% of monthly rent, whichever is less (varies by locality).",
        "notice_to_enter": "Reasonable advance notice required; not strictly defined by statute in all cases.",
        "rent_increase_notice": "30-90 days depending on tenancy length and increase size.",
        "required_disclosures": ["Lead paint (pre-1978)", "Bed bug history", "Sprinkler system presence"],
    },
    "TX": {
        "state_name": "Texas",
        "security_deposit_limit": "No statutory cap, must be 'reasonable'.",
        "late_fee_rules": "Must be specified in the lease; no statutory cap but must be reasonable.",
        "notice_to_enter": "No statewide statute; lease terms typically govern.",
        "rent_increase_notice": "No statutory notice period outside lease term unless local ordinance applies.",
        "required_disclosures": ["Lead paint (pre-1978)"],
    },
}

LETTER_TEMPLATES = {
    "repair_request": (
        "Dear {landlord_name},\n\n"
        "I am writing to formally request a repair at {property_address}, {unit_label}, "
        "which I currently lease. The issue is as follows:\n\n"
        "{issue_description}\n\n"
        "Please arrange for this repair within a reasonable time as required under "
        "applicable law. Please contact me at {tenant_email} to schedule access.\n\n"
        "Thank you,\n{tenant_name}\n{date_today}"
    ),
    "security_deposit_demand": (
        "Dear {landlord_name},\n\n"
        "My tenancy at {property_address}, {unit_label} ended on {lease_end_date}. "
        "I am requesting the return of my security deposit of ${security_deposit}, "
        "along with an itemized statement of any deductions, as required by law.\n\n"
        "Please respond within the statutory timeframe for your state.\n\n"
        "Sincerely,\n{tenant_name}\n{date_today}"
    ),
    "illegal_fee_dispute": (
        "Dear {landlord_name},\n\n"
        "I am writing regarding a fee charged on my account at {property_address}, "
        "{unit_label}: {fee_description}. Based on the tenant rights information for "
        "my state, I believe this fee may not comply with applicable limits.\n\n"
        "I would appreciate clarification or a correction to this charge.\n\n"
        "Regards,\n{tenant_name}\n{date_today}"
    ),
    "eviction_response": (
        "Dear {landlord_name},\n\n"
        "I am responding to the notice dated {notice_date} regarding my tenancy at "
        "{property_address}, {unit_label}. I am requesting additional information "
        "about the basis for this notice and preserving all rights available to me "
        "under state law.\n\n"
        "{additional_notes}\n\n"
        "Sincerely,\n{tenant_name}\n{date_today}"
    ),
}

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(role: UserRole):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != role:
            raise HTTPException(status_code=403, detail=f"Requires {role.value} role")
        return user
    return dependency


require_landlord = require_role(UserRole.landlord)
require_tenant = require_role(UserRole.tenant)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PropertyCreate(BaseModel):
    name: str
    address_line1: str
    city: str
    state: str
    zip_code: str

    @field_validator("state")
    @classmethod
    def upper_state(cls, v):
        return v.upper()


class UnitCreate(BaseModel):
    unit_label: str
    bedrooms: int = 1
    bathrooms: float = 1.0
    rent_amount: float


class InviteCreate(BaseModel):
    unit_id: int
    invited_email: EmailStr
    rent_amount: float
    start_date: date
    end_date: date
    security_deposit: float = 0.0


class InviteAccept(BaseModel):
    token: str
    email: EmailStr
    password: str
    full_name: str


class MaintenanceRequestCreate(BaseModel):
    unit_id: int
    title: str
    description: str
    photo_url: Optional[str] = None


class MaintenanceStatusUpdate(BaseModel):
    status: MaintenanceStatus


class MessageCreate(BaseModel):
    property_id: int
    recipient_id: int
    body: str


class LegalityCheckRequest(BaseModel):
    state: str
    question_type: str  # e.g. "late_fee", "deposit", "entry_notice", "rent_increase"
    context: Optional[str] = None


class LetterGenerateRequest(BaseModel):
    letter_type: str
    lease_id: int
    issue_description: Optional[str] = None
    fee_description: Optional[str] = None
    notice_date: Optional[str] = None
    additional_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="PropertyHub API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "PropertyHub API", "legal_disclaimer": LEGAL_DISCLAIMER}


# ---- Auth -------------------------------------------------------------

@app.post("/auth/signup", response_model=Token)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return Token(access_token=token)


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return Token(access_token=token)


# ---- Landlord: Properties & Units -------------------------------------

@app.post("/properties")
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    landlord: User = Depends(require_landlord),
):
    prop = Property(landlord_id=landlord.id, **payload.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@app.get("/properties")
def list_properties(db: Session = Depends(get_db), landlord: User = Depends(require_landlord)):
    return db.query(Property).filter(Property.landlord_id == landlord.id).all()


@app.post("/properties/{property_id}/units")
def create_unit(
    property_id: int,
    payload: UnitCreate,
    db: Session = Depends(get_db),
    landlord: User = Depends(require_landlord),
):
    prop = db.query(Property).filter(
        Property.id == property_id, Property.landlord_id == landlord.id
    ).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    unit = Unit(property_id=property_id, **payload.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


# ---- Invites (landlord invites tenant to a unit) -----------------------

@app.post("/invites")
def create_invite(
    payload: InviteCreate,
    db: Session = Depends(get_db),
    landlord: User = Depends(require_landlord),
):
    unit = db.query(Unit).join(Property).filter(
        Unit.id == payload.unit_id, Property.landlord_id == landlord.id
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    lease = Lease(
        unit_id=unit.id,
        tenant_id=None,
        rent_amount=payload.rent_amount,
        start_date=payload.start_date,
        end_date=payload.end_date,
        security_deposit=payload.security_deposit,
    )
    db.add(lease)
    db.flush()  # get lease.id before commit

    invite = Invite(
        unit_id=unit.id,
        lease_id=lease.id,
        invited_email=payload.invited_email,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    # NOTE: in production, send an actual email with a link containing invite.token
    return {"invite_token": invite.token, "invite_link": f"/invite/accept?token={invite.token}"}


@app.post("/invites/accept", response_model=Token)
def accept_invite(payload: InviteAccept, db: Session = Depends(get_db)):
    invite = db.query(Invite).filter(Invite.token == payload.token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.accepted:
        raise HTTPException(status_code=400, detail="Invite already used")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invite expired")
    if invite.invited_email.lower() != payload.email.lower():
        raise HTTPException(status_code=400, detail="Email does not match invite")

    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        tenant = existing_user
    else:
        tenant = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=UserRole.tenant,
        )
        db.add(tenant)
        db.flush()

    lease = db.query(Lease).filter(Lease.id == invite.lease_id).first()
    lease.tenant_id = tenant.id
    invite.accepted = True

    db.commit()

    token = create_access_token({"sub": str(tenant.id), "role": tenant.role.value})
    return Token(access_token=token)


# ---- Dashboards ---------------------------------------------------------

@app.get("/dashboard/landlord")
def landlord_dashboard(db: Session = Depends(get_db), landlord: User = Depends(require_landlord)):
    properties = db.query(Property).filter(Property.landlord_id == landlord.id).all()
    property_ids = [p.id for p in properties]
    units = db.query(Unit).filter(Unit.property_id.in_(property_ids)).all()
    unit_ids = [u.id for u in units]
    leases = db.query(Lease).filter(Lease.unit_id.in_(unit_ids)).all()

    total_units = len(units)
    occupied_units = len([l for l in leases if l.tenant_id and l.is_active])
    occupancy_rate = (occupied_units / total_units * 100) if total_units else 0.0

    lease_ids = [l.id for l in leases]
    payments = db.query(Payment).filter(Payment.lease_id.in_(lease_ids)).all()
    rent_owed = sum(p.amount for p in payments if not p.paid_date)
    rent_collected = sum(p.amount for p in payments if p.paid_date)
    late_payments = [p for p in payments if p.is_late]

    open_requests = db.query(MaintenanceRequest).filter(
        MaintenanceRequest.unit_id.in_(unit_ids),
        MaintenanceRequest.status != MaintenanceStatus.resolved,
    ).all()
    resolved_requests = db.query(MaintenanceRequest).filter(
        MaintenanceRequest.unit_id.in_(unit_ids),
        MaintenanceRequest.status == MaintenanceStatus.resolved,
        MaintenanceRequest.resolved_at.isnot(None),
    ).all()
    if resolved_requests:
        avg_resolution_hours = sum(
            (r.resolved_at - r.created_at).total_seconds() / 3600 for r in resolved_requests
        ) / len(resolved_requests)
    else:
        avg_resolution_hours = None

    upcoming_expirations = sorted(
        [l for l in leases if l.is_active], key=lambda l: l.end_date
    )[:10]

    return {
        "occupancy_rate_pct": round(occupancy_rate, 1),
        "total_units": total_units,
        "occupied_units": occupied_units,
        "rent_collected": rent_collected,
        "rent_owed": rent_owed,
        "open_maintenance_requests": len(open_requests),
        "avg_resolution_hours": round(avg_resolution_hours, 1) if avg_resolution_hours else None,
        "late_payment_count": len(late_payments),
        "upcoming_lease_expirations": [
            {"lease_id": l.id, "unit_id": l.unit_id, "end_date": l.end_date} for l in upcoming_expirations
        ],
    }


@app.get("/dashboard/tenant")
def tenant_dashboard(db: Session = Depends(get_db), tenant: User = Depends(require_tenant)):
    lease = db.query(Lease).filter(Lease.tenant_id == tenant.id, Lease.is_active == True).first()
    if not lease:
        return {"lease": None, "message": "No active lease found."}

    unit = db.query(Unit).filter(Unit.id == lease.unit_id).first()
    prop = db.query(Property).filter(Property.id == unit.property_id).first()

    next_payment = db.query(Payment).filter(
        Payment.lease_id == lease.id, Payment.paid_date.is_(None)
    ).order_by(Payment.due_date).first()

    open_requests = db.query(MaintenanceRequest).filter(
        MaintenanceRequest.unit_id == unit.id,
        MaintenanceRequest.tenant_id == tenant.id,
        MaintenanceRequest.status != MaintenanceStatus.resolved,
    ).count()

    return {
        "property_name": prop.name,
        "unit_label": unit.unit_label,
        "state": prop.state,
        "rent_amount": lease.rent_amount,
        "lease_end_date": lease.end_date,
        "next_payment_due": next_payment.due_date if next_payment else None,
        "next_payment_amount": next_payment.amount if next_payment else None,
        "open_maintenance_requests": open_requests,
        "document_url": lease.document_url,
    }


# ---- Maintenance requests ------------------------------------------------

@app.post("/maintenance-requests")
def submit_maintenance_request(
    payload: MaintenanceRequestCreate,
    db: Session = Depends(get_db),
    tenant: User = Depends(require_tenant),
):
    lease = db.query(Lease).filter(
        Lease.unit_id == payload.unit_id, Lease.tenant_id == tenant.id, Lease.is_active == True
    ).first()
    if not lease:
        raise HTTPException(status_code=403, detail="No active lease on this unit")

    req = MaintenanceRequest(
        unit_id=payload.unit_id,
        tenant_id=tenant.id,
        title=payload.title,
        description=payload.description,
        photo_url=payload.photo_url,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@app.get("/maintenance-requests")
def list_maintenance_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == UserRole.tenant:
        return db.query(MaintenanceRequest).filter(MaintenanceRequest.tenant_id == user.id).all()

    # landlord: all requests across their properties
    properties = db.query(Property).filter(Property.landlord_id == user.id).all()
    property_ids = [p.id for p in properties]
    units = db.query(Unit).filter(Unit.property_id.in_(property_ids)).all()
    unit_ids = [u.id for u in units]
    return db.query(MaintenanceRequest).filter(MaintenanceRequest.unit_id.in_(unit_ids)).all()


@app.patch("/maintenance-requests/{request_id}")
def update_maintenance_status(
    request_id: int,
    payload: MaintenanceStatusUpdate,
    db: Session = Depends(get_db),
    landlord: User = Depends(require_landlord),
):
    req = db.query(MaintenanceRequest).filter(MaintenanceRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = payload.status
    if payload.status == MaintenanceStatus.resolved:
        req.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req


# ---- Messaging ------------------------------------------------------------

@app.post("/messages")
def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    sender: User = Depends(get_current_user),
):
    msg = Message(
        property_id=payload.property_id,
        sender_id=sender.id,
        recipient_id=payload.recipient_id,
        body=payload.body,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@app.get("/messages")
def list_messages(
    property_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Message).filter(
        Message.property_id == property_id,
        (Message.sender_id == user.id) | (Message.recipient_id == user.id),
    ).order_by(Message.created_at).all()


# ---- Rights Center ---------------------------------------------------------

@app.get("/rights/{state}")
def get_state_rights(state: str):
    state = state.upper()
    data = STATE_RIGHTS_DATA.get(state)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No rights data loaded yet for '{state}'. Coverage is expanding state by state.",
        )
    return {**data, "disclaimer": LEGAL_DISCLAIMER}


@app.post("/rights/check")
def check_legality(payload: LegalityCheckRequest):
    """
    'Is this legal?' checker — answers only from structured legal-facts data,
    never from free-form AI guessing.
    """
    state = payload.state.upper()
    data = STATE_RIGHTS_DATA.get(state)
    if not data:
        raise HTTPException(status_code=404, detail=f"No rights data loaded yet for '{state}'.")

    field_map = {
        "late_fee": "late_fee_rules",
        "deposit": "security_deposit_limit",
        "entry_notice": "notice_to_enter",
        "rent_increase": "rent_increase_notice",
    }
    field = field_map.get(payload.question_type)
    if not field:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown question_type. Valid options: {list(field_map.keys())}",
        )

    return {
        "state": data["state_name"],
        "question_type": payload.question_type,
        "relevant_rule": data[field],
        "disclaimer": LEGAL_DISCLAIMER,
    }


@app.post("/letters/generate")
def generate_letter(
    payload: LetterGenerateRequest,
    db: Session = Depends(get_db),
    tenant: User = Depends(require_tenant),
):
    template = LETTER_TEMPLATES.get(payload.letter_type)
    if not template:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown letter_type. Valid options: {list(LETTER_TEMPLATES.keys())}",
        )

    lease = db.query(Lease).filter(Lease.id == payload.lease_id, Lease.tenant_id == tenant.id).first()
    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found for this tenant")

    unit = db.query(Unit).filter(Unit.id == lease.unit_id).first()
    prop = db.query(Property).filter(Property.id == unit.property_id).first()
    landlord = db.query(User).filter(User.id == prop.landlord_id).first()

    fill = {
        "landlord_name": landlord.full_name,
        "tenant_name": tenant.full_name,
        "tenant_email": tenant.email,
        "property_address": f"{prop.address_line1}, {prop.city}, {prop.state} {prop.zip_code}",
        "unit_label": unit.unit_label,
        "lease_end_date": lease.end_date,
        "security_deposit": lease.security_deposit,
        "date_today": date.today().isoformat(),
        "issue_description": payload.issue_description or "[describe the issue]",
        "fee_description": payload.fee_description or "[describe the fee]",
        "notice_date": payload.notice_date or "[notice date]",
        "additional_notes": payload.additional_notes or "",
    }

    letter_text = template.format(**fill)
    return {"letter_type": payload.letter_type, "letter_text": letter_text, "disclaimer": LEGAL_DISCLAIMER}
