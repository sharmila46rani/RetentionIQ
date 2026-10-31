from datetime import datetime
from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING
from app.models.base import Base, utc_now, CUSTOMER_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.subscription import Subscription
    from app.models.support import SupportCase
    from app.models.campaign import CampaignContact
    from app.models.churn import ChurnOutcome
    from app.models.retention import RetentionOutcome


class Customer(Base):
    """Customer entity representing accounts and subscribers."""
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="Standard", index=True)
    cohort_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    signup_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="customer", cascade="all, delete-orphan", order_by="Subscription.start_date"
    )
    support_cases: Mapped[List["SupportCase"]] = relationship(
        "SupportCase", back_populates="customer", cascade="all, delete-orphan", order_by="SupportCase.opened_at"
    )
    campaign_contacts: Mapped[List["CampaignContact"]] = relationship(
        "CampaignContact", back_populates="customer", cascade="all, delete-orphan"
    )
    churn_outcomes: Mapped[List["ChurnOutcome"]] = relationship(
        "ChurnOutcome", back_populates="customer", cascade="all, delete-orphan"
    )
    retention_outcomes: Mapped[List["RetentionOutcome"]] = relationship(
        "RetentionOutcome", back_populates="customer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_customer_cohort_tier", "cohort_month", "customer_tier"),
    )

    def __init__(self, **kwargs):
        if "customer_id" in kwargs:
            validate_id(kwargs["customer_id"], CUSTOMER_ID_REGEX, "Customer")
        super().__init__(**kwargs)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Customer {self.customer_id}: {self.full_name} ({self.company_name})>"
