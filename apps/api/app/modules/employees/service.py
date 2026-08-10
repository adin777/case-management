from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.models import Employee, User


def sync_employee_for_user(db: Session, user: User) -> Employee:
    """Create or link the organizational person and mirror profile compatibility fields."""
    employee = db.get(Employee, user.employee_record_id) if user.employee_record_id else None
    if not employee:
        predicates = []
        if user.directory_object_id:
            predicates.append(Employee.directory_object_id == user.directory_object_id)
        if user.employee_id:
            predicates.append(Employee.employee_number == user.employee_id)
        if user.email:
            predicates.append(func.lower(Employee.email) == user.email.lower())
        employee = db.scalar(select(Employee).where(or_(*predicates))) if predicates else None
    if not employee:
        employee = Employee(email=user.email, display_name=user.display_name)
        db.add(employee)
        db.flush()
    employee.first_name = user.first_name
    employee.last_name = user.last_name
    employee.display_name = user.display_name
    employee.email = user.email
    employee.department = user.department
    employee.job_title = user.job_title
    employee.phone = user.phone
    employee.mobile_phone = user.mobile_phone
    employee.employee_number = user.employee_id
    employee.computer_identifier = user.computer_identifier
    employee.directory_object_id = user.directory_object_id
    employee.source = user.source
    employee.status = user.status
    employee.archived_at = user.archived_at
    user.employee_record_id = employee.id
    return employee
