from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from app.models.database import get_db_session, get_engine
from app.services.churn_prediction import ChurnPredictionService

predictions_bp = Blueprint("predictions", __name__, url_prefix="/predictions")


@predictions_bp.route("")
@predictions_bp.route("/")
def prediction_center():
    """Churn prediction control center with model selection, risk tiers, and factor attribution."""
    session = get_db_session(get_engine())
    predictor = ChurnPredictionService(session)

    model_type = request.args.get("model_type", "RULE_BASED_BASELINE")
    cutoff = datetime(2026, 5, 31, 23, 59, 59)

    # 1. Predictions with explainability factors
    pred_res = predictor.generate_predictions(prediction_cutoff=cutoff, model_type=model_type)

    # 2. Confusion matrix and holdout evaluation metrics
    eval_res = predictor.evaluate_model_performance(prediction_cutoff=cutoff, model_type=model_type)

    return render_template(
        "predictions.html",
        predictions=pred_res["predictions"],
        risk_distribution=pred_res["risk_distribution"],
        evaluation=eval_res,
        model_type=model_type,
    )


@predictions_bp.route("/api", methods=["GET"])
def api_predictions():
    session = get_db_session(get_engine())
    predictor = ChurnPredictionService(session)
    model_type = request.args.get("model_type", "RULE_BASED_BASELINE")
    res = predictor.generate_predictions(model_type=model_type)
    session.close()
    return jsonify(res)


@predictions_bp.route("/api/evaluate", methods=["GET"])
def api_evaluation():
    session = get_db_session(get_engine())
    predictor = ChurnPredictionService(session)
    model_type = request.args.get("model_type", "RULE_BASED_BASELINE")
    eval_res = predictor.evaluate_model_performance(model_type=model_type)
    session.close()
    return jsonify(eval_res)
