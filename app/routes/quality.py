from flask import Blueprint, render_template, jsonify
from app.models.database import get_db_session, get_engine
from app.services.data_quality import DataQualityAuditService
from app.services.auth_service import require_role

quality_bp = Blueprint("quality", __name__, url_prefix="/quality")


@quality_bp.route("")
@quality_bp.route("/")
def quality_view():
    """Automated 13-point data quality report and anomaly inspector."""
    session = get_db_session(get_engine())
    service = DataQualityAuditService(session)
    report = service.run_full_audit()
    return render_template("quality.html", report=report)


@quality_bp.route("/audit", methods=["GET", "POST"])
@require_role("admin", "analyst")
def run_audit_live():
    """Trigger live re-audit."""
    session = get_db_session(get_engine())
    service = DataQualityAuditService(session)
    report = service.run_full_audit()
    return render_template("quality.html", report=report)


@quality_bp.route("/api/audit", methods=["GET"])
def api_audit_report():
    session = get_db_session(get_engine())
    service = DataQualityAuditService(session)
    report = service.run_full_audit()
    session.close()
    return jsonify(report)
