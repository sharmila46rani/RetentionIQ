from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models.database import get_db_session, get_engine
from app.services.analytics_service import BusinessAnalyticsService
from app.services.churn_prediction import ChurnPredictionService
from app.models import Customer, Subscription

main_bp = Blueprint("main", __name__)


@main_bp.route("/switch-role/<role>")
def switch_role(role):
    """Switch active business actor session role."""
    valid_roles = {
        "admin": "System Administrator",
        "marketing": "Marketing & Sales Operations",
        "support": "Support Agent",
        "analyst": "Data Analyst",
        "customer": "Customer (Self-Service)",
    }
    role_key = role.lower()
    if role_key in valid_roles:
        session["actor_role"] = valid_roles[role_key]
        session["actor_key"] = role_key
    ref = request.referrer
    return redirect(ref if ref else url_for("main.dashboard"))


@main_bp.route("/")
@main_bp.route("/dashboard")
def dashboard():
    """Executive Dashboard with live KPI stat cards, charts, and risk alerts."""
    session = get_db_session(get_engine())
    analytics = BusinessAnalyticsService(session)
    predictor = ChurnPredictionService(session)

    summary = analytics.get_executive_summary()
    cohort_data = analytics.get_monthly_cohort_analytics()

    # Predict risk for active subscribers
    pred_res = predictor.generate_predictions(model_type="RULE_BASED_BASELINE")
    all_preds = pred_res.get("predictions", [])

    # Filter top high/critical risk accounts
    cust_map = {c.customer_id: c.company_name for c in session.query(Customer).all()}
    top_risk = [p for p in all_preds if p["risk_category"] in ["Critical", "High"]]
    for p in top_risk:
        p["company_name"] = cust_map.get(p["customer_id"], "Unknown")

    top_risk = top_risk[:10]  # Show top 10

    return render_template(
        "dashboard.html",
        summary=summary,
        cohort_data=cohort_data,
        top_risk_customers=top_risk,
    )


@main_bp.route("/docs")
@main_bp.route("/documentation")
def documentation_view():
    """System Documentation and technical defensibility references."""
    return render_template("documentation.html")
