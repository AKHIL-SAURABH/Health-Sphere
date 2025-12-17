import uuid
from fastapi import UploadFile, File
import shutil
import os
from .models import MedicalRecord
from fastapi.middleware.cors import CORSMiddleware



from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv()

from .database import Base, engine, SessionLocal
from .models import User
from .schemas import UserCreate, UserLogin, Token
from .auth import hash_password, verify_password, create_access_token

from .models import Patient, Doctor, Appointment
from .schemas import (
    UserCreate,
    UserLogin,
    Token,
    PatientCreate,
    DoctorCreate,
    AppointmentCreate,
    MedicalRecordResponse
)

from .core.security import require_role
from datetime import datetime
import uuid

from .models import BedStatus
from .schemas import BedStatusCreate


from .ml.predictor import predict_xray
from .models import AIPrediction, AIPredictionResult
from .schemas import AIPredictionResponse
from fastapi.staticfiles import StaticFiles

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from .models import User, Patient
from .schemas import UserCreate
from .database import get_db
from .auth import hash_password



Base.metadata.create_all(bind=engine)


app = FastAPI(title="HealthSphere API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",              # local frontend
        "https://health-sphere-c2a3.onrender.com",  # backend itself
        # you can add vercel URL later
    ],
    allow_credentials=True,
    allow_methods=["*"],   # IMPORTANT: enables OPTIONS
    allow_headers=["*"],
)


os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




@app.post("/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 1️⃣ Check if email already exists
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # 2️⃣ Create user
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password),
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)   # ✅ user.id now exists

    # 3️⃣ AUTO-CREATE PATIENT PROFILE (IMPORTANT)
    if new_user.role == "PATIENT":
        patient = Patient(
            user_id=new_user.id,
            age="",
            gender="",
            contact_number=""
        )
        db.add(patient)
        db.commit()

    # 4️⃣ Return response
    return {"message": "User registered successfully"}


@app.post("/auth/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        {"sub": str(db_user.id), "role": db_user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "name": db_user.name,
            "email": db_user.email,
            "role": db_user.role,
        },
    }

@app.post("/patients/profile")
def create_patient_profile(
    data: PatientCreate,
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    patient = Patient(
        user_id=user["sub"],
        age=data.age,
        gender=data.gender,
        contact_number=data.contact_number
    )
    db.add(patient)
    db.commit()
    return {"message": "Patient profile created"}

@app.post("/doctors/profile")
def create_doctor_profile(
    data: DoctorCreate,
    user=Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db)
):
    doctor = Doctor(
        user_id=user["sub"],
        specialization=data.specialization,
        experience_years=data.experience_years
    )
    db.add(doctor)
    db.commit()
    return {"message": "Doctor profile created"}

@app.post("/appointments/book")
def book_appointment(
    data: AppointmentCreate,
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.user_id == user["sub"]).first()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date
    )
    db.add(appointment)
    db.commit()
    return {"message": "Appointment booked"}


@app.post("/medvault/upload")
def upload_medical_record(
    record_type: str,
    file: UploadFile = File(...),
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.user_id == user["sub"]).first()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    record = MedicalRecord(
        patient_id=patient.id,
        record_type=record_type,
        file_path=file_path
    )
    db.add(record)
    db.commit()

    return {"message": "Medical record uploaded"}


@app.get("/medvault/records")
def get_medical_records(
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(
        Patient.user_id == user["sub"]
    ).first()

    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.patient_id == patient.id)
        .order_by(MedicalRecord.created_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "record_type": r.record_type,
            "file_path": r.file_path,
            "created_at": r.created_at,
        }
        for r in records
    ]

@app.post("/admin/bed-status")
def update_bed_status(
    data: BedStatusCreate,
    user=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    bed = BedStatus(
        hospital_name=data.hospital_name,
        total_beds=data.total_beds,
        available_beds=data.available_beds
    )
    db.add(bed)
    db.commit()
    return {"message": "Bed status updated"}

@app.get("/beds")
def get_bed_status(db: Session = Depends(get_db)):
    return db.query(BedStatus).all()


@app.get("/doctors/appointments")
def get_doctor_appointments(
    user=Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == user["sub"]).first()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found")

    return db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).all()


@app.post("/healthai/predict", response_model=AIPredictionResponse)
def healthai_predict(
    file: UploadFile = File(...),
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.user_id == user["sub"]).first()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    os.makedirs("uploads", exist_ok=True)
    image_path = f"uploads/{uuid.uuid4()}_{file.filename}"

    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    prediction = AIPrediction(
        patient_id=patient.id,
        image_path=image_path
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    # 🔥 REAL HealthAI output
    ai_output = predict_xray(image_path)

    # Store only top-3 in DB
    for res in ai_output["top_3"]:
        db.add(
            AIPredictionResult(
                prediction_id=prediction.id,
                disease_name=res["disease"],
                confidence_score=str(res["confidence"])
            )
        )

    db.commit()


    return {
        "prediction_id": prediction.id,
        "results": ai_output["top_3"],
        "all_probabilities": ai_output["all_predictions"],
        "note": "AI-assisted prediction. Doctor verification required."
    }


@app.post("/healthai/verify/{prediction_id}")
def verify_ai_prediction(
    prediction_id: str,
    user=Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db)
):
    prediction = db.query(AIPrediction).filter(
        AIPrediction.id == prediction_id
    ).first()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    prediction.doctor_verified = "YES"
    db.commit()

    return {"message": "AI prediction verified by doctor"}
