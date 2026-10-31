from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.models.database import get_db_session, get_engine
from app.models import CampaignContact, RetentionOutcome, Offer
from app.services.experiment_service import (
    RandomizedExperimentEngine,
    ExperimentConflictException,
)
from app.services.auth_service import require_role

campaigns_bp = Blueprint("campaigns", __name__)


@campaigns_bp.route("/campaigns")
def campaign_view():
    """Campaign recipient and contact management directory."""
    session = get_db_session(get_engine())

    page = request.args.get("page", 1, type=int)
    per_page = 25

    query = session.query(CampaignContact).order_by(CampaignContact.assigned_at.desc())
    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    contacts = query.offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "campaigns.html",
        contacts=contacts,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        max=max,
        min=min,
    )


@campaigns_bp.route("/experiments")
def experiment_view():
    """Randomized retention trial analytics and lift calculation."""
    session = get_db_session(get_engine())
    engine = RandomizedExperimentEngine(session)

    # Evaluate default experiment
    default_exp_id = "EXP-2026-Q1-RET"
    metrics = engine.evaluate_retention_outcomes_with_attribution(default_exp_id)
    offers = session.query(Offer).filter_by(status="Active").all()

    return render_template(
        "experiments.html",
        experiment_metrics=metrics,
        offers=offers,
        launch_result=None,
    )


@campaigns_bp.route("/experiments/launch", methods=["POST"])
@require_role("admin", "marketing")
def launch_experiment_route():
    """Launch a new randomized trial with stratified 50/50 allocation (EC-03)."""
    session = get_db_session(get_engine())
    engine = RandomizedExperimentEngine(session)

    exp_id = request.form.get("experiment_id", "EXP-2026-Q2-RET")
    offer_id = request.form.get("offer_id")

    offers = session.query(Offer).filter_by(status="Active").all()

    try:
        launch_res = engine.launch_experiment(
            experiment_id=exp_id,
            offer_id=offer_id,
            target_risk_categories=["High", "Critical"]
        )
        metrics = engine.evaluate_retention_outcomes_with_attribution(exp_id)
        error = None
    except ExperimentConflictException as e:
        launch_res = None
        error = str(e)
        metrics = engine.evaluate_retention_outcomes_with_attribution("EXP-2026-Q1-RET")

    return render_template(
        "experiments.html",
        experiment_metrics=metrics,
        offers=offers,
        launch_result=launch_res,
        conflict_error=error,
    )


@campaigns_bp.route("/outcomes")
def outcome_view():
    """Retention outcomes and multi-touch attribution resolution (EC-04)."""
    session = get_db_session(get_engine())

    page = request.args.get("page", 1, type=int)
    per_page = 25

    query = session.query(RetentionOutcome).order_by(RetentionOutcome.evaluated_at.desc())
    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    outcomes = query.offset((page - 1) * per_page).limit(per_page).all()

    retained_count = sum(1 for r in query.all() if r.retained_after_horizon)
    total_rev = sum(r.incremental_revenue for r in query.all())
    total_cost = sum(r.offer_cost_incurred for r in query.all())
    multi_attr = sum(1 for r in query.all() if r.attribution_status == "Multi_Attributed_Flagged")

    return render_template(
        "outcomes.html",
        outcomes=outcomes,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        retained_count=retained_count,
        total_attributed_revenue=total_rev,
        total_offer_cost=total_cost,
        multi_attributed_count=multi_attr,
        max=max,
        min=min,
    )


# REST APIs
@campaigns_bp.route("/api/v1/experiments/<experiment_id>", methods=["GET"])
def api_experiment_metrics(experiment_id):
    session = get_db_session(get_engine())
    engine = RandomizedExperimentEngine(session)
    res = engine.evaluate_retention_outcomes_with_attribution(experiment_id)
    session.close()
    return jsonify(res)
