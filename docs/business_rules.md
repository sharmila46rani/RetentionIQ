# RETENTIONIQ — Business Logic & Governance Rules

**Document Version:** 1.0.0
**Domain:** Customer Churn Analytics, Margin Gating & Randomized Experimentation

---

## 1. Customer Churn Definitions

### 1.1 Voluntary vs. Involuntary Churn
RetentionIQ categorizes customer churn into two distinct operational classifications:

1. **Voluntary Churn:**
   - **Trigger:** Subscriber actively requests cancellation or terminates their subscription.
   - **Root Drivers:** Value realization decline, lack of feature adoption, competitive migration, pricing friction, or persistent unresolved support escalations.
   - **Lifecycle State:** `Subscription.status` transitions from `Active` to `Canceled`, with `churn_reason = 'Voluntary'`.

2. **Involuntary Churn (Passive / Delinquency):**
   - **Trigger:** Multiple recurring credit card billing rejections (insufficient funds, expired cards, bank processing blocks) that remain uncollected past the grace period.
   - **Threshold:** $\ge 3$ consecutive failed charge attempts and invoice unpaid $\ge 30$ days past due date.
   - **Lifecycle State:** `Subscription.status` transitions from `Active` to `Delinquent`, then to `Canceled` with `churn_reason = 'Involuntary'`.

### 1.2 30-Day Forward Prediction Horizon
- The platform evaluates churn risk over a standardized **30-day forward observation window**:
  $$\text{Target Window} = [T_{\text{pred}}, T_{\text{pred}} + 30\text{ days}]$$
- A customer is defined as churned within the horizon if their subscription status transitions to `Canceled` on or before $T_{\text{pred}} + 30\text{ days}$.

---

## 2. Feature Engineering & Temporal Integrity (EC-01)

### 2.1 Point-in-Time Cutoff Rule
To ensure absolute mathematical integrity and prevent temporal data leakage:
- **Feature Boundary:** For any prediction executed at timestamp $T_{\text{pred}}$, all feature calculations must exclusively ingest records where:
  $$\text{Timestamp}_{\text{event}} \le T_{\text{pred}}$$
- Any usage telemetry, billing transaction, or support ticket created after $T_{\text{pred}}$ is strictly masked from the feature pipeline.

### 2.2 Mandatory Edge Case 1: Prior Churn Leakage Sentry
- **Problem:** If a subscriber canceled at $T_{\text{churn}} \le T_{\text{pred}}$, predicting their churn probability is invalid and represents backward leakage.
- **Enforcement:**
  - `FeatureEngineeringService` queries `Subscription.canceled_at`.
  - If `canceled_at <= T_pred`, the customer is flagged with violation `EC-01: CHURN_PRECEDES_PREDICTION_DATE`.
  - Flagged accounts are archived in the anomaly audit log and safely excluded from the active prediction candidate pool.

---

## 3. Explainable Churn Risk Scoring & Playbooks

### 3.1 Transparent Weighted Baseline Scoring
The transparent rule-based heuristic scoring engine computes a composite risk score $S \in [0.0, 1.0]$:
$$S = 0.35 \cdot S_{\text{usage}} + 0.30 \cdot S_{\text{billing}} + 0.20 \cdot S_{\text{support}} + 0.15 \cdot S_{\text{tenure}}$$

| Component | Weight | Indicators Evaluated | Threshold Triggers |
|---|---|---|---|
| **Usage Velocity** | 35% | Month-over-month decline %, Active days | Decline $> 40\%$ (+0.65), Active days $\le 5$ (+0.35) |
| **Billing Health** | 30% | Latest invoice status, Failed charges count, Overdue balance | Latest invoice failed (+0.60), Failed charges $\ge 2$ (+0.35) |
| **Support Friction**| 20% | Unresolved tickets, Critical escalations, CSAT score | Unresolved tickets $\ge 2$ (+0.40), Critical ticket (+0.40), CSAT $< 3.0$ (+0.30) |
| **Tenure Vulnerability** | 15% | Customer account age | Tenure $\le 2$ months (+0.60), Tenure $\le 4$ months (+0.30) |

### 3.2 Risk Tiers & Recommended Action Playbooks
- **Low Risk ($S < 0.30$):**
  - *Playbook:* Standard lifecycle engagement; quarterly business review cadence.
- **Medium Risk ($0.30 \le S < 0.60$):**
  - *Playbook:* Automated re-engagement campaign; highlight unused premium features and onboarding webinars.
- **High Risk ($0.60 \le S < 0.80$):**
  - *Playbook:* Deploy targeted 20% retention credit; schedule proactive CSM technical check-in.
- **Critical Risk ($S \ge 0.80$):**
  - *Playbook:* Immediate executive outreach; dedicated CSM intervention; expedited billing/technical hotline support.

---

## 4. Retention Offer & Margin Gating (EC-02)

### 4.1 10-Point Pre-Flight Eligibility Gate
Before any retention offer is dispatched to a customer, the `OfferEligibilityEngine` validates 10 business predicates:
1. **Offer Status:** Offer catalog status must be `Active`.
2. **Offer Validity Window:** Current date must satisfy $\text{Valid From} \le \text{Today} \le \text{Valid To}$.
3. **Subscription Lifecycle:** Subscription must be in `Active` status.
4. **Plan Cohort Match:** Subscription plan must exist in `Offer.eligible_plans`.
5. **Minimum Customer Tenure:** Account tenure must meet or exceed `Offer.min_tenure_months`.
6. **Minimum MRR Threshold:** Subscription MRR must meet or exceed `Offer.min_subscription_mrr`.
7. **Discount Cap Enforcement:** Calculated discount cannot exceed `Offer.max_discount_cap` or `Offer.max_offer_cost`.
8. **Cooldown Period (60 Days):** Customer must not have received an offer contact in the prior 60 days.
9. **Risk Tier Predicate:** Customer risk category must match allowed tiers configured in `EligibilityRule`.
10. **Contribution Margin Guard:** Net projected 3-month contribution margin must remain $\ge 20\%$.

### 4.2 Financial Margin Threshold Formula
Promotions must never generate a negative or dilutive contribution margin:
$$\text{Horizon Revenue} = \text{MRR} \times 3$$
$$\text{Gross Horizon Margin} = (\text{MRR} - \text{Unit Cost}) \times 3$$
$$\text{Net Horizon Value} = \text{Gross Horizon Margin} - \text{Calculated Discount Cost}$$
$$\text{Margin Ratio} = \frac{\text{Net Horizon Value}}{\text{Horizon Revenue}} \ge 20\%$$

### 4.3 Mandatory Edge Case 2: Ineligible Dispatch Interception
- **Problem:** Operational teams attempting to deliver promotional incentives to unqualified subscribers.
- **Enforcement:** If any eligibility predicate or margin check fails, `OfferEligibilityEngine.dispatch_offer_with_guard()` aborts the operation, raises `IneligibleCustomerException`, logs the failed rule codes, and prevents database insertion.

---

## 5. Randomized Controlled Trials (A/B Testing) (EC-03)

### 5.1 Stratified Random Allocation Protocol
To isolate causal impact from confounding covariates:
1. **Population Freezing:** Active subscribers meeting experiment criteria are frozen into an immutable candidate pool.
2. **Stratification:** Candidates are partitioned into strata defined by `Risk Tier × Subscription Plan` (e.g. `High_Scale`, `Critical_Growth`).
3. **50/50 Allocation:** Within each stratum bucket, candidates are shuffled with fixed master seed `20261022` and divided equally:
   - **Treatment Arm (50%):** Delivered the targeted retention offer.
   - **Control Arm (50%):** Kept on status quo lifecycle messaging with offer suppressed.

### 5.2 Mandatory Edge Case 3: Contamination & Leakage Guard
- **Problem:** A customer assigned to both Treatment and Control, or assigned across simultaneous overlapping retention trials.
- **Enforcement:**
  - Database schema enforces `UniqueConstraint('experiment_id', 'customer_id')` on `CampaignContact`.
  - The experiment engine executes a pre-flight candidate scan. If an active assignment exists, it raises `ExperimentConflictException`, aborting invalid duplicate insertions.

---

## 6. Retention Outcomes & Attribution Rules (EC-04)

### 6.1 Statistical Lift & ROI Accounting Formulas
- **Treatment Retention Rate ($R_T$):**
  $$R_T = \frac{\text{Retained Customers in Treatment Group}}{N_{\text{Treatment}}}$$
- **Control Retention Rate ($R_C$):**
  $$R_C = \frac{\text{Retained Customers in Control Group}}{N_{\text{Control}}}$$
- **Absolute Incremental Lift:**
  $$\text{Lift}_{\text{abs}} = R_T - R_C$$
- **Relative Lift:**
  $$\text{Lift}_{\text{rel}} = \frac{R_T - R_C}{R_C}$$
- **Incremental Retained Customers:**
  $$\Delta \text{Customers} = \text{Lift}_{\text{abs}} \times N_{\text{Treatment}}$$
- **Incremental Financial Benefit:**
  $$\Delta \text{Benefit} = \Delta \text{Customers} \times \text{Expected Contribution Margin}$$
- **Incremental Campaign Cost:**
  $$\text{Cost}_{\text{total}} = \sum_{\text{Treatment}} \text{Incurred Offer Cost}$$
- **Financial Return on Investment (ROI):**
  $$\text{ROI} = \frac{\Delta \text{Benefit} - \text{Cost}_{\text{total}}}{\text{Cost}_{\text{total}}} \times 100\%$$

### 6.2 Mandatory Edge Case 4: Multi-Touch Attribution Resolution
- **Problem:** A retained subscriber received multiple promotional contacts over overlapping evaluation windows. Attributing full revenue to each offer creates multi-attribution double-counting.
- **Enforcement:**
  - RetentionIQ implements a documented **Last-Touch Primary Attribution Policy**:
    1. The most recent valid promotional contact is designated `Primary_Attributed` and receives incremental financial credit.
    2. Prior overlapping contacts are tagged `Multi_Attributed_Flagged` with full audit logs preserved, but $0.00$ incremental revenue assigned to protect ROI calculation integrity.
