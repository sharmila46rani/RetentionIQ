from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    precision_recall_curve,
)
from sqlalchemy.orm import Session

from app.services.feature_engineering import FeatureEngineeringService
from app.models import ChurnOutcome, Customer


FEATURE_COLUMNS = [
    "plan_code",
    "mrr",
    "tenure_months",
    "recent_active_days",
    "recent_logins",
    "recent_session_mins",
    "recent_decline_pct",
    "recent_utilization",
    "avg_active_3m",
    "avg_logins_3m",
    "billing_fail_count",
    "latest_bill_failed",
    "outstanding_balance",
    "total_cases",
    "unresolved_cases",
    "critical_cases",
    "avg_res_hours",
    "avg_csat",
]


class RuleBasedScoringEngine:
    """Transparent weighted heuristic scoring baseline."""

    @staticmethod
    def compute_score_and_factors(row: pd.Series) -> Tuple[float, str, List[str], str]:
        """Compute transparent risk score and human-interpretable factors."""
        factors = []

        # 1. Usage Component (35% weight)
        usage_risk = 0.0
        decline = row["recent_decline_pct"]
        active_days = row["recent_active_days"]

        if decline > 40.0:
            usage_risk += 0.65
            factors.append(f"Severe usage decline ({decline:.1f}% decrease in logins)")
        elif decline > 20.0:
            usage_risk += 0.35
            factors.append(f"Moderate usage drop ({decline:.1f}% decrease in logins)")

        if active_days <= 5:
            usage_risk += 0.35
            factors.append(f"Very low platform activity ({active_days} active days this month)")
        elif active_days <= 10:
            usage_risk += 0.15

        usage_risk = min(1.0, usage_risk)

        # 2. Billing Component (30% weight)
        billing_risk = 0.0
        fail_count = row["billing_fail_count"]
        latest_failed = row["latest_bill_failed"]
        balance = row["outstanding_balance"]

        if latest_failed == 1:
            billing_risk += 0.60
            factors.append("Latest invoice payment failed (delinquency risk)")
        if fail_count >= 2:
            billing_risk += 0.35
            factors.append(f"Repeated billing payment failures ({fail_count} failed charges)")
        elif fail_count == 1:
            billing_risk += 0.15

        if balance > 100.0:
            billing_risk += 0.15
            factors.append(f"Outstanding past-due balance (${balance:.2f})")

        billing_risk = min(1.0, billing_risk)

        # 3. Support Friction Component (20% weight)
        support_risk = 0.0
        unresolved = row["unresolved_cases"]
        critical = row["critical_cases"]
        csat = row["avg_csat"]

        if unresolved >= 2:
            support_risk += 0.40
            factors.append(f"Multiple unresolved support tickets ({unresolved} tickets open)")
        elif unresolved == 1:
            support_risk += 0.20

        if critical >= 1:
            support_risk += 0.40
            factors.append(f"Critical priority support escalation logged ({critical} tickets)")

        if csat < 3.0:
            support_risk += 0.30
            factors.append(f"Low satisfaction rating (CSAT: {csat:.1f}/5.0)")

        support_risk = min(1.0, support_risk)

        # 4. Tenure Component (15% weight)
        tenure_risk = 0.0
        tenure = row["tenure_months"]
        if tenure <= 2.0:
            tenure_risk = 0.60
            factors.append(f"High-vulnerability onboarding window (tenure: {tenure:.1f} months)")
        elif tenure <= 4.0:
            tenure_risk = 0.30
        else:
            tenure_risk = 0.05

        # Weighted composite score
        total_score = (
            0.35 * usage_risk +
            0.30 * billing_risk +
            0.20 * support_risk +
            0.15 * tenure_risk
        )
        total_score = float(np.clip(total_score, 0.0, 1.0))

        # Risk Category classification
        if total_score >= 0.80:
            category = "Critical"
            action = "Immediate executive outreach; assign dedicated CSM; deliver critical relief offer."
        elif total_score >= 0.60:
            category = "High"
            action = "Deliver targeted 20% retention credit; schedule technical onboarding check-in."
        elif total_score >= 0.30:
            category = "Medium"
            action = "Trigger automated re-engagement campaign; highlight unused premium features."
        else:
            category = "Low"
            action = "Standard customer lifecycle; monitor quarterly business review cadence."

        # Keep top 3 factors or provide default if none triggered
        if not factors:
            factors = ["Stable platform telemetry; no acute friction indicators observed."]
        else:
            factors = factors[:3]

        return round(total_score, 3), category, factors, action


class ChurnPredictionService:
    """End-to-end churn prediction, risk tiering, factor explainability, and ML model evaluation."""

    def __init__(self, session: Session):
        self.session = session

    def generate_predictions(
        self,
        prediction_cutoff: datetime = datetime(2026, 5, 31, 23, 59, 59),
        model_type: str = "RULE_BASED_BASELINE",
        horizon_days: int = 30
    ) -> Dict[str, Any]:
        """Generate predictions for active customers with explainability factors."""
        features_df, anomalies = FeatureEngineeringService.extract_customer_features(
            self.session,
            prediction_cutoff=prediction_cutoff,
            enforce_temporal_guard=True
        )

        if features_df.empty:
            return {
                "model_type": model_type,
                "prediction_cutoff": prediction_cutoff.isoformat(),
                "horizon_days": horizon_days,
                "total_predicted": 0,
                "predictions": [],
                "anomalies": anomalies,
            }

        predictions = []

        if model_type == "RULE_BASED_BASELINE":
            for _, row in features_df.iterrows():
                score, category, factors, action = RuleBasedScoringEngine.compute_score_and_factors(row)
                predictions.append({
                    "customer_id": row["customer_id"],
                    "subscription_id": row["subscription_id"],
                    "plan_name": row["plan_name"],
                    "mrr": row["mrr"],
                    "tenure_months": row["tenure_months"],
                    "risk_score": score,
                    "risk_category": category,
                    "prediction_date": prediction_cutoff.isoformat(),
                    "prediction_horizon_days": horizon_days,
                    "contributing_factors": factors,
                    "recommended_action": action,
                    "model_type": "RULE_BASED_BASELINE",
                })
        elif model_type in ["LOGISTIC_REGRESSION", "RANDOM_FOREST"]:
            # Train and score using ML classifier
            ml_results = self.train_and_predict_ml(features_df, model_type)
            predictions = ml_results["predictions"]
        else:
            raise ValueError(f"Unknown model_type: '{model_type}'")

        # Summary distribution
        risk_dist = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        for p in predictions:
            risk_dist[p["risk_category"]] = risk_dist.get(p["risk_category"], 0) + 1

        return {
            "model_type": model_type,
            "prediction_cutoff": prediction_cutoff.isoformat(),
            "horizon_days": horizon_days,
            "total_predicted": len(predictions),
            "risk_distribution": risk_dist,
            "predictions": predictions,
            "anomalies": anomalies,
        }

    def train_and_predict_ml(
        self,
        features_df: pd.DataFrame,
        model_name: str = "RANDOM_FOREST",
        random_state: int = 20261022
    ) -> Dict[str, Any]:
        """Train ML classifier on ground truth and predict probabilities."""
        # Query ground truth labels
        ground_truth_records = self.session.query(ChurnOutcome).all()
        gt_dict = {gt.customer_id: int(gt.actual_churned) for gt in ground_truth_records}

        features_df = features_df.copy()
        features_df["actual_churned"] = features_df["customer_id"].map(gt_dict).fillna(0).astype(int)

        X = features_df[FEATURE_COLUMNS].fillna(0)
        y = features_df["actual_churned"]

        # Train model
        if model_name == "LOGISTIC_REGRESSION":
            clf = LogisticRegression(max_iter=1000, random_state=random_state)
        else:
            clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=random_state)

        clf.fit(X, y)
        probs = clf.predict_proba(X)[:, 1]

        predictions = []
        for idx, (_, row) in enumerate(features_df.iterrows()):
            prob = float(probs[idx])
            if prob >= 0.70:
                cat = "Critical"
                act = "Immediate executive outreach; assign dedicated CSM; deliver critical relief offer."
            elif prob >= 0.45:
                cat = "High"
                act = "Deliver targeted 20% retention credit; schedule technical onboarding check-in."
            elif prob >= 0.20:
                cat = "Medium"
                act = "Trigger automated re-engagement campaign; highlight unused premium features."
            else:
                cat = "Low"
                act = "Standard customer lifecycle; monitor quarterly business review cadence."

            # Derive top rule-based factors for explainability
            _, _, factors, _ = RuleBasedScoringEngine.compute_score_and_factors(row)

            predictions.append({
                "customer_id": row["customer_id"],
                "subscription_id": row["subscription_id"],
                "plan_name": row["plan_name"],
                "mrr": row["mrr"],
                "tenure_months": row["tenure_months"],
                "risk_score": round(prob, 3),
                "risk_category": cat,
                "prediction_date": datetime(2026, 5, 31).isoformat(),
                "prediction_horizon_days": 30,
                "contributing_factors": factors,
                "recommended_action": act,
                "model_type": model_name,
            })

        return {"predictions": predictions, "model": clf}

    def evaluate_model_performance(
        self,
        prediction_cutoff: datetime = datetime(2026, 5, 31, 23, 59, 59),
        model_type: str = "RULE_BASED_BASELINE"
    ) -> Dict[str, Any]:
        """Compute formal evaluation metrics (Precision, Recall, F1, ROC-AUC, Confusion Matrix) against Ground Truth."""
        if model_type in ["RANDOM_FOREST", "LOGISTIC_REGRESSION"]:
            # Perform genuine Temporal Train/Test Split
            features_df, _ = FeatureEngineeringService.extract_customer_features(
                self.session, prediction_cutoff, enforce_temporal_guard=True
            )
            ground_truth_records = self.session.query(ChurnOutcome).all()
            gt_dict = {gt.customer_id: int(gt.actual_churned) for gt in ground_truth_records}
            features_df = features_df.copy()
            features_df["actual_churned"] = features_df["customer_id"].map(gt_dict).fillna(0).astype(int)

            cust_dates = {c.customer_id: c.signup_date for c in self.session.query(Customer).all()}
            features_df["signup_date"] = features_df["customer_id"].map(cust_dates)

            # Temporal Split: Early cohorts for training, later cohorts held out for testing
            split_date = datetime(2025, 9, 1)
            train_df = features_df[features_df["signup_date"] < split_date]
            test_df = features_df[features_df["signup_date"] >= split_date]

            X_train = train_df[FEATURE_COLUMNS].fillna(0)
            y_train = train_df["actual_churned"]
            X_test = test_df[FEATURE_COLUMNS].fillna(0)
            y_test = test_df["actual_churned"]

            if model_type == "LOGISTIC_REGRESSION":
                clf = LogisticRegression(max_iter=1000, random_state=20261022)
            else:
                clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=20261022)

            clf.fit(X_train, y_train)
            test_probs = clf.predict_proba(X_test)[:, 1]
            test_preds = (test_probs >= 0.45).astype(int)

            y_true = y_test.to_numpy()
            y_scores = test_probs
            y_pred = test_preds

            split_info = {
                "evaluation_mode": "TEMPORAL_HELD_OUT_TEST_SPLIT",
                "train_sample_size": len(X_train),
                "test_sample_size": len(X_test),
                "train_cutoff": "Before 2025-09-01",
                "test_window": "2025-09-01 to 2026-05-31",
            }
        else:
            # 1. Extract features and predictions for Rule-Based Baseline
            pred_result = self.generate_predictions(prediction_cutoff=prediction_cutoff, model_type=model_type)
            predictions = pred_result["predictions"]

            # 2. Extract Ground Truth
            ground_truth = self.session.query(ChurnOutcome).filter(
                ChurnOutcome.prediction_cutoff_date <= prediction_cutoff
            ).all()
            gt_map = {gt.customer_id: int(gt.actual_churned) for gt in ground_truth}

            y_true = []
            y_scores = []
            y_pred = []

            for p in predictions:
                cid = p["customer_id"]
                if cid in gt_map:
                    actual = gt_map[cid]
                    score = p["risk_score"]
                    # Decision threshold: High or Critical is predicted positive churn
                    binary_pred = 1 if p["risk_category"] in ["High", "Critical"] else 0

                    y_true.append(actual)
                    y_scores.append(score)
                    y_pred.append(binary_pred)

            y_true = np.array(y_true)
            y_scores = np.array(y_scores)
            y_pred = np.array(y_pred)
            split_info = {
                "evaluation_mode": "FULL_COHORT_RULE_BASELINE",
                "train_sample_size": 0,
                "test_sample_size": len(y_true),
                "train_cutoff": "N/A (Heuristic Rule Baseline)",
                "test_window": f"Up to {prediction_cutoff.strftime('%Y-%m-%d')}",
            }

        if len(y_true) == 0 or len(np.unique(y_true)) < 2:
            return {
                "model_type": model_type,
                "sample_size": len(y_true),
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "roc_auc": 0.0,
                "confusion_matrix": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
                "status": "Insufficient class diversity in ground truth window",
            }

        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)

        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        try:
            auc = roc_auc_score(y_true, y_scores)
        except Exception:
            auc = 0.5

        return {
            "model_type": model_type,
            "split_info": split_info,
            "sample_size": len(y_true),
            "actual_churn_rate": float(np.mean(y_true)),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(auc), 4),
            "confusion_matrix": {
                "tp": int(tp),
                "fp": int(fp),
                "tn": int(tn),
                "fn": int(fn),
            },
        }
