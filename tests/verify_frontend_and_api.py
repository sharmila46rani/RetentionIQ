"""Automated comprehensive frontend and API verification script."""
import json
import urllib.parse
import urllib.request
import sys

BASE_URL = "http://127.0.0.1:5000"

def get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "RetentionIQ-QA-Bot"})
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode("utf-8")

def post_form(path, data):
    url = f"{BASE_URL}{path}"
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "RetentionIQ-QA-Bot"
    })
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode("utf-8")

def post_json(path, payload):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "User-Agent": "RetentionIQ-QA-Bot"
    })
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode("utf-8")

def run_checks():
    print("=" * 70)
    print("STARTING FRONTEND UI & BACKEND API VERIFICATION SUITE")
    print("=" * 70)

    checks = [
        # 1. Executive Dashboard
        ("1. Executive Dashboard", "/", ["Executive Dashboard", "Active Subscribers", "Overall Churn Rate", "cohortTrendChart"]),
        # 2. Customer Management
        ("2. Customer Management Directory", "/customers/", ["Customer Management", "table", "Search", "CUS-000001"]),
        # 3. Customer 360 Detail
        ("3. Customer 360 Detail", "/customers/CUS-000001", ["Profile", "Subscription Plan", "CUS-000001"]),
        # 4. Subscription Management
        ("4. Subscription Contracts", "/subscriptions/", ["Subscription Management", "Plan", "MRR", "Active"]),
        # 5. Usage Telemetry
        ("5. Usage Analytics", "/usage", ["Usage Analytics", "Active Days", "Decline %", "avgActiveDaysChart"]),
        # 6. Billing Analytics
        ("6. Billing Analytics", "/billing", ["Billing Analytics", "Total Invoiced", "Total Collected"]),
        # 7. Support Case Analytics
        ("7. Support Analytics", "/support", ["Support Case Analytics", "Total Support Cases", "Active / Open Cases"]),
        # 8. Predictions - Rule Based
        ("8. Predictions (Rule-Based)", "/predictions/?model_type=RULE_BASED_BASELINE", ["Churn Risk", "Confusion Matrix", "RULE_BASED_BASELINE"]),
        # 9. Predictions - Random Forest
        ("9. Predictions (Random Forest)", "/predictions/?model_type=RANDOM_FOREST", ["RANDOM_FOREST", "Precision", "Recall"]),
        # 10. Predictions - Logistic Regression
        ("10. Predictions (Logistic Regression)", "/predictions/?model_type=LOGISTIC_REGRESSION", ["LOGISTIC_REGRESSION", "ROC-AUC"]),
        # 11. Retention Offers Catalog
        ("11. Retention Offers Catalog", "/offers", ["Retention Offer Catalog", "OFF-2026-000001"]),
        # 12. Offer Eligibility Gate (GET)
        ("12. Offer Eligibility Gate", "/eligibility", ["Offer Eligibility & Margin Gatekeeper", "Evaluate Subscriber Eligibility"]),
        # 13. Campaign Management
        ("13. Campaign Management", "/campaigns", ["Campaign Management", "Total Contact Deliveries"]),
        # 14. Randomized Experiments
        ("14. A/B Experiment Engine", "/experiments", ["Randomized Experiment Engine", "Launch Randomized Trial"]),
        # 15. Retention Outcomes
        ("15. Retention Outcomes Tracking", "/outcomes", ["Retention Outcomes & Attribution", "Retained Customers", "Attributed Revenue"]),
        # 16. Data Quality & Audit
        ("16. Data Quality & Audit", "/quality/", ["Data Quality & Anomaly Suite", "Total Audit Checks", "Passed Checks"]),
        # 17. Synthetic Data Studio
        ("17. Synthetic Data Studio", "/generator/", ["Synthetic Data Generator", "Master Seed"]),
        # 18. Data Exports
        ("18. Data Exports & SQL", "/exports/", ["Data Exports & Reproducibility", "Export Manifest", "Generated Artifacts"]),
        # 19. Documentation
        ("19. System Documentation", "/docs", ["System Documentation & Requirement Traceability", "Relational Data Model", "Mandatory Edge Cases"]),
    ]

    all_passed = True
    for name, path, expected_tokens in checks:
        try:
            status, html = get(path)
            missing = [t for t in expected_tokens if t not in html]
            if status == 200 and not missing:
                print(f"  [PASS] {name:<35} -> HTTP 200 OK (all {len(expected_tokens)} tokens found)")
            else:
                print(f"  [FAIL] {name:<35} -> Status: {status}, Missing: {missing}")
                all_passed = False
        except Exception as e:
            print(f"  [ERROR] {name:<35} -> {e}")
            all_passed = False

    # 20. Test Customer Filter
    print("\n[Testing Dynamic Filters]...")
    st, html = get("/customers/?search=Corp&industry=FinTech")
    if st == 200 and "Customer Management" in html:
        print("  [PASS] Customer Search & Industry Filter -> HTTP 200 OK")
    else:
        print(f"  [FAIL] Customer Search Filter -> Status: {st}")
        all_passed = False

    # 21. Test Subscription Filter
    st, html = get("/subscriptions/?plan=Enterprise&status=Active")
    if st == 200 and "Subscription Management" in html:
        print("  [PASS] Subscription Plan & Status Filter -> HTTP 200 OK")
    else:
        print(f"  [FAIL] Subscription Plan Filter -> Status: {st}")
        all_passed = False

    # 22. Test Interactive Eligibility Form (POST)
    print("\n[Testing Interactive Form Submissions]...")
    st, html = post_form("/eligibility", {
        "customer_id": "CUS-000001",
        "offer_id": "OFF-2026-000001",
        "risk_category": "High"
    })
    if st == 200 and ("APPROVED / ELIGIBLE" in html or "REJECTED / INELIGIBLE" in html):
        print("  [PASS] Interactive Eligibility Evaluation -> HTTP 200 OK (Decision rendered)")
    else:
        print(f"  [FAIL] Eligibility POST -> Status {st}")
        all_passed = False

    # 23. Test REST APIs
    print("\n[Testing REST API Endpoints]...")
    apis = [
        ("/api/v1/analytics/executive", ["customer_kpis", "experiment_kpis"]),
        ("/customers/api", ["customers", "total"]),
        ("/api/v1/offers", ["offers"]),
        ("/api/v1/experiments/EXP-2026-Q1-RET", ["treatment_group_size", "control_group_size", "treatment_retention_rate"]),
        ("/exports/api/manifest", ["checksums", "row_counts"]),
        ("/quality/api/audit", ["total_checks", "passed_checks", "failed_checks"]),
    ]
    for path, expected_keys in apis:
        try:
            status, body = get(path)
            data = json.loads(body)
            missing = [k for k in expected_keys if k not in data]
            if status == 200 and not missing:
                print(f"  [PASS] API {path:<32} -> HTTP 200 OK (keys: {expected_keys})")
            else:
                print(f"  [FAIL] API {path:<32} -> Status: {status}, Missing keys: {missing}")
                all_passed = False
        except Exception as e:
            print(f"  [ERROR] API {path:<32} -> {e}")
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("ALL FRONTEND UI MODULES & BACKEND APIS VERIFIED SUCCESSFULLY!")
    else:
        print("SOME CHECKS FAILED. REVIEW OUTPUT ABOVE.")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
