import re
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    def to_dict(self):
        """Serialize model instance to dictionary with ISO-formatted datetimes."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result


def utc_now():
    """Get current UTC datetime with timezone awareness removed for SQLite/MySQL parity."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ID Validation Regex Patterns
CUSTOMER_ID_REGEX = re.compile(r"^CUS-\d{6}$")
SUBSCRIPTION_ID_REGEX = re.compile(r"^SUB-CUS-\d{6}-\d{2}$")
USAGE_SNAPSHOT_ID_REGEX = re.compile(r"^SNAP-SUB-CUS-\d{6}-\d{2}-\d{4}-\d{2}$")
BILLING_EVENT_ID_REGEX = re.compile(r"^BIL-CUS-\d{6}-\d{6}$")
SUPPORT_CASE_ID_REGEX = re.compile(r"^CAS-CUS-\d{6}-\d{3}$")
OFFER_ID_REGEX = re.compile(r"^OFF-\d{4}-\d{6}$")
ELIGIBILITY_RULE_ID_REGEX = re.compile(r"^RUL-OFF-\d{4}-\d{6}-\d{2}$")
CAMPAIGN_CONTACT_ID_REGEX = re.compile(r"^CAM-\d{4}-\d{6}$")
CHURN_OUTCOME_ID_REGEX = re.compile(r"^CHURN-CUS-\d{6}-\d{4}$")
RETENTION_OUTCOME_ID_REGEX = re.compile(r"^RET-CAM-\d{4}-\d{6}$")


def validate_id(id_value: str, pattern: re.Pattern, entity_name: str) -> bool:
    """Validate that an ID conforms to the strict naming convention."""
    if not id_value or not pattern.match(id_value):
        raise ValueError(f"Invalid {entity_name} ID format: '{id_value}'. Expected pattern: {pattern.pattern}")
    return True
