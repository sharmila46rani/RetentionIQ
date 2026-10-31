from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, RETENTION_OUTCOME_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.campaign import CampaignContact
    from app.models.churn import ChurnOutcome


class RetentionOutcome(Base):
    """Retention campaign financial and behavioral outcome evaluation record."""
    __tablename__ = "retention_outcomes"

    retention_id: Mapped[str] = mapped_column(String(35), primary_key=True)
    contact_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("campaign_contacts.contact_id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True
    )
    churn_id: Mapped[Optional[str]] = mapped_column(
        String(30), ForeignKey("churn_outcomes.churn_id", ondelete="SET NULL"), nullable=True, index=True
    )
    retained_after_horizon: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    days_retained: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incremental_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    offer_cost_incurred: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    net_campaign_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attribution_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Primary_Attributed", index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    campaign_contact: Mapped["CampaignContact"] = relationship("CampaignContact", back_populates="retention_outcome")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="retention_outcomes")
    churn_outcome: Mapped[Optional["ChurnOutcome"]] = relationship("ChurnOutcome", back_populates="retention_outcome")

    __table_args__ = (
        CheckConstraint(
            "attribution_status IN ('Primary_Attributed', 'Multi_Attributed_Flagged', 'Non_Attributed')",
            name="chk_retention_attribution_valid"
        ),
        CheckConstraint("days_retained >= 0", name="chk_retention_days_positive"),
        Index("idx_retention_status_eval", "attribution_status", "evaluated_at"),
    )

    def __init__(self, **kwargs):
        if "retention_id" in kwargs:
            validate_id(kwargs["retention_id"], RETENTION_OUTCOME_ID_REGEX, "RetentionOutcome")
        super().__init__(**kwargs)

    @property
    def net_roi_percentage(self) -> float:
        if self.offer_cost_incurred > 0:
            return (self.net_campaign_value / self.offer_cost_incurred) * 100.0
        return 0.0

    def __repr__(self) -> str:
        return f"<RetentionOutcome {self.retention_id}: retained={self.retained_after_horizon} [Net: ${self.net_campaign_value:.2f}]>"
