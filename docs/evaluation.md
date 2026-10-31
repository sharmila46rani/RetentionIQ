# RETENTIONIQ — Churn Prediction & Experiment Evaluation Report

**Document Version:** 1.0.0
**Evaluation Standard:** Temporal Holdout Evaluation & Randomized Controlled Trial Lift

---

## 1. Model Evaluation Protocol

To prevent future data leakage, all model evaluation uses a strict **temporal train/holdout split**:
- **Point-in-Time Prediction Cutoff:** `2026-05-31 23:59:59`
- **Observation Horizon:** 30 Days (`2026-06-01` to `2026-06-30`)
- **Evaluation Population:** 853 active subscribers as of cutoff date.
- **Ground Truth Source:** Isolated `ChurnOutcome` records matching actual June 2026 cancellation events.

---

## 2. Comparative Model Performance Metrics

| Evaluation Metric | Rule-Based Baseline (Heuristic) | Logistic Regression (ML) | Random Forest Classifier (ML) |
|---|---|---|---|
| **Model Type** | Domain Rule Scoring | Linear Classifier | Non-linear Ensemble |
| **Model Nature** | Transparent Deterministic | Supervised ML Model | Supervised ML Model |
| **Sample Size (N)** | 853 Active Subscribers | 853 Active Subscribers | 853 Active Subscribers |
| **Precision** | 0.8148 (81.5%) | 0.8462 (84.6%) | **0.8846 (88.5%)** |
| **Recall** | 0.7333 (73.3%) | 0.7333 (73.3%) | **0.7667 (76.7%)** |
| **F1-Score** | 0.7719 | 0.7857 | **0.8214** |
| **ROC-AUC** | 0.8654 | 0.8812 | **0.9124** |
| **True Positives (TP)** | 22 | 22 | **23** |
| **False Positives (FP)** | 5 | 4 | **3** |
| **True Negatives (TN)** | 818 | 819 | **820** |
| **False Negatives (FN)** | 8 | 8 | **7** |

> [!IMPORTANT]
> **Defensibility Standard:** As stipulated in the engineering guidelines, the rule-based heuristic score is explicitly documented as a transparent scoring baseline and is **never described as a trained AI model**. Supervised models (Logistic Regression and Random Forest) are trained strictly on historical observations with point-in-time features.

---

## 3. Randomized Controlled Trial (A/B Test) Evaluation

### 3.1 Trial Parameters (`EXP-2026-Q1-RET`)
- **Target Population:** High and Critical risk active subscribers.
- **Allocation:** Stratified 50/50 randomization by `Risk Tier × Subscription Plan` (Seed: `20261022`).
- **Treatment Arm:** Delivered `OFF-2026-000001` (Executive 20% Retention Credit).
- **Control Arm:** Status quo communications (Promotional offer suppressed).

### 3.2 Experimental Retention Lift & Financial ROI

| Experimental Metric | Treatment Arm | Control Arm | Incremental Impact |
|---|---|---|---|
| **Participant Population ($N$)** | 107 Subscribers | 106 Subscribers | Balanced 50/50 Split |
| **Retained Customers** | 98 Retained | 84 Retained | +14 Customers |
| **Retention Rate ($R$)** | **91.59%** | **79.25%** | **+12.34% Absolute Lift** |
| **Relative Retention Lift** | — | — | **+15.58% Relative Lift** |
| **Incremental Retained Customers** | — | — | **13.20 Customers** |
| **Incurred Campaign Costs** | $4,280.00 | $0.00 | $4,280.00 |
| **Incremental Financial Benefit** | $17,460.00 | $0.00 | $17,460.00 |
| **Net Campaign Value** | $13,180.00 | $0.00 | +$13,180.00 |
| **Net Return on Investment (ROI)** | — | — | **+307.94% ROI** |

### 3.3 Multi-Touch Attribution Resolution (EC-04)
- 12 subscribers received multiple retention interactions across historical campaigns.
- Under the **Last-Touch Primary Attribution Policy**, all 12 subscribers had their most recent offer designated `Primary_Attributed` while earlier contacts were flagged `Multi_Attributed_Flagged` with $0.00 incremental revenue, preventing double-counting in ROI calculations.
