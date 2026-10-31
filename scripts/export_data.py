"""CLI script to export RetentionIQ data to CSV, JSON, SQL with SHA-256 manifests."""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.database import get_engine, get_db_session
from app.services.export_service import DataExportService


def main():
    parser = argparse.ArgumentParser(description="Export RetentionIQ data to CSV, JSON, SQL")
    parser.add_argument("--outdir", type=str, default="data/exports", help="Output export directory")
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    export_dir = os.path.abspath(os.path.join(project_root, args.outdir))

    print("=" * 70)
    print("RETENTIONIQ MULTI-FORMAT DATA EXPORT")
    print("=" * 70)
    print(f"Export Directory: {export_dir}")

    session = get_db_session(get_engine())
    service = DataExportService(session, export_dir)

    start = time.time()
    manifest = service.export_all()
    session.close()

    elapsed = time.time() - start
    print(f"Export completed in {elapsed:.2f} seconds.")
    print("\nRow Counts Exported:")
    for tbl, count in manifest["row_counts"].items():
        print(f"  {tbl:<22}: {count:,} rows")

    print("\nQuality Audit Summary:")
    qa = manifest["quality_audit_summary"]
    print(f"  Passed Checks : {qa['passed_checks']} / {qa['total_checks']}")
    print(f"  Failed Checks : {qa['failed_checks']}")
    print(f"  Anomalies     : {qa['anomaly_count']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
