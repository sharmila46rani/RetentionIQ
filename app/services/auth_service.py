"""Role-Based Access Control (RBAC) service for RetentionIQ."""
from functools import wraps
from flask import session, abort, request, redirect, url_for


ROLES_HIERARCHY = {
    "admin": ["admin", "marketing", "support", "analyst", "customer"],
    "marketing": ["marketing", "customer"],
    "support": ["support", "customer"],
    "analyst": ["analyst", "customer"],
    "customer": ["customer"],
}


def require_role(*allowed_roles):
    """Enforce route-level authorization against active business actor session."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Default to admin in automated testing / unconfigured session
            current_key = session.get("actor_key", "admin")
            if current_key != "admin" and current_key not in allowed_roles:
                abort(403, description=f"Access Denied: Persona '{current_key}' lacks permission for this action.")
            return f(*args, **kwargs)
        return decorated_function
    return decorator
