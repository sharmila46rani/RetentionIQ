import os
from flask import Flask, render_template, session


def create_app(test_config=None):
    """Application factory for RetentionIQ."""
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="templates",
        static_folder="static",
    )

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "retentioniq-secret-key-20261022"),
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
    )

    if test_config:
        app.config.from_mapping(test_config)

    # Custom Jinja filters
    @app.template_filter("number_format")
    def number_format_filter(value):
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return value

    @app.template_filter("currency")
    def currency_filter(value):
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return value

    # Context processor for Multi-Actor role-based view context
    @app.context_processor
    def inject_actor():
        return {
            "current_actor": session.get("actor_role", "System Administrator"),
            "current_actor_key": session.get("actor_key", "admin"),
        }

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.customers import customers_bp
    from app.routes.subscriptions import subscriptions_bp
    from app.routes.analytics import analytics_bp
    from app.routes.predictions import predictions_bp
    from app.routes.offers import offers_bp
    from app.routes.campaigns import campaigns_bp
    from app.routes.quality import quality_bp
    from app.routes.generator import generator_bp
    from app.routes.exports import exports_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(subscriptions_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(offers_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(quality_bp)
    app.register_blueprint(generator_bp)
    app.register_blueprint(exports_bp)

    from app.models.database import close_db_session

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        close_db_session()

    # Global Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("documentation.html", error_message=f"Access Forbidden (403): {getattr(e, 'description', 'Insufficient permissions')}"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("documentation.html", error_message="Page Not Found (404)"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("documentation.html", error_message="Internal Server Error (500)"), 500

    return app
