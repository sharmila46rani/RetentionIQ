import pytest
from datetime import datetime, timezone, timedelta
from app.models.database import get_engine, get_db_session
from app.models import (
    Customer,
    Subscription,
    Offer,
    EligibilityRule,
    CampaignContact,
    ChurnOutcome,
    RetentionOutcome,
    utc_now,
)
from app.services.feature_engineering import FeatureEngineeringService
from app.services.eligibility_service import OfferEligibilityEngine, IneligibleCustomerException
from app.services.experiment_service import RandomizedExperimentEngine, ExperimentConflictException


@pytest.fixture(scope="function")
def db_session():
    """Retrieve clean session bound to database for each test."""
    engine = get_engine()
    session = get_db_session(engine)
    session.rollback()
    yield session
    session.rollback()
    session.close()


def test_edge_case_01_temporal_leakage_exclusion(db_session):
    """EC-01: Customers whose churn date precedes the prediction cutoff must be flagged and excluded."""
    cutoff = datetime(2026, 5, 31, 23, 59, 59)
    features_df, anomalies = FeatureEngineeringService.extract_customer_features(
        db_session,
        prediction_cutoff=cutoff,
        enforce_temporal_guard=True
    )

    # 1. Verify anomalies were recorded
    assert len(anomalies) > 0
    rule_codes = [a["rule_violated"] for a in anomalies]
    assert "EC-01: CHURN_PRECEDES_PREDICTION_DATE" in rule_codes

    # 2. Verify excluded customers are NOT in the active prediction features matrix
    churned_cust_ids = set(a["customer_id"] for a in anomalies)
    features_cust_ids = set(features_df["customer_id"])
    assert len(churned_cust_ids.intersection(features_cust_ids)) == 0, "Leaked prior churned customers found in features!"


def test_edge_case_02_ineligible_offer_dispatch(db_session):
    """EC-02: An offer dispatch attempted on an ineligible customer must raise IneligibleCustomerException."""
    engine = OfferEligibilityEngine(db_session)
    now = utc_now()

    # Clean up test records if present
    db_session.query(CampaignContact).filter_by(customer_id="CUS-009999").delete()
    db_session.query(Subscription).filter_by(customer_id="CUS-009999").delete()
    db_session.query(Customer).filter_by(customer_id="CUS-009999").delete()
    db_session.commit()

    # Create a fresh ineligible customer with 0 tenure
    bad_cust = Customer(
        customer_id="CUS-009999",
        first_name="Zero",
        last_name="Tenure",
        email=f"zero.tenure.{int(now.timestamp())}@test.org",
        company_name="Newbie Inc",
        industry="SaaS",
        customer_tier="Standard",
        cohort_month=now.strftime("%Y-%m"),
        signup_date=now - timedelta(days=2),  # 2 days tenure
    )
    bad_sub = Subscription(
        subscription_id="SUB-CUS-009999-01",
        customer_id="CUS-009999",
        plan_name="Starter",
        billing_cycle="Monthly",
        mrr=49.0,  # Below minimum $100 MRR for OFF-2026-000001
        unit_cost=10.0,
        status="Active",
        start_date=now - timedelta(days=2),
    )
    db_session.add_all([bad_cust, bad_sub])
    db_session.commit()

    # Attempt dispatch of executive offer (requires 3 months tenure and $100 MRR)
    with pytest.raises(IneligibleCustomerException) as exc_info:
        engine.dispatch_offer_with_guard(
            customer_id="CUS-009999",
            offer_id="OFF-2026-000001",
            experiment_id="EXP-EDGE-CASE-02",
            risk_category="Low"
        )

    err_msg = str(exc_info.value)
    assert "CUS-009999" in err_msg
    assert "OFF-2026-000001" in err_msg
    assert "MIN_TENURE" in err_msg or "MIN_MRR" in err_msg or "PLAN_INELIGIBLE" in err_msg


def test_edge_case_03_treatment_control_leakage(db_session):
    """EC-03: Attempting to assign a customer already assigned in an experiment must raise ExperimentConflictException."""
    engine = RandomizedExperimentEngine(db_session)
    now = utc_now()
    exp_id = "EXP-COLLISION-TEST"

    # Pick an active customer who is in the candidate pool
    active_sub = db_session.query(Subscription).filter_by(status="Active").first()
    assert active_sub is not None
    cid = active_sub.customer_id

    # Clean up test contact
    db_session.query(CampaignContact).filter_by(experiment_id=exp_id).delete()
    db_session.commit()

    contact1 = CampaignContact(
        contact_id="CAM-2026-999001",
        experiment_id=exp_id,
        customer_id=cid,
        offer_id="OFF-2026-000001",
        experiment_group="Treatment",
        stratum_id="Stratum:Test",
        assigned_at=now,
    )
    db_session.add(contact1)
    db_session.commit()

    # Launching experiment targeting same customer must detect collision
    with pytest.raises(ExperimentConflictException) as exc_info:
        engine.launch_experiment(
            experiment_id=exp_id,
            offer_id="OFF-2026-000001",
            target_risk_categories=["Low", "Medium", "High", "Critical"]
        )

    assert cid in str(exc_info.value)
    assert exp_id in str(exc_info.value)


def test_edge_case_04_multi_touch_attribution_resolution(db_session):
    """EC-04: Retained customers targeted by multiple offers must have ambiguous records flagged to prevent double counting."""
    now = utc_now()
    cid = "CUS-000002"

    # Clean up test contacts and retention outcomes
    db_session.query(RetentionOutcome).filter(
        RetentionOutcome.contact_id.in_(["CAM-2026-999002", "CAM-2026-999003"])
    ).delete()
    db_session.query(CampaignContact).filter(
        CampaignContact.contact_id.in_(["CAM-2026-999002", "CAM-2026-999003"])
    ).delete()
    db_session.commit()

    # Insert two contacts for the same customer
    c1 = CampaignContact(
        contact_id="CAM-2026-999002",
        experiment_id="EXP-MULTI-01",
        customer_id=cid,
        offer_id="OFF-2026-000001",
        experiment_group="Treatment",
        stratum_id="Stratum:Test",
        assigned_at=now - timedelta(days=20),
        delivery_status="Delivered",
    )
    c2 = CampaignContact(
        contact_id="CAM-2026-999003",
        experiment_id="EXP-MULTI-02",
        customer_id=cid,
        offer_id="OFF-2026-000002",
        experiment_group="Treatment",
        stratum_id="Stratum:Test",
        assigned_at=now - timedelta(days=5),
        delivery_status="Delivered",
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    engine = RandomizedExperimentEngine(db_session)
    res1 = engine.evaluate_retention_outcomes_with_attribution("EXP-MULTI-01")
    res2 = engine.evaluate_retention_outcomes_with_attribution("EXP-MULTI-02")

    # Fetch outcomes
    r1 = db_session.query(RetentionOutcome).filter_by(contact_id="CAM-2026-999002").first()
    r2 = db_session.query(RetentionOutcome).filter_by(contact_id="CAM-2026-999003").first()

    assert r1 is not None
    assert r2 is not None

    # One should be primary, the other multi-attributed flagged
    statuses = {r1.attribution_status, r2.attribution_status}
    assert "Multi_Attributed_Flagged" in statuses, "Expected Multi_Attributed_Flagged policy flag"
