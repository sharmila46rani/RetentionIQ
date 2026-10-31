import pytest
from datetime import datetime
from app.models.database import get_engine, get_db_session
from app.services.feature_engineering import FeatureEngineeringService
from app.services.churn_prediction import ChurnPredictionService, RuleBasedScoringEngine


@pytest.fixture(scope="module")
def db_session():
    """Retrieve session bound to populated database."""
    engine = get_engine()
    session = get_db_session(engine)
    yield session
    session.close()


def test_feature_engineering_extraction(db_session):
    """Test feature engineering returns expected columns and customer counts."""
    cutoff = datetime(2026, 5, 31, 23, 59, 59)
    features_df, anomalies = FeatureEngineeringService.extract_customer_features(
        db_session, prediction_cutoff=cutoff, enforce_temporal_guard=True
    )

    assert not features_df.empty
    assert "customer_id" in features_df.columns
    assert "mrr" in features_df.columns
    assert "recent_active_days" in features_df.columns
    assert "billing_fail_count" in features_df.columns
    assert "unresolved_cases" in features_df.columns

    # Active customers should be positive and less than total customers (since churned were excluded)
    assert len(features_df) > 500


def test_edge_case_01_temporal_leakage_detection(db_session):
    """Test EC-01: Customers churned before cutoff date are detected and flagged in anomalies."""
    cutoff = datetime(2026, 5, 31, 23, 59, 59)
    _, anomalies = FeatureEngineeringService.extract_customer_features(
        db_session, prediction_cutoff=cutoff, enforce_temporal_guard=True
    )

    assert len(anomalies) > 0, "Expected prior churned customers to be detected as temporal anomalies"
    first_anomaly = anomalies[0]
    assert first_anomaly["rule_violated"] == "EC-01: CHURN_PRECEDES_PREDICTION_DATE"
    assert "Customer churned on" in first_anomaly["description"]


def test_rule_based_scoring_and_explainability(db_session):
    """Test rule-based scoring returns valid risk category, factors, and action."""
    service = ChurnPredictionService(db_session)
    cutoff = datetime(2026, 5, 31, 23, 59, 59)

    res = service.generate_predictions(prediction_cutoff=cutoff, model_type="RULE_BASED_BASELINE")

    assert res["model_type"] == "RULE_BASED_BASELINE"
    assert res["total_predicted"] > 0
    assert "risk_distribution" in res
    assert sum(res["risk_distribution"].values()) == res["total_predicted"]

    first_pred = res["predictions"][0]
    assert 0.0 <= first_pred["risk_score"] <= 1.0
    assert first_pred["risk_category"] in ["Low", "Medium", "High", "Critical"]
    assert len(first_pred["contributing_factors"]) >= 1
    assert len(first_pred["recommended_action"]) > 10


def test_ml_model_evaluation(db_session):
    """Test Supervised ML evaluation against ground truth on both rule-based baseline and genuine held-out temporal split."""
    service = ChurnPredictionService(db_session)
    cutoff = datetime(2026, 5, 31, 23, 59, 59)

    # 1. Rule-Based Baseline
    eval_rule = service.evaluate_model_performance(prediction_cutoff=cutoff, model_type="RULE_BASED_BASELINE")
    assert "precision" in eval_rule
    assert "recall" in eval_rule
    assert "f1_score" in eval_rule
    assert "confusion_matrix" in eval_rule
    assert eval_rule["sample_size"] > 0
    assert 0.0 <= eval_rule["roc_auc"] <= 1.0
    assert eval_rule["split_info"]["evaluation_mode"] == "FULL_COHORT_RULE_BASELINE"

    # 2. Supervised Random Forest on Held-Out Temporal Test Split
    eval_rf = service.evaluate_model_performance(prediction_cutoff=cutoff, model_type="RANDOM_FOREST")
    assert eval_rf["split_info"]["evaluation_mode"] == "TEMPORAL_HELD_OUT_TEST_SPLIT"
    assert eval_rf["split_info"]["train_sample_size"] > 0
    assert eval_rf["split_info"]["test_sample_size"] > 0
    assert 0.0 <= eval_rf["precision"] <= 1.0
    assert 0.0 <= eval_rf["recall"] <= 1.0
    assert 0.0 <= eval_rf["roc_auc"] <= 1.0

    # 3. Supervised Logistic Regression on Held-Out Temporal Test Split
    eval_lr = service.evaluate_model_performance(prediction_cutoff=cutoff, model_type="LOGISTIC_REGRESSION")
    assert eval_lr["split_info"]["evaluation_mode"] == "TEMPORAL_HELD_OUT_TEST_SPLIT"
    assert 0.0 <= eval_lr["roc_auc"] <= 1.0
