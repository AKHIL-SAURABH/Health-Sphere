from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any
from typing import Optional, List



# =========================
# AUTH SCHEMAS
# =========================

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


# =========================
# PATIENT / DOCTOR SCHEMAS
# =========================

class PatientCreate(BaseModel):
    age: str
    gender: str
    contact_number: str


class DoctorCreate(BaseModel):
    specialization: str
    experience_years: str


# =========================
# APPOINTMENT SCHEMA
# =========================

class AppointmentCreate(BaseModel):
    doctor_id: UUID
    appointment_date: datetime

class MedicalRecordResponse(BaseModel):
    id: UUID
    record_type: str
    file_path: str
    created_at: datetime

class BedStatusCreate(BaseModel):
    hospital_name: str
    total_beds: str
    available_beds: str

# =========================
# AI Prediction Result
# =========================
class AIPredictionResultSchema(BaseModel):
    disease: str
    confidence: float

    class Config:
        from_attributes = True


# =========================
# Patient Upload Response
# =========================
class AIPredictionResponse(BaseModel):
    prediction_id: str
    results: List[AIPredictionResultSchema]
    note: str


# =========================
# Doctor View / History
# =========================
class AIPredictionDoctorView(BaseModel):
    prediction_id: str
    image_path: str
    results: List[AIPredictionResultSchema]

    doctor_verified: str
    doctor_notes: Optional[str]

    created_at: datetime

    class Config:
        from_attributes = True

