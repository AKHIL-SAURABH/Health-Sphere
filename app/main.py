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

from sqlalchemy.orm import Session
from fastapi import Depends
from app.models import Doctor, User
from app.database import get_db


from .core.security import require_role
from datetime import datetime
import uuid
from datetime import datetime, date, time
from .models import Appointment, Bed, BedAllocation, BedStatus
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
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password),
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ✅ AUTO-CREATE PROFILES
    if new_user.role == "PATIENT":
        db.add(Patient(user_id=new_user.id))

    if new_user.role == "DOCTOR":
        db.add(
            Doctor(
                user_id=new_user.id,
                specialization="",
                experience_years="",
                availability_status="AVAILABLE"
            )
        )

    db.commit()
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
    # ✅ CREATE DOCTOR PROFILE IF ROLE = DOCTOR
    if role == "DOCTOR":
        existing = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if not existing:
            doctor = Doctor(
                user_id=user.id,
                specialization=None,
                experience_years=None,
                availability_status="AVAILABLE"
            )
            db.add(doctor)
    db.commit()

    return {"message": f"Role updated to {role}"}

@app.get("/doctors")
def list_doctors(db: Session = Depends(get_db)):
    doctors = (
        db.query(Doctor, User)
        .join(User, Doctor.user_id == User.id)
        .filter(Doctor.specialization.isnot(None))
        .all()
    )

    return [
        {
            "doctor_id": d.id,
            "name": u.name,
            "email": u.email,
            "specialization": d.specialization,
            "experience_years": d.experience_years,
            "availability_status": d.availability_status
        }
        for d, u in doctors
    ]


# @app.post("/appointments/book")
# def book_appointment(
#     data: AppointmentCreate,
#     user=Depends(require_role("PATIENT")),
#     db: Session = Depends(get_db)
# ):
#     patient = db.query(Patient).filter(Patient.user_id == user["sub"]).first()
#     if not patient:
#         raise HTTPException(status_code=400, detail="Patient profile not found")

#     appointment = Appointment(
#         patient_id=patient.id,
#         doctor_id=data.doctor_id,
#         appointment_date=data.appointment_date
#     )
#     db.add(appointment)
#     db.commit()
#     return {"message": "Appointment booked"}


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


# @app.post("/admin/bed-status")
# def update_bed_status(
#     data: BedStatusCreate,
#     user=Depends(require_role("ADMIN")),
#     db: Session = Depends(get_db)
# ):
#     bed = BedStatus(
#         hospital_name=data.hospital_name,
#         total_beds=data.total_beds,
#         available_beds=data.available_beds
#     )
#     db.add(bed)
#     db.commit()
#     return {"message": "Bed status updated"}

@app.post("/medislot/appointments")
def book_appointment(
    appointment_date: date,
    appointment_time: time,
    doctor_id: str,
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    # 🔒 Prevent duplicate pending bookings
    existing = db.query(Appointment).filter(
        Appointment.patient_id == user["sub"],
        Appointment.doctor_id == doctor_id,
        Appointment.status == "PENDING"
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending appointment with this doctor"
        )

    appointment = Appointment(
        patient_id=user["sub"],
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status="PENDING"
    )

    db.add(appointment)
    db.commit()

    return {"message": "Appointment booked successfully"}



@app.get("/medislot/my-appointments")
def my_appointments(
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(
        Patient.user_id == user["sub"]
    ).first()

    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    return db.query(Appointment).filter(
        Appointment.patient_id == patient.id
    ).order_by(Appointment.created_at.desc()).all()

@app.get("/medislot/doctor/appointments")
def doctor_appointments(
    user=Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(
        Doctor.user_id == user["sub"]
    ).first()

    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found")

    return db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).order_by(Appointment.created_at.desc()).all()


@app.post("/medislot/appointments/{appointment_id}/status")
def update_appointment_status(
    appointment_id: str,
    status: str,
    user=Depends(require_role("DOCTOR")),
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = status
    db.commit()

    return {"message": "Status updated"}



# @app.get("/doctors/appointments")
# def get_doctor_appointments(
#     user=Depends(require_role("DOCTOR")),
#     db: Session = Depends(get_db)
# ):
#     doctor = db.query(Doctor).filter(Doctor.user_id == user["sub"]).first()
#     if not doctor:
#         raise HTTPException(status_code=400, detail="Doctor profile not found")

#     return db.query(Appointment).filter(
#         Appointment.doctor_id == doctor.id
#     ).all()


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
            "doctor_verified": p.doctor_verified,
            "doctor_notes": p.doctor_notes,          
            "verified_by": p.verified_by,             
            "verified_at": p.verified_at, 
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
            .filter(AIPrediction.doctor_verified.in_(["VERIFIED", "YES"]))
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


# #ADD BED (ADMIN ONLY)
# @app.post("/admin/beds")
# def add_bed(
#     ward: str,
#     bed_number: str,
#     admin=Depends(require_role("ADMIN")),
#     db: Session = Depends(get_db)
# ):
#     bed = Bed(
#         ward=ward,
#         bed_number=bed_number,
#         is_available=True
#     )
#     db.add(bed)
#     db.commit()
#     db.refresh(bed)

#     return {
#         "id": bed.id,
#         "ward": bed.ward,
#         "bed_number": bed.bed_number,
#         "is_available": bed.is_available
#     }

# #LIST BEDS (ADMIN ONLY)
# @app.get("/admin/beds")
# def list_beds(
#     admin=Depends(require_role("ADMIN")),
#     db: Session = Depends(get_db)
# ):
#     beds = db.query(Bed).all()
#     return [
#         {
#             "id": b.id,
#             "ward": b.ward,
#             "bed_number": b.bed_number,
#             "is_available": b.is_available,
#             "created_at": b.created_at
#         }
#         for b in beds
#     ]

# # ALLOCATE BED (ADMIN ONLY)
# @app.post("/admin/beds/{bed_id}/allocate")
# def allocate_bed(
#     bed_id: str,
#     patient_id: str,
#     admin=Depends(require_role("ADMIN")),
#     db: Session = Depends(get_db)
# ):
#     bed = db.query(Bed).filter(
#         Bed.id == bed_id,
#         Bed.is_available == True
#     ).first()

#     if not bed:
#         raise HTTPException(400, "Bed not available")

#     allocation = BedAllocation(
#         bed_id=bed.id,
#         patient_id=patient_id
#     )

#     bed.is_available = False
#     db.add(allocation)
#     db.commit()

#     return {"message": "Bed allocated"}


# # RELEASE BED (ADMIN ONLY)
# @app.post("/admin/beds/{bed_id}/release")
# def release_bed(
#     bed_id: str,
#     admin=Depends(require_role("ADMIN")),
#     db: Session = Depends(get_db)
# ):
#     allocation = (
#         db.query(BedAllocation)
#         .filter(
#             BedAllocation.bed_id == bed_id,
#             BedAllocation.status == "ACTIVE"
#         )
#         .first()
#     )

#     if not allocation:
#         raise HTTPException(404, "Allocation not found")

#     allocation.status = "RELEASED"
#     allocation.released_at = datetime.utcnow()

#     bed = db.query(Bed).filter(Bed.id == bed_id).first()
#     bed.is_available = True

#     db.commit()
#     return {"message": "Bed released"}


# #ALLOCATION HISTORY (ADMIN ONLY)
# @app.get("/admin/bed-allocations")
# def get_bed_allocations(
#     admin=Depends(require_role("ADMIN")),
#     db: Session = Depends(get_db)
# ):
#     allocations = (
#         db.query(BedAllocation, Bed, User)
#         .join(Bed, BedAllocation.bed_id == Bed.id)
#         .join(User, BedAllocation.patient_id == User.id)
#         .order_by(BedAllocation.allocated_at.desc())
#         .all()
#     )

#     return [
#         {
#             "allocation_id": a.id,
#             "patient_name": u.name,
#             "ward": b.ward,
#             "bed_number": b.bed_number,
#             "status": a.status,
#             "allocated_at": a.allocated_at,
#             "released_at": a.released_at
#         }
#         for a, b, u in allocations
#     ]


# # PATIENT VIEW (MY BED)
# @app.get("/patient/my-bed")
# def my_bed(
#     user=Depends(require_role("PATIENT")),
#     db: Session = Depends(get_db)
# ):
#     allocation = (
#         db.query(BedAllocation, Bed)
#         .join(Bed, BedAllocation.bed_id == Bed.id)
#         .filter(
#             BedAllocation.patient_id == user["sub"],
#             BedAllocation.status == "ACTIVE"
#         )
#         .first()
#     )

#     if not allocation:
#         return {"message": "No bed allocated"}

#     a, b = allocation
#     return {
#         "ward": b.ward,
#         "bed_number": b.bed_number,
#         "allocated_at": a.allocated_at
#     }



#ADMIN ADD BED
@app.post("/medislot/beds")
def add_bed(
    ward: str,
    bed_number: str,
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    bed = Bed(ward=ward, bed_number=bed_number, is_available=True)
    db.add(bed)
    db.commit()
    db.refresh(bed)

    return {
        "id": bed.id,
        "ward": bed.ward,
        "bed_number": bed.bed_number,
        "is_available": bed.is_available
    }

#PUBLIC LIST ALL BEDS
@app.get("/medislot/beds")
def list_beds(db: Session = Depends(get_db)):
    beds = db.query(Bed).all()
    return beds


#PATIENT REQUEST BED
@app.post("/medislot/beds/{bed_id}/request")
def request_bed(
    bed_id: str,
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    existing = db.query(BedAllocation).filter(
        BedAllocation.patient_id == user["sub"],
        BedAllocation.status.in_(["REQUESTED", "ACTIVE"])
    ).first()

    if existing:
        raise HTTPException(400, "You already have a bed request or allocation")

    allocation = BedAllocation(
        bed_id=bed_id,
        patient_id=user["sub"],
        status="REQUESTED"
    )

    db.add(allocation)
    db.commit()

    return {"message": "Bed request submitted"}

#ADMIN VIEW BED REQUESTS
@app.get("/medislot/bed-requests")
def bed_requests(
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    data = (
        db.query(BedAllocation, Bed, User)
        .join(Bed)
        .join(User)
        .order_by(BedAllocation.allocated_at.desc())
        .all()
    )

    return [
        {
            "allocation_id": a.id,
            "patient_name": u.name,
            "ward": b.ward,
            "bed_number": b.bed_number,
            "status": a.status
        }
        for a, b, u in data
    ]

#ADMIN: APPROVE/REJECT BED REQUEST
@app.post("/medislot/bed-requests/{allocation_id}/decision")
def decide_bed_request(
    allocation_id: str,
    action: str,  # APPROVE | REJECT
    admin=Depends(require_role("ADMIN")),
    db: Session = Depends(get_db)
):
    allocation = db.query(BedAllocation).filter(
        BedAllocation.id == allocation_id
    ).first()

    if not allocation:
        raise HTTPException(404, "Request not found")

    bed = db.query(Bed).filter(Bed.id == allocation.bed_id).first()

    if action == "APPROVE":
        allocation.status = "ACTIVE"
        bed.is_available = False
    elif action == "REJECT":
        allocation.status = "REJECTED"
    else:
        raise HTTPException(400, "Invalid action")

    db.commit()
    return {"message": f"Request {action.lower()}ed"}


#PATIENT: VIEW MY BED ALLOCATION STATUS
@app.get("/medislot/my-bed")
def my_bed(
    user=Depends(require_role("PATIENT")),
    db: Session = Depends(get_db)
):
    allocation = (
        db.query(BedAllocation, Bed)
        .join(Bed)
        .filter(BedAllocation.patient_id == user["sub"])
        .order_by(BedAllocation.allocated_at.desc())
        .first()
    )

    if not allocation:
        return {"status": "NONE"}

    a, b = allocation
    return {
        "status": a.status,
        "ward": b.ward,
        "bed_number": b.bed_number,
        "allocated_at": a.allocated_at
    }
