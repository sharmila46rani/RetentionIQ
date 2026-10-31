import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    Subscription,
    UsageSnapshot,
    BillingEvent,
    SupportCase,
    ChurnOutcome,
)


class FeatureEngineeringService:
    """Service for computing point-in-time feature matrices with strict temporal leakage prevention."""

    @staticmethod
    def extract_customer_features(
        session: Session,
        prediction_cutoff: datetime,
        enforce_temporal_guard: bool = True
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """Extract point-in-time features for all active customers as of prediction_cutoff in bulk."""
        anomalies = []

        # 1. Fetch all customers and subscriptions in one query
        customers = session.query(Customer).all()
        subs = session.query(Subscription).all()
        sub_by_cust = {s.customer_id: s for s in subs}

        # 2. Bulk fetch snapshots strictly on or before cutoff date
        all_snapshots = session.query(UsageSnapshot).filter(
            UsageSnapshot.snapshot_date <= prediction_cutoff
        ).order_by(UsageSnapshot.snapshot_date.desc()).all()
        snapshots_by_sub = defaultdict(list)
        for snap in all_snapshots:
            snapshots_by_sub[snap.subscription_id].append(snap)

        # 3. Bulk fetch billing events strictly on or before cutoff date
        all_bills = session.query(BillingEvent).filter(
            BillingEvent.billing_date <= prediction_cutoff
        ).order_by(BillingEvent.billing_date.desc()).all()
        bills_by_sub = defaultdict(list)
        for bill in all_bills:
            bills_by_sub[bill.subscription_id].append(bill)

        # 4. Bulk fetch support cases strictly on or before cutoff date
        all_cases = session.query(SupportCase).filter(
            SupportCase.opened_at <= prediction_cutoff
        ).all()
        cases_by_cust = defaultdict(list)
        for case in all_cases:
            cases_by_cust[case.customer_id].append(case)

        plan_tier_map = {"Starter": 1, "Growth": 2, "Scale": 3, "Enterprise": 4}
        records = []

        for cust in customers:
            sub = sub_by_cust.get(cust.customer_id)
            if not sub:
                continue

            # EC-01 Temporal Leakage Detection:
            # If subscription was already canceled on or before prediction cutoff,
            # this customer is already churned and must be excluded from forward prediction.
            if sub.canceled_at and sub.canceled_at <= prediction_cutoff:
                anomalies.append({
                    "customer_id": cust.customer_id,
                    "subscription_id": sub.subscription_id,
                    "rule_violated": "EC-01: CHURN_PRECEDES_PREDICTION_DATE",
                    "churn_date": sub.canceled_at.isoformat(),
                    "prediction_cutoff": prediction_cutoff.isoformat(),
                    "description": f"Customer churned on {sub.canceled_at.date()} prior to prediction cutoff {prediction_cutoff.date()}."
                })
                if enforce_temporal_guard:
                    continue  # Safely exclude from valid candidate pool

            # Only customers who signed up on or before prediction cutoff
            if cust.signup_date > prediction_cutoff:
                continue

            tenure_days = max(1, (prediction_cutoff - sub.start_date).days)
            tenure_months = tenure_days / 30.5

            # Telemetry for this subscription
            snaps = snapshots_by_sub.get(sub.subscription_id, [])
            if snaps:
                latest_snap = snaps[0]
                recent_active_days = latest_snap.active_days
                recent_logins = latest_snap.login_count
                recent_session_mins = latest_snap.total_session_minutes
                recent_decline_pct = latest_snap.usage_decline_pct
                recent_utilization = latest_snap.license_utilization_pct
                avg_active_3m = float(np.mean([s.active_days for s in snaps[:3]]))
                avg_logins_3m = float(np.mean([s.login_count for s in snaps[:3]]))
            else:
                recent_active_days = 0
                recent_logins = 0
                recent_session_mins = 0.0
                recent_decline_pct = 0.0
                recent_utilization = 0.0
                avg_active_3m = 0.0
                avg_logins_3m = 0.0

            # Billing for this subscription
            bills = bills_by_sub.get(sub.subscription_id, [])
            billing_fail_count = sum(1 for b in bills if b.status == "Failed")
            latest_bill_failed = 1 if (bills and bills[0].status == "Failed") else 0
            outstanding_balance = sum(b.outstanding_balance for b in bills)

            # Support cases for this customer
            cases = cases_by_cust.get(cust.customer_id, [])
            total_cases = len(cases)
            unresolved_cases = sum(1 for c in cases if c.status != "Resolved")
            critical_cases = sum(1 for c in cases if c.priority == "Critical")
            resolved_cases = [c for c in cases if c.resolved_at and c.resolved_at <= prediction_cutoff]
            avg_res_hours = float(np.mean([c.resolution_hours for c in resolved_cases])) if resolved_cases else 0.0

            csat_scores = [c.csat_score for c in cases if c.csat_score is not None]
            avg_csat = float(np.mean(csat_scores)) if csat_scores else 5.0

            plan_code = plan_tier_map.get(sub.plan_name, 1)

            records.append({
                "customer_id": cust.customer_id,
                "subscription_id": sub.subscription_id,
                "plan_name": sub.plan_name,
                "plan_code": plan_code,
                "mrr": sub.mrr,
                "tenure_months": round(tenure_months, 1),
                "plan_change_count": sub.plan_change_count,
                # Usage features
                "recent_active_days": recent_active_days,
                "recent_logins": recent_logins,
                "recent_session_mins": round(recent_session_mins, 1),
                "recent_decline_pct": round(recent_decline_pct, 1),
                "recent_utilization": round(recent_utilization, 1),
                "avg_active_3m": round(avg_active_3m, 1),
                "avg_logins_3m": round(avg_logins_3m, 1),
                # Billing features
                "billing_fail_count": billing_fail_count,
                "latest_bill_failed": latest_bill_failed,
                "outstanding_balance": round(outstanding_balance, 2),
                # Support features
                "total_cases": total_cases,
                "unresolved_cases": unresolved_cases,
                "critical_cases": critical_cases,
                "avg_res_hours": round(avg_res_hours, 1),
                "avg_csat": round(avg_csat, 2),
            })

        features_df = pd.DataFrame(records)
        return features_df, anomalies
