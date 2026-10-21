import enum
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, CheckConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class AppointmentStatus(str, enum.Enum):
    BOOKED = "BOOKED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    IN_CONSULTATION = "IN_CONSULTATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

class TriageSeverity(int, enum.Enum):
    CRITICAL = 1      # Immediate resuscitation
    URGENT = 2        # Severe acute condition
    SEMI_URGENT = 3   # Moderate symptoms
    NON_URGENT = 4    # Routine consultation

class Department(Base):
    __tablename__ = "departments"

    dept_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_name = Column(String(100), unique=True, nullable=False, index=True)
    default_slot_duration_mins = Column(Integer, default=15, nullable=False)
    floor_number = Column(Integer, default=1, nullable=False)

    doctors = relationship("Doctor", back_populates="department", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "dept_id": self.dept_id,
            "dept_name": self.dept_name,
            "default_slot_duration_mins": self.default_slot_duration_mins,
            "floor_number": self.floor_number,
            "doctor_count": len(self.doctors)
        }

class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    specialization = Column(String(100), nullable=False, index=True)
    room_number = Column(String(20), nullable=False)
    max_daily_capacity = Column(Integer, default=30, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), nullable=False)

    department = relationship("Department", back_populates="doctors")
    slots = relationship("TimeSlot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")
    triages = relationship("EmergencyTriage", back_populates="doctor")

    def to_dict(self):
        return {
            "doctor_id": self.doctor_id,
            "name": self.name,
            "specialization": self.specialization,
            "room_number": self.room_number,
            "max_daily_capacity": self.max_daily_capacity,
            "is_available": self.is_available,
            "department_name": self.department.dept_name if self.department else None
        }

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(120), nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    total_visits = Column(Integer, default=0, nullable=False)
    past_no_shows = Column(Integer, default=0, nullable=False)

    appointments = relationship("Appointment", back_populates="patient")
    triages = relationship("EmergencyTriage", back_populates="patient")

    def set_password(self, password: str):
        """Hashes and sets patient password securely using pbkdf2:sha256."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies supplied password against stored cryptographic hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def no_show_ratio(self) -> float:
        if self.total_visits == 0:
            return 0.0
        return round(self.past_no_shows / self.total_visits, 3)

    def to_dict(self):
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            "email": self.email,
            "total_visits": self.total_visits,
            "past_no_shows": self.past_no_shows,
            "no_show_ratio": self.no_show_ratio
        }

class TimeSlot(Base):
    __tablename__ = "time_slots"

    slot_id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)
    is_overbooked = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_slot_end_after_start"),
        Index("idx_doctor_time_slot", "doctor_id", "start_time", "end_time"),
    )

    doctor = relationship("Doctor", back_populates="slots")
    appointments = relationship("Appointment", back_populates="slot")

    @property
    def duration_minutes(self) -> int:
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return 0

    def to_dict(self):
        return {
            "slot_id": self.slot_id,
            "doctor_id": self.doctor_id,
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
            "duration_minutes": self.duration_minutes,
            "is_booked": self.is_booked,
            "is_overbooked": self.is_overbooked
        }

class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("time_slots.slot_id"), nullable=False)
    booking_timestamp = Column(DateTime, default=datetime.now, nullable=False)
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    predicted_no_show_prob = Column(Float, default=0.0, nullable=False)
    is_secondary_overbook = Column(Boolean, default=False, nullable=False)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    slot = relationship("TimeSlot", back_populates="appointments")

    def to_dict(self):
        return {
            "appointment_id": self.appointment_id,
            "patient_name": self.patient.name if self.patient else None,
            "doctor_name": self.doctor.name if self.doctor else None,
            "doctor_room": self.doctor.room_number if self.doctor else None,
            "specialization": self.doctor.specialization if self.doctor else None,
            "slot_time": f"{self.slot.start_time.strftime('%H:%M')} - {self.slot.end_time.strftime('%H:%M')}" if self.slot else None,
            "status": self.status.value,
            "predicted_no_show_prob": self.predicted_no_show_prob,
            "is_secondary_overbook": self.is_secondary_overbook
        }

class EmergencyTriage(Base):
    __tablename__ = "emergency_triage"

    triage_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    severity_level = Column(Integer, default=TriageSeverity.URGENT.value, nullable=False)
    arrival_time = Column(DateTime, default=datetime.now, nullable=False)
    preempted_slot_id = Column(Integer, ForeignKey("time_slots.slot_id"), nullable=True)

    patient = relationship("Patient", back_populates="triages")
    doctor = relationship("Doctor", back_populates="triages")
    preempted_slot = relationship("TimeSlot")

    def to_dict(self):
        return {
            "triage_id": self.triage_id,
            "patient_name": self.patient.name if self.patient else None,
            "doctor_name": self.doctor.name if self.doctor else None,
            "severity_level": self.severity_level,
            "arrival_time": self.arrival_time.strftime("%H:%M:%S")
        }

class HistoricalRecord(Base):
    __tablename__ = "historical_records"

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    lead_days = Column(Integer, default=0, nullable=False)
    day_of_week = Column(Integer, default=0, nullable=False)
    sms_sent = Column(Boolean, default=False, nullable=False)
    no_show_flag = Column(Boolean, default=False, nullable=False)

    patient = relationship("Patient")

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "patient_id": self.patient_id,
            "lead_days": self.lead_days,
            "day_of_week": self.day_of_week,
            "sms_sent": self.sms_sent,
            "no_show_flag": self.no_show_flag
        }

class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id = Column(Integer, primary_key=True, autoincrement=True)
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"), unique=True, nullable=False)
    diagnosis = Column(String(255), nullable=False)
    medicines = Column(String(1000), nullable=False)
    advice = Column(String(500), nullable=True)
    follow_up_days = Column(Integer, default=7, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    appointment = relationship("Appointment", backref="prescription")

    def to_dict(self):
        return {
            "prescription_id": self.prescription_id,
            "appointment_id": self.appointment_id,
            "diagnosis": self.diagnosis,
            "medicines": self.medicines,
            "advice": self.advice,
            "follow_up_days": self.follow_up_days,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
        }


