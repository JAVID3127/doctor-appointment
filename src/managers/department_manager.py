from typing import List, Optional
from sqlalchemy.orm import Session
from ..models import Department, Doctor

class DepartmentManager:
    """Manages hospital OPD clinical departments, room assignments, and floor routing."""

    def __init__(self, session: Session):
        self.session = session

    def register_department(self, name: str, slot_duration_mins: int = 15, floor_number: int = 1) -> Department:
        existing = self.session.query(Department).filter(Department.dept_name.ilike(name)).first()
        if existing:
            return existing
        dept = Department(
            dept_name=name,
            default_slot_duration_mins=slot_duration_mins,
            floor_number=floor_number
        )
        self.session.add(dept)
        self.session.commit()
        self.session.refresh(dept)
        return dept

    def get_department_by_id(self, dept_id: int) -> Optional[Department]:
        return self.session.query(Department).filter(Department.dept_id == dept_id).first()

    def get_department_by_name(self, name: str) -> Optional[Department]:
        return self.session.query(Department).filter(Department.dept_name.ilike(name)).first()

    def get_all_departments(self) -> List[Department]:
        return self.session.query(Department).order_by(Department.dept_name).all()

    def get_doctors_in_department(self, dept_id: int) -> List[Doctor]:
        dept = self.get_department_by_id(dept_id)
        return dept.doctors if dept else []
