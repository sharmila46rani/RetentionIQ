import time
import os
from flask import Blueprint, render_template, request, jsonify, current_app
from app.models.database import get_engine, drop_db
from app.services.synthetic_generator import SyntheticDataGenerator, DEFAULT_SEED
from app.services.auth_service import require_role

generator_bp = Blueprint("generator", __name__, url_prefix="/generator")


@generator_bp.route("")
@generator_bp.route("/")
def generator_view():
    """Synthetic Data Generator UI."""
    return render_template("generator.html", generation_success=None)


@generator_bp.route("/run", methods=["POST"])
@require_role("admin")
def run_generator_route():
    """Trigger parameterized synthetic data generation."""
    customers = int(request.form.get("customers", 1000))
    months = int(request.form.get("months", 18))
    seed = int(request.form.get("seed", DEFAULT_SEED))
    reset_db = bool(request.form.get("reset_db"))

    start = time.time()
    gen = SyntheticDataGenerator(num_customers=customers, months=months, seed=seed)
    gen.generate_all()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    gen.export_to_files(project_root)

    engine = get_engine()
    if reset_db:
        drop_db(engine)
    gen.save_to_database(engine)

    elapsed = time.time() - start

    success_payload = {
        "customers": customers,
        "months": months,
        "seed": seed,
        "elapsed": elapsed,
    }

    return render_template("generator.html", generation_success=success_payload)


@generator_bp.route("/api/run", methods=["POST"])
def api_run_generator():
    payload = request.get_json() or {}
    customers = int(payload.get("customers", 1000))
    months = int(payload.get("months", 18))
    seed = int(payload.get("seed", DEFAULT_SEED))
    reset_db = bool(payload.get("reset_db", False))

    start = time.time()
    gen = SyntheticDataGenerator(num_customers=customers, months=months, seed=seed)
    gen.generate_all()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    gen.export_to_files(project_root)

    engine = get_engine()
    if reset_db:
        drop_db(engine)
    gen.save_to_database(engine)

    elapsed = time.time() - start

    return jsonify({
        "status": "success",
        "customers": customers,
        "months": months,
        "seed": seed,
        "elapsed_seconds": round(elapsed, 2),
    })
