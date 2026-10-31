import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    Subscription,
    Offer,
    CampaignContact,
    ChurnOutcome,
    RetentionOutcome,
    utc_now,
)
from app.services.eligibility_service import OfferEligibilityEngine, IneligibleCustomerException
from app.services.churn_prediction import ChurnPredictionService


class ExperimentConflictException(Exception):
    """Raised when treatment/control contamination or overlapping active assignment is detected (EC-03)."""
    def __init__(self, customer_id: str, experiment_id: str, reason: str):
        self.customer_id = customer_id
        self.experiment_id = experiment_id
        self.reason = reason
        super().__init__(
            f"Experiment assignment collision for Customer '{customer_id}' in Experiment '{experiment_id}': {reason}"
        )


class RandomizedExperimentEngine:
    """Rigorous A/B testing experiment engine with stratified randomization and contamination guardrails."""

    def __init__(self, session: Session, seed: int = 20261022):
        self.session = session
        self.seed = seed
        self.rng = random.Random(seed)

    def launch_experiment(
        self,
        experiment_id: str,
        offer_id: str,
        target_risk_categories: List[str] = ["High", "Critical"],
        prediction_cutoff: Optional[datetime] = None,
        channel: str = "Email",
    ) -> Dict[str, Any]:
        """Execute the 8-step randomized retention trial process."""
        now = utc_now()
        pred_dt = prediction_cutoff or now

        # Step 1: Predict risk categories for active subscriber population
        predictor = ChurnPredictionService(self.session)
        pred_result = predictor.generate_predictions(prediction_cutoff=pred_dt)
        risk_map = {p["customer_id"]: p["risk_category"] for p in pred_result["predictions"]}

        # Step 2: Identify & Filter strictly eligible candidates
        eligibility_engine = OfferEligibilityEngine(self.session)
        eligible_candidates = []
        ineligible_audit = []

        for p in pred_result["predictions"]:
            cid = p["customer_id"]
            risk_cat = p["risk_category"]

            # EC-03 Contamination Guard: Check if customer already exists in this experiment
            existing = self.session.query(CampaignContact).filter_by(
                experiment_id=experiment_id, customer_id=cid
            ).first()
            if existing:
                raise ExperimentConflictException(
                    customer_id=cid,
                    experiment_id=experiment_id,
                    reason=f"Customer '{cid}' already assigned to group '{existing.experiment_group}'."
                )

            if risk_cat in target_risk_categories:
                eval_res = eligibility_engine.evaluate(cid, offer_id, risk_category=risk_cat, as_of_date=now)
                if eval_res.is_eligible:
                    eligible_candidates.append({
                        "customer_id": cid,
                        "plan_name": p["plan_name"],
                        "risk_category": risk_cat,
                        "stratum": f"{risk_cat}_{p['plan_name']}",
                    })
                else:
                    ineligible_audit.append(eval_res.to_dict())

        # Step 3: Freeze population
        eligible_candidates.sort(key=lambda x: x["customer_id"])

        # Step 4: Stratified 50/50 Randomization with Contamination Guard (EC-03)
        strata = {}
        for cand in eligible_candidates:
            st = cand["stratum"]
            if st not in strata:
                strata[st] = []
            strata[st].append(cand)

        treatment_contacts = []
        control_contacts = []
        contact_seq = 1

        for stratum_name, bucket in sorted(strata.items()):
            # Deterministic reproducible shuffle
            self.rng.shuffle(bucket)
            n_bucket = len(bucket)
            n_treat = n_bucket // 2

            for idx, cand in enumerate(bucket):
                cid = cand["customer_id"]

                # EC-03 Contamination Guard: Check if customer already exists in this experiment
                existing = self.session.query(CampaignContact).filter_by(
                    experiment_id=experiment_id, customer_id=cid
                ).first()
                if existing:
                    raise ExperimentConflictException(
                        customer_id=cid,
                        experiment_id=experiment_id,
                        reason=f"Customer already assigned to group '{existing.experiment_group}'."
                    )

                is_treatment = (idx < n_treat)
                group = "Treatment" if is_treatment else "Control"
                contact_id = f"CAM-{now.year}-{contact_seq + int(now.timestamp()) % 900000:06d}"
                contact_seq += 1

                contact = CampaignContact(
                    contact_id=contact_id,
                    experiment_id=experiment_id,
                    customer_id=cid,
                    offer_id=offer_id if is_treatment else None,
                    experiment_group=group,
                    stratum_id=stratum_name,
                    assigned_at=now,
                    delivery_date=now if is_treatment else None,
                    delivery_channel=channel,
                    delivery_status="Delivered" if is_treatment else "Suppressed",
                    is_eligible=True,
                    eligibility_notes="Passed stratified experiment eligibility screening.",
                    response_status="Pending",
                )
                self.session.add(contact)

                if is_treatment:
                    treatment_contacts.append(contact)
                else:
                    control_contacts.append(contact)

        self.session.commit()

        return {
            "experiment_id": experiment_id,
            "offer_id": offer_id,
            "target_risk_categories": target_risk_categories,
            "total_candidates_evaluated": len(pred_result["predictions"]),
            "eligible_population_frozen": len(eligible_candidates),
            "treatment_count": len(treatment_contacts),
            "control_count": len(control_contacts),
            "ineligible_count": len(ineligible_audit),
            "strata_count": len(strata),
        }

    def evaluate_retention_outcomes_with_attribution(
        self,
        experiment_id: str,
        horizon_days: int = 30
    ) -> Dict[str, Any]:
        """Track customer outcomes and resolve multi-touch attribution (EC-04)."""
        contacts = self.session.query(CampaignContact).filter_by(experiment_id=experiment_id).all()
        if not contacts:
            return {"error": f"No contacts found for experiment '{experiment_id}'"}

        ground_truths = self.session.query(ChurnOutcome).all()
        gt_map = {gt.customer_id: gt for gt in ground_truths}

        subs = self.session.query(Subscription).all()
        sub_map = {s.customer_id: s for s in subs}

        offers = self.session.query(Offer).all()
        offer_map = {o.offer_id: o for o in offers}

        eval_records = []
        multi_attributed_count = 0

        for contact in contacts:
            cid = contact.customer_id
            gt = gt_map.get(cid)
            sub = sub_map.get(cid)
            off = offer_map.get(contact.offer_id) if contact.offer_id else None

            # Check for existing outcomes
            existing_ret = self.session.query(RetentionOutcome).filter_by(contact_id=contact.contact_id).first()
            if existing_ret:
                eval_records.append(existing_ret)
                continue

            # EC-04 Multi-touch Attribution Detection:
            # Check if customer has multiple contacts across active campaigns
            all_customer_contacts = self.session.query(CampaignContact).filter(
                CampaignContact.customer_id == cid,
                CampaignContact.delivery_status.in_(["Sent", "Delivered"])
            ).order_by(CampaignContact.assigned_at.desc()).all()

            is_multi_attributed = len(all_customer_contacts) > 1
            if is_multi_attributed:
                multi_attributed_count += 1
                # Documented Attribution Rule: Last-Touch Attribution
                # If this is the latest contact, mark as Primary; else Multi_Attributed_Flagged
                if all_customer_contacts[0].contact_id == contact.contact_id:
                    attribution_status = "Primary_Attributed"
                else:
                    attribution_status = "Multi_Attributed_Flagged"
            else:
                attribution_status = "Primary_Attributed"

            # Determine retention status
            actual_churned = gt.actual_churned if gt else (sub.status == "Canceled")
            retained = not actual_churned
            days_ret = horizon_days if retained else 12

            # Financial accounting
            mrr = sub.mrr if sub else 0.0
            if contact.experiment_group == "Treatment" and off:
                offer_cost = min(off.max_offer_cost, mrr * (off.discount_pct / 100.0) if off.discount_pct > 0 else off.discount_amount)
            else:
                offer_cost = 0.0

            # Only attribute incremental revenue if retained and primary
            if retained and attribution_status == "Primary_Attributed":
                inc_rev = mrr
            else:
                inc_rev = 0.0

            net_val = inc_rev - offer_cost

            ret_id = f"RET-{contact.contact_id}"
            now = utc_now()
            ret_outcome = RetentionOutcome(
                retention_id=ret_id,
                contact_id=contact.contact_id,
                customer_id=cid,
                churn_id=gt.churn_id if gt else None,
                retained_after_horizon=retained,
                days_retained=days_ret,
                incremental_revenue=round(inc_rev, 2),
                offer_cost_incurred=round(offer_cost, 2),
                net_campaign_value=round(net_val, 2),
                attribution_status=attribution_status,
                evaluated_at=now,
            )
            self.session.add(ret_outcome)
            eval_records.append(ret_outcome)

        self.session.commit()

        # Compute Lift Metrics
        treat_outcomes = [r for r in eval_records if r.campaign_contact.experiment_group == "Treatment"]
        ctrl_outcomes = [r for r in eval_records if r.campaign_contact.experiment_group == "Control"]

        n_treat = len(treat_outcomes)
        n_ctrl = len(ctrl_outcomes)

        retained_treat = sum(1 for r in treat_outcomes if r.retained_after_horizon)
        retained_ctrl = sum(1 for r in ctrl_outcomes if r.retained_after_horizon)

        rate_treat = (retained_treat / n_treat) if n_treat > 0 else 0.0
        rate_ctrl = (retained_ctrl / n_ctrl) if n_ctrl > 0 else 0.0

        abs_lift = rate_treat - rate_ctrl
        rel_lift = (abs_lift / rate_ctrl) if rate_ctrl > 0 else 0.0
        inc_retained = abs_lift * n_treat

        total_cost = sum(r.offer_cost_incurred for r in treat_outcomes)
        gross_attributed_rev = sum(r.incremental_revenue for r in treat_outcomes if r.retained_after_horizon)
        gross_attributed_roi = ((gross_attributed_rev - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0

        # Causal incremental revenue accounting: Lift * Total Treatment Portfolio Revenue
        genuinely_incremental_rev = max(0.0, abs_lift) * gross_attributed_rev
        genuinely_incremental_roi = ((genuinely_incremental_rev - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0

        return {
            "experiment_id": experiment_id,
            "total_contacts": len(eval_records),
            "treatment_group_size": n_treat,
            "control_group_size": n_ctrl,
            "treatment_retention_rate": round(rate_treat, 4),
            "control_retention_rate": round(rate_ctrl, 4),
            "absolute_incremental_lift": round(abs_lift, 4),
            "relative_lift": round(rel_lift, 4),
            "incremental_retained_customers": round(inc_retained, 2),
            "campaign_cost_incurred": round(total_cost, 2),
            # Causal incremental metrics
            "genuinely_incremental_revenue": round(genuinely_incremental_rev, 2),
            "incremental_roi_pct": round(genuinely_incremental_roi, 2),
            # Gross attributed metrics
            "gross_attributed_revenue": round(gross_attributed_rev, 2),
            "gross_attributed_roi_pct": round(gross_attributed_roi, 2),
            # Legacy compatibility aliases
            "incremental_benefit": round(gross_attributed_rev, 2),
            "roi_percentage": round(gross_attributed_roi, 2),
            "multi_attributed_flagged_count": multi_attributed_count,
        }
