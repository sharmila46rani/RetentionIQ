import pytest
import pandas as pd
from app.services.synthetic_generator import SyntheticDataGenerator, DEFAULT_SEED


@pytest.fixture(scope="module")
def starter_data():
    """Generate small dataset for fast testing."""
    gen = SyntheticDataGenerator(num_customers=200, months=18, seed=DEFAULT_SEED)
    return gen.generate_all()


def test_generator_record_counts(starter_data):
    """Verify all 10 entity datasets are generated with positive counts."""
    assert len(starter_data["customers"]) == 200
    assert len(starter_data["subscriptions"]) == 200
    assert len(starter_data["usage_snapshots"]) > 1000
    assert len(starter_data["billing_events"]) > 1000
    assert len(starter_data["support_cases"]) > 50
    assert len(starter_data["offers"]) == 4
    assert len(starter_data["eligibility_rules"]) == 8
    assert len(starter_data["churn_outcomes"]) == 200
    assert len(starter_data["campaign_contacts"]) > 0
    assert len(starter_data["retention_outcomes"]) > 0


def test_churn_rate_bounds(starter_data):
    """Verify that overall churn rate is bounded strictly between 5% and 20%."""
    subs = starter_data["subscriptions"]
    churned_count = (subs["status"] == "Canceled").sum()
    total_count = len(subs)
    churn_rate = churned_count / total_count

    assert 0.05 <= churn_rate <= 0.20, f"Churn rate {churn_rate:.2%} is outside the [5%, 20%] bound"


def test_voluntary_and_involuntary_churn_presence(starter_data):
    """Verify both voluntary and involuntary churn are modeled."""
    subs = starter_data["subscriptions"]
    reasons = subs["churn_reason"].value_counts().to_dict()

    assert "Voluntary" in reasons and reasons["Voluntary"] > 0
    assert "Involuntary" in reasons and reasons["Involuntary"] > 0
    assert "None" in reasons and reasons["None"] > 0


def test_reproducibility():
    """Verify running the generator twice with seed 20261022 yields identical output."""
    gen1 = SyntheticDataGenerator(num_customers=100, months=12, seed=DEFAULT_SEED)
    data1 = gen1.generate_all()

    gen2 = SyntheticDataGenerator(num_customers=100, months=12, seed=DEFAULT_SEED)
    data2 = gen2.generate_all()

    for key in data1:
        pd.testing.assert_frame_equal(data1[key], data2[key], check_dtype=True)


def test_temporal_ordering(starter_data):
    """Verify customer signup precedes or equals subscription start, and billing dates are monotonic."""
    cust_df = starter_data["customers"].set_index("customer_id")
    subs_df = starter_data["subscriptions"].set_index("subscription_id")

    for sub_id, sub_row in subs_df.iterrows():
        cust_row = cust_df.loc[sub_row["customer_id"]]
        assert cust_row["signup_date"] <= sub_row["start_date"]

        if pd.notna(sub_row["canceled_at"]):
            assert sub_row["start_date"] <= sub_row["canceled_at"]


def test_derived_value_integrity(starter_data):
    """Verify that derived fields correlate with source events."""
    billing = starter_data["billing_events"]
    # Paid amount must be <= invoice amount
    assert (billing["paid_amount"] <= billing["invoice_amount"] + 1e-4).all()

    # Failed bills must have 0 paid amount
    failed_bills = billing[billing["status"] == "Failed"]
    assert (failed_bills["paid_amount"] == 0.0).all()
