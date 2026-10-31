from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, SUBSCRIPTION_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.usage import UsageSnapshot
    from app.models.billing import BillingEvent
    from app.models.churn import ChurnOutcome


class Subscription(Base):
    """Subscription entity capturing customer contract tier and lifecycle status."""
    __tablename__ = "subscriptions"

    subscription_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="Monthly")
    mrr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Active", index=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    trial_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    churn_reason: Mapped[str] = mapped_column(String(50), nullable=False, default="None", index=True)
    plan_change_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="subscriptions")
    usage_snapshots: Mapped[List["UsageSnapshot"]] = relationship(
        "UsageSnapshot", back_populates="subscription", cascade="all, delete-orphan", order_by="UsageSnapshot.snapshot_date"
    )
    billing_events: Mapped[List["BillingEvent"]] = relationship(
        "BillingEvent", back_populates="subscription", cascade="all, delete-orphan", order_by="BillingEvent.billing_date"
    )
    churn_outcomes: Mapped[List["ChurnOutcome"]] = relationship(
        "ChurnOutcome", back_populates="subscription", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("mrr >= 0", name="chk_subscription_mrr_positive"),
        CheckConstraint("unit_cost >= 0", name="chk_subscription_unit_cost_positive"),
        CheckConstraint(
            "status IN ('Active', 'Delinquent', 'Canceled', 'Expired', 'Paused')",
            name="chk_subscription_status_valid"
        ),
        CheckConstraint(
            "churn_reason IN ('Voluntary', 'Involuntary', 'None')",
            name="chk_subscription_churn_reason_valid"
        ),
        Index("idx_subscription_cust_status", "customer_id", "status"),
        Index("idx_subscription_plan_status", "plan_name", "status"),
    )

    def __init__(self, **kwargs):
        if "subscription_id" in kwargs:
            validate_id(kwargs["subscription_id"], SUBSCRIPTION_ID_REGEX, "Subscription")
        super().__init__(**kwargs)

    @property
    def gross_margin(self) -> float:
        return max(0.0, self.mrr - self.unit_cost)

    @property
    def margin_percentage(self) -> float:
        return (self.gross_margin / self.mrr * 100.0) if self.mrr > 0 else 0.0

    def __repr__(self) -> str:
        return f"<Subscription {self.subscription_id}: {self.plan_name} (${self.mrr}/mo) [{self.status}]>"
