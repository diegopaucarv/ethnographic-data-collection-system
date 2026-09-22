"""Pydantic models for Ayni collection system."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator

ALLOWED_FORM_TYPES = {"ENT", "OBS", "REC", "MEM"}
ALLOWED_STATUSES = {"draft", "submitted"}


def validate_form_type(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in ALLOWED_FORM_TYPES:
        raise ValueError("Unsupported form type")
    return normalized


def validate_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_STATUSES:
        raise ValueError("Unsupported status")
    return normalized


def validate_data(value: dict[str, Any]) -> dict[str, Any]:
    if len(str(value).encode("utf-8")) > 1_000_000:
        raise ValueError("Submission payload is too large")
    return value


# User/Auth Models
class UserBase(BaseModel):
    email: str
    name: str


class UserLogin(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserCreate(UserBase):
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value


class User(UserBase):
    id: str
    role: str  # "admin", "collector"
    created_at: datetime
    updated_at: datetime


# Form Definition Models
class FormDefinition(BaseModel):
    code: str  # ETN, OBS, REC, MEM
    title: str
    description: str
    order: int
    fields: list[dict[str, Any]]  # Field configuration


# Form Submission Models
class EtnographicScene(BaseModel):
    """Ficha de escena etnográfica"""
    date: str
    time_start: str
    place: str
    people: Optional[str] = None
    context: Optional[str] = None
    researcher_position: Optional[str] = None
    reflexivity: Optional[str] = None
    initial_impressions: Optional[str] = None
    key_moments: Optional[str] = None
    participant_reactions: Optional[str] = None
    personal_notes: Optional[str] = None
    image_url: Optional[str] = None


class ObservationDay(BaseModel):
    """Jornada de observación"""
    date: str
    time_start: str
    time_end: str
    place: str
    position: str
    main_activity: str
    participants: Optional[str] = None
    interruptions: Optional[str] = None
    image_url: Optional[str] = None


class SceneRecord(BaseModel):
    """Registro de escenas"""
    date: str
    dense_description: str
    exact_phrases: Optional[str] = None
    interpretations: Optional[str] = None
    preliminary_codes: Optional[str] = None
    image_url: Optional[str] = None


class AnalyticMemo(BaseModel):
    """Memo analítico"""
    date: str
    main_findings: str
    emergent_questions: str
    connections: Optional[str] = None
    next_steps: Optional[str] = None
    conceptual_insights: Optional[str] = None
    methodological_notes: Optional[str] = None
    reflexivity: Optional[str] = None


class FormSubmission(BaseModel):
    """Generic form submission wrapper"""
    id: str
    user_id: str
    form_type: str  # "ETN", "OBS", "REC", "MEM"
    form_code: str  # ETN-001, OBS-002, etc.
    data: dict[str, Any]
    status: str  # "draft", "submitted", "synced"
    client_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None


class FormSubmissionCreate(BaseModel):
    """Create a new form submission."""
    form_type: str
    data: dict[str, Any]
    status: str = "draft"
    client_id: Optional[str] = Field(default=None, min_length=1, max_length=128)

    _validate_type = field_validator("form_type")(validate_form_type)
    _validate_data = field_validator("data")(validate_data)
    _validate_status = field_validator("status")(validate_status)


class FormSubmissionUpdate(BaseModel):
    """Update a form submission."""
    data: Optional[dict[str, Any]] = None
    status: Optional[str] = None

    _validate_data = field_validator("data")(validate_data)
    _validate_status = field_validator("status")(validate_status)


class TeamFormsList(BaseModel):
    """List of forms submitted by team (read-only for non-admins)"""
    forms: list[FormSubmission]
    total: int
