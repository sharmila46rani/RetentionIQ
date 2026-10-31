from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, BILLING_EVENT_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.subscription import Subscription


class BillingEvent(Base):
    """Invoice and payment transaction records."""
    __tablename__ = "billing_events"

    billing_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("subscriptions.subscription_id", ondelete="CASCADE"), nullable=False, index=True
    )
    billing_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    invoice_amount: Mapped[float] = mapped_column(Float, nullable=False)
    paid_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str] = mapped_column(String(100), nullable=False, default="None")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="billing_events")

    __table_args__ = (
        CheckConstraint("invoice_amount >= 0", name="chk_billing_invoice_positive"),
        CheckConstraint("paid_amount >= 0", name="chk_billing_paid_positive"),
        CheckConstraint(
            "status IN ('Paid', 'Pending', 'Failed', 'Refunded')",
            name="chk_billing_status_valid"
        ),
        CheckConstraint("retry_count >= 0", name="chk_billing_retries_positive"),
        Index("idx_billing_sub_status", "subscription_id", "status"),
        Index("idx_billing_date_status", "billing_date", "status"),
    )

    def __init__(self, **kwargs):
        if "billing_id" in kwargs:
            validate_id(kwargs["billing_id"], BILLING_EVENT_ID_REGEX, "BillingEvent")
        super().__init__(**kwargs)

    @property
    def outstanding_balance(self) -> float:
        return max(0.0, self.invoice_amount - self.paid_amount)

    @property
    def is_delinquent(self) -> bool:
        return self.status == "Failed" or (self.status == "Pending" and utc_now() > self.due_date)

    def __repr__(self) -> str:
        return f"<BillingEvent {self.billing_id}: ${self.invoice_amount:.2f} [{self.status}]>"
