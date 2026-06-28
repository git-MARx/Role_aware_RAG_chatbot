import random
import bcrypt
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, Session

# ── DB connection ──────────────────────────────────────────────────────────────
DB_URL = "postgresql+psycopg2://rahularya@localhost:5432/hr_chatbot"

engine = create_engine(DB_URL)
Base = declarative_base()

PASSWORD = "Test@123"

LEAVE_POLICY = [
    ("PL", 15),
    ("GL", 10),
]

PAYSLIP_MONTHS = [(4, 2025), (5, 2025), (6, 2025)]  # April–June 2025

SALARY_RANGE = {
    "manager":  (120000, 180000),
    "hr":       (70000,  100000),
    "employee": (60000,  100000),
}

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March",    4: "April",
    5: "May",     6: "June",     7: "July",      8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

PAYSLIP_DIR = Path(__file__).parent / "data" / "payslips"


# ── Models ─────────────────────────────────────────────────────────────────────
class Employee(Base):
    __tablename__ = "employees"

    emp_id        = Column(Integer, primary_key=True)
    name          = Column(String, nullable=False)
    role          = Column(String, nullable=False)
    department    = Column(String, nullable=False)
    manager_id    = Column(Integer, ForeignKey("employees.emp_id"), nullable=True)
    password_hash = Column(String, nullable=False)

    leaves        = relationship("Leave",   back_populates="employee")
    payslips      = relationship("Payslip", back_populates="employee")


class Leave(Base):
    __tablename__ = "leaves"

    id          = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.emp_id"), nullable=False)
    leave_type  = Column(String, nullable=False)
    total       = Column(Integer, nullable=False)
    used        = Column(Integer, nullable=False)

    employee    = relationship("Employee", back_populates="leaves")


class Payslip(Base):
    __tablename__ = "payslips"

    id          = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.emp_id"), nullable=False)
    month       = Column(Integer, nullable=False)
    year        = Column(Integer, nullable=False)
    file_path   = Column(String, nullable=False)

    employee    = relationship("Employee", back_populates="payslips")


# ── Helpers ────────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def make_employee(name, role, department, manager_id, pw_hash) -> Employee:
    emp = Employee(
        name=name,
        role=role,
        department=department,
        manager_id=manager_id,
        password_hash=pw_hash,
    )
    emp.leaves = [
        Leave(leave_type=lt, total=total, used=random.randint(0, 4))
        for lt, total in LEAVE_POLICY
    ]
    return emp


def generate_payslip_txt(emp: Employee, month: int, year: int, basic: int) -> str:
    hra          = int(basic * 0.40)
    travel       = 5000
    gross        = basic + hra + travel
    pf           = int(basic * 0.12)
    tax          = int(basic * 0.10)
    total_deduct = pf + tax
    net_pay      = gross - total_deduct

    def fmt(n): return f"{n:>12,}"

    lines = [
        "=" * 52,
        "          ACME CORP — PAY SLIP",
        "=" * 52,
        f"  Employee Name  : {emp.name}",
        f"  Employee ID    : EMP{emp.emp_id:03d}",
        f"  Department     : {emp.department}",
        f"  Month & Year   : {MONTH_NAMES[month]} {year}",
        "=" * 52,
        "",
        "  EARNINGS",
        "  " + "-" * 38,
        f"  Basic Salary   : ₹{fmt(basic)}",
        f"  HRA (40%)      : ₹{fmt(hra)}",
        f"  Travel Allow   : ₹{fmt(travel)}",
        "  " + " " * 24 + "----------",
        f"  Gross Salary   : ₹{fmt(gross)}",
        "",
        "  DEDUCTIONS",
        "  " + "-" * 38,
        f"  Provident Fund : ₹{fmt(pf)}",
        f"  Income Tax     : ₹{fmt(tax)}",
        "  " + " " * 24 + "----------",
        f"  Total Deduct   : ₹{fmt(total_deduct)}",
        "",
        "=" * 52,
        f"  NET PAY        : ₹{fmt(net_pay)}",
        "=" * 52,
    ]
    return "\n".join(lines)


def seed_payslips(session: Session, employees: list[Employee]):
    PAYSLIP_DIR.mkdir(parents=True, exist_ok=True)

    for emp in employees:
        lo, hi = SALARY_RANGE[emp.role]
        basic = random.randrange(lo, hi + 1, 1000)  # round to nearest 1000

        for month, year in PAYSLIP_MONTHS:
            txt = generate_payslip_txt(emp, month, year, basic)
            file_path = PAYSLIP_DIR / f"emp_{emp.emp_id:03d}_{year}_{month:02d}.txt"
            file_path.write_text(txt, encoding="utf-8")

            session.add(Payslip(
                employee_id=emp.emp_id,
                month=month,
                year=year,
                file_path=str(file_path),
            ))


# ── Seed ───────────────────────────────────────────────────────────────────────
def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    pw_hash = hash_password(PASSWORD)

    with Session(engine) as session:

        # Root: top manager
        vikram = make_employee("Vikram Sharma", "manager", "Management", None, pw_hash)
        session.add(vikram)
        session.flush()

        # Level 2: department managers
        priya   = make_employee("Priya Nair",    "manager", "Engineering", vikram.emp_id, pw_hash)
        arjun   = make_employee("Arjun Mehta",   "manager", "Finance",     vikram.emp_id, pw_hash)
        kavitha = make_employee("Kavitha Reddy", "manager", "Operations",  vikram.emp_id, pw_hash)
        session.add_all([priya, arjun, kavitha])
        session.flush()

        # Level 3: subordinates
        engineering_team = ["Rohan Verma", "Sneha Iyer", "Amit Patel", "Deepak Joshi"]
        finance_team     = ["Pooja Gupta", "Rahul Singh", "Neha Joshi"]
        operations_team  = ["Suresh Kumar", "Divya Pillai", "Kiran Rao", "Mohan Das", "Anita Bose"]

        for name in engineering_team:
            session.add(make_employee(name, "employee", "Engineering", priya.emp_id, pw_hash))
        for name in finance_team:
            session.add(make_employee(name, "employee", "Finance", arjun.emp_id, pw_hash))
        for name in operations_team:
            session.add(make_employee(name, "employee", "Operations", kavitha.emp_id, pw_hash))

        # HR hierarchy
        meera = make_employee("Meera Krishnan", "hr", "HR", None, pw_hash)
        session.add(meera)
        session.flush()

        session.add(make_employee("Sunita Yadav", "hr", "HR", meera.emp_id, pw_hash))
        session.add(make_employee("Ravi Nambiar", "hr", "HR", meera.emp_id, pw_hash))

        session.flush()

        # Payslips
        all_employees = session.query(Employee).all()
        seed_payslips(session, all_employees)

        session.commit()

    total_emp = 1 + 3 + len(engineering_team) + len(finance_team) + len(operations_team) + 3
    total_payslips = total_emp * len(PAYSLIP_MONTHS)
    print(f"Done — {total_emp} employees, {total_payslips} payslip files written to {PAYSLIP_DIR}")


if __name__ == "__main__":
    main()
