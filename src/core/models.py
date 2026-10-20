import enum
from datetime import datetime
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
    CRITICAL = 1      # Immediate resuscitation (Cardiac arrest, severe trauma)
    URGENT = 2        # High risk, severe chest/abdominal pain
    SEMI_URGENT = 3   # Moderate symptoms, standard priority
    NON_URGENT = 4    # Routine checkup

class Department(Base):
    __tablename__ = "departments"

    dept_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_name = Column(String(100), unique=True, nullable=False, index=True)
    default_slot_duration_mins = Column(Integer, default=15, nullable=False)
    floor_number = Column(Integer, default=1, nullable=False)

    doctors = relationship("Doctor", back_populates="department", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Department(id={self.dept_id}, name='{self.dept_name}')>"

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

    def __repr__(self):
        return f"<Doctor(id={self.doctor_id}, name='{self.name}', spec='{self.specialization}', avail={self.is_available})>"

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    total_visits = Column(Integer, default=0, nullable=False)
    past_no_shows = Column(Integer, default=0, nullable=False)

    appointments = relationship("Appointment", back_populates="patient")
    triages = relationship("EmergencyTriage", back_populates="patient")

    @property
    def no_show_ratio(self) -> float:
        if self.total_visits == 0:
            return 0.0
        return round(self.past_no_shows / self.total_visits, 3)

    def __repr__(self):
        return f"<Patient(id={self.patient_id}, name='{self.name}')>"

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

    def __repr__(self):
        st = self.start_time.strftime("%H:%M") if self.start_time else "?"
        et = self.end_time.strftime("%H:%M") if self.end_time else "?"
        return f"<TimeSlot(id={self.slot_id}, doc={self.doctor_id}, {st}-{et}, overbooked={self.is_overbooked})>"

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

    def __repr__(self):
        return (f"<Appointment(id={self.appointment_id}, doc={self.doctor_id}, "
                f"status={self.status.value}, p_noshow={self.predicted_no_show_prob:.2f}, "
                f"overbook={self.is_secondary_overbook})>")

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

    def __repr__(self):
        return (f"<EmergencyTriage(id={self.triage_id}, pat={self.patient_id}, "
                f"doc={self.doctor_id}, severity=LEVEL {self.severity_level})>")
