from flask import Blueprint, render_template, request, jsonify
from app.models.database import get_db_session, get_engine
from app.models import Subscription

subscriptions_bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")


@subscriptions_bp.route("")
@subscriptions_bp.route("/")
def subscription_list():
    """Subscription contracts directory with plan and status filters."""
    session = get_db_session(get_engine())

    page = request.args.get("page", 1, type=int)
    per_page = 25
    plan = request.args.get("plan")
    status = request.args.get("status")

    query = session.query(Subscription)
    if plan:
        query = query.filter(Subscription.plan_name == plan)
    if status:
        query = query.filter(Subscription.status == status)

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    subscriptions = query.order_by(Subscription.subscription_id).offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "subscriptions.html",
        subscriptions=subscriptions,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        selected_plan=plan,
        selected_status=status,
        max=max,
        min=min,
    )


@subscriptions_bp.route("/api", methods=["GET"])
def api_subscriptions_list():
    session = get_db_session(get_engine())
    subs = session.query(Subscription).limit(100).all()
    data = [s.to_dict() for s in subs]
    session.close()
    return jsonify({"total": len(data), "subscriptions": data})
