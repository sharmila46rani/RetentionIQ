import hashlib
import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd


# Master Seed
DEFAULT_SEED = 20261022

# Plan Configurations: (Name, Base MRR, Unit Cost)
PLANS = [
    ("Starter", 49.0, 8.0),
    ("Growth", 149.0, 22.0),
    ("Scale", 399.0, 60.0),
    ("Enterprise", 999.0, 140.0),
]
PLAN_DISTRIBUTION = [0.45, 0.30, 0.18, 0.07]

TIERS = ["Standard", "Pro", "Enterprise"]
TIER_DISTRIBUTION = [0.55, 0.32, 0.13]

INDUSTRIES = ["SaaS", "FinTech", "HealthTech", "E-Commerce", "Logistics", "Media"]

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
]

COMPANIES = [
    "Apex Global", "Beacon Innovations", "Crestline Systems", "Delta Dynamics",
    "Echo Analytics", "Frontier Data", "Genesis Software", "Horizon Tech",
    "Ironclad Solutions", "Jupiter Cloud", "Krypton Labs", "Luminary Corp",
    "Matrix Networks", "Nexus Platforms", "Omega Operations", "Pulse Media",
    "Quantum Ventures", "Radiant Systems", "Stratosphere Cloud", "Titan Industrial",
    "Unified Logistics", "Vertex AI", "Waypoint Digital", "Xenon Labs",
]


class SyntheticDataGenerator:
    """Configurable synthetic data generator for RetentionIQ.

    Generates 10 relational entities and isolated ground-truth churn outcomes
    with guaranteed reproducibility using fixed random seed (20261022).
    """

    def __init__(self, num_customers: int = 1000, months: int = 18, seed: int = DEFAULT_SEED):
        self.num_customers = num_customers
        self.months = months
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.py_rng = random.Random(seed)

        # Baseline dates: exact 18 calendar months spanning from 2025-01 to 2026-06
        self.month_dates = []
        for i in range(self.months):
            y = 2025 + (i // 12)
            m = 1 + (i % 12)
            self.month_dates.append(datetime(y, m, 1))
        # Cutoff date for prediction horizon: Month 17 (e.g. May 31, 2026)
        self.cutoff_date = datetime(2026, 5, 31, 23, 59, 59)
        self.observation_end_date = datetime(2026, 6, 30, 23, 59, 59)

        # Container datasets
        self.customers: List[Dict] = []
        self.subscriptions: List[Dict] = []
        self.usage_snapshots: List[Dict] = []
        self.billing_events: List[Dict] = []
        self.support_cases: List[Dict] = []
        self.offers: List[Dict] = []
        self.eligibility_rules: List[Dict] = []
        self.campaign_contacts: List[Dict] = []
        self.churn_outcomes: List[Dict] = []
        self.retention_outcomes: List[Dict] = []

    def generate_all(self) -> Dict[str, pd.DataFrame]:
        """Generate all datasets sequentially preserving parent-child integrity."""
        print(f"[SyntheticGenerator] Initializing generation for {self.num_customers:,} customers across {self.months} months (Seed: {self.seed})...")

        self._generate_catalog_offers()
        self._generate_customers_and_subscriptions()
        self._generate_monthly_telemetry_and_churn()
        self._generate_campaigns_and_experiments()

        datasets = {
            "customers": pd.DataFrame(self.customers),
            "subscriptions": pd.DataFrame(self.subscriptions),
            "usage_snapshots": pd.DataFrame(self.usage_snapshots),
            "billing_events": pd.DataFrame(self.billing_events),
            "support_cases": pd.DataFrame(self.support_cases),
            "offers": pd.DataFrame(self.offers),
            "eligibility_rules": pd.DataFrame(self.eligibility_rules),
            "campaign_contacts": pd.DataFrame(self.campaign_contacts),
            "churn_outcomes": pd.DataFrame(self.churn_outcomes),
            "retention_outcomes": pd.DataFrame(self.retention_outcomes),
        }

        print(f"[SyntheticGenerator] Generation complete. Generated records:")
        for name, df in datasets.items():
            print(f"  - {name}: {len(df):,} records")

        return datasets

    def _generate_catalog_offers(self):
        """Create standard catalog retention offers and eligibility rules."""
        catalog = [
            {
                "offer_id": "OFF-2026-000001",
                "offer_name": "Executive 20% Retention Credit",
                "offer_type": "Discount",
                "discount_pct": 20.0,
                "discount_amount": 0.0,
                "max_offer_cost": 200.0,
                "eligible_plans": "Growth,Scale,Enterprise",
                "min_tenure_months": 3,
                "min_subscription_mrr": 100.0,
                "max_discount_cap": 250.0,
                "valid_from": datetime(2026, 1, 1),
                "valid_to": datetime(2026, 12, 31),
                "status": "Active",
                "rules": [
                    ("MIN_TENURE", "tenure_months", "GTE", "3", 0.20),
                    ("MIN_MRR", "subscription_mrr", "GTE", "100.0", 0.20),
                    ("RISK_TIER", "risk_category", "IN", "High,Critical", 0.20),
                ],
            },
            {
                "offer_id": "OFF-2026-000002",
                "offer_name": "Free 1-Month Loyalty Relief",
                "offer_type": "Free_Month",
                "discount_pct": 100.0,
                "discount_amount": 0.0,
                "max_offer_cost": 150.0,
                "eligible_plans": "Starter,Growth",
                "min_tenure_months": 6,
                "min_subscription_mrr": 49.0,
                "max_discount_cap": 149.0,
                "valid_from": datetime(2026, 1, 1),
                "valid_to": datetime(2026, 12, 31),
                "status": "Active",
                "rules": [
                    ("MIN_TENURE", "tenure_months", "GTE", "6", 0.15),
                    ("RISK_TIER", "risk_category", "IN", "Medium,High,Critical", 0.15),
                ],
            },
            {
                "offer_id": "OFF-2026-000003",
                "offer_name": "Scale Tier Upgrade Incentive",
                "offer_type": "Tier_Upgrade",
                "discount_pct": 30.0,
                "discount_amount": 0.0,
                "max_offer_cost": 120.0,
                "eligible_plans": "Growth",
                "min_tenure_months": 4,
                "min_subscription_mrr": 149.0,
                "max_discount_cap": 120.0,
                "valid_from": datetime(2026, 1, 1),
                "valid_to": datetime(2026, 12, 31),
                "status": "Active",
                "rules": [
                    ("MIN_TENURE", "tenure_months", "GTE", "4", 0.25),
                    ("MARGIN_THRESHOLD", "unit_margin", "GTE", "0.25", 0.25),
                ],
            },
            {
                "offer_id": "OFF-2026-000004",
                "offer_name": "Feature Addon Booster Pack",
                "offer_type": "Feature_Addon",
                "discount_pct": 0.0,
                "discount_amount": 50.0,
                "max_offer_cost": 50.0,
                "eligible_plans": "Starter,Growth,Scale,Enterprise",
                "min_tenure_months": 1,
                "min_subscription_mrr": 49.0,
                "max_discount_cap": 50.0,
                "valid_from": datetime(2026, 1, 1),
                "valid_to": datetime(2026, 12, 31),
                "status": "Active",
                "rules": [
                    ("MIN_TENURE", "tenure_months", "GTE", "1", 0.10),
                ],
            },
        ]

        rule_counter = 1
        for off in catalog:
            rules = off.pop("rules")
            off["created_at"] = datetime(2025, 1, 1)
            self.offers.append(off)

            for r_code, param, op, val, margin in rules:
                rule_id = f"RUL-{off['offer_id']}-{rule_counter:02d}"
                rule_counter += 1
                self.eligibility_rules.append({
                    "rule_id": rule_id,
                    "offer_id": off["offer_id"],
                    "rule_code": r_code,
                    "parameter_name": param,
                    "operator": op,
                    "parameter_value": val,
                    "margin_threshold_pct": margin,
                    "is_active": True,
                    "created_at": datetime(2025, 1, 1),
                })

    def _generate_customers_and_subscriptions(self):
        """Generate master Customer and Subscription entities."""
        # Distribute signup months across the first 12 months (or months 1 to 14) so they have history
        signup_month_indices = self.rng.integers(0, min(12, self.months), size=self.num_customers)

        # Behavioral archetypes:
        # 0: Healthy/Loyal (72%)
        # 1: At-Risk Voluntary (Declining Usage) (14%)
        # 2: At-Risk Involuntary (Payment Failures) (7%)
        # 3: High Support Friction (7%)
        archetype_probs = [0.72, 0.14, 0.07, 0.07]
        self.archetypes = self.rng.choice([0, 1, 2, 3], size=self.num_customers, p=archetype_probs)

        # Plan assignments
        plan_indices = self.rng.choice(len(PLANS), size=self.num_customers, p=PLAN_DISTRIBUTION)
        tier_indices = self.rng.choice(len(TIERS), size=self.num_customers, p=TIER_DISTRIBUTION)

        for i in range(self.num_customers):
            cust_id = f"CUS-{i + 1:06d}"
            first_name = FIRST_NAMES[i % len(FIRST_NAMES)]
            last_name = LAST_NAMES[(i * 7) % len(LAST_NAMES)]
            company = f"{COMPANIES[i % len(COMPANIES)]} {i + 1}"
            industry = INDUSTRIES[i % len(INDUSTRIES)]
            tier = TIERS[tier_indices[i]]

            m_idx = signup_month_indices[i]
            signup_date = self.month_dates[m_idx] + timedelta(days=int(self.rng.integers(0, 20)))
            cohort_month = signup_date.strftime("%Y-%m")

            customer_rec = {
                "customer_id": cust_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": f"contact.{i+1}@{company.lower().replace(' ', '')}.com",
                "company_name": company,
                "industry": industry,
                "customer_tier": tier,
                "cohort_month": cohort_month,
                "signup_date": signup_date,
                "created_at": signup_date,
                "updated_at": signup_date,
            }
            self.customers.append(customer_rec)

            # Subscription
            sub_id = f"SUB-{cust_id}-01"
            p_name, base_mrr, unit_cost = PLANS[plan_indices[i]]
            billing_cycle = "Annual" if self.rng.random() < 0.20 else "Monthly"

            sub_rec = {
                "subscription_id": sub_id,
                "customer_id": cust_id,
                "plan_name": p_name,
                "billing_cycle": billing_cycle,
                "mrr": float(base_mrr),
                "unit_cost": float(unit_cost),
                "status": "Active",
                "start_date": signup_date,
                "end_date": None,
                "trial_end_date": signup_date + timedelta(days=14),
                "canceled_at": None,
                "churn_reason": "None",
                "plan_change_count": 0,
                "created_at": signup_date,
                "updated_at": signup_date,
                # internal tracking:
                "_signup_month_idx": m_idx,
                "_archetype": self.archetypes[i],
            }
            self.subscriptions.append(sub_rec)

    def _generate_monthly_telemetry_and_churn(self):
        """Simulate monthly usage, billing, support tickets, and correlated churn."""
        case_counter = 1

        for i, sub in enumerate(self.subscriptions):
            cust_id = sub["customer_id"]
            sub_id = sub["subscription_id"]
            signup_idx = sub["_signup_month_idx"]
            archetype = sub["_archetype"]
            plan_name = sub["plan_name"]
            mrr = sub["mrr"]

            # Baseline activity levels by plan
            if plan_name == "Starter":
                base_logins, base_sessions, base_apis = 15, 120.0, 500
            elif plan_name == "Growth":
                base_logins, base_sessions, base_apis = 40, 450.0, 3000
            elif plan_name == "Scale":
                base_logins, base_sessions, base_apis = 90, 1100.0, 12000
            else:  # Enterprise
                base_logins, base_sessions, base_apis = 220, 2800.0, 50000

            # Determine if and when customer churns
            # Bounded between 5% and 20% overall (archetypes 1, 2, 3 have higher churn probability)
            will_churn = False
            churn_month_idx = None
            churn_reason = "None"
            primary_driver = "None"

            churn_dice = self.rng.random()
            if archetype == 1 and churn_dice < 0.50:  # Voluntary usage decline
                will_churn = True
                low_m = min(self.months - 1, max(signup_idx + 2, int(self.months * 0.5)))
                churn_month_idx = int(self.rng.integers(low_m, self.months)) if low_m < self.months else self.months - 1
                churn_reason = "Voluntary"
                primary_driver = "Usage_Drop"
            elif archetype == 2 and churn_dice < 0.50:  # Involuntary payment failure
                will_churn = True
                low_m = min(self.months - 1, max(signup_idx + 2, int(self.months * 0.55)))
                churn_month_idx = int(self.rng.integers(low_m, self.months)) if low_m < self.months else self.months - 1
                churn_reason = "Involuntary"
                primary_driver = "Payment_Failure"
            elif archetype == 3 and churn_dice < 0.40:  # Support frustration
                will_churn = True
                low_m = min(self.months - 1, max(signup_idx + 2, int(self.months * 0.55)))
                churn_month_idx = int(self.rng.integers(low_m, self.months)) if low_m < self.months else self.months - 1
                churn_reason = "Voluntary"
                primary_driver = "Support_Frustration"
            elif archetype == 0 and churn_dice < 0.01:  # Rare healthy voluntary churn
                will_churn = True
                low_m = min(self.months - 1, max(signup_idx + 3, int(self.months * 0.6)))
                churn_month_idx = int(self.rng.integers(low_m, self.months)) if low_m < self.months else self.months - 1
                churn_reason = "Voluntary"
                primary_driver = "Competitor"

            # Simulate monthly records from signup up to churn or end of period
            last_active_m_idx = churn_month_idx if will_churn else self.months - 1

            prev_events = base_logins
            for m_idx in range(signup_idx, last_active_m_idx + 1):
                m_date = self.month_dates[m_idx]
                month_str = m_date.strftime("%Y-%m")
                tenure_months = m_idx - signup_idx

                # Compute behavioral trajectory
                if will_churn and (last_active_m_idx - m_idx) <= 3:
                    # Degrading metrics near churn
                    decline_factor = max(0.15, (last_active_m_idx - m_idx + 0.5) / 4.0)
                    active_days = max(1, int(self.rng.integers(2, 8) * decline_factor))
                    logins = max(1, int(base_logins * decline_factor * self.rng.uniform(0.7, 1.1)))
                    session_mins = max(10.0, float(base_sessions * decline_factor * self.rng.uniform(0.7, 1.1)))
                    api_calls = max(10, int(base_apis * decline_factor * self.rng.uniform(0.7, 1.1)))
                    utilization = max(5.0, 75.0 * decline_factor)
                else:
                    # Normal or growing metrics
                    tenure_growth = min(1.4, 1.0 + (tenure_months * 0.02))
                    noise = self.rng.uniform(0.85, 1.15)
                    active_days = min(28, int(self.rng.integers(12, 26)))
                    logins = int(base_logins * tenure_growth * noise)
                    session_mins = float(base_sessions * tenure_growth * noise)
                    api_calls = int(base_apis * tenure_growth * noise)
                    utilization = float(min(98.0, 65.0 * tenure_growth * noise))

                # Usage decline % relative to prior month
                usage_decline = ((prev_events - logins) / prev_events * 100.0) if prev_events > 0 else 0.0
                prev_events = logins

                # 1. Usage Snapshot
                snap_id = f"SNAP-{sub_id}-{month_str}"
                self.usage_snapshots.append({
                    "snapshot_id": snap_id,
                    "subscription_id": sub_id,
                    "snapshot_month": month_str,
                    "snapshot_date": m_date + timedelta(days=27),
                    "active_days": active_days,
                    "login_count": logins,
                    "total_session_minutes": round(session_mins, 1),
                    "feature_events_count": int(logins * self.rng.uniform(2.5, 4.5)),
                    "api_call_count": api_calls,
                    "license_utilization_pct": round(utilization, 1),
                    "usage_decline_pct": round(usage_decline, 1),
                    "created_at": m_date + timedelta(days=28),
                })

                # 2. Billing Event
                bill_id = f"BIL-{cust_id}-{m_date.strftime('%Y%m')}"
                bill_date = m_date + timedelta(days=1)
                due_date = bill_date + timedelta(days=7)

                # Billing status logic
                is_failed_month = will_churn and (churn_reason == "Involuntary") and (m_idx == last_active_m_idx)
                if is_failed_month:
                    b_status = "Failed"
                    retries = int(self.rng.integers(2, 4))
                    paid = 0.0
                    reason = self.py_rng.choice(["Insufficient_Funds", "Expired_Card", "Bank_Reject"])
                else:
                    b_status = "Paid"
                    retries = 0 if self.rng.random() < 0.93 else 1
                    paid = mrr
                    reason = "None"

                self.billing_events.append({
                    "billing_id": bill_id,
                    "subscription_id": sub_id,
                    "billing_date": bill_date,
                    "due_date": due_date,
                    "invoice_amount": float(mrr),
                    "paid_amount": float(paid),
                    "status": b_status,
                    "retry_count": retries,
                    "failure_reason": reason,
                    "created_at": bill_date,
                })

                # 3. Support Cases (stochastic, correlated with archetype)
                case_prob = 0.08
                if archetype == 3:  # High friction
                    case_prob = 0.40
                elif will_churn and (last_active_m_idx - m_idx) <= 2:
                    case_prob = 0.30

                if self.rng.random() < case_prob:
                    case_id = f"CAS-{cust_id}-{case_counter:03d}"
                    case_counter += 1
                    category = self.py_rng.choice(["Billing", "Technical", "Product_Bug", "Feature_Request", "Account"])
                    priority = "Critical" if archetype == 3 and self.rng.random() < 0.4 else self.py_rng.choice(["Low", "Medium", "High"])
                    opened_dt = m_date + timedelta(days=int(self.rng.integers(2, 25)))

                    if archetype == 3 and self.rng.random() < 0.4:
                        res_hours = float(self.rng.uniform(72.0, 180.0))
                        csat = int(self.rng.integers(1, 3))
                        escalations = int(self.rng.integers(1, 3))
                        c_status = "Resolved" if self.rng.random() < 0.7 else "Escalated"
                    else:
                        res_hours = float(self.rng.uniform(2.0, 24.0))
                        csat = int(self.rng.integers(4, 6))
                        escalations = 0
                        c_status = "Resolved"

                    self.support_cases.append({
                        "case_id": case_id,
                        "customer_id": cust_id,
                        "category": category,
                        "priority": priority,
                        "status": c_status,
                        "opened_at": opened_dt,
                        "resolved_at": opened_dt + timedelta(hours=res_hours) if c_status == "Resolved" else None,
                        "resolution_hours": round(res_hours, 1) if c_status == "Resolved" else None,
                        "escalation_count": escalations,
                        "csat_score": csat,
                        "created_at": opened_dt,
                    })

            # Update subscription status if churned
            if will_churn:
                churn_dt = self.month_dates[churn_month_idx] + timedelta(days=int(self.rng.integers(10, 27)))
                sub["status"] = "Canceled"
                sub["canceled_at"] = churn_dt
                sub["end_date"] = churn_dt
                sub["churn_reason"] = churn_reason
                sub["updated_at"] = churn_dt

            # 4. Generate Ground Truth ChurnOutcome record at prediction cutoff (Month 17: 2026-05-31)
            # Was customer active on cutoff date, and did they churn in 30-day window (Month 18: June 2026)?
            is_active_at_cutoff = (not will_churn) or (sub["canceled_at"] > self.cutoff_date)
            churned_in_horizon = will_churn and (self.cutoff_date < sub["canceled_at"] <= self.observation_end_date)

            churn_id = f"CHURN-{cust_id}-2026"
            self.churn_outcomes.append({
                "churn_id": churn_id,
                "customer_id": cust_id,
                "subscription_id": sub_id,
                "prediction_cutoff_date": self.cutoff_date,
                "observation_window_start": self.cutoff_date,
                "observation_window_end": self.observation_end_date,
                "actual_churned": bool(churned_in_horizon),
                "actual_churn_date": sub["canceled_at"] if churned_in_horizon else None,
                "churn_type": churn_reason if churned_in_horizon else "Retained",
                "primary_churn_driver": primary_driver if churned_in_horizon else "None",
                "is_ground_truth": True,
                "created_at": self.observation_end_date,
            })

        # Remove internal generator tracking fields from subscriptions
        for sub in self.subscriptions:
            sub.pop("_signup_month_idx", None)
            sub.pop("_archetype", None)

    def _generate_campaigns_and_experiments(self):
        """Generate historical randomized retention campaigns and outcome measurements."""
        campaign_dt = datetime(2026, 4, 15, 10, 0, 0)
        exp_id = "EXP-2026-Q1-RET"
        contact_counter = 1

        # Candidate pool: active customers around Month 15/16 with elevated risk
        # Pick ~25% of eligible customer base
        eligible_subs = [s for s in self.subscriptions if s["status"] == "Active"]
        target_count = min(len(eligible_subs), max(50, int(len(eligible_subs) * 0.25)))

        selected_subs = self.py_rng.sample(eligible_subs, target_count)
        # Sort deterministically
        selected_subs.sort(key=lambda x: x["customer_id"])

        for i, sub in enumerate(selected_subs):
            cust_id = sub["customer_id"]
            plan = sub["plan_name"]
            contact_id = f"CAM-2026-{contact_counter:06d}"
            contact_counter += 1

            # 50/50 Stratified Treatment / Control Allocation
            group = "Treatment" if (i % 2 == 0) else "Control"
            stratum = f"Plan:{plan}"

            # Offer assignment for treatment
            offer_id = "OFF-2026-000001" if group == "Treatment" else None
            status = "Accepted" if group == "Treatment" and (self.rng.random() < 0.65) else (
                "Ignored" if group == "Treatment" else "Pending"
            )

            contact = {
                "contact_id": contact_id,
                "experiment_id": exp_id,
                "customer_id": cust_id,
                "offer_id": offer_id,
                "experiment_group": group,
                "stratum_id": stratum,
                "assigned_at": campaign_dt,
                "delivery_date": campaign_dt + timedelta(hours=2) if group == "Treatment" else None,
                "delivery_channel": "Email",
                "delivery_status": "Delivered" if group == "Treatment" else "Suppressed",
                "is_eligible": True,
                "eligibility_notes": "Passed all tenure, MRR, and margin gates.",
                "response_date": campaign_dt + timedelta(days=2) if status == "Accepted" else None,
                "response_status": status,
                "created_at": campaign_dt,
            }
            self.campaign_contacts.append(contact)

            # Retention Outcome Tracking
            # Treatment with accepted offer has 30% higher retention than control
            churn_rec = next((c for c in self.churn_outcomes if c["customer_id"] == cust_id), None)
            baseline_churned = churn_rec["actual_churned"] if churn_rec else False

            if group == "Treatment" and status == "Accepted":
                retained = not baseline_churned or (self.rng.random() < 0.40)  # Causal rescue
                cost = 40.0
            else:
                retained = not baseline_churned
                cost = 0.0

            incremental_rev = sub["mrr"] if retained else 0.0
            net_val = incremental_rev - cost

            ret_id = f"RET-{contact_id}"
            self.retention_outcomes.append({
                "retention_id": ret_id,
                "contact_id": contact_id,
                "customer_id": cust_id,
                "churn_id": churn_rec["churn_id"] if churn_rec else None,
                "retained_after_horizon": retained,
                "days_retained": 30 if retained else int(self.rng.integers(5, 20)),
                "incremental_revenue": round(incremental_rev, 2),
                "offer_cost_incurred": round(cost, 2),
                "net_campaign_value": round(net_val, 2),
                "attribution_status": "Primary_Attributed",
                "evaluated_at": self.observation_end_date,
                "created_at": self.observation_end_date,
            })

    def save_to_database(self, engine):
        """Persist generated datasets to SQLite / MySQL database in bulk."""
        print("[SyntheticGenerator] Persisting records to database...")
        from app.models import init_db
        init_db(engine)

        # Insert in parent-first sequence
        table_order = [
            ("offers", self.offers),
            ("eligibility_rules", self.eligibility_rules),
            ("customers", self.customers),
            ("subscriptions", self.subscriptions),
            ("usage_snapshots", self.usage_snapshots),
            ("billing_events", self.billing_events),
            ("support_cases", self.support_cases),
            ("campaign_contacts", self.campaign_contacts),
            ("churn_outcomes", self.churn_outcomes),
            ("retention_outcomes", self.retention_outcomes),
        ]

        with engine.begin() as conn:
            for tbl_name, records in table_order:
                if records:
                    df = pd.DataFrame(records)
                    df.to_sql(tbl_name, con=conn, if_exists="append", index=False)
                    print(f"  [DB] Inserted {len(records):,} rows into '{tbl_name}'")

    def export_to_files(self, base_dir: str) -> Dict[str, str]:
        """Export datasets to CSV, JSON, and Ground Truth directories, returning checksums."""
        gen_dir = os.path.join(base_dir, "data", "generated")
        exp_dir = os.path.join(base_dir, "data", "exports")
        gt_dir = os.path.join(base_dir, "data", "ground_truth")

        for d in [gen_dir, exp_dir, gt_dir]:
            os.makedirs(d, exist_ok=True)

        datasets = {
            "customers": self.customers,
            "subscriptions": self.subscriptions,
            "usage_snapshots": self.usage_snapshots,
            "billing_events": self.billing_events,
            "support_cases": self.support_cases,
            "offers": self.offers,
            "eligibility_rules": self.eligibility_rules,
            "campaign_contacts": self.campaign_contacts,
            "churn_outcomes": self.churn_outcomes,
            "retention_outcomes": self.retention_outcomes,
        }

        checksums = {}

        for name, data in datasets.items():
            df = pd.DataFrame(data)

            # Export to CSV
            csv_path = os.path.join(gen_dir, f"{name}.csv")
            df.to_csv(csv_path, index=False)

            # Compute SHA-256
            hasher = hashlib.sha256()
            with open(csv_path, "rb") as f:
                hasher.update(f.read())
            checksums[f"{name}.csv"] = hasher.hexdigest()

            # Export to JSON
            json_path = os.path.join(gen_dir, f"{name}.json")
            # Convert datetimes to string
            df_json = df.copy()
            for col in df_json.columns:
                if pd.api.types.is_datetime64_any_dtype(df_json[col]):
                    df_json[col] = df_json[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(df_json.to_dict(orient="records"), f, indent=2)

        # Isolated Ground Truth exports (Section 9 & 10 requirement)
        gt_df = pd.DataFrame(self.churn_outcomes)
        gt_csv = os.path.join(gt_dir, "ground_truth.csv")
        gt_json = os.path.join(gt_dir, "ground_truth.json")
        gt_df.to_csv(gt_csv, index=False)
        gt_df_json = gt_df.copy()
        for col in gt_df_json.columns:
            if pd.api.types.is_datetime64_any_dtype(gt_df_json[col]):
                gt_df_json[col] = gt_df_json[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        with open(gt_json, "w", encoding="utf-8") as f:
            json.dump(gt_df_json.to_dict(orient="records"), f, indent=2)

        # Save checksum manifest
        manifest_path = os.path.join(exp_dir, "manifest.json")
        manifest_payload = {
            "seed": self.seed,
            "num_customers": self.num_customers,
            "months": self.months,
            "generated_at": datetime.now().isoformat(),
            "checksums": checksums,
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_payload, f, indent=2)

        return checksums
