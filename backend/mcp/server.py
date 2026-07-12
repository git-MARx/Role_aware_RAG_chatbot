from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

from backend.repository.sql_queries import (
    get_manager_id,
    get_leave_balance_by_type,
    deduct_leave,
    insert_leave_application,
    get_my_applications as _get_my_applications,
    get_pending_approvals as _get_pending_approvals,
    approve_leave_application,
    decline_leave_application,
)

mcp = FastMCP("hr-leave-tools")


def _count_working_days(start: date, end: date) -> int:
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


@mcp.tool()
def apply_leave(emp_id: int, leave_type: str, start_date: str, end_date: str, reason: str) -> dict:
    """Apply for leave on behalf of an employee. emp_id must come from the authenticated session."""
    try:
        start = date.fromisoformat(start_date)
        end   = date.fromisoformat(end_date)
    except ValueError:
        return {"success": False, "reason": f"Invalid date format. Please provide dates as YYYY-MM-DD (got: start='{start_date}', end='{end_date}')."}

    if end < start:
        return {"success": False, "reason": "End date cannot be before start date."}

    working_days = _count_working_days(start, end)
    if working_days == 0:
        return {"success": False, "reason": "No working days in the selected date range."}

    balance = get_leave_balance_by_type(emp_id, leave_type)
    if balance < working_days:
        return {
            "success": False,
            "reason": (
                f"Insufficient {leave_type} balance. "
                f"Available: {balance} day(s), Requested: {working_days} working day(s)."
            ),
        }

    manager_id = get_manager_id(emp_id)
    status     = "approved" if manager_id is None else "pending"

    deduct_leave(emp_id, leave_type, working_days)
    app_id = insert_leave_application(
        emp_id=emp_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        working_days=working_days,
        reason=reason,
        pending_to=manager_id,
        status=status,
    )

    msg = (
        f"Leave applied successfully (ID: {app_id}). "
        f"{working_days} {leave_type} day(s) deducted from your balance. "
        + ("Pending manager approval." if status == "pending" else "Auto-approved.")
    )
    return {"success": True, "application_id": app_id, "status": status, "working_days": working_days, "message": msg}


@mcp.tool()
def get_my_applications(emp_id: int) -> list:
    """Get all leave applications submitted by the employee."""
    return _get_my_applications(emp_id)


@mcp.tool()
def get_pending_approvals(manager_id: int) -> list:
    """Get all leave applications pending approval by this manager."""
    return _get_pending_approvals(manager_id)


@mcp.tool()
def approve_leave(manager_id: int, application_id: int) -> dict:
    """Approve a pending leave application. Only the assigned manager can approve."""
    success = approve_leave_application(manager_id, application_id)
    if not success:
        return {"success": False, "reason": "Application not found, already actioned, or not assigned to you."}
    return {"success": True, "message": f"Application {application_id} approved."}


@mcp.tool()
def decline_leave(manager_id: int, application_id: int, reason: str) -> dict:
    """Decline a pending leave application. Balance is restored to the employee."""
    success = decline_leave_application(manager_id, application_id, reason)
    if not success:
        return {"success": False, "reason": "Application not found, already actioned, or not assigned to you."}
    return {"success": True, "message": f"Application {application_id} declined. Employee's balance has been restored."}


if __name__ == "__main__":
    mcp.run(transport="stdio")
