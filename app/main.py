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
from .schemas import AIPredictionDoctorView
from fastapi.staticfiles import StaticFiles

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from .models import User, Patient
from .schemas import UserCreate
from .database import get_db
from .auth import hash_password
from .core.security import get_current_user
from typing import List
from sqlalchemy import func



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

@app.get("/auth/me")
def get_me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns currently logged-in user's full profile
    """

    db_user = db.query(User).filter(User.id == user["sub"]).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": db_user.id,
        "name": db_user.name,
        "email": db_user.email,
        "role": db_user.role,
    }

@app.get("/admin/users")
def get_all_users(
    user=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role
        }
        for u in users
    ]


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


@app.post("/admin/users/{user_id}/role")
def update_user_role(
    user_id: str,
    role: str,
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    if role not in ["PATIENT", "DOCTOR", "ADMIN"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    db.commit()

    return {"message": f"Role updated to {role}"}


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

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_disk_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_disk_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    record = MedicalRecord(
        patient_id=patient.id,
        record_type=record_type,
        file_path=f"uploads/{filename}"  # ✅ CRITICAL FIX
    )

    db.add(record)
    db.commit()

    return {"message": "Medical record uploaded successfully"}




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

@app.get("/medvault/doctor/records")
def doctor_view_records(
    user=Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db)
):
    records = (
        db.query(MedicalRecord)
        .join(Patient)
        .join(User, Patient.user_id == User.id)
        .order_by(MedicalRecord.created_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "record_type": r.record_type,
            "file_path": r.file_path,
            "created_at": r.created_at,
            "patient_id": r.patient_id,
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
    # 1️⃣ Find patient
    patient = db.query(Patient).filter(
        Patient.user_id == user["sub"]
    ).first()

    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    # 2️⃣ Save X-ray
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads", "xray")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    filename = f"{uuid.uuid4()}_{file.filename}"
    image_path = os.path.join(UPLOAD_DIR, filename)

    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3️⃣ Create AI prediction entry
    prediction = AIPrediction(
        patient_id=patient.id,
        image_path=f"uploads/xray/{filename}",
        doctor_verified="NO"
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    # 4️⃣ Run AI model
    ai_output = predict_xray(image_path)

    # 5️⃣ Store TOP-3 predictions
    for res in ai_output["top_3"]:
        db.add(
            AIPredictionResult(
                prediction_id=prediction.id,
                disease_name=res["disease"],
                confidence_score=str(res["confidence"])
            )
        )

    db.commit()

    # 6️⃣ Return structured response
    return {
        "prediction_id": prediction.id,
        "results": ai_output["top_3"],
        "all_probabilities": ai_output["all_predictions"],
        "doctor_verified": "NO",
        "note": "AI-assisted prediction. Doctor verification required."
    }


@app.patch("/healthai/verify/{prediction_id}")
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

    return {"message": "Prediction verified by doctor"}



@app.get("/healthai/pending")
def get_pending_predictions(
    user=Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db)
):
    predictions = (
        db.query(AIPrediction)
        .filter(AIPrediction.doctor_verified == "NO")
        .order_by(AIPrediction.created_at.desc())
        .all()
    )

    response = []

    for p in predictions:
        response.append({
            "prediction_id": p.id,
            "image_path": p.image_path,
            "created_at": p.created_at,
            "results": [
                {
                    "disease": r.disease_name,
                    "confidence": float(r.confidence_score)
                }
                for r in p.results
            ]
        })

    return response



@app.post("/healthai/verify/{prediction_id}")
def verify_prediction(
    prediction_id: str,
    action: str,  # VERIFIED or REJECTED
    notes: str = "",
    user=Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db)
):
    if action not in ["VERIFIED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    prediction = db.query(AIPrediction).filter(
        AIPrediction.id == prediction_id
    ).first()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    prediction.doctor_verified = (
        "YES" if action == "VERIFIED" else "REJECTED"
    )
    prediction.doctor_notes = notes

    db.commit()

    return {
        "message": f"Prediction {action.lower()} successfully"
    }


@app.get("/healthai/my-predictions")
def get_my_healthai_predictions(
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(
        Patient.user_id == user["sub"]
    ).first()

    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    predictions = (
        db.query(AIPrediction)
        .filter(AIPrediction.patient_id == patient.id)
        .order_by(AIPrediction.created_at.desc())
        .all()
    )

    response = []
    for p in predictions:
        response.append({
            "prediction_id": p.id,
            "image_path": p.image_path,
            "doctor_verified": p.doctor_verified,
            "results": [
                {
                    "disease": r.disease_name,
                    "confidence": float(r.confidence_score)
                }
                for r in p.results
            ],
            "created_at": p.created_at
        })

    return response


@app.get("/admin/healthai/predictions")
def get_all_predictions(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    predictions = db.query(AIPrediction).all()

    return [
        {
            "prediction_id": p.id,
            "patient_id": p.patient_id,
            "image_path": p.image_path,
            "doctor_verified": p.doctor_verified,
            "doctor_notes": p.doctor_notes,
            "created_at": p.created_at,
            "results": [
                {
                    "disease": r.disease_name,
                    "confidence": float(r.confidence_score)
                }
                for r in p.results
            ]
        }
        for p in predictions
    ]


@app.get("/admin/stats")
def admin_stats(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    return {
        "total_users": db.query(User).count(),
        "patients": db.query(User).filter(User.role == "PATIENT").count(),
        "doctors": db.query(User).filter(User.role == "DOCTOR").count(),

        "medvault_records": db.query(MedicalRecord).count(),

        "ai_predictions": db.query(AIPrediction).count(),
        "pending_predictions": db.query(AIPrediction)
            .filter(AIPrediction.doctor_verified == "NO")
            .count(),
        "verified_predictions": db.query(AIPrediction)
            .filter(AIPrediction.doctor_verified == "VERIFIED")
            .count(),
        "rejected_predictions": db.query(AIPrediction)
            .filter(AIPrediction.doctor_verified == "REJECTED")
            .count(),
    }

@app.get("/admin/recent/healthai")
def recent_healthai_activity(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    records = (
        db.query(AIPrediction)
        .order_by(AIPrediction.created_at.desc())
        .limit(10)
        .all()
    )

    return [
        {
            "prediction_id": r.id,
            "patient_id": r.patient_id,
            "status": r.doctor_verified,
            "created_at": r.created_at
        }
        for r in records
    ]

@app.get("/admin/recent/medvault")
def recent_medvault_activity(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    records = (
        db.query(MedicalRecord)
        .order_by(MedicalRecord.created_at.desc())
        .limit(10)
        .all()
    )

    return [
        {
            "record_id": r.id,
            "patient_id": r.patient_id,
            "record_type": r.record_type,
            "created_at": r.created_at
        }
        for r in records
    ]


@app.get("/admin/analytics/healthai/daily")
def healthai_daily_trends(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    data = (
        db.query(
            func.date(AIPrediction.created_at).label("date"),
            func.count().label("count")
        )
        .group_by(func.date(AIPrediction.created_at))
        .order_by(func.date(AIPrediction.created_at))
        .all()
    )

    return [
        {"date": str(d.date), "count": d.count}
        for d in data
    ]

@app.get("/admin/analytics/healthai/status")
def healthai_status_distribution(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    data = (
        db.query(
            AIPrediction.doctor_verified,
            func.count().label("count")
        )
        .group_by(AIPrediction.doctor_verified)
        .all()
    )

    return [
        {"status": s.doctor_verified, "count": s.count}
        for s in data
    ]

@app.get("/admin/analytics/medvault/daily")
def medvault_daily_uploads(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    data = (
        db.query(
            func.date(MedicalRecord.created_at).label("date"),
            func.count().label("count")
        )
        .group_by(func.date(MedicalRecord.created_at))
        .order_by(func.date(MedicalRecord.created_at))
        .all()
    )

    return [
        {"date": str(d.date), "count": d.count}
        for d in data
    ]

@app.get("/admin/analytics/medvault/types")
def medvault_type_distribution(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    data = (
        db.query(
            MedicalRecord.record_type,
            func.count().label("count")
        )
        .group_by(MedicalRecord.record_type)
        .all()
    )

    return [
        {"type": r.record_type, "count": r.count}
        for r in data
    ]

@app.get("/admin/analytics/users/roles")
def user_role_distribution(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    data = (
        db.query(
            User.role,
            func.count().label("count")
        )
        .group_by(User.role)
        .all()
    )

    return [
        {"role": r.role, "count": r.count}
        for r in data
    ]

@app.get("/admin/analytics/users/daily")
def user_growth_daily(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    data = (
        db.query(
            func.date(User.created_at).label("date"),
            func.count().label("count")
        )
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
        .all()
    )

    return [
        {"date": str(d.date), "count": d.count}
        for d in data
    ]
