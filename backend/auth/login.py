import json
import uuid

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from config.settings import engine, redis_client, SESSION_TTL

router = APIRouter()


class LoginRequest(BaseModel):
    emp_id: int
    password: str


@router.post("/login")
def login(data: LoginRequest):
    with Session(engine) as session:
        row = session.execute(
            text("""
                SELECT emp_id, name, role, department, manager_id, password_hash
                FROM employees
                WHERE emp_id = :emp_id
            """),
            {"emp_id": data.emp_id},
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    print(data.password.encode(), row.password_hash.encode())
    if not bcrypt.checkpw(data.password.encode(), row.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_token = str(uuid.uuid4())

    employee_context = {
        "emp_id":     row.emp_id,
        "name":       row.name,
        "role":       row.role,
        "department": row.department,
        "manager_id": row.manager_id,
    }

    redis_client.setex(
        f"session:{session_token}",
        SESSION_TTL,
        json.dumps(employee_context),
    )

    return {"session_token": session_token}
