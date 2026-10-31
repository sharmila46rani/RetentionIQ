from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, CHURN_OUTCOME_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.subscription import Subscription
    from app.models.retention import RetentionOutcome


class ChurnOutcome(Base):
    """Ground truth churn outcome evaluation record isolated from prediction features."""
    __tablename__ = "churn_outcomes"

    churn_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("subscriptions.subscription_id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_cutoff_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    observation_window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    observation_window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_churned: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    actual_churn_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    churn_type: Mapped[str] = mapped_column(String(30), nullable=False, default="Retained", index=True)
    primary_churn_driver: Mapped[str] = mapped_column(String(50), nullable=False, default="None")
    is_ground_truth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="churn_outcomes")
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="churn_outcomes")
    retention_outcome: Mapped[Optional["RetentionOutcome"]] = relationship(
        "RetentionOutcome", back_populates="churn_outcome", uselist=False
    )

    __table_args__ = (
        UniqueConstraint("customer_id", "prediction_cutoff_date", name="uq_customer_cutoff_churn"),
        CheckConstraint(
            "churn_type IN ('Voluntary', 'Involuntary', 'Retained')",
            name="chk_churn_type_valid"
        ),
        CheckConstraint(
            "primary_churn_driver IN ('Usage_Drop', 'Payment_Failure', 'Support_Frustration', 'Competitor', 'None')",
            name="chk_churn_driver_valid"
        ),
        Index("idx_churn_cutoff_type", "prediction_cutoff_date", "churn_type"),
    )

    def __init__(self, **kwargs):
        if "churn_id" in kwargs:
            validate_id(kwargs["churn_id"], CHURN_OUTCOME_ID_REGEX, "ChurnOutcome")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<ChurnOutcome {self.churn_id}: churned={self.actual_churned} ({self.churn_type})>"
