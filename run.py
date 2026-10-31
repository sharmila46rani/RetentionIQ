"""Application entry point for RetentionIQ."""
import os
from app.app import create_app
from app.models.database import init_db, get_engine

app = create_app()

if __name__ == "__main__":
    # Ensure database tables exist
    init_db(get_engine())
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f"RETENTIONIQ SERVER STARTING ON http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
