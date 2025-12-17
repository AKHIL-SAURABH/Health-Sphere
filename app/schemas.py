from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any

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


class AIPredictionResponse(BaseModel):
    prediction_id: str
    results: List[Dict[str, Any]]
    all_probabilities: List[Dict[str, Any]]
    note: str

