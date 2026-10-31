import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.models.base import Base, validate_id, CUSTOMER_ID_REGEX
from app.models.customer import Customer
from app.models.subscription import Subscription
from app.models.usage import UsageSnapshot
from app.models.billing import BillingEvent
from app.models.support import SupportCase
from app.models.offer import Offer
from app.models.eligibility import EligibilityRule
from app.models.campaign import CampaignContact
from app.models.churn import ChurnOutcome
from app.models.retention import RetentionOutcome


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory SQLite database with foreign keys enabled for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


def test_id_regex_validation():
    """Test deterministic ID formatting rules and error handling."""
    # Valid customer ID
    assert validate_id("CUS-000001", CUSTOMER_ID_REGEX, "Customer") is True

    # Invalid customer IDs
    with pytest.raises(ValueError, match="Invalid Customer ID format"):
        validate_id("CUS-1", CUSTOMER_ID_REGEX, "Customer")

    with pytest.raises(ValueError, match="Invalid Customer ID format"):
        validate_id("CUSTOMER-000001", CUSTOMER_ID_REGEX, "Customer")


def test_customer_creation_and_properties(db_session):
    """Test Customer entity persistence and property getters."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customer = Customer(
        customer_id="CUS-000001",
        first_name="Alice",
        last_name="Smith",
        email="alice.smith@acme.inc",
        company_name="Acme Inc",
        industry="SaaS",
        customer_tier="Enterprise",
        cohort_month="2025-01",
        signup_date=now - timedelta(days=365),
    )
    db_session.add(customer)
    db_session.commit()

    retrieved = db_session.query(Customer).filter_by(customer_id="CUS-000001").first()
    assert retrieved is not None
    assert retrieved.full_name == "Alice Smith"
    assert retrieved.company_name == "Acme Inc"
    assert retrieved.email == "alice.smith@acme.inc"


def test_subscription_creation_and_margins(db_session):
    """Test Subscription entity, gross margin calculation, and customer relation."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customer = Customer(
        customer_id="CUS-000002",
        first_name="Bob",
        last_name="Jones",
        email="bob@techcorp.io",
        company_name="TechCorp",
        industry="FinTech",
        customer_tier="Pro",
        cohort_month="2025-06",
        signup_date=now - timedelta(days=180),
    )
    db_session.add(customer)
    db_session.commit()

    sub = Subscription(
        subscription_id="SUB-CUS-000002-01",
        customer_id="CUS-000002",
        plan_name="Growth",
        billing_cycle="Monthly",
        mrr=299.0,
        unit_cost=49.0,
        status="Active",
        start_date=now - timedelta(days=180),
    )
    db_session.add(sub)
    db_session.commit()

    assert sub.gross_margin == 250.0
    assert round(sub.margin_percentage, 2) == round((250.0 / 299.0) * 100.0, 2)
    assert len(customer.subscriptions) == 1
    assert customer.subscriptions[0].subscription_id == "SUB-CUS-000002-01"


def test_foreign_key_enforcement(db_session):
    """Test that creating a Subscription with non-existent customer_id raises IntegrityError."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sub = Subscription(
        subscription_id="SUB-CUS-999999-01",
        customer_id="CUS-999999",  # Non-existent
        plan_name="Starter",
        billing_cycle="Monthly",
        mrr=49.0,
        unit_cost=10.0,
        status="Active",
        start_date=now,
    )
    db_session.add(sub)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete(db_session):
    """Test that deleting a Customer cascades deletion to subscriptions and support cases."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customer = Customer(
        customer_id="CUS-000003",
        first_name="Charlie",
        last_name="Brown",
        email="charlie@peanuts.org",
        company_name="Peanuts Media",
        industry="Media",
        customer_tier="Standard",
        cohort_month="2025-03",
        signup_date=now - timedelta(days=200),
    )
    db_session.add(customer)
    db_session.commit()

    sub = Subscription(
        subscription_id="SUB-CUS-000003-01",
        customer_id="CUS-000003",
        plan_name="Starter",
        billing_cycle="Monthly",
        mrr=99.0,
        unit_cost=15.0,
        status="Active",
        start_date=now - timedelta(days=200),
    )
    case = SupportCase(
        case_id="CAS-CUS-000003-001",
        customer_id="CUS-000003",
        category="Technical",
        priority="High",
        status="Resolved",
        opened_at=now - timedelta(days=10),
        resolved_at=now - timedelta(days=9),
        resolution_hours=24.0,
        escalation_count=0,
        csat_score=5,
    )
    db_session.add_all([sub, case])
    db_session.commit()

    # Delete Customer
    db_session.delete(customer)
    db_session.commit()

    # Ensure cascading deletion removed sub and case
    assert db_session.query(Subscription).filter_by(subscription_id="SUB-CUS-000003-01").first() is None
    assert db_session.query(SupportCase).filter_by(case_id="CAS-CUS-000003-001").first() is None


def test_usage_snapshot_composite_uniqueness(db_session):
    """Test unique constraint on (subscription_id, snapshot_month)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customer = Customer(
        customer_id="CUS-000004",
        first_name="Dana",
        last_name="White",
        email="dana@ufc.com",
        company_name="UFC Sports",
        industry="Media",
        customer_tier="Enterprise",
        cohort_month="2025-01",
        signup_date=now - timedelta(days=100),
    )
    sub = Subscription(
        subscription_id="SUB-CUS-000004-01",
        customer_id="CUS-000004",
        plan_name="Enterprise",
        billing_cycle="Monthly",
        mrr=999.0,
        unit_cost=120.0,
        status="Active",
        start_date=now - timedelta(days=100),
    )
    snap1 = UsageSnapshot(
        snapshot_id="SNAP-SUB-CUS-000004-01-2026-01",
        subscription_id="SUB-CUS-000004-01",
        snapshot_month="2026-01",
        snapshot_date=now,
        active_days=20,
        login_count=45,
        total_session_minutes=900.0,
        feature_events_count=120,
        api_call_count=5000,
        license_utilization_pct=85.0,
        usage_decline_pct=0.0,
    )
    db_session.add_all([customer, sub, snap1])
    db_session.commit()

    # Duplicate record for the same subscription and month must fail composite unique constraint
    snap2 = UsageSnapshot(
        snapshot_id="SNAP-SUB-CUS-000004-02-2026-01",
        subscription_id="SUB-CUS-000004-01",
        snapshot_month="2026-01",
        snapshot_date=now,
        active_days=22,
    )
    db_session.add(snap2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_offer_eligibility_and_experiment_relationship(db_session):
    """Test Offer, EligibilityRule, CampaignContact, ChurnOutcome, and RetentionOutcome relationships."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Customer & Subscription
    customer = Customer(
        customer_id="CUS-000005",
        first_name="Eva",
        last_name="Green",
        email="eva@healthcorp.com",
        company_name="HealthCorp",
        industry="HealthTech",
        customer_tier="Enterprise",
        cohort_month="2025-01",
        signup_date=now - timedelta(days=300),
    )
    sub = Subscription(
        subscription_id="SUB-CUS-000005-01",
        customer_id="CUS-000005",
        plan_name="Scale",
        billing_cycle="Monthly",
        mrr=499.0,
        unit_cost=80.0,
        status="Active",
        start_date=now - timedelta(days=300),
    )
    # 2. Offer & Rule
    offer = Offer(
        offer_id="OFF-2026-000001",
        offer_name="Executive 20% Retention Credit",
        offer_type="Discount",
        discount_pct=20.0,
        discount_amount=0.0,
        max_offer_cost=100.0,
        eligible_plans="Scale,Enterprise",
        min_tenure_months=6,
        min_subscription_mrr=200.0,
        max_discount_cap=120.0,
        valid_from=now - timedelta(days=10),
        valid_to=now + timedelta(days=50),
        status="Active",
    )
    rule = EligibilityRule(
        rule_id="RUL-OFF-2026-000001-01",
        offer_id="OFF-2026-000001",
        rule_code="MIN_TENURE",
        parameter_name="tenure_months",
        operator="GTE",
        parameter_value="6",
        margin_threshold_pct=0.25,
        is_active=True,
    )
    # 3. Campaign Contact
    contact = CampaignContact(
        contact_id="CAM-2026-000001",
        experiment_id="EXP-2026-Q1-RET",
        customer_id="CUS-000005",
        offer_id="OFF-2026-000001",
        experiment_group="Treatment",
        stratum_id="Risk:High_Plan:Scale",
        assigned_at=now - timedelta(days=20),
        delivery_date=now - timedelta(days=20),
        delivery_channel="Email",
        delivery_status="Delivered",
        is_eligible=True,
        response_status="Accepted",
    )
    # 4. Churn Outcome Ground Truth
    churn = ChurnOutcome(
        churn_id="CHURN-CUS-000005-2026",
        customer_id="CUS-000005",
        subscription_id="SUB-CUS-000005-01",
        prediction_cutoff_date=now - timedelta(days=30),
        observation_window_start=now - timedelta(days=30),
        observation_window_end=now,
        actual_churned=False,
        churn_type="Retained",
        primary_churn_driver="None",
        is_ground_truth=True,
    )
    # 5. Retention Outcome
    retention = RetentionOutcome(
        retention_id="RET-CAM-2026-000001",
        contact_id="CAM-2026-000001",
        customer_id="CUS-000005",
        churn_id="CHURN-CUS-000005-2026",
        retained_after_horizon=True,
        days_retained=30,
        incremental_revenue=499.0,
        offer_cost_incurred=99.8,
        net_campaign_value=399.2,
        attribution_status="Primary_Attributed",
        evaluated_at=now,
    )

    db_session.add_all([customer, sub, offer, rule, contact, churn, retention])
    db_session.commit()

    # Verify relationships
    assert len(offer.eligibility_rules) == 1
    assert offer.eligibility_rules[0].rule_code == "MIN_TENURE"
    assert contact.customer.full_name == "Eva Green"
    assert contact.offer.offer_name == "Executive 20% Retention Credit"
    assert contact.retention_outcome.net_campaign_value == 399.2
    assert round(contact.retention_outcome.net_roi_percentage, 1) == 400.0


def test_experiment_customer_unique_constraint(db_session):
    """Test that a customer cannot be assigned multiple times to the same experiment."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customer = Customer(
        customer_id="CUS-000006",
        first_name="Frank",
        last_name="Underwood",
        email="frank@house.gov",
        company_name="House Gov",
        industry="Logistics",
        customer_tier="Standard",
        cohort_month="2025-01",
        signup_date=now,
    )
    db_session.add(customer)
    db_session.commit()

    contact1 = CampaignContact(
        contact_id="CAM-2026-000002",
        experiment_id="EXP-2026-Q1-RET",
        customer_id="CUS-000006",
        experiment_group="Treatment",
        stratum_id="Risk:Low",
        assigned_at=now,
    )
    db_session.add(contact1)
    db_session.commit()

    # Second contact for same customer in same experiment must violate uniqueness
    contact2 = CampaignContact(
        contact_id="CAM-2026-000003",
        experiment_id="EXP-2026-Q1-RET",
        customer_id="CUS-000006",
        experiment_group="Control",
        stratum_id="Risk:Low",
        assigned_at=now,
    )
    db_session.add(contact2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_subscription_negative_mrr_constraint(db_session):
    """Test that negative MRR violates the check constraint."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customer = Customer(
        customer_id="CUS-000007",
        first_name="George",
        last_name="Washington",
        email="george@founding.org",
        company_name="Mount Vernon",
        industry="Logistics",
        customer_tier="Standard",
        cohort_month="2025-01",
        signup_date=now,
    )
    db_session.add(customer)
    db_session.commit()

    sub = Subscription(
        subscription_id="SUB-CUS-000007-01",
        customer_id="CUS-000007",
        plan_name="Starter",
        billing_cycle="Monthly",
        mrr=-50.0,  # Invalid negative MRR
        unit_cost=10.0,
        status="Active",
        start_date=now,
    )
    db_session.add(sub)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_model_to_dict_serialization(db_session):
    """Test JSON/dict serialization for API readiness."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customer = Customer(
        customer_id="CUS-000008",
        first_name="Hannah",
        last_name="Arendt",
        email="hannah@philosophy.edu",
        company_name="Thinkers Club",
        industry="Media",
        customer_tier="Standard",
        cohort_month="2025-02",
        signup_date=now,
    )
    db_session.add(customer)
    db_session.commit()

    data = customer.to_dict()
    assert isinstance(data, dict)
    assert data["customer_id"] == "CUS-000008"
    assert data["first_name"] == "Hannah"
    assert "created_at" in data
    assert isinstance(data["created_at"], str)  # ISO-formatted datetime string
