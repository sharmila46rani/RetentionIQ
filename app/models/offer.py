from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, DateTime, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, OFFER_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.eligibility import EligibilityRule
    from app.models.campaign import CampaignContact


class Offer(Base):
    """Retention offer catalog entity defining incentives and eligibility limits."""
    __tablename__ = "offers"

    offer_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    offer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    offer_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    discount_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_offer_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    eligible_plans: Mapped[str] = mapped_column(String(255), nullable=False, default="Starter,Growth,Scale,Enterprise")
    min_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_subscription_mrr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_discount_cap: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    eligibility_rules: Mapped[List["EligibilityRule"]] = relationship(
        "EligibilityRule", back_populates="offer", cascade="all, delete-orphan"
    )
    campaign_contacts: Mapped[List["CampaignContact"]] = relationship(
        "CampaignContact", back_populates="offer"
    )

    __table_args__ = (
        CheckConstraint(
            "offer_type IN ('Discount', 'Free_Month', 'Feature_Addon', 'Tier_Upgrade')",
            name="chk_offer_type_valid"
        ),
        CheckConstraint(
            "status IN ('Draft', 'Active', 'Paused', 'Expired')",
            name="chk_offer_status_valid"
        ),
        CheckConstraint("discount_pct >= 0 AND discount_pct <= 100", name="chk_offer_discount_pct_range"),
        CheckConstraint("discount_amount >= 0", name="chk_offer_discount_amt_positive"),
        CheckConstraint("max_offer_cost >= 0", name="chk_offer_cost_positive"),
        Index("idx_offer_status_validity", "status", "valid_from", "valid_to"),
    )

    def __init__(self, **kwargs):
        if "offer_id" in kwargs:
            validate_id(kwargs["offer_id"], OFFER_ID_REGEX, "Offer")
        super().__init__(**kwargs)

    def is_currently_active(self, target_date: datetime = None) -> bool:
        check_dt = target_date or utc_now()
        return self.status == "Active" and (self.valid_from <= check_dt <= self.valid_to)

    def __repr__(self) -> str:
        return f"<Offer {self.offer_id}: {self.offer_name} ({self.offer_type}) [{self.status}]>"
