from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    Subscription,
    UsageSnapshot,
    BillingEvent,
    SupportCase,
    Offer,
    CampaignContact,
    ChurnOutcome,
    RetentionOutcome,
)
from app.services.churn_prediction import ChurnPredictionService


class BusinessAnalyticsService:
    """Enterprise metrics aggregator computing live business, prediction, and experimental KPIs."""

    def __init__(self, session: Session):
        self.session = session

    def get_executive_summary(self) -> Dict[str, Any]:
        """Compute top-level KPI metrics across all 10 entities for the Executive Dashboard."""
        customers = self.session.query(Customer).all()
        subs = self.session.query(Subscription).all()
        churn_records = self.session.query(ChurnOutcome).all()
        contacts = self.session.query(CampaignContact).all()
        retention_outcomes = self.session.query(RetentionOutcome).all()

        total_customers = len(customers)
        active_subs = [s for s in subs if s.status == "Active"]
        canceled_subs = [s for s in subs if s.status == "Canceled"]

        active_count = len(active_subs)
        churned_count = len(canceled_subs)

        total_mrr = sum(s.mrr for s in active_subs)
        total_arr = total_mrr * 12.0

        voluntary_churn = sum(1 for s in canceled_subs if s.churn_reason == "Voluntary")
        involuntary_churn = sum(1 for s in canceled_subs if s.churn_reason == "Involuntary")

        overall_churn_rate = (churned_count / total_customers * 100.0) if total_customers > 0 else 0.0
        retention_rate = 100.0 - overall_churn_rate

        # Experiment summary
        treat_contacts = [c for c in contacts if c.experiment_group == "Treatment"]
        ctrl_contacts = [c for c in contacts if c.experiment_group == "Control"]

        treat_ret = [r for r in retention_outcomes if r.campaign_contact.experiment_group == "Treatment"]
        ctrl_ret = [r for r in retention_outcomes if r.campaign_contact.experiment_group == "Control"]

        treat_rate = (sum(1 for r in treat_ret if r.retained_after_horizon) / len(treat_ret)) if treat_ret else 0.0
        ctrl_rate = (sum(1 for r in ctrl_ret if r.retained_after_horizon) / len(ctrl_ret)) if ctrl_ret else 0.0
        abs_lift = treat_rate - ctrl_rate
        rel_lift = (abs_lift / ctrl_rate) if ctrl_rate > 0 else 0.0

        total_campaign_cost = sum(r.offer_cost_incurred for r in retention_outcomes)
        total_campaign_benefit = sum(r.incremental_revenue for r in retention_outcomes if r.retained_after_horizon)
        gross_campaign_roi = (
            ((total_campaign_benefit - total_campaign_cost) / total_campaign_cost * 100.0)
            if total_campaign_cost > 0 else 0.0
        )

        # Causal Incremental Accounting
        genuinely_incremental_revenue = max(0.0, abs_lift) * total_campaign_benefit
        incremental_roi = (
            ((genuinely_incremental_revenue - total_campaign_cost) / total_campaign_cost * 100.0)
            if total_campaign_cost > 0 else 0.0
        )

        return {
            "customer_kpis": {
                "total_customers": total_customers,
                "active_subscribers": active_count,
                "churned_customers": churned_count,
                "voluntary_churn": voluntary_churn,
                "involuntary_churn": involuntary_churn,
                "churn_rate_pct": round(overall_churn_rate, 2),
                "retention_rate_pct": round(retention_rate, 2),
                "active_mrr": round(total_mrr, 2),
                "active_arr": round(total_arr, 2),
            },
            "experiment_kpis": {
                "total_campaign_contacts": len(contacts),
                "treatment_population": len(treat_contacts),
                "control_population": len(ctrl_contacts),
                "treatment_retention_rate": round(treat_rate * 100.0, 2),
                "control_retention_rate": round(ctrl_rate * 100.0, 2),
                "absolute_incremental_lift_pct": round(abs_lift * 100.0, 2),
                "relative_lift_pct": round(rel_lift * 100.0, 2),
                "total_campaign_cost": round(total_campaign_cost, 2),
                "gross_attributed_revenue": round(total_campaign_benefit, 2),
                "gross_attributed_roi_pct": round(gross_campaign_roi, 2),
                "genuinely_incremental_revenue": round(genuinely_incremental_revenue, 2),
                "incremental_roi_pct": round(incremental_roi, 2),
                # Legacy compatibility aliases
                "total_campaign_benefit": round(total_campaign_benefit, 2),
                "campaign_roi_pct": round(gross_campaign_roi, 2),
            },
        }

    def get_monthly_cohort_analytics(self) -> List[Dict[str, Any]]:
        """Compute monthly cohort onboarding, active, and churn progression."""
        customers = self.session.query(Customer).all()
        subs = self.session.query(Subscription).all()
        sub_by_cust = {s.customer_id: s for s in subs}

        cohort_map = defaultdict(lambda: {"total": 0, "active": 0, "churned": 0, "mrr": 0.0})

        for c in customers:
            month = c.cohort_month
            sub = sub_by_cust.get(c.customer_id)
            cohort_map[month]["total"] += 1
            if sub and sub.status == "Active":
                cohort_map[month]["active"] += 1
                cohort_map[month]["mrr"] += sub.mrr
            else:
                cohort_map[month]["churned"] += 1

        results = []
        for month in sorted(cohort_map.keys()):
            data = cohort_map[month]
            tot = data["total"]
            ret_rate = (data["active"] / tot * 100.0) if tot > 0 else 0.0
            results.append({
                "cohort_month": month,
                "total_signups": tot,
                "active_count": data["active"],
                "churned_count": data["churned"],
                "retention_rate_pct": round(ret_rate, 1),
                "current_mrr": round(data["mrr"], 2),
            })

        return results

    def get_usage_trends(self) -> List[Dict[str, Any]]:
        """Compute aggregated monthly platform usage metrics."""
        snaps = self.session.query(UsageSnapshot).all()
        by_month = defaultdict(lambda: {
            "active_days": [], "logins": [], "session_mins": [], "api_calls": [], "utilization": []
        })

        for s in snaps:
            m = s.snapshot_month
            by_month[m]["active_days"].append(s.active_days)
            by_month[m]["logins"].append(s.login_count)
            by_month[m]["session_mins"].append(s.total_session_minutes)
            by_month[m]["api_calls"].append(s.api_call_count)
            by_month[m]["utilization"].append(s.license_utilization_pct)

        results = []
        for m in sorted(by_month.keys()):
            data = by_month[m]
            results.append({
                "month": m,
                "avg_active_days": round(float(np.mean(data["active_days"])), 1),
                "avg_logins": round(float(np.mean(data["logins"])), 1),
                "avg_session_mins": round(float(np.mean(data["session_mins"])), 1),
                "total_api_calls": int(sum(data["api_calls"])),
                "avg_license_utilization": round(float(np.mean(data["utilization"])), 1),
            })
        return results

    def get_billing_summary(self) -> Dict[str, Any]:
        """Compute invoicing, collected revenue, failure rates, and delinquency."""
        bills = self.session.query(BillingEvent).all()
        total_invoiced = sum(b.invoice_amount for b in bills)
        total_collected = sum(b.paid_amount for b in bills)
        failed_count = sum(1 for b in bills if b.status == "Failed")
        paid_count = sum(1 for b in bills if b.status == "Paid")
        total_count = len(bills)

        failure_rate = (failed_count / total_count * 100.0) if total_count > 0 else 0.0
        outstanding = total_invoiced - total_collected

        return {
            "total_invoiced": round(total_invoiced, 2),
            "total_collected": round(total_collected, 2),
            "total_outstanding": round(outstanding, 2),
            "total_invoices_count": total_count,
            "paid_invoices_count": paid_count,
            "failed_invoices_count": failed_count,
            "failure_rate_pct": round(failure_rate, 2),
        }

    def get_support_analytics(self) -> Dict[str, Any]:
        """Compute customer support case metrics, CSAT scores, and escalations."""
        cases = self.session.query(SupportCase).all()
        total_cases = len(cases)
        open_cases = sum(1 for c in cases if c.status in ["Open", "In_Progress", "Escalated"])
        resolved_cases = [c for c in cases if c.status == "Resolved" and c.resolution_hours is not None]

        avg_resolution = (float(np.mean([c.resolution_hours for c in resolved_cases]))) if resolved_cases else 0.0
        csat_ratings = [c.csat_score for c in cases if c.csat_score is not None]
        avg_csat = (float(np.mean(csat_ratings))) if csat_ratings else 5.0

        by_category = defaultdict(int)
        for c in cases:
            by_category[c.category] += 1

        return {
            "total_cases": total_cases,
            "open_cases": open_cases,
            "resolved_cases": len(resolved_cases),
            "avg_resolution_hours": round(avg_resolution, 1),
            "avg_csat": round(avg_csat, 2),
            "category_breakdown": dict(by_category),
        }
