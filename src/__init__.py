"""
Doctor-Patient Appointment Scheduling System
Week 5: Smart Overbooking Engine & Dynamic Conflict Resolution
"""
from .core.models import (
    Base, Department, Doctor, Patient, TimeSlot,
    Appointment, EmergencyTriage, AppointmentStatus, TriageSeverity
)
from .core.db import init_db, get_session
from .overbooking.smart_overbooker import SmartOverbookingEngine
from .conflicts.conflict_resolver import ConflictResolutionEngine
