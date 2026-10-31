import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.models import (
    Base,
    Customer,
    Subscription,
    UsageSnapshot,
    BillingEvent,
    SupportCase,
    Offer,
    EligibilityRule,
    CampaignContact,
    ChurnOutcome,
    RetentionOutcome,
)
from app.services.data_quality import DataQualityAuditService


class DataExportService:
    """Multi-format data export engine supporting CSV, JSON, SQL DDL+DML, and SHA-256 manifests."""

    def __init__(self, session: Session, base_export_dir: str):
        self.session = session
        self.base_dir = base_export_dir
        self.csv_dir = os.path.join(base_export_dir, "csv")
        self.json_dir = os.path.join(base_export_dir, "json")
        self.sql_dir = os.path.join(base_export_dir, "sql")
        self.gt_dir = os.path.join(base_export_dir, "ground_truth")

        for d in [self.csv_dir, self.json_dir, self.sql_dir, self.gt_dir]:
            os.makedirs(d, exist_ok=True)

    def export_all(self) -> Dict[str, Any]:
        """Execute complete multi-format export and generate manifest."""
        entities = [
            ("offers", Offer),
            ("eligibility_rules", EligibilityRule),
            ("customers", Customer),
            ("subscriptions", Subscription),
            ("usage_snapshots", UsageSnapshot),
            ("billing_events", BillingEvent),
            ("support_cases", SupportCase),
            ("campaign_contacts", CampaignContact),
            ("churn_outcomes", ChurnOutcome),
            ("retention_outcomes", RetentionOutcome),
        ]

        checksums = {}
        row_counts = {}

        # 1. Export CSV & JSON for each entity
        for tbl_name, model in entities:
            records = self.session.query(model).all()
            data = [r.to_dict() for r in records]
            df = pd.DataFrame(data)
            row_counts[tbl_name] = len(df)

            # CSV
            csv_path = os.path.join(self.csv_dir, f"{tbl_name}.csv")
            df.to_csv(csv_path, index=False)
            checksums[f"csv/{tbl_name}.csv"] = self._compute_sha256(csv_path)

            # JSON
            json_path = os.path.join(self.json_dir, f"{tbl_name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            checksums[f"json/{tbl_name}.json"] = self._compute_sha256(json_path)

        # 2. Export isolated Ground Truth
        gt_records = self.session.query(ChurnOutcome).all()
        gt_data = [r.to_dict() for r in gt_records]
        gt_df = pd.DataFrame(gt_data)

        gt_csv_path = os.path.join(self.gt_dir, "ground_truth.csv")
        gt_df.to_csv(gt_csv_path, index=False)
        checksums["ground_truth/ground_truth.csv"] = self._compute_sha256(gt_csv_path)

        gt_json_path = os.path.join(self.gt_dir, "ground_truth.json")
        with open(gt_json_path, "w", encoding="utf-8") as f:
            json.dump(gt_data, f, indent=2)
        checksums["ground_truth/ground_truth.json"] = self._compute_sha256(gt_json_path)

        # 3. Export SQL (DDL + DML Statements)
        sql_path = os.path.join(self.sql_dir, "retentioniq_dump.sql")
        self._generate_sql_dump(entities, sql_path)
        checksums["sql/retentioniq_dump.sql"] = self._compute_sha256(sql_path)

        # 4. Run automated data quality audit and export report
        audit_service = DataQualityAuditService(self.session)
        audit_report = audit_service.run_full_audit()
        val_report_path = os.path.join(self.base_dir, "validation_report.json")
        with open(val_report_path, "w", encoding="utf-8") as f:
            json.dump(audit_report, f, indent=2)
        checksums["validation_report.json"] = self._compute_sha256(val_report_path)

        # 5. Build Master Manifest
        manifest = {
            "exported_at": datetime.now().isoformat(),
            "export_directory": self.base_dir,
            "row_counts": row_counts,
            "checksums": checksums,
            "quality_audit_summary": {
                "total_checks": audit_report["total_checks"],
                "passed_checks": audit_report["passed_checks"],
                "failed_checks": audit_report["failed_checks"],
                "warnings": audit_report["warning_checks"],
                "anomaly_count": audit_report["total_anomaly_count"],
            },
        }

        manifest_path = os.path.join(self.base_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    def _generate_sql_dump(self, entities: List[Tuple[str, Any]], filepath: str):
        """Generate ANSI SQL DDL and DML dump compatible with SQLite and MySQL."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("-- ========================================================\n")
            f.write("-- RETENTIONIQ COMPREHENSIVE DATABASE DUMP\n")
            f.write(f"-- Generated At: {datetime.now().isoformat()}\n")
            f.write("-- Target: SQLite & MySQL 8.0+ Compatible\n")
            f.write("-- ========================================================\n\n")

            # DDL Schema Creation
            for tbl_name, model in entities:
                create_stmt = str(CreateTable(model.__table__).compile())
                f.write(f"-- Schema: {tbl_name}\n")
                f.write(f"{create_stmt.strip()};\n\n")

            # DML Inserts
            for tbl_name, model in entities:
                records = self.session.query(model).all()
                if not records:
                    continue
                f.write(f"-- Records: {tbl_name} ({len(records)} rows)\n")
                cols = [c.name for c in model.__table__.columns]
                col_names = ", ".join(cols)

                for r in records:
                    vals = []
                    for c in cols:
                        v = getattr(r, c)
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, bool):
                            vals.append("1" if v else "0")
                        elif isinstance(v, datetime):
                            vals.append(f"'{v.strftime('%Y-%m-%d %H:%M:%S')}'")
                        else:
                            clean_v = str(v).replace("'", "''")
                            vals.append(f"'{clean_v}'")
                    f.write(f"INSERT INTO {tbl_name} ({col_names}) VALUES ({', '.join(vals)});\n")
                f.write("\n")

    @staticmethod
    def _compute_sha256(filepath: str) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
