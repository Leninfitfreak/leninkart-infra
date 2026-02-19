# Project Notes (LeninKart Infra)

This file tracks ongoing issues, actions taken, and resolution steps. Append to this file for each change until project completion.

## 2026-02-09
Issue: Product/Order APIs returning 503 from UI; DB creds mismatch after moving to Vault; Kafka client disconnects and TLS verify errors in sidecars.

Actions Taken (Repo Changes):
- Added Vault auth reviewer ServiceAccount + ClusterRoleBinding in `platform/vault/config/06-vault-auth-rbac.yaml`.
- Added note `docs/VAULT_SETUP_NOTE.md` describing Vault setup and ExternalSecrets integration.
- Removed hardcoded Postgres secret manifest `platform/postgres/postgres-secret.yaml`.
- Added ExternalSecret for Postgres admin creds: `platform/external-secrets/applications/postgres-admin-secret.yaml`.
- Fixed invalid YAML in `platform/external-secrets/applications/product-service-db-secret.yaml`.
- Updated product/order deployments to load Vault secrets via `envFrom` when enabled:
  - `applications/product-service/helm/templates/deployment.yaml`
  - `applications/order-service/helm/templates/deployment.yaml`
- Removed hardcoded DB username/password from dev values and set DB secret names:
  - `applications/product-service/helm/values-dev.yaml`
  - `applications/order-service/helm/values-dev.yaml`
- Updated Kafka bootstrap server to service DNS (not pod DNS):
  - `applications/product-service/helm/values-dev.yaml`
  - `applications/order-service/helm/values-dev.yaml`
- Added Istio DestinationRules to enforce `ISTIO_MUTUAL` for services (ingress → service):
  - `platform/istio/config/destinationrules.yaml`
- Switched Postgres StatefulSet to a new identity to force fresh init (declarative reset):
  - `platform/postgres/postgres-statefulset.yaml` now uses `postgres-v2` + new PVC.

Actions Taken (Cluster/Runtime):
- Unsealed Vault and configured Kubernetes auth.
- Wrote Vault policy `leninkart-policy` and role `leninkart-role`.
- Added Vault secrets for DB creds:
  - `secret/leninkart/product-service/database`
  - `secret/leninkart/order-service/database`
  - `secret/leninkart/postgres/admin`
- Applied ExternalSecrets in `platform/external-secrets/applications`.

Current Status:
- Postgres is now running as `postgres-v2-0` with new PVC and Vault-backed credentials.
- Product/Order pods are running; endpoints exist.
- UI still shows intermittent 503 due to mTLS/Kafka issues before sync.

Next Steps:
- Commit and push the latest GitOps changes.
- Sync Argo apps: `istio-config-dev`, `dev-product-service`, `dev-order-service`, `postgres-dev`.
- Restart product/order deployments after sync to pick up new config.
- Verify:
  - `kubectl -n dev get endpoints leninkart-product-service`
  - `kubectl -n dev get endpoints leninkart-order-service`
  - UI `/api/products` and `/api/orders` return 200.

## 2026-02-09 (Follow-up)
Issue: Browser showing `TLS_error: CERTIFICATE_VERIFY_FAILED` and 503s from gateway to `/`, `/api/products`, `/api/orders`.

Actions Taken (Repo Changes):
- Updated Istio DestinationRules to **disable TLS** for dev services to stop gateway → service TLS verification failures:
  - `platform/istio/config/destinationrules.yaml`

Next Steps:
- Commit + push this change.
- Sync Argo app `istio-config-dev`.
- Restart `product-service` and `dev-order-service-order-service` deployments after sync.

## 2026-02-09 (Follow-up 2)
Issue: TLS verify failures persist on Kafka traffic and 503s still seen from gateway.

Actions Taken (Repo Changes):
- Added namespace-level PeerAuthentication in `dev` to allow plaintext (PERMISSIVE):
  - `platform/istio/config/peerauthentication-dev.yaml`

Next Steps:
- Commit + push.
- Sync Argo app `istio-config-dev`.
- Restart `product-service` and `dev-order-service-order-service` deployments.

## 2026-02-09 (Frontend + Services)
Issue: Need a production-quality login UI and user-centric data across orders/products.

Actions Taken (Repo Changes):
- Frontend (C:/Projects/Services/leninkart-frontend):
  - Replaced `src/index.js` with a login-first UI, user stats, and richer layout.
  - Replaced `src/index.css` with new design system, gradients, and responsive layout.
  - Added user tracking in API calls:
    - `X-User` header on buy requests
    - `createdBy` on product creation
- Product Service (C:/Projects/Services/leninkart-product-service):
  - Added `createdBy` field to `Product`.
  - Included user in Kafka payload for order creation.
- Order Service (C:/Projects/Services/leninkart-order-service):
  - Added `userName` field to `OrderEntity`.
  - Persisted user from Kafka payload in `OrderConsumer`.

Next Steps:
- Commit and push dev branch changes in the three services repos.
- Deploy new frontend image/tag and update infra Helm values for dev.

## 2026-02-10 (Auth + User-scoped Data)
Issue: Add login page + JWT auth with user-scoped products and orders.

Actions Taken (Repo Changes):
- Frontend (C:/Projects/Services/leninkart-frontend):
  - Implemented login page that calls `POST /auth/login` and stores JWT.
  - Added axios interceptor to attach `Authorization: Bearer <token>` to API calls.
  - Updated dashboard to show user-based data and stats.
  - Updated UI theme to LeninKart branding with primary color #1976D2.
- Product Service (C:/Projects/Services/leninkart-product-service):
  - Added JWT auth support (`JwtService`, `JwtAuthFilter`, `AuthController`).
  - Added in-memory auth user store (configurable via `APP_AUTH_USERS`).
  - Enforced user-scoped product visibility; `createdBy` set from JWT user.
  - Added `app.jwt.*` and `app.auth.users` configuration.
- Order Service (C:/Projects/Services/leninkart-order-service):
  - Added JWT auth filter and `JwtService`.
  - Enforced user-scoped order visibility using `userName` from JWT.
  - Added `app.jwt.*` configuration.
- Infra (C:/Projects/infra/leninkart-infra):
  - Added `/auth` route to product-service in `platform/istio/config/virtualservice.yaml`.

Next Steps:
- Build/push new images for frontend/product/order services.
- Update dev Helm values with new image tags.
- Sync Argo apps: `frontend-dev`, `dev-product-service`, `dev-order-service`, `istio-config-dev`.
- Provide `APP_JWT_SECRET` and `APP_AUTH_USERS` in dev environment (Vault/ExternalSecrets).

## 2026-02-10 (Hardcoded JWT config in dev)
Issue: Use hardcoded JWT/auth config for now; Vault integration later.

Actions Taken (Repo Changes):
- Added hardcoded JWT + auth user values in dev Helm values:
  - `applications/product-service/helm/values-dev.yaml`
  - `applications/order-service/helm/values-dev.yaml`

Values Added:
- `APP_JWT_SECRET=leninkart-dev-secret`
- `APP_JWT_ISSUER=leninkart`
- `APP_JWT_TTL_SECONDS=86400`
- `APP_AUTH_USERS=leninkart:leninkart123:USER,admin:admin123:ADMIN` (product-service only)

Next Steps:
- Sync Argo apps `dev-product-service` and `dev-order-service`.
- Rebuild/push images if not already done, then update image tags in values.

## 2026-02-10 (Service repo pushes)
Issue: Push frontend/product/order service changes to dev branch.

Actions Taken:
- Committed and pushed service changes to dev:
  - Frontend: 5073c36 (dev)
  - Product service: d01bbc1 (dev)
  - Order service: b28b6ac (dev)

Notes:
- These are separate repos, so commit hashes differ by design.

## 2026-02-10 (JWT build fix)
Issue: Maven build failed due to JwtParserBuilder.verifyWith expecting SecretKey.

Actions Taken (Repo Changes):
- Updated JWT key type to `javax.crypto.SecretKey` in both services:
  - `C:/Projects/Services/leninkart-order-service/src/main/java/com/example/order/auth/JwtService.java`
  - `C:/Projects/Services/leninkart-product-service/src/main/java/com/example/product/auth/JwtService.java`

Next Steps:
- Rebuild service images and push new tags.

## 2026-02-10 (Workflow path fixes)
Issue: GitHub Actions workflows updating wrong Helm values path (helm/... not found).

Actions Taken (Repo Changes):
- Updated values file paths in service workflows to match infra layout:
  - Frontend: `.github/workflows/ci-cd.yaml` -> `applications/frontend/helm/values-*.yaml`
  - Product service: `.github/workflows/ci-cd.yml` -> `applications/product-service/helm/values-*.yaml`
  - Order service: `.github/workflows/ci-cd.yaml` -> `applications/order-service/helm/values-*.yaml`

Next Steps:
- Commit + push these workflow updates to each service repo.

## 2026-02-10 (Infra sync + rollout)
Issue: Sync infra dev branch and apply service restarts.

Actions Taken:
- Rebased and pushed infra dev with updated product/order values and Istio route.
- Rolled out deployments in dev namespace:
  - frontend
  - product-service
  - dev-order-service-order-service

## 2026-02-10 (Signup + DB users)
Issue: Login only supported hardcoded users; add signup with persistent users.

Actions Taken (Repo Changes):
- Frontend (C:/Projects/Services/leninkart-frontend):
  - Added login/signup toggle and POST /auth/signup support.
  - Improved auth error handling for 409/401 responses.
- Product Service (C:/Projects/Services/leninkart-product-service):
  - Added UserAccount entity + UserRepository (users table).
  - Added UserService with BCrypt password hashing.
  - Added UserSeeder to seed accounts from APP_AUTH_USERS.
  - /auth/signup now creates users and returns JWT.
  - Added spring-security-crypto dependency.

Next Steps:
- Build and push updated frontend + product-service images.
- Update dev Helm image tags and sync Argo.

## 2026-02-10 (Workflow env cleanup)
Issue: Workflow defaults still referenced old helm/ path in env.

Actions Taken (Repo Changes):
- Updated workflow env defaults to use applications/* path:
  - Product service: `.github/workflows/ci-cd.yml` (CHART_PATH, VALUES_FILE)
  - Order service: `.github/workflows/ci-cd.yaml` (VALUES_FILE)

Next Steps:
- Commit + push these workflow updates on dev.

## 2026-02-10 (Frontend signup UX refinement)
Issue: Signup was auto-logging users in immediately after account creation.

Actions Taken (Repo Changes):
- Updated `C:/Projects/Services/leninkart-frontend/src/index.js`:
  - Signup no longer creates a session automatically.
  - After successful signup, user is switched to login mode with success notice.
  - Added additional signup fields and validation:
    - Full name
    - Work email format check
    - Confirm password match
    - Password minimum length
  - Replaced generic UI labels with more professional titles and copy.
- Updated `C:/Projects/Services/leninkart-frontend/src/index.css`:
  - Added `.notice` style for successful account creation message.

Next Steps:
- Build and push new frontend image.
- Update infra frontend image tag in dev values and sync Argo app.

## 2026-02-10 (Email-based auth alignment)
Issue: Frontend signup/login flow needed email-first inputs and backend/database needed matching fields and validation.

Actions Taken (Repo Changes):
- Frontend (C:/Projects/Services/leninkart-frontend/src/index.js):
  - Login now sends `email` + `password`.
  - Signup now sends `fullName` + `email` + `password`.
  - Updated validation and auth error messaging to email-based wording.
  - Signup still requires manual sign-in after account creation.
- Product service auth updates:
  - `AuthRequest` now supports `email`, `fullName`, and legacy `username` fallback.
  - `AuthController` now uses email-first login and validates signup with `fullName/email/password`.
  - `UserAccount` now persists `email` and `full_name` columns.
  - `UserRepository` includes `findByEmailIgnoreCase` and `existsByEmailIgnoreCase`.
  - `UserService` now creates users with full name + email and authenticates email-first (username fallback for legacy users).
  - Seeder now maps legacy non-email seed users to synthetic email for compatibility.

Validation Note:
- Local Maven CLI is unavailable in this environment (`mvn` not found), so compile validation was not run here.

## 2026-02-10 (Docker + workflow hardening)
Issue: Align Docker/runtime behavior and workflow infra checkout across all services for reliable dev releases.

Actions Taken (Repo Changes):
- Frontend (`C:/Projects/Services/leninkart-frontend`):
  - Dockerfile: switched to `COPY package*.json` and quieter npm install flags.
  - Workflow: made infra repo reference owner-agnostic (`github.repository_owner/leninkart-infra`).
- Product service (`C:/Projects/Services/leninkart-product-service`):
  - Dockerfile: added dependency prefetch, standardized Maven build flags, moved runtime to JRE image, exposed 8081, simplified entrypoint.
  - Workflow: checkout infra into `infra/` path and run updates/commit from that path.
- Order service (`C:/Projects/Services/leninkart-order-service`):
  - Dockerfile: standardized Maven build flags (`-T1C`) and runtime comment cleanup.
  - Workflow: checkout infra into `infra/` path and run updates/commit from that path.

## 2026-02-10 (Workflow push race fix)
Issue: Service release workflows failed to push infra updates due to concurrent writes on `dev`.

Actions Taken:
- Updated all service workflows to handle infra push race safely:
  - Added `git pull --rebase origin $INFRA_BRANCH` before push.
  - Added retry loop (3 attempts) for push step.
  - Switched git config usage from global to repo-local in product/order workflows.
- Files updated:
  - `C:/Projects/Services/leninkart-frontend/.github/workflows/ci-cd.yaml`
  - `C:/Projects/Services/leninkart-product-service/.github/workflows/ci-cd.yml`
  - `C:/Projects/Services/leninkart-order-service/.github/workflows/ci-cd.yaml`

## 2026-02-13 (Signup 500 fix)
Issue: Signup returned generic auth error due to backend 500 on DB unique constraint (`users.username`).

Root Cause:
- Existing row already had `username=<email>` but signup pre-check only validated `email` field.
- Insert then failed with `duplicate key value violates unique constraint` and surfaced as 500.

Fix Applied:
- Updated `C:/Projects/Services/leninkart-product-service/src/main/java/com/example/product/auth/AuthController.java`:
  - Signup now checks both `findByEmail(email)` and `findByUsername(email)`.
  - Added `DataIntegrityViolationException` catch and returns HTTP 409 Conflict.

Expected Result:
- Existing account attempt now returns 409 and frontend shows "User already exists. Please sign in." instead of generic failure.

## 2026-02-13 (Kafka producer bootstrap alignment)
Issue: Product-service producer was still using `kafka:9092` from custom env lookup, while consumer/service config uses dev service DNS.

Actions Taken:
- Updated product-service Kafka bootstrap source to Spring property/env:
  - `C:/Projects/Services/leninkart-product-service/src/main/resources/application.properties`
  - `spring.kafka.bootstrap-servers=${SPRING_KAFKA_BOOTSTRAP_SERVERS:kafka.dev.svc.cluster.local:9092}`
- Refactored custom producer config to consume `spring.kafka.bootstrap-servers` via `@Value`:
  - `C:/Projects/Services/leninkart-product-service/src/main/java/com/example/product/config/KafkaProducerConfig.java`

Service Check Result:
- `order-service`: already aligned to `SPRING_KAFKA_BOOTSTRAP_SERVERS` with dev DNS.
- `frontend`: no Kafka client config.

## 2026-02-13 (Kafka scale to 2 brokers)
Issue: Need 2 Kafka brokers for improved availability and multi-broker replication in dev.

Actions Taken (Repo Changes):
- Updated Kafka StatefulSet to 2 replicas with dynamic pod-aware broker identity/listeners:
  - `platform/kafka/kafka.yaml`
  - Added startup command to derive `KAFKA_NODE_ID` from pod ordinal.
  - Added dynamic `KAFKA_ADVERTISED_LISTENERS` per pod hostname.
  - Updated controller quorum voters to include broker 1 and 2.
  - Set replication factors to 2 for offsets/transaction/default topics.
- Updated app bootstrap server lists to both broker endpoints:
  - `applications/product-service/helm/values-dev.yaml`
  - `applications/order-service/helm/values-dev.yaml`

Operational Note:
- With only 2 brokers, keep `min.insync.replicas=1` for availability during single-node disruption.

## 2026-02-13 - Kafka 2-broker HA recovery (dev)
- Issue:
  - Kafka scale-out from 1 broker to 2 brokers failed with KRaft voter mismatch on `kafka-0`.
  - Error seen: `Configured voter set: [1, 2] ... state file: [1]`.
  - `order-service` consumer showed repeated bootstrap disconnects.
- Actions taken:
  - Kept Kafka at 2 replicas in infra.
  - Updated `platform/kafka/kafka.yaml` with init container `kafka-storage-prepare` to:
    - run one-time KRaft metadata reset marker logic (`.kraft-2node-init`),
    - enforce `chown -R 1000:1000 /var/lib/kafka/data` before Kafka starts.
  - Committed and pushed to `dev` branch.
  - Force recreated Kafka pods to apply new pod template.
  - Restarted `dev-order-service-order-service`, `product-service`, `frontend`, and `postgres-v2` during recovery window.
- Verification:
  - `kafka-0` and `kafka-1` are both `2/2 Running`.
  - `dev-order-service-order-service` is `2/2 Running`.
  - Latest order-service logs show successful consumer group join and partition assignment.
- Infra commit:
  - `1abe69c` (`fix(kafka): prepare pvc permissions and one-time kraft metadata reset for 2-broker quorum`)

## 2026-02-13 - Added Infra Learning Dump
- Added `INFRA_LEARNING_DUMP.md` (root) to document repo structure, GitOps flow, and explain key manifests for learning.

## 2026-02-18 - Enable OTel traces/metrics export from app services
- Issue:
  - Jaeger UI showed `Service (0)` and no traces.
  - OTel collector was healthy, but app pods were not sending telemetry.
- Root cause:
  - `otel:` block existed in values, but Helm templates render only `.Values.env` into container env.
  - No `OTEL_*` runtime variables were present in `product-service` and `order-service` pods.
- Fix applied:
  - Added telemetry env vars under `env` in:
    - `applications/product-service/helm/values-dev.yaml`
    - `applications/order-service/helm/values-dev.yaml`
  - Added: `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_TRACES_EXPORTER`, `OTEL_METRICS_EXPORTER`, `OTEL_LOGS_EXPORTER`, `MANAGEMENT_TRACING_ENABLED`, `MANAGEMENT_TRACING_SAMPLING_PROBABILITY`.
- Expected result after Argo sync/redeploy:
  - Services appear in Jaeger dropdown.
  - Traces visible for product/order requests.

## 2026-02-19 - Add ready-made Grafana dashboards (JVM/HTTP/Kafka)
- Added dashboard provisioning for Grafana using file-based providers.
- Added prebuilt dashboard ConfigMap with 3 dashboards:
  - `LeninKart JVM Overview`
  - `LeninKart HTTP Overview`
  - `LeninKart Kafka Overview`
- Updated Grafana deployments to mount:
  - datasource provisioning
  - dashboard provider provisioning
  - dashboard JSON files
- Note:
  - Panels show data only for metrics currently present in Prometheus.
  - If Kafka/JVM series are missing, update scrape pipeline accordingly.
