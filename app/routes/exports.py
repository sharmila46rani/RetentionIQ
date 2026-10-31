import os
import json
from flask import Blueprint, render_template, send_from_directory, jsonify, abort
from app.models.database import get_db_session, get_engine
from app.services.export_service import DataExportService
from app.services.auth_service import require_role

exports_bp = Blueprint("exports", __name__, url_prefix="/exports")


def get_export_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "exports"))


@exports_bp.route("")
@exports_bp.route("/")
def exports_view():
    """Data exports directory and checksum manifest view."""
    exp_dir = get_export_dir()
    manifest_path = os.path.join(exp_dir, "manifest.json")
    manifest = None
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    return render_template("exports.html", manifest=manifest, export_success=False)


@exports_bp.route("/trigger", methods=["GET", "POST"])
@require_role("admin", "analyst")
def trigger_export_route():
    """Trigger fresh multi-format export."""
    exp_dir = get_export_dir()
    session = get_db_session(get_engine())
    service = DataExportService(session, exp_dir)
    manifest = service.export_all()
    session.close()

    return render_template("exports.html", manifest=manifest, export_success=True)


@exports_bp.route("/download/<path:relative_path>")
def download_file(relative_path):
    """Download exported CSV, JSON, or SQL file."""
    exp_dir = get_export_dir()
    file_path = os.path.abspath(os.path.join(exp_dir, relative_path))

    # Security check: prevent directory traversal
    try:
        if os.path.commonpath([exp_dir, file_path]) != exp_dir or not os.path.exists(file_path) or os.path.isdir(file_path):
            abort(404)
    except (ValueError, OSError):
        abort(404)

    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    return send_from_directory(directory, filename, as_attachment=True)


@exports_bp.route("/api/manifest", methods=["GET"])
def api_manifest():
    exp_dir = get_export_dir()
    manifest_path = os.path.join(exp_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return jsonify({"error": "No manifest found. Please run export."}), 404
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)
