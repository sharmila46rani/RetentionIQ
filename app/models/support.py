from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, SUPPORT_CASE_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.customer import Customer


class SupportCase(Base):
    """Customer support case telemetry record."""
    __tablename__ = "support_cases"

    case_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Open", index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    escalation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    csat_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="support_cases")

    __table_args__ = (
        CheckConstraint(
            "category IN ('Billing', 'Technical', 'Product_Bug', 'Feature_Request', 'Account')",
            name="chk_support_category_valid"
        ),
        CheckConstraint(
            "priority IN ('Low', 'Medium', 'High', 'Critical')",
            name="chk_support_priority_valid"
        ),
        CheckConstraint(
            "status IN ('Open', 'In_Progress', 'Resolved', 'Escalated')",
            name="chk_support_status_valid"
        ),
        CheckConstraint(
            "csat_score IS NULL OR (csat_score >= 1 AND csat_score <= 5)",
            name="chk_support_csat_range"
        ),
        CheckConstraint("escalation_count >= 0", name="chk_support_escalations_positive"),
        Index("idx_support_cust_status", "customer_id", "status"),
        Index("idx_support_priority_status", "priority", "status"),
    )

    def __init__(self, **kwargs):
        if "case_id" in kwargs:
            validate_id(kwargs["case_id"], SUPPORT_CASE_ID_REGEX, "SupportCase")
        super().__init__(**kwargs)

    @property
    def is_resolved(self) -> bool:
        return self.status == "Resolved"

    def __repr__(self) -> str:
        return f"<SupportCase {self.case_id}: {self.category} [{self.priority}/{self.status}]>"
