# RETENTIONIQ — Comprehensive Data Dictionary
**Version:** 1.0.0
**Target RDBMS:** SQLite (Local Dev) / MySQL 8.0+ (Enterprise Compatibility)

---

## 1. Overview
The RetentionIQ relational model consists of 10 primary entities modeling the full customer intelligence, subscription lifecycle, operational telemetries, churn prediction ground truth, retention offers, eligibility rules, A/B experiments, and financial retention outcomes.

All primary keys use human-readable deterministic string identifiers adhering to strict regex validation.

---

## 2. Entity Specifications

### 2.1 Customer (`customers`)
Represents subscriber corporate accounts and profile attributes.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `customer_id` | `VARCHAR(20)` | No | PK | Regex: `^CUS-\d{6}$` | Unique identifier, e.g. `CUS-000001` |
| `first_name` | `VARCHAR(100)` | No | No | String | Primary contact first name |
| `last_name` | `VARCHAR(100)` | No | No | String | Primary contact last name |
| `email` | `VARCHAR(255)` | No | Unique | Valid email format | Contact email address, indexed |
| `company_name` | `VARCHAR(255)` | No | No | String | Company or organization name |
| `industry` | `VARCHAR(100)` | No | No | SaaS, FinTech, HealthTech, E-Commerce, Logistics, Media | Industry vertical |
| `customer_tier` | `VARCHAR(50)` | No | No | Standard, Pro, Enterprise | Customer business tier |
| `cohort_month` | `VARCHAR(7)` | No | No | Format: `YYYY-MM` | Onboarding cohort month, indexed |
| `signup_date` | `DATETIME` | No | No | Datetime $\le$ current date | Initial account registration date |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |
| `updated_at` | `DATETIME` | No | No | UTC Datetime | Record last updated timestamp |

---

### 2.2 Subscription (`subscriptions`)
Represents recurring software subscription agreements and lifecycle states.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `subscription_id` | `VARCHAR(30)` | No | PK | Regex: `^SUB-CUS-\d{6}-\d{2}$` | Unique subscription ID, e.g. `SUB-CUS-000001-01` |
| `customer_id` | `VARCHAR(20)` | No | FK | Exists in `customers.customer_id` | Foreign key referencing Customer |
| `plan_name` | `VARCHAR(50)` | No | No | Starter, Growth, Scale, Enterprise | Subscribed software plan |
| `billing_cycle` | `VARCHAR(20)` | No | No | Monthly, Annual | Recurring billing frequency |
| `mrr` | `FLOAT` | No | No | $\ge 0.0$ | Monthly recurring revenue in USD |
| `unit_cost` | `FLOAT` | No | No | $\ge 0.0$, default 0.0 | Infrastructure / service unit cost in USD |
| `status` | `VARCHAR(30)` | No | No | Active, Delinquent, Canceled, Expired, Paused | Current lifecycle state |
| `start_date` | `DATETIME` | No | No | Datetime | Contract start timestamp |
| `end_date` | `DATETIME` | Yes | No | Datetime $\ge$ `start_date` | Contract termination or scheduled renewal date |
| `trial_end_date` | `DATETIME` | Yes | No | Datetime | Trial period expiration if applicable |
| `canceled_at` | `DATETIME` | Yes | No | Datetime | Exact cancellation event timestamp |
| `churn_reason` | `VARCHAR(50)` | No | No | Voluntary, Involuntary, None | Root churn category classification |
| `plan_change_count`| `INTEGER` | No | No | $\ge 0$, default 0 | Number of plan upgrades/downgrades |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |
| `updated_at` | `DATETIME` | No | No | UTC Datetime | Record last updated timestamp |

---

### 2.3 UsageSnapshot (`usage_snapshots`)
Monthly behavioral telemetry aggregated per subscription.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `snapshot_id` | `VARCHAR(45)` | No | PK | Regex: `^SNAP-SUB-CUS-\d{6}-\d{2}-\d{4}-\d{2}$` | Deterministic composite snapshot ID |
| `subscription_id` | `VARCHAR(30)` | No | FK | Exists in `subscriptions.subscription_id` | Foreign key referencing Subscription |
| `snapshot_month` | `VARCHAR(7)` | No | Composite Unique | Format: `YYYY-MM` | Snapshot calendar month |
| `snapshot_date` | `DATETIME` | No | No | Datetime | Effective evaluation timestamp |
| `active_days` | `INTEGER` | No | No | $0 \le x \le 31$ | Number of days with active user sessions |
| `login_count` | `INTEGER` | No | No | $\ge 0$ | Total login events recorded |
| `total_session_minutes` | `FLOAT` | No | No | $\ge 0.0$ | Total session duration in minutes |
| `feature_events_count` | `INTEGER` | No | No | $\ge 0$ | Key feature utilization actions |
| `api_call_count` | `INTEGER` | No | No | $\ge 0$ | Total API requests triggered |
| `license_utilization_pct`| `FLOAT` | No | No | $0.0 \le x \le 100.0$ | Percentage of provisioned seats active |
| `usage_decline_pct` | `FLOAT` | No | No | $-\infty < x \le 100.0$ | Month-over-month relative drop in activity |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |

---

### 2.4 BillingEvent (`billing_events`)
Invoicing, charge attempts, retries, and payment statuses.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `billing_id` | `VARCHAR(30)` | No | PK | Regex: `^BIL-CUS-\d{6}-\d{6}$` | Unique billing event ID, e.g. `BIL-CUS-000001-202601` |
| `subscription_id` | `VARCHAR(30)` | No | FK | Exists in `subscriptions.subscription_id` | Foreign key referencing Subscription |
| `billing_date` | `DATETIME` | No | No | Datetime | Invoicing timestamp |
| `due_date` | `DATETIME` | No | No | Datetime $\ge$ `billing_date` | Payment deadline |
| `invoice_amount` | `FLOAT` | No | No | $\ge 0.0$ | Total billed amount in USD |
| `paid_amount` | `FLOAT` | No | No | $\ge 0.0$, default 0.0 | Actual settled payment amount in USD |
| `status` | `VARCHAR(30)` | No | No | Paid, Pending, Failed, Refunded | Transaction outcome state |
| `retry_count` | `INTEGER` | No | No | $\ge 0$, default 0 | Number of re-billing charge attempts |
| `failure_reason` | `VARCHAR(100)`| No | No | Insufficient_Funds, Expired_Card, Bank_Reject, None | Rejection reason code |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |

---

### 2.5 SupportCase (`support_cases`)
Customer support ticketing lifecycle and satisfaction metrics.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `case_id` | `VARCHAR(30)` | No | PK | Regex: `^CAS-CUS-\d{6}-\d{3}$` | Ticket identifier, e.g. `CAS-CUS-000001-001` |
| `customer_id` | `VARCHAR(20)` | No | FK | Exists in `customers.customer_id` | Foreign key referencing Customer |
| `category` | `VARCHAR(50)` | No | No | Billing, Technical, Product_Bug, Feature_Request, Account | Ticket domain category |
| `priority` | `VARCHAR(20)` | No | No | Low, Medium, High, Critical | SLA severity priority |
| `status` | `VARCHAR(30)` | No | No | Open, In_Progress, Resolved, Escalated | Ticket handling status |
| `opened_at` | `DATETIME` | No | No | Datetime | Ticket submission timestamp |
| `resolved_at` | `DATETIME` | Yes | No | Datetime $\ge$ `opened_at` | Ticket resolution timestamp |
| `resolution_hours` | `FLOAT` | Yes | No | $\ge 0.0$ | Total elapsed hours to resolution |
| `escalation_count` | `INTEGER` | No | No | $\ge 0$, default 0 | Number of tier escalations |
| `csat_score` | `INTEGER` | Yes | No | Integer $1 \le x \le 5$ | Customer satisfaction rating |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |

---

### 2.6 Offer (`offers`)
Retention incentives catalog and financial discounting parameters.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `offer_id` | `VARCHAR(30)` | No | PK | Regex: `^OFF-\d{4}-\d{6}$` | Unique offer catalog ID, e.g. `OFF-2026-000001` |
| `offer_name` | `VARCHAR(150)`| No | No | String | Descriptive offer name |
| `offer_type` | `VARCHAR(50)` | No | No | Discount, Free_Month, Feature_Addon, Tier_Upgrade | Offer mechanic classification |
| `discount_pct` | `FLOAT` | No | No | $0.0 \le x \le 100.0$ | Percentage discount on subscription |
| `discount_amount` | `FLOAT` | No | No | $\ge 0.0$ | Fixed dollar credit or discount |
| `max_offer_cost` | `FLOAT` | No | No | $\ge 0.0$ | Maximum financial concession ceiling |
| `eligible_plans` | `VARCHAR(255)`| No | No | Comma-separated plan names | Target plans eligible for offer |
| `min_tenure_months`| `INTEGER` | No | No | $\ge 0$ | Minimum required customer tenure |
| `min_subscription_mrr`| `FLOAT`| No | No | $\ge 0.0$ | Minimum MRR threshold required |
| `max_discount_cap` | `FLOAT` | No | No | $\ge 0.0$ | Hard dollar cap on percentage discounts |
| `valid_from` | `DATETIME` | No | No | Datetime | Offer validity start date |
| `valid_to` | `DATETIME` | No | No | Datetime $\ge$ `valid_from` | Offer validity expiration date |
| `status` | `VARCHAR(20)` | No | No | Draft, Active, Paused, Expired | Catalog availability state |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |

---

### 2.7 EligibilityRule (`eligibility_rules`)
Parameterized boolean and mathematical guardrails governing offer dispatch.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `rule_id` | `VARCHAR(40)` | No | PK | Regex: `^RUL-OFF-\d{4}-\d{6}-\d{2}$` | Unique rule ID, e.g. `RUL-OFF-2026-000001-01` |
| `offer_id` | `VARCHAR(30)` | No | FK | Exists in `offers.offer_id` | Foreign key referencing Offer |
| `rule_code` | `VARCHAR(50)` | No | No | MIN_TENURE, MIN_MRR, RISK_TIER, COHORT, MARGIN_THRESHOLD, SUBSCRIPTION_STATUS | Rule classification code |
| `parameter_name` | `VARCHAR(100)`| No | No | String | Attribute name evaluated |
| `operator` | `VARCHAR(20)` | No | No | GT, GTE, LT, LTE, EQ, IN, NOT_IN | Comparison operator |
| `parameter_value` | `VARCHAR(255)`| No | No | String / JSON / Scalar | Threshold value or allowed set |
| `margin_threshold_pct`| `FLOAT` | No | No | $0.0 \le x \le 1.0$, default 0.20 | Minimum required contribution margin after discount |
| `is_active` | `BOOLEAN` | No | No | True / False, default True | Toggle rule evaluation |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |

---

### 2.8 CampaignContact (`campaign_contacts`)
Randomized experiment participant assignments, dispatch records, and responses.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `contact_id` | `VARCHAR(30)` | No | PK | Regex: `^CAM-\d{4}-\d{6}$` | Unique campaign record, e.g. `CAM-2026-000001` |
| `experiment_id` | `VARCHAR(50)` | No | No | String, e.g. `EXP-2026-Q1-RET` | Experiment campaign identifier |
| `customer_id` | `VARCHAR(20)` | No | FK | Exists in `customers.customer_id` | Foreign key referencing Customer |
| `offer_id` | `VARCHAR(30)` | Yes | FK | Exists in `offers.offer_id` | Foreign key referencing Offer (null for control) |
| `experiment_group` | `VARCHAR(20)`| No | No | Treatment, Control | Randomized trial cohort arm |
| `stratum_id` | `VARCHAR(100)`| No | No | String, e.g. `Risk:High_Plan:Scale` | Stratification partition bucket |
| `assigned_at` | `DATETIME` | No | No | Datetime | Timestamp assignment was frozen |
| `delivery_date` | `DATETIME` | Yes | No | Datetime $\ge$ `assigned_at` | Timestamp offer was communicated |
| `delivery_channel` | `VARCHAR(30)`| No | No | Email, In_App, CSM_Outreach | Communication delivery mechanism |
| `delivery_status` | `VARCHAR(30)`| No | No | Sent, Delivered, Failed, Suppressed | Dispatch status |
| `is_eligible` | `BOOLEAN` | No | No | True / False, default True | Gatekeeper eligibility check result |
| `eligibility_notes`| `TEXT` | Yes | No | Text | Rule evaluation audit trail / reasons |
| `response_date` | `DATETIME` | Yes | No | Datetime $\ge$ `delivery_date` | Timestamp customer accepted or declined |
| `response_status` | `VARCHAR(30)`| No | No | Accepted, Rejected, Ignored, Pending | Customer reaction to offer |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |

---

### 2.9 ChurnOutcome (`churn_outcomes`)
Independent ground-truth churn events isolated from model training features.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `churn_id` | `VARCHAR(30)` | No | PK | Regex: `^CHURN-CUS-\d{6}-\d{4}$` | Unique churn outcome ID |
| `customer_id` | `VARCHAR(20)` | No | FK | Exists in `customers.customer_id` | Foreign key referencing Customer |
| `subscription_id` | `VARCHAR(30)`| No | FK | Exists in `subscriptions.subscription_id` | Foreign key referencing Subscription |
| `prediction_cutoff_date`| `DATETIME`| No | Composite Unique | Datetime | Point-in-time prediction horizon boundary |
| `observation_window_start`| `DATETIME`| No | No | Datetime = `prediction_cutoff_date` | Observation window start |
| `observation_window_end`| `DATETIME`| No | No | Datetime = start + 30 days | Observation window close |
| `actual_churned` | `BOOLEAN` | No | No | True / False | Ground truth churn flag |
| `actual_churn_date` | `DATETIME` | Yes | No | Null if retained | Exact cancellation or non-payment cutoff |
| `churn_type` | `VARCHAR(30)`| No | No | Voluntary, Involuntary, Retained | Categorical churn driver class |
| `primary_churn_driver` | `VARCHAR(50)`| No | No | Usage_Drop, Payment_Failure, Support_Frustration, Competitor, None | Primary root cause factor |
| `is_ground_truth` | `BOOLEAN` | No | No | True (Hardcoded) | Sentry marker ensuring isolation from features |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |

---

### 2.10 RetentionOutcome (`retention_outcomes`)
Causal retention measurements, incremental revenue, offer costs, and net ROI.

| Field Name | Type | Nullable | Uniqueness | Allowed / Default Values | Description & Validation Rules |
|---|---|---|---|---|---|
| `retention_id` | `VARCHAR(35)` | No | PK | Regex: `^RET-CAM-\d{4}-\d{6}$` | Unique retention tracking ID |
| `contact_id` | `VARCHAR(30)` | No | FK, Unique | Exists in `campaign_contacts.contact_id` | 1:1 foreign key with CampaignContact |
| `customer_id` | `VARCHAR(20)` | No | FK | Exists in `customers.customer_id` | Foreign key referencing Customer |
| `churn_id` | `VARCHAR(30)` | Yes | FK | Exists in `churn_outcomes.churn_id` | Foreign key referencing ChurnOutcome |
| `retained_after_horizon`| `BOOLEAN`| No | No | True / False | Whether customer stayed active $\ge 30$ days |
| `days_retained` | `INTEGER` | No | No | $\ge 0$ | Additional customer lifecycle days gained |
| `incremental_revenue`| `FLOAT` | No | No | $\ge 0.0$ | Additional MRR earned due to retention |
| `offer_cost_incurred`| `FLOAT` | No | No | $\ge 0.0$ | Net dollar cost of the incentive delivered |
| `net_campaign_value` | `FLOAT` | No | No | Real number | `incremental_revenue` - `offer_cost_incurred` |
| `attribution_status` | `VARCHAR(50)`| No | No | Primary_Attributed, Multi_Attributed_Flagged, Non_Attributed | Attribution audit classification |
| `evaluated_at` | `DATETIME` | No | No | Datetime | Measurement completion timestamp |
| `created_at` | `DATETIME` | No | No | UTC Datetime | Record creation audit timestamp |
