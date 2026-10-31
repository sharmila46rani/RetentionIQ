from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, CAMPAIGN_CONTACT_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.offer import Offer
    from app.models.retention import RetentionOutcome


class CampaignContact(Base):
    """Campaign contact and randomized experiment assignment record."""
    __tablename__ = "campaign_contacts"

    contact_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True
    )
    offer_id: Mapped[Optional[str]] = mapped_column(
        String(30), ForeignKey("offers.offer_id", ondelete="SET NULL"), nullable=True, index=True
    )
    experiment_group: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stratum_id: Mapped[str] = mapped_column(String(100), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivery_channel: Mapped[str] = mapped_column(String(30), nullable=False, default="Email")
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="Sent", index=True)
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    eligibility_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    response_status: Mapped[str] = mapped_column(String(30), nullable=False, default="Pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="campaign_contacts")
    offer: Mapped[Optional["Offer"]] = relationship("Offer", back_populates="campaign_contacts")
    retention_outcome: Mapped[Optional["RetentionOutcome"]] = relationship(
        "RetentionOutcome", back_populates="campaign_contact", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("experiment_id", "customer_id", name="uq_experiment_customer_assignment"),
        CheckConstraint(
            "experiment_group IN ('Treatment', 'Control')",
            name="chk_campaign_experiment_group_valid"
        ),
        CheckConstraint(
            "delivery_channel IN ('Email', 'In_App', 'CSM_Outreach')",
            name="chk_campaign_delivery_channel_valid"
        ),
        CheckConstraint(
            "delivery_status IN ('Sent', 'Delivered', 'Failed', 'Suppressed')",
            name="chk_campaign_delivery_status_valid"
        ),
        CheckConstraint(
            "response_status IN ('Accepted', 'Rejected', 'Ignored', 'Pending')",
            name="chk_campaign_response_status_valid"
        ),
        Index("idx_campaign_exp_group", "experiment_id", "experiment_group"),
        Index("idx_campaign_cust_exp", "customer_id", "experiment_id"),
    )

    def __init__(self, **kwargs):
        if "contact_id" in kwargs:
            validate_id(kwargs["contact_id"], CAMPAIGN_CONTACT_ID_REGEX, "CampaignContact")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<CampaignContact {self.contact_id}: {self.experiment_id} ({self.experiment_group}) [{self.response_status}]>"
