"""Database initialization script for RetentionIQ."""
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import init_db, get_engine


def main():
    print("Initializing RetentionIQ database...")
    engine = get_engine()
    init_db(engine)
    print(f"Database successfully initialized with URI: {engine.url}")


if __name__ == "__main__":
    main()
