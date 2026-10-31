from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    Subscription,
    Offer,
    EligibilityRule,
    CampaignContact,
    utc_now,
)


class IneligibleCustomerException(Exception):
    """Raised when an offer dispatch is attempted for an ineligible customer (EC-02)."""
    def __init__(self, customer_id: str, offer_id: str, violations: List[str]):
        self.customer_id = customer_id
        self.offer_id = offer_id
        self.violations = violations
        super().__init__(
            f"Customer '{customer_id}' is ineligible for Offer '{offer_id}'. "
            f"Violations: {'; '.join(violations)}"
        )


@dataclass
class EligibilityEvaluationResult:
    """Detailed audit record of an eligibility decision."""
    is_eligible: bool
    customer_id: str
    offer_id: str
    passed_rules: List[str]
    violated_rules: List[str]
    calculated_offer_cost: float
    expected_margin: float
    evaluated_at: str

    def to_dict(self) -> Dict:
        return {
            "is_eligible": self.is_eligible,
            "customer_id": self.customer_id,
            "offer_id": self.offer_id,
            "passed_rules": self.passed_rules,
            "violated_rules": self.violated_rules,
            "calculated_offer_cost": round(self.calculated_offer_cost, 2),
            "expected_margin": round(self.expected_margin, 2),
            "evaluated_at": self.evaluated_at,
        }


class OfferEligibilityEngine:
    """Configurable 10-point gatekeeper and financial contribution margin validation engine."""

    def __init__(self, session: Session):
        self.session = session

    def evaluate(
        self,
        customer_id: str,
        offer_id: str,
        risk_category: Optional[str] = None,
        as_of_date: Optional[datetime] = None
    ) -> EligibilityEvaluationResult:
        """Evaluate customer against all offer constraints, configurable rules, and unit margin thresholds."""
        check_dt = as_of_date or utc_now()
        passed_rules = []
        violated_rules = []

        # 1. Fetch Customer and active Subscription
        customer = self.session.query(Customer).filter_by(customer_id=customer_id).first()
        if not customer:
            return EligibilityEvaluationResult(
                is_eligible=False,
                customer_id=customer_id,
                offer_id=offer_id,
                passed_rules=[],
                violated_rules=["CUSTOMER_NOT_FOUND: Customer does not exist."],
                calculated_offer_cost=0.0,
                expected_margin=0.0,
                evaluated_at=check_dt.isoformat(),
            )

        sub = self.session.query(Subscription).filter_by(customer_id=customer_id).order_by(
            Subscription.start_date.desc()
        ).first()

        if not sub:
            return EligibilityEvaluationResult(
                is_eligible=False,
                customer_id=customer_id,
                offer_id=offer_id,
                passed_rules=[],
                violated_rules=["NO_SUBSCRIPTION: Customer has no subscription record."],
                calculated_offer_cost=0.0,
                expected_margin=0.0,
                evaluated_at=check_dt.isoformat(),
            )

        # 2. Fetch Offer and associated EligibilityRules
        offer = self.session.query(Offer).filter_by(offer_id=offer_id).first()
        if not offer:
            return EligibilityEvaluationResult(
                is_eligible=False,
                customer_id=customer_id,
                offer_id=offer_id,
                passed_rules=[],
                violated_rules=[f"OFFER_NOT_FOUND: Offer '{offer_id}' does not exist."],
                calculated_offer_cost=0.0,
                expected_margin=0.0,
                evaluated_at=check_dt.isoformat(),
            )

        # Check 1: Offer Catalog Status & Validity Dates
        if offer.status != "Active":
            violated_rules.append(f"OFFER_STATUS: Offer status is '{offer.status}', expected 'Active'.")
        elif not (offer.valid_from <= check_dt <= offer.valid_to):
            violated_rules.append(
                f"OFFER_DATES: Current date {check_dt.date()} is outside offer window "
                f"({offer.valid_from.date()} to {offer.valid_to.date()})."
            )
        else:
            passed_rules.append("OFFER_STATUS_AND_DATES: Offer is active and within valid dates.")

        # Check 2: Subscription Status
        if sub.status != "Active":
            violated_rules.append(f"SUBSCRIPTION_STATUS: Subscription status is '{sub.status}', expected 'Active'.")
        else:
            passed_rules.append("SUBSCRIPTION_STATUS: Subscription is Active.")

        # Check 3: Product Cohort / Plan Eligibility
        allowed_plans = [p.strip() for p in offer.eligible_plans.split(",")]
        if sub.plan_name not in allowed_plans:
            violated_rules.append(
                f"PLAN_INELIGIBLE: Plan '{sub.plan_name}' is not in eligible plans ({offer.eligible_plans})."
            )
        else:
            passed_rules.append(f"PLAN_ELIGIBILITY: Plan '{sub.plan_name}' is eligible.")

        # Check 4: Minimum Customer Tenure
        tenure_months = max(0, (check_dt - sub.start_date).days // 30)
        if tenure_months < offer.min_tenure_months:
            violated_rules.append(
                f"MIN_TENURE: Customer tenure ({tenure_months} months) < required {offer.min_tenure_months} months."
            )
        else:
            passed_rules.append(f"MIN_TENURE: Tenure ({tenure_months} months) meets minimum ({offer.min_tenure_months}).")

        # Check 5: Minimum Subscription MRR
        if sub.mrr < offer.min_subscription_mrr:
            violated_rules.append(
                f"MIN_MRR: Subscription MRR (${sub.mrr:.2f}) < required ${offer.min_subscription_mrr:.2f}."
            )
        else:
            passed_rules.append(f"MIN_MRR: Subscription MRR (${sub.mrr:.2f}) satisfies threshold.")

        # Check 6: Previous Offer Usage (Cooldown Period - 60 days)
        recent_contacts = self.session.query(CampaignContact).filter(
            CampaignContact.customer_id == customer_id,
            CampaignContact.delivery_status.in_(["Sent", "Delivered"]),
            CampaignContact.assigned_at >= (check_dt - timedelta(days=60))
        ).all()

        if recent_contacts:
            violated_rules.append(
                f"COOLDOWN_VIOLATION: Customer received offer contact within last 60 days "
                f"(Contact: {recent_contacts[0].contact_id})."
            )
        else:
            passed_rules.append("COOLDOWN_PERIOD: No conflicting offer sent in prior 60 days.")

        # Check 7: Discount Calculation & Contribution Margin
        if offer.discount_pct > 0:
            raw_discount = sub.mrr * (offer.discount_pct / 100.0)
            if offer.max_discount_cap > 0:
                discount_cost = min(raw_discount, offer.max_discount_cap)
            else:
                discount_cost = raw_discount
        else:
            discount_cost = offer.discount_amount

        # Ceiling check
        if offer.max_offer_cost > 0 and discount_cost > offer.max_offer_cost:
            discount_cost = offer.max_offer_cost

        # Unit Contribution Margin Validation:
        # Net 3-month expected value = 3 * (MRR - Unit Cost) - Discount Cost
        horizon_months = 3
        gross_margin_horizon = (sub.mrr - sub.unit_cost) * horizon_months
        net_margin_horizon = gross_margin_horizon - discount_cost

        # Minimum margin ratio check (default 20%)
        margin_rule = self.session.query(EligibilityRule).filter_by(
            offer_id=offer_id, rule_code="MARGIN_THRESHOLD"
        ).first()
        min_margin_pct = margin_rule.margin_threshold_pct if margin_rule else 0.20

        total_horizon_revenue = sub.mrr * horizon_months
        margin_pct = (net_margin_horizon / total_horizon_revenue) if total_horizon_revenue > 0 else 0.0

        if margin_pct < min_margin_pct:
            violated_rules.append(
                f"MARGIN_THRESHOLD_VIOLATION: Net margin ({margin_pct:.1%}) below required {min_margin_pct:.1%}. "
                f"(Discount: ${discount_cost:.2f}, Gross: ${gross_margin_horizon:.2f})"
            )
        else:
            passed_rules.append(f"MARGIN_THRESHOLD: Net contribution margin is profitable ({margin_pct:.1%}).")

        # Check 8: Specific Parameterized Eligibility Rules (e.g. RISK_TIER)
        rules = self.session.query(EligibilityRule).filter_by(offer_id=offer_id, is_active=True).all()
        for r in rules:
            if r.rule_code == "RISK_TIER" and risk_category:
                allowed_tiers = [t.strip() for t in r.parameter_value.split(",")]
                if risk_category not in allowed_tiers:
                    violated_rules.append(
                        f"RISK_TIER_MISMATCH: Customer risk category '{risk_category}' "
                        f"not in allowed tiers ({r.parameter_value})."
                    )
                else:
                    passed_rules.append(f"RISK_TIER: Risk category '{risk_category}' matches rule.")

        is_eligible = len(violated_rules) == 0

        return EligibilityEvaluationResult(
            is_eligible=is_eligible,
            customer_id=customer_id,
            offer_id=offer_id,
            passed_rules=passed_rules,
            violated_rules=violated_rules,
            calculated_offer_cost=discount_cost,
            expected_margin=net_margin_horizon,
            evaluated_at=check_dt.isoformat(),
        )

    def dispatch_offer_with_guard(
        self,
        customer_id: str,
        offer_id: str,
        experiment_id: str,
        experiment_group: str = "Treatment",
        risk_category: Optional[str] = None
    ) -> CampaignContact:
        """Attempt to dispatch offer to customer with strict eligibility enforcement (EC-02).

        Raises:
            IneligibleCustomerException: If customer fails any eligibility or margin criteria.
        """
        eval_result = self.evaluate(customer_id, offer_id, risk_category=risk_category)

        if not eval_result.is_eligible:
            # Raise exception and preserve audit trail for EC-02
            raise IneligibleCustomerException(
                customer_id=customer_id,
                offer_id=offer_id,
                violations=eval_result.violated_rules
            )

        # Eligible: create CampaignContact
        now = utc_now()
        contact_id = f"CAM-{now.year}-{int(now.timestamp()) % 1000000:06d}"
        contact = CampaignContact(
            contact_id=contact_id,
            experiment_id=experiment_id,
            customer_id=customer_id,
            offer_id=offer_id,
            experiment_group=experiment_group,
            stratum_id="Evaluated:Direct",
            assigned_at=now,
            delivery_date=now,
            delivery_channel="Email",
            delivery_status="Delivered",
            is_eligible=True,
            eligibility_notes=f"Passed checks: {len(eval_result.passed_rules)} rules satisfied.",
            response_status="Pending",
        )
        self.session.add(contact)
        self.session.commit()
        return contact
