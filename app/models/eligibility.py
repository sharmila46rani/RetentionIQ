from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, ELIGIBILITY_RULE_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.offer import Offer


class EligibilityRule(Base):
    """Rule predicate governing customer eligibility and margin gating for an offer."""
    __tablename__ = "eligibility_rules"

    rule_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    offer_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("offers.offer_id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parameter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False, default="GTE")
    parameter_value: Mapped[str] = mapped_column(String(255), nullable=False)
    margin_threshold_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.20)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    offer: Mapped["Offer"] = relationship("Offer", back_populates="eligibility_rules")

    __table_args__ = (
        CheckConstraint(
            "operator IN ('GT', 'GTE', 'LT', 'LTE', 'EQ', 'IN', 'NOT_IN')",
            name="chk_rule_operator_valid"
        ),
        CheckConstraint("margin_threshold_pct >= 0 AND margin_threshold_pct <= 1.0", name="chk_rule_margin_range"),
        Index("idx_rule_offer_code", "offer_id", "rule_code"),
    )

    def __init__(self, **kwargs):
        if "rule_id" in kwargs:
            validate_id(kwargs["rule_id"], ELIGIBILITY_RULE_ID_REGEX, "EligibilityRule")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<EligibilityRule {self.rule_id}: {self.rule_code} {self.operator} {self.parameter_value}>"
