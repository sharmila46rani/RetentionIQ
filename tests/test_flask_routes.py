import pytest
from app.app import create_app


@pytest.fixture(scope="module")
def client():
    """Create test client using Flask app."""
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_dashboard_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Executive Dashboard" in res.data
    assert b"Active Subscribers" in res.data


def test_customers_routes(client):
    res = client.get("/customers/")
    assert res.status_code == 200
    assert b"Customer Management" in res.data

    res_detail = client.get("/customers/CUS-000001")
    assert res_detail.status_code == 200
    assert b"360" in res_detail.data


def test_predictions_route(client):
    res = client.get("/predictions/")
    assert res.status_code == 200
    assert b"Churn Risk" in res.data


def test_subscriptions_route(client):
    res = client.get("/subscriptions/")
    assert res.status_code == 200
    assert b"Subscription Management" in res.data


def test_usage_route(client):
    res = client.get("/usage")
    assert res.status_code == 200
    assert b"Usage Analytics" in res.data


def test_billing_route(client):
    res = client.get("/billing")
    assert res.status_code == 200
    assert b"Billing Analytics" in res.data


def test_support_route(client):
    res = client.get("/support")
    assert res.status_code == 200
    assert b"Support Case Analytics" in res.data


def test_offers_and_eligibility_routes(client):
    res_offers = client.get("/offers")
    assert res_offers.status_code == 200
    assert b"Retention Offer Catalog" in res_offers.data

    res_elig = client.get("/eligibility")
    assert res_elig.status_code == 200
    assert b"Offer Eligibility" in res_elig.data


def test_campaigns_and_experiments_routes(client):
    res_camp = client.get("/campaigns")
    assert res_camp.status_code == 200
    assert b"Campaign Management" in res_camp.data

    res_exp = client.get("/experiments")
    assert res_exp.status_code == 200
    assert b"Randomized Experiment" in res_exp.data

    res_out = client.get("/outcomes")
    assert res_out.status_code == 200
    assert b"Retention Outcomes" in res_out.data


def test_quality_and_governance_routes(client):
    res_qual = client.get("/quality/")
    assert res_qual.status_code == 200
    assert b"Data Quality" in res_qual.data

    res_gen = client.get("/generator/")
    assert res_gen.status_code == 200
    assert b"Synthetic Data Generator" in res_gen.data

    res_exp = client.get("/exports/")
    assert res_exp.status_code == 200
    assert b"Data Exports" in res_exp.data

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    assert b"System Documentation" in res_docs.data


def test_rest_apis(client):
    res = client.get("/api/v1/analytics/executive")
    assert res.status_code == 200
    json_data = res.get_json()
    assert "customer_kpis" in json_data
    assert "experiment_kpis" in json_data

    res_cust = client.get("/customers/api")
    assert res_cust.status_code == 200

    res_audit = client.get("/quality/api/audit")
    assert res_audit.status_code == 200
    audit_data = res_audit.get_json()
    assert audit_data["passed_checks"] == 13

    # Offers API
    res_offers = client.get("/api/v1/offers")
    assert res_offers.status_code == 200
    assert len(res_offers.get_json()["offers"]) > 0

    # Eligibility evaluation API
    res_eval = client.post(
        "/api/v1/eligibility/evaluate",
        json={"customer_id": "CUS-000001", "offer_id": "OFF-2026-000001", "risk_category": "High"},
    )
    assert res_eval.status_code == 200
    eval_json = res_eval.get_json()
    assert "is_eligible" in eval_json
    assert "passed_rules" in eval_json
    assert "violated_rules" in eval_json

    # Experiment API
    res_exp = client.get("/api/v1/experiments/EXP-2026-Q1-RET")
    assert res_exp.status_code == 200
    exp_json = res_exp.get_json()
    assert "absolute_incremental_lift" in exp_json
    assert "treatment_retention_rate" in exp_json


def test_model_selection_and_filters(client):
    # ML Models via UI
    res_rf = client.get("/predictions/?model_type=RANDOM_FOREST")
    assert res_rf.status_code == 200
    assert b"RANDOM_FOREST" in res_rf.data

    res_lr = client.get("/predictions/?model_type=LOGISTIC_REGRESSION")
    assert res_lr.status_code == 200
    assert b"LOGISTIC_REGRESSION" in res_lr.data

    # Customer filters
    res_cf = client.get("/customers/?industry=FinTech&tier=Enterprise")
    assert res_cf.status_code == 200

    # Subscription filters
    res_sf = client.get("/subscriptions/?plan=Enterprise&status=Active")
    assert res_sf.status_code == 200


def test_export_endpoints_and_security(client):
    # Manifest endpoint
    res_man = client.get("/exports/api/manifest")
    assert res_man.status_code == 200
    assert "checksums" in res_man.get_json()

    # Valid file download
    res_dl = client.get("/exports/download/csv/offers.csv")
    assert res_dl.status_code == 200

    # Directory traversal prevention
    res_bad = client.get("/exports/download/../../app/app.py")
    assert res_bad.status_code in [404, 400]
