"""CLI script for synthetic data generation in RetentionIQ."""
import argparse
import os
import sys
import time

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.synthetic_generator import SyntheticDataGenerator, DEFAULT_SEED
from app.models.database import get_engine, init_db, drop_db


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic data for RetentionIQ")
    parser.add_argument("--customers", type=int, default=1000, help="Number of subscribers (default: 1000)")
    parser.add_argument("--months", type=int, default=18, help="Number of historical months (default: 18)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Master random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--save-db", action="store_true", help="Persist records into database")
    parser.add_argument("--reset-db", action="store_true", help="Drop existing tables before inserting")
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    print("=" * 70)
    print("RETENTIONIQ SYNTHETIC DATA GENERATION ENGINE")
    print("=" * 70)
    print(f"Target Subscribers : {args.customers:,}")
    print(f"Historical Horizon : {args.months} months")
    print(f"Random Seed        : {args.seed}")
    print(f"Persist Database   : {args.save_db or args.reset_db}")
    print("-" * 70)

    generator = SyntheticDataGenerator(
        num_customers=args.customers,
        months=args.months,
        seed=args.seed,
    )

    datasets = generator.generate_all()

    # Checksum & File exports
    print("\n[Exporting Datasets to CSV and JSON]...")
    checksums = generator.export_to_files(project_root)

    print("\n[Generated Dataset SHA-256 Checksums]:")
    for fname, sha in sorted(checksums.items()):
        print(f"  {fname:<25} : {sha}")

    # Database persistence if requested
    if args.save_db or args.reset_db:
        engine = get_engine()
        if args.reset_db:
            print("\n[Resetting Database]...")
            drop_db(engine)
        generator.save_to_database(engine)

    elapsed = time.time() - start_time
    print("-" * 70)
    print(f"Generation & Export successfully completed in {elapsed:.2f} seconds.")
    print("=" * 70)


if __name__ == "__main__":
    main()
