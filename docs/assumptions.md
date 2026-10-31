# RETENTIONIQ — Operational & Financial Assumptions

**Document Version:** 1.0.0
**Context:** Technical and Financial Assumptions for the YottaFlex AI Code Challenge

---

## 1. Data Timeline & Horizon Assumptions

1. **Temporal Horizon:**
   - Baseline historical telemetry spans 18 calendar months from **January 1, 2025** through **June 30, 2026**.
   - Signup cohorts are staggered across the initial 12 months to generate realistic varying customer tenure (ranging from 6 to 18 months).
2. **Prediction Horizon & Cutoff:**
   - Standard prediction cutoff boundary: **May 31, 2026 (Month 17)**.
   - Forward prediction observation horizon: **30 days (June 1, 2026 to June 30, 2026 / Month 18)**.
3. **Master Reproducibility Seed:**
   - Fixed random state: `20261022`.
   - Used uniformly across NumPy random number generators, Python random module, and scikit-learn classifiers to ensure bit-for-bit identical datasets and test metrics.

---

## 2. Product Plans, Pricing & Unit Economics

The subscription economics model follows enterprise B2B SaaS industry standards with explicit infrastructure and support delivery costs:

| Plan Name | Monthly MRR (USD) | Unit Delivery Cost (COGS) | Base Gross Margin ($) | Base Margin Ratio (%) |
|---|---|---|---|---|
| **Starter** | $49.00 | $8.00 | $41.00 | 83.7% |
| **Growth** | $149.00 | $22.00 | $127.00 | 85.2% |
| **Scale** | $399.00 | $60.00 | $339.00 | 85.0% |
| **Enterprise** | $999.00 | $140.00 | $859.00 | 86.0% |

- **Billing Cycles:** 80% Monthly recurring, 20% Annual upfront billing.
- **Trial Period:** 14-day free trial on signup before first billing invoice.

---

## 3. Behavioral Archetypes & Churn Calibration

Subscribers are initialized into four behavioral archetypes:
1. **Healthy / Loyal (72% of subscriber base):**
   - High login frequency, stable/increasing active days, zero billing charge failures, CSAT scores between 4 and 5.
   - Low natural churn probability ($\sim 0.7\%$).
2. **At-Risk Voluntary — Usage Drop (14% of subscriber base):**
   - Progressive telemetry decay (-20% to -60% drop in active days and session duration over a 3-month window).
   - High voluntary cancellation probability ($\sim 50\%$).
3. **At-Risk Involuntary — Payment Failure (7% of subscriber base):**
   - Recurring payment charge rejections (`Insufficient_Funds`, `Expired_Card`, `Bank_Reject`).
   - High involuntary cancellation probability ($\sim 50\%$) following 2–3 failed retry attempts.
4. **Support Friction (7% of subscriber base):**
   - Frequent tickets, critical priority bug escalations, prolonged resolution hours ($>72\text{ hours}$), and low satisfaction ratings (CSAT 1–2).
   - Elevated voluntary cancellation probability ($\sim 40\%$).

### 3.1 Churn Calibration Target
- **Challenge Requirement:** Overall churn bounded between 5.0% and 20.0%.
- **Engine Output:** Calibrated to **14.70%** overall churn (113 voluntary, 34 involuntary per 1,000 subscribers), positioning the metric stably in the target band.

---

## 4. Promotion & Eligibility Financial Assumptions

1. **Retention Lifetime Horizon:**
   - When evaluating unit contribution margin for promotional eligibility, a customer successfully retained is assumed to remain active for a minimum **3-month evaluation horizon**.
2. **Minimum Contribution Margin Threshold:**
   - No retention offer may dilute net margin below **20.0%** of expected 3-month contract revenue.
   - Formula:
     $$\text{Net 3-Month Value} = 3 \times (\text{MRR} - \text{Unit Cost}) - \text{Discount Cost} \ge 0.20 \times (3 \times \text{MRR})$$
3. **Offer Receptivity (Response Rate):**
   - In randomized experiments, customers assigned to the Treatment arm exhibit an empirical offer acceptance rate of $\sim 65\%$.

---

## 5. Causal Evidence Disclaimer

- **Important Methodological Note:**
  As required by sound data science practices, simulated randomized controlled trial outcomes in this demonstration platform reflect probabilistic synthetic business rules and **do not constitute actual real-world causal evidence**.
  Real-world causal attribution requires prospective production deployment, rigorous holdout control groups, and adherence to experimental runtime protocols.
