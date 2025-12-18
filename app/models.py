from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .database import Base


# =========================
# USER
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # PATIENT | DOCTOR | ADMIN
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)


# =========================
# PATIENT
# =========================
class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    age = Column(String)
    gender = Column(String)
    contact_number = Column(String)

    user = relationship("User", back_populates="patient")
    records = relationship("MedicalRecord", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")


# =========================
# DOCTOR
# =========================
class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    specialization = Column(String)
    experience_years = Column(String)
    availability_status = Column(String, default="AVAILABLE")

    user = relationship("User", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")


# =========================
# APPOINTMENT
# =========================
class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=False)

    appointment_date = Column(DateTime, nullable=False)
    status = Column(String, default="BOOKED")
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


# =========================
# MEDICAL RECORD (MedVault)
# =========================
class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=True)

    record_type = Column(String)  # PRESCRIPTION | REPORT
    file_path = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="records")

class BedStatus(Base):
    __tablename__ = "bed_status"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hospital_name = Column(String, nullable=False)
    total_beds = Column(String, nullable=False)
    available_beds = Column(String, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)


# =========================
# AI PREDICTION (HealthAI)
# =========================
class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    image_path = Column(String, nullable=False)

    # 🔍 Doctor verification status
    doctor_verified = Column(String, default="NO")  # NO / VERIFIED / REJECTED
    doctor_notes = Column(String, nullable=True)

    # 👨‍⚕️ Doctor audit trail
    verified_by = Column(String, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Relationships
    results = relationship(
        "AIPredictionResult",
        back_populates="prediction",
        cascade="all, delete"
    )




class AIPredictionResult(Base):
    __tablename__ = "ai_prediction_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prediction_id = Column(String, ForeignKey("ai_predictions.id"), nullable=False)
    disease_name = Column(String, nullable=False)
    confidence_score = Column(String, nullable=False)

    prediction = relationship("AIPrediction", back_populates="results")
