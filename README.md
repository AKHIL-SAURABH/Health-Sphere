# 🏥 HealthSphere — Backend API

![HealthAI Banner](https://github.com/AKHIL-SAURABH/HealthSphere-Backend/blob/main/HealthSphere%20healthcare%20management%20system%20overview.png?raw=true)

HealthSphere Backend is a **production-ready FastAPI server** that powers the HealthSphere healthcare management platform.
It handles **authentication, role-based access control, appointment scheduling (MediSlot), bed allocation, medical records (MedVault), HealthAI predictions, admin analytics, and audit logs**.

This backend is **fully deployed on Render** and serves as the core API for the HealthSphere web application.

---

## 🌐 Live Deployment

* **Backend API (Render):**
  👉 [https://health-sphere-c2a3.onrender.com/](https://health-sphere-c2a3.onrender.com/)

* **Frontend Web App (Vercel):**
  👉 **Visit the frontend repository to access the live web app**
  
  🔗 *Frontend Repository Link (Vercel-deployed)*
  https://github.com/AKHIL-SAURABH/HealthSphere-Frontend

> ⚠️ **Important:**
> Users interact with HealthSphere via the **frontend web application**.
> This backend repository provides the API services only.

---

## 🚀 Backend Tech Stack — HealthSphere

### ⚙️ Core Technologies

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-High%20Performance-009688?logo=fastapi)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI%20Server-333333?logo=uvicorn)

---

### 🗄️ Database & ORM

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red)
![Alembic](https://img.shields.io/badge/Alembic-Migrations-darkred)

---

### 🔐 Authentication & Security

![JWT](https://img.shields.io/badge/JWT-Authentication-black?logo=jsonwebtokens)
![OAuth2](https://img.shields.io/badge/OAuth2-Security-blueviolet)
![Role Based Access](https://img.shields.io/badge/RBAC-Admin%20%7C%20Doctor%20%7C%20Patient-green)

---

### ☁️ Deployment & Infrastructure

![Render](https://img.shields.io/badge/Render-Backend%20Hosting-46E3B7)
![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?logo=docker)
![Gunicorn](https://img.shields.io/badge/Gunicorn-Production%20Server-499848)

---

### 🧠 AI / ML Integration

![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Enabled-orange)
![HealthAI](https://img.shields.io/badge/HealthAI-X--Ray%20Prediction-purple)

---

### 🧰 Additional Tools

![Pydantic](https://img.shields.io/badge/Pydantic-Data%20Validation-e92063)
![CORS](https://img.shields.io/badge/CORS-Configured-yellow)
![REST API](https://img.shields.io/badge/REST-API-green)
![Git](https://img.shields.io/badge/Git-Version%20Control-orange?logo=git)

---

## 🚀 Core Features

### 🔐 Authentication & Authorization

* JWT-based authentication
* Role-based access control:

  * **ADMIN**
  * **DOCTOR**
  * **PATIENT**
* Secure protected routes using FastAPI dependencies

---

### 🩺 MediSlot — Appointment Management

* Patients can:

  * Request appointments with doctors
  * View appointment status (Pending / Approved / Cancelled / Completed)
* Doctors can:

  * View assigned appointments
  * Approve, cancel, or complete appointments
* Duplicate and invalid bookings are prevented at API level

---

### 🛏️ Bed Allocation System

* Admin:

  * Add beds (ward + bed number)
  * View all beds and availability
  * Review patient bed requests
  * Approve / reject requests
  * Release beds when treatment completes
* Patients:

  * View available beds
  * Request bed allocation
  * Track allocation status in real time

---

### 📁 MedVault — Medical Records

* Secure file upload system
* Patient medical records management
* Doctor review and remarks
* Role-based access to files

---

### 🤖 HealthAI Integration

* AI-based medical prediction workflow
* Patient uploads diagnostic files
* Doctor verifies and approves predictions
* Status synchronization between patient and doctor dashboards

---

### 📊 Admin Analytics & Monitoring

* Platform usage statistics
* Appointment trends
* Bed allocation insights
* System activity overview

---

### 🧾 Audit Logs

* Tracks:

  * User actions
  * Admin decisions
  * Doctor approvals
* Improves traceability and accountability

---

## 🛠️ Tech Stack

* **Framework:** FastAPI
* **Language:** Python
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Authentication:** JWT
* **Deployment:** Render
* **File Storage:** Local / Configurable
* **API Docs:** Swagger & OpenAPI

---



## 📦 Project Structure

```
app/
├── main.py
├── models/
├── schemas/
├── routes/
├── services/
├── dependencies/
├── database.py
├── auth/
├── utils/
└── requirements.txt
```

---

## ▶️ Running Locally

```bash
git clone <backend-repo-url>
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

* API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔐 Environment Variables

```env
DATABASE_URL=postgresql://...
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## 🔗 Related Repositories

### 🌐 Frontend (Required to Use the App)

👉 **HealthSphere Frontend Repository**
👉 Deployed on **Vercel**
👉 This is where users log in and use the platform

> ⭐ **To experience the full HealthSphere platform, visit the frontend repository and open the deployed web app.**
> https://github.com/AKHIL-SAURABH/HealthSphere-Frontend

---

## ✅ Project Status

✔ Fully functional
✔ Production deployed
✔ Role-based workflows implemented
✔ Ready for future enhancements (mobile app, notifications, scaling)

---

## 👨‍💻 Author

**Akhil Saurabh**

Computer Science | Full Stack | AI-Driven Systems
HealthSphere — End-to-End Healthcare Platform

---


