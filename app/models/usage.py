from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utc_now, USAGE_SNAPSHOT_ID_REGEX, validate_id

if TYPE_CHECKING:
    from app.models.subscription import Subscription


class UsageSnapshot(Base):
    """Monthly usage telemetry snapshot per subscription."""
    __tablename__ = "usage_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(45), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("subscriptions.subscription_id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    active_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_session_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feature_events_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    api_call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    license_utilization_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    usage_decline_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="usage_snapshots")

    __table_args__ = (
        UniqueConstraint("subscription_id", "snapshot_month", name="uq_subscription_month_snapshot"),
        CheckConstraint("active_days >= 0 AND active_days <= 31", name="chk_usage_active_days"),
        CheckConstraint("login_count >= 0", name="chk_usage_login_count"),
        CheckConstraint("total_session_minutes >= 0", name="chk_usage_session_mins"),
        CheckConstraint("feature_events_count >= 0", name="chk_usage_features"),
        CheckConstraint("api_call_count >= 0", name="chk_usage_api_calls"),
        CheckConstraint("license_utilization_pct >= 0 AND license_utilization_pct <= 100", name="chk_usage_license_pct"),
        Index("idx_usage_sub_date", "subscription_id", "snapshot_date"),
    )

    def __init__(self, **kwargs):
        if "snapshot_id" in kwargs:
            validate_id(kwargs["snapshot_id"], USAGE_SNAPSHOT_ID_REGEX, "UsageSnapshot")
        super().__init__(**kwargs)

    @property
    def avg_session_duration(self) -> float:
        return (self.total_session_minutes / self.login_count) if self.login_count > 0 else 0.0

    def __repr__(self) -> str:
        return f"<UsageSnapshot {self.snapshot_id}: {self.active_days} active days, decline={self.usage_decline_pct:.1f}%>"
