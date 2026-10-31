# RETENTIONIQ — System Limitations & Future Roadmap

**Document Version:** 1.0.0
**Context:** Honest Engineering Appraisal for Technical Defensibility

---

## 1. Synthetic Data & Behavioral Modeling Limitations

1. **Synthetic Process Simplification:**
   - The synthetic data generation engine models customer behavior using correlated state transition distributions and decay coefficients. While realistic and calibrated (14.70% churn), synthetic data cannot model exogenous macroeconomic shocks, sudden industry-wide price wars, or unpredictable market disruptions.
2. **Fixed Observation Cadence:**
   - Usage telemetry is captured as monthly aggregates (`UsageSnapshot`). While optimal for contract-level SaaS analytics, sub-daily usage spikes (e.g. hourly API throttle limits) require streaming telemetry infrastructure (such as Apache Kafka or Flink).
3. **Storage & Scaling Ceiling:**
   - SQLite is selected for local zero-dependency development and easily handles the required 20,000 subscribers (~360,000 snapshots). For enterprise deployments exceeding 1,000,000 concurrent subscribers, a distributed columnar analytical store (e.g., ClickHouse, Snowflake, or Google BigQuery) should serve analytical queries while MySQL 8.0 handles OLTP operations.

---

## 2. Machine Learning & Predictive Limitations

1. **Fixed 30-Day Forward Horizon:**
   - Models are calibrated for a 30-day forward prediction window. For multi-quarter contract renewal planning (e.g., annual enterprise renewals), survival analysis techniques (such as Kaplan-Meier estimators or Cox Proportional Hazards models) should supplement classification algorithms.
2. **Tabular Feature Representation:**
   - Features represent structured behavioral metrics (session duration, login drops, payment retries). Unstructured text signals (e.g. sentiment from raw support ticket transcripts or sales email threads) are not currently processed with NLP/LLM embeddings.

---

## 3. Causal Experimentation & Attribution Limitations

1. **Synthetic Causal Lift:**
   - Simulated treatment/control experiments demonstrate how randomized trials, stratification, and lift formulas operate algorithmically. However, synthetic response functions do not replace actual human behavioral experiments in a live production environment.
2. **Attribution Simplification:**
   - The platform implements **Last-Touch Primary Attribution** to resolve multi-touch campaign conflicts (EC-04). While operationally robust and simple to audit, complex multi-channel enterprise environments may benefit from Algorithmic Multi-Touch Attribution (e.g., Markov Chains or Shapley Value attribution).

---

## 4. Security, Authentication & Session Limitations

1. **Demonstration Persona-Based Authorization vs. Real Authentication:**
   - The application implements **Role-Based Access Control (RBAC)** at the backend route level via the `@require_role` decorator in `app/services/auth_service.py` across five business actors (`admin`, `marketing`, `support`, `analyst`, `customer`).
   - However, **real user authentication is NOT implemented**. There is no user account database table, no password hashing (e.g. bcrypt/Argon2), no registration or login/logout workflow, and no cryptographic authentication tokens (JWT or OAuth2). Persona identity is controlled entirely via Flask session (`session['actor_key']`) and the `/switch-role/<role>` route.
   - *Production Disclaimer:* In a production multi-tenant SaaS environment, an enterprise identity provider (IdP) such as Auth0, Okta, Keycloak, or AWS Cognito must be integrated, or a dedicated `users` table with salted password hashes and multi-factor authentication (MFA) must be introduced.
2. **Missing Anti-CSRF Token Middleware:**
   - While state-modifying actions are restricted to HTTP POST methods and browser session cookies use `SameSite=Lax` and `HttpOnly=True` hardening, the platform currently lacks cryptographic per-request CSRF tokens (such as `Flask-WTF` / `WTForms` CSRF validation).
   - In production, CSRF middleware must be enabled on all HTML form submissions and mutation APIs.
3. **Local Database Security:**
   - SQLite is used for local zero-dependency development. While SQLite foreign keys and relational integrity are strictly enforced, SQLite lacks native network encryption or fine-grained table/column-level user permissions. Production deployments should transition to MySQL 8.0+ / PostgreSQL with TLS 1.3 encryption in transit and encrypted data-at-rest volumes.

---

## 5. Technical Roadmap & Future Enhancements

- [ ] **Enterprise User Authentication:** Implement database-backed user identity with bcrypt password hashing, session tokens, and MFA.
- [ ] **CSRF Token Middleware:** Introduce `Flask-WTF` CSRF token validation across all forms and asynchronous mutation requests.
- [ ] **Streaming Telemetry Ingestion:** Transition from monthly snapshots to real-time event streaming via Redis / Kafka.
- [ ] **LLM Sentiment Extraction:** Ingest raw customer support transcripts and feedback surveys to calculate an NLP-derived CSAT risk score.
- [ ] **Dynamic Pricing Optimization:** Implement contextual multi-armed bandits to personalize offer discount percentages dynamically based on customer price elasticity.
