from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.models.database import get_db_session, get_engine
from app.models import Offer, Customer, EligibilityRule
from app.services.eligibility_service import OfferEligibilityEngine, IneligibleCustomerException
from app.services.auth_service import require_role

offers_bp = Blueprint("offers", __name__)


@offers_bp.route("/offers")
@offers_bp.route("/offers/")
def offer_catalog():
    """Catalog of active retention offers and configured eligibility rules."""
    session = get_db_session(get_engine())
    offers = session.query(Offer).all()
    return render_template("offers.html", offers=offers)


@offers_bp.route("/offers/<offer_id>/toggle-status", methods=["POST"])
@require_role("admin", "marketing")
def toggle_offer_status(offer_id):
    """Toggle offer status between Active and Paused without destructive DB actions."""
    session = get_db_session(get_engine())
    offer = session.query(Offer).filter_by(offer_id=offer_id).first()
    if offer:
        offer.status = "Paused" if offer.status == "Active" else "Active"
        session.commit()
    return redirect(request.referrer or url_for("offers.offer_catalog"))


@offers_bp.route("/eligibility", methods=["GET", "POST"])
def eligibility_view():
    """Interactive eligibility gatekeeper and contribution margin check."""
    session = get_db_session(get_engine())
    engine = OfferEligibilityEngine(session)

    customers = session.query(Customer).order_by(Customer.customer_id).limit(200).all()
    offers = session.query(Offer).filter_by(status="Active").all()

    selected_cid = request.args.get("customer_id")
    selected_oid = request.args.get("offer_id")
    selected_risk = request.args.get("risk_category", "High")
    result = None
    dispatch_error = None
    dispatch_success = None

    if request.method == "POST":
        selected_cid = request.form.get("customer_id")
        selected_oid = request.form.get("offer_id")
        selected_risk = request.form.get("risk_category", "High")

    if selected_cid and selected_oid:
        result = engine.evaluate(selected_cid, selected_oid, risk_category=selected_risk)

    return render_template(
        "eligibility.html",
        customers=customers,
        offers=offers,
        selected_customer_id=selected_cid,
        selected_offer_id=selected_oid,
        selected_risk=selected_risk,
        result=result,
        dispatch_error=dispatch_error,
        dispatch_success=dispatch_success,
    )


@offers_bp.route("/eligibility/dispatch", methods=["POST"])
@require_role("admin", "marketing")
def dispatch_offer_route():
    """Dispatch retention offer with strict gatekeeping (EC-02)."""
    session = get_db_session(get_engine())
    engine = OfferEligibilityEngine(session)

    cid = request.form.get("customer_id")
    oid = request.form.get("offer_id")
    risk_cat = request.form.get("risk_category", "High")

    customers = session.query(Customer).limit(200).all()
    offers = session.query(Offer).filter_by(status="Active").all()

    eval_res = engine.evaluate(cid, oid, risk_category=risk_cat)

    try:
        contact = engine.dispatch_offer_with_guard(
            customer_id=cid,
            offer_id=oid,
            experiment_id="EXP-MANUAL-DISPATCH",
            experiment_group="Treatment",
            risk_category=risk_cat
        )
        dispatch_success = contact.contact_id
        dispatch_error = None
    except IneligibleCustomerException as e:
        dispatch_success = None
        dispatch_error = str(e)

    return render_template(
        "eligibility.html",
        customers=customers,
        offers=offers,
        selected_customer_id=cid,
        selected_offer_id=oid,
        selected_risk=risk_cat,
        result=eval_res,
        dispatch_error=dispatch_error,
        dispatch_success=dispatch_success,
    )


# REST APIs
@offers_bp.route("/api/v1/offers", methods=["GET"])
def api_offers_list():
    session = get_db_session(get_engine())
    offers = session.query(Offer).all()
    data = [o.to_dict() for o in offers]
    session.close()
    return jsonify({"offers": data})


@offers_bp.route("/api/v1/eligibility/evaluate", methods=["POST"])
def api_evaluate_eligibility():
    payload = request.get_json() or {}
    cid = payload.get("customer_id")
    oid = payload.get("offer_id")
    risk = payload.get("risk_category")

    if not cid or not oid:
        return jsonify({"error": "Missing customer_id or offer_id"}), 400

    session = get_db_session(get_engine())
    engine = OfferEligibilityEngine(session)
    res = engine.evaluate(cid, oid, risk_category=risk)
    session.close()
    return jsonify(res.to_dict())
