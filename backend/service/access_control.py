from typing import Literal

Role     = Literal["employee", "manager", "hr", "admin"]
Category = Literal["personal", "someone_else", "policy", "chitchat"]
Access   = Literal["full", "partial", "denied"]


def check_access(role: Role, category: Category) -> Access:
    if category == "personal":
        return "full"

    if category == "someone_else":
        if role in ("hr", "manager"):
            return "partial"
        return "denied"
    return "denied"
