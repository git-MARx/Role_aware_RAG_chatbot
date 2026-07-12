from datetime import date, datetime
from typing import Literal, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from config.settings import engine


def _serialize(row: dict) -> dict:
    return {
        k: v.isoformat() if isinstance(v, (date, datetime)) else v
        for k, v in row.items()
    }

Access = Literal["full", "partial", "denied"]
Role   = Literal["employee", "manager", "hr", "admin"]


def _resolve_target_emp_id(role: Role, requester_emp_id: int, name: str) -> Optional[int]:
    """
    Looks up the target employee by name, then applies hierarchy rules
    to decide whether the requester can see them:
      - manager → only direct reportees (subject.manager_id = requester_emp_id)
      - hr      → full purview over non-hr employees;
                  for hr-on-hr, only direct reportees (same restriction as manager)
    Returns the target's emp_id if visible, else None.
    """
    with Session(engine) as session:
        subject = session.execute(
            text("SELECT emp_id, manager_id, role FROM employees WHERE name ILIKE :name"),
            {"name": f"%{name}%"},
        ).fetchone()

    if subject is None:
        return None

    if role == "manager":
        return subject.emp_id if subject.manager_id == requester_emp_id else None

    if role == "hr":
        if subject.role == "hr":
            return subject.emp_id if subject.manager_id == requester_emp_id else None
        return subject.emp_id

    return None


def _resolve_target(access: Access, role: Role, emp_id: int, name: str) -> Optional[int]:
    if access == "denied":
        return None
    if access == "full":
        return emp_id
    return _resolve_target_emp_id(role, emp_id, name)


def get_total_leave_balance(access: Access, role: Role, emp_id: int, name: str) -> Optional[int]:
    target_id = _resolve_target(access, role, emp_id, name)
    if target_id is None:
        return None

    with Session(engine) as session:
        result = session.execute(
            text("""
                SELECT COALESCE(SUM(total - used), 0) AS balance
                FROM leaves
                WHERE employee_id = :target_id
            """),
            {"target_id": target_id},
        ).fetchone()

    return {"balance":result.balance}


def get_labeled_leave_balance(access: Access, role: Role, emp_id: int, name: str) -> Optional[dict]:
    target_id = _resolve_target(access, role, emp_id, name)
    if target_id is None:
        return None

    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT leave_type, (total - used) AS balance
                FROM leaves
                WHERE employee_id = :target_id
            """),
            {"target_id": target_id},
        ).fetchall()

    return {row.leave_type: row.balance for row in rows}


def get_payslip(access: Access, role: Role, emp_id: int, name: str) -> Optional[str]:
    target_id = _resolve_target(access, role, emp_id, name)
    if target_id is None:
        return None

    with Session(engine) as session:
        row = session.execute(
            text("""
                SELECT file_path
                FROM payslips
                WHERE employee_id = :target_id
                ORDER BY year DESC, month DESC
                LIMIT 1
            """),
            {"target_id": target_id},
        ).fetchone()

    return {'path':row.file_path} if row else None


def get_manager_id(emp_id: int) -> Optional[int]:
    with Session(engine) as session:
        row = session.execute(
            text("SELECT manager_id FROM employees WHERE emp_id = :emp_id"),
            {"emp_id": emp_id},
        ).fetchone()
    return row.manager_id if row else None


def get_leave_balance_by_type(emp_id: int, leave_type: str) -> int:
    with Session(engine) as session:
        row = session.execute(
            text("""
                SELECT (total - used) AS balance
                FROM leaves
                WHERE employee_id = :emp_id AND leave_type = :leave_type
            """),
            {"emp_id": emp_id, "leave_type": leave_type},
        ).fetchone()
    return int(row.balance) if row else 0


def deduct_leave(emp_id: int, leave_type: str, days: int) -> None:
    with Session(engine) as session:
        session.execute(
            text("""
                UPDATE leaves SET used = used + :days
                WHERE employee_id = :emp_id AND leave_type = :leave_type
            """),
            {"emp_id": emp_id, "leave_type": leave_type, "days": days},
        )
        session.commit()


def insert_leave_application(
    emp_id: int,
    leave_type: str,
    start_date: str,
    end_date: str,
    working_days: int,
    reason: str,
    pending_to: Optional[int],
    status: str,
) -> int:
    with Session(engine) as session:
        row = session.execute(
            text("""
                INSERT INTO leave_applications
                    (emp_id, leave_type, start_date, end_date, working_days, reason, pending_to, status)
                VALUES
                    (:emp_id, :leave_type, :start_date, :end_date, :working_days, :reason, :pending_to, :status)
                RETURNING id
            """),
            {
                "emp_id": emp_id, "leave_type": leave_type,
                "start_date": start_date, "end_date": end_date,
                "working_days": working_days, "reason": reason,
                "pending_to": pending_to, "status": status,
            },
        ).fetchone()
        session.commit()
    return row.id


def get_my_applications(emp_id: int) -> list[dict]:
    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT id, leave_type, start_date, end_date, working_days,
                       reason, status, applied_on, actioned_on, decline_reason
                FROM leave_applications
                WHERE emp_id = :emp_id
                ORDER BY applied_on DESC
            """),
            {"emp_id": emp_id},
        ).fetchall()
    return [_serialize(row._asdict()) for row in rows]


def get_pending_approvals(manager_id: int) -> list[dict]:
    with Session(engine) as session:
        rows = session.execute(
            text("""
                SELECT la.id, e.name AS employee_name, la.leave_type,
                       la.start_date, la.end_date, la.working_days, la.reason, la.applied_on
                FROM leave_applications la
                JOIN employees e ON e.emp_id = la.emp_id
                WHERE la.pending_to = :manager_id AND la.status = 'pending'
                ORDER BY la.applied_on ASC
            """),
            {"manager_id": manager_id},
        ).fetchall()
    return [_serialize(row._asdict()) for row in rows]


def approve_leave_application(manager_id: int, application_id: int) -> bool:
    with Session(engine) as session:
        result = session.execute(
            text("""
                UPDATE leave_applications
                SET status = 'approved', actioned_on = NOW()
                WHERE id = :id AND pending_to = :manager_id AND status = 'pending'
            """),
            {"id": application_id, "manager_id": manager_id},
        )
        session.commit()
    return result.rowcount == 1


def decline_leave_application(manager_id: int, application_id: int, reason: str) -> bool:
    with Session(engine) as session:
        row = session.execute(
            text("""
                UPDATE leave_applications
                SET status = 'declined', actioned_on = NOW(), decline_reason = :reason
                WHERE id = :id AND pending_to = :manager_id AND status = 'pending'
                RETURNING emp_id, leave_type, working_days
            """),
            {"id": application_id, "manager_id": manager_id, "reason": reason},
        ).fetchone()
        if row is None:
            return False
        session.execute(
            text("""
                UPDATE leaves SET used = used - :days
                WHERE employee_id = :emp_id AND leave_type = :leave_type
            """),
            {"emp_id": row.emp_id, "leave_type": row.leave_type, "days": row.working_days},
        )
        session.commit()
    return True


def _get_emp_id_by_name(name: str) -> int:
    with Session(engine) as session:
        row = session.execute(
            text("SELECT emp_id FROM employees WHERE name ILIKE :name"),
            {"name": f"%{name}%"},
        ).fetchone()
    return row.emp_id


if __name__ == "__main__":
    priya  = _get_emp_id_by_name("Priya Nair")     # manager, Engineering
    meera  = _get_emp_id_by_name("Meera Krishnan") # senior hr, no manager
    sunita = _get_emp_id_by_name("Sunita Yadav")   # junior hr, reports to Meera
    rohan  = _get_emp_id_by_name("Rohan Verma")    # employee, reports to Priya

    cases = [
        ("Employee — full access, own data",         "full",    "employee", rohan,  "Rohan Verma"),
        ("Manager — partial, own direct reportee",    "partial", "manager",  priya,  "Rohan Verma"),
        ("Manager — partial, NOT their reportee",     "partial", "manager",  priya,  "Suresh Kumar"),
        ("HR — partial, non-hr employee (full purview)", "partial", "hr",    meera,  "Rohan Verma"),
        ("HR — partial, own junior hr reportee",      "partial", "hr",      meera,  "Sunita Yadav"),
        ("Junior HR — partial, senior hr (no access)", "partial", "hr",     sunita, "Meera Krishnan"),
        ("Employee — denied, someone else",            "denied", "employee", rohan, "Priya Nair"),
    ]

    for label, access, role, requester_id, target_name in cases:
        print()
        print(label, access, role, requester_id, target_name)
        print()
        total   = get_total_leave_balance(access, role, requester_id, target_name)
        labeled = get_labeled_leave_balance(access, role, requester_id, target_name)
        payslip = get_payslip(access, role, requester_id, target_name)

        print(label)
        print(f"  total leave balance : {total}")
        print(f"  labeled balance     : {labeled}")
        print(f"  payslip file        : {payslip}")
        print("-" * 60)
