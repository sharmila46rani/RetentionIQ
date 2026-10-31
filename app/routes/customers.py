from flask import Blueprint, render_template, request, jsonify, abort
from app.models.database import get_db_session, get_engine
from app.models import (
    Customer,
    Subscription,
    UsageSnapshot,
    BillingEvent,
    SupportCase,
    CampaignContact,
)
from app.services.churn_prediction import ChurnPredictionService, RuleBasedScoringEngine
from app.services.feature_engineering import FeatureEngineeringService

customers_bp = Blueprint("customers", __name__, url_prefix="/customers")


@customers_bp.route("")
@customers_bp.route("/")
def customer_list():
    """Customer management directory with search, filter, and pagination."""
    session = get_db_session(get_engine())

    page = request.args.get("page", 1, type=int)
    per_page = 25
    industry = request.args.get("industry")
    tier = request.args.get("tier")

    query = session.query(Customer)
    if industry:
        query = query.filter(Customer.industry == industry)
    if tier:
        query = query.filter(Customer.customer_tier == tier)

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    customers = query.order_by(Customer.customer_id).offset((page - 1) * per_page).limit(per_page).all()

    # Distinct industries for filter
    industries = [r[0] for r in session.query(Customer.industry).distinct().all()]

    return render_template(
        "customers.html",
        customers=customers,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        industries=sorted(industries),
        selected_industry=industry,
        selected_tier=tier,
        max=max,
        min=min,
    )


@customers_bp.route("/<customer_id>")
def customer_detail(customer_id):
    """360-degree customer intelligence view with telemetries and churn risk factors."""
    session = get_db_session(get_engine())

    customer = session.query(Customer).filter_by(customer_id=customer_id).first()
    if not customer:
        abort(404)
    subs = session.query(Subscription).filter_by(customer_id=customer_id).order_by(Subscription.start_date.desc()).all()
    primary_sub = subs[0] if subs else None

    # Telemetries
    usage_snaps = []
    billing_events = []
    if primary_sub:
        usage_snaps = session.query(UsageSnapshot).filter_by(
            subscription_id=primary_sub.subscription_id
        ).order_by(UsageSnapshot.snapshot_date.asc()).all()

        billing_events = session.query(BillingEvent).filter_by(
            subscription_id=primary_sub.subscription_id
        ).order_by(BillingEvent.billing_date.desc()).all()

    support_cases = session.query(SupportCase).filter_by(
        customer_id=customer_id
    ).order_by(SupportCase.opened_at.desc()).all()

    campaign_contacts = session.query(CampaignContact).filter_by(
        customer_id=customer_id
    ).order_by(CampaignContact.assigned_at.desc()).all()

    # Point-in-time risk score & factor explainability
    predictor = ChurnPredictionService(session)
    preds = predictor.generate_predictions(model_type="RULE_BASED_BASELINE")
    customer_pred = next((p for p in preds["predictions"] if p["customer_id"] == customer_id), None)

    if not customer_pred:
        customer_pred = {
            "risk_score": 0.15,
            "risk_category": "Low",
            "contributing_factors": ["Normal account telemetry."],
            "recommended_action": "Standard customer lifecycle review.",
        }

    usage_snapshots_json = [s.to_dict() for s in usage_snaps]

    return render_template(
        "customer_detail.html",
        customer=customer,
        primary_sub=primary_sub,
        usage_snapshots=usage_snaps,
        usage_snapshots_json=usage_snapshots_json,
        billing_events=billing_events,
        support_cases=support_cases,
        campaign_contacts=campaign_contacts,
        risk_data=customer_pred,
    )


# REST API Endpoints
@customers_bp.route("/api", methods=["GET"])
def api_customers_list():
    session = get_db_session(get_engine())
    customers = session.query(Customer).limit(100).all()
    data = [c.to_dict() for c in customers]
    session.close()
    return jsonify({"total": len(data), "customers": data})


@customers_bp.route("/api/<customer_id>", methods=["GET"])
def api_customer_detail(customer_id):
    session = get_db_session(get_engine())
    customer = session.query(Customer).filter_by(customer_id=customer_id).first()
    if not customer:
        session.close()
        return jsonify({"error": "Customer not found"}), 404
    data = customer.to_dict()
    session.close()
    return jsonify(data)
