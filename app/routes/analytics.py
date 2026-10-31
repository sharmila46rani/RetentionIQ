from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.models.database import get_db_session, get_engine
from app.models import UsageSnapshot, BillingEvent, SupportCase
from app.services.analytics_service import BusinessAnalyticsService
from app.services.auth_service import require_role

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/usage")
def usage_view():
    """Platform usage telemetry analytics view."""
    session = get_db_session(get_engine())
    analytics = BusinessAnalyticsService(session)

    page = request.args.get("page", 1, type=int)
    per_page = 25

    query = session.query(UsageSnapshot).order_by(UsageSnapshot.snapshot_date.desc())
    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    snapshots = query.offset((page - 1) * per_page).limit(per_page).all()

    trends = analytics.get_usage_trends()

    return render_template(
        "usage.html",
        snapshots=snapshots,
        usage_trends=trends,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        max=max,
        min=min,
    )


@analytics_bp.route("/billing")
def billing_view():
    """Billing transactions and payment reconciliation analytics."""
    session = get_db_session(get_engine())
    analytics = BusinessAnalyticsService(session)

    page = request.args.get("page", 1, type=int)
    per_page = 25

    query = session.query(BillingEvent).order_by(BillingEvent.billing_date.desc())
    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    bills = query.offset((page - 1) * per_page).limit(per_page).all()

    summary = analytics.get_billing_summary()

    return render_template(
        "billing.html",
        billing_events=bills,
        billing_summary=summary,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        max=max,
        min=min,
    )


@analytics_bp.route("/support")
def support_view():
    """Customer support case analytics and satisfaction tracking."""
    session = get_db_session(get_engine())
    analytics = BusinessAnalyticsService(session)

    page = request.args.get("page", 1, type=int)
    per_page = 25

    query = session.query(SupportCase).order_by(SupportCase.opened_at.desc())
    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    cases = query.offset((page - 1) * per_page).limit(per_page).all()

    support_data = analytics.get_support_analytics()

    return render_template(
        "support.html",
        support_cases=cases,
        support_data=support_data,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        max=max,
        min=min,
    )


@analytics_bp.route("/support/update-status", methods=["POST"])
@require_role("admin", "support")
def update_support_status():
    """Update support ticket status without deleting existing records."""
    session = get_db_session(get_engine())
    case_id = request.form.get("case_id")
    new_status = request.form.get("status")
    if case_id and new_status in ["Open", "In_Progress", "Resolved", "Escalated"]:
        case = session.query(SupportCase).filter_by(case_id=case_id).first()
        if case:
            case.status = new_status
            if new_status == "Resolved" and not case.resolved_at:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                case.resolved_at = now
                case.resolution_hours = max(0.5, (now - case.opened_at).total_seconds() / 3600.0)
            session.commit()
    return redirect(request.referrer or url_for("analytics.support_view"))


# REST APIs
@analytics_bp.route("/api/v1/analytics/executive", methods=["GET"])
def api_executive_summary():
    session = get_db_session(get_engine())
    analytics = BusinessAnalyticsService(session)
    summary = analytics.get_executive_summary()
    session.close()
    return jsonify(summary)


@analytics_bp.route("/api/v1/analytics/cohorts", methods=["GET"])
def api_cohorts():
    session = get_db_session(get_engine())
    analytics = BusinessAnalyticsService(session)
    cohorts = analytics.get_monthly_cohort_analytics()
    session.close()
    return jsonify(cohorts)
