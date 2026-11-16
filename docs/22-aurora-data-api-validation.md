# Aurora Data API feasibility experiments

This is an isolated experiment, not a production persistence migration or an AWS
deployment of the website. The application continues to use SQLAlchemy, psycopg,
session advisory locks and LangGraph PostgresSaver. No production routes or schemas
are changed. The experiment uses fictional data and fixed 1,536-dimensional vectors;
it never constructs a live generation/embedding client.

## What is being tested

| Mechanism | Acceptance evidence |
| --- | --- |
| Checkpoints | The actual application workflow can draft, interrupt for review, revise and approve with a new saver instance; recovery after committed approval creates one response. Typed payloads larger than a Data API response round-trip in bounded chunks. Partial writes roll back; acknowledgement loss and replay are idempotent. |
| Student exclusion | Independent workers have one winner per student. Database-time expiry permits takeover with an increasing token. Old owners cannot renew, release another owner's lease, write business effects or publish checkpoints. Fencing and mutation share one short transaction. |
| Hybrid retrieval | The unchanged application search, candidate fusion, references and parent packing match a direct SQLAlchemy/psycopg baseline. Tests cover source/profile/date restrictions, deterministic ties, duplicate sources, concurrent source changes and large Unicode parent reads. |

`backend/experiments/data_api/` supplies an explicit SQL transport, experimental
checkpointer, lease implementation and a narrow **read-only retrieval adapter**. It is
not a SQLAlchemy dialect. The saver stores full typed checkpoint values rather than
deduplicating channel versions; storage efficiency and a complete asynchronous saver
interface remain outside this prototype.

Checkpoint objects and pending writes use 16 KiB binary parts, a checksum and an
atomic transaction. Pending writes retain LangGraph's task-path/index ordering.
Large parent text is read in 4,096-character pieces inside the same read snapshot.
Array inputs are JSON parameters expanded and cast in SQL. Model calls and reranking
never run inside a database transaction. Data API's transaction timeout means a
session advisory lock cannot simply be held across arbitrary model work.

Local workflow tests use a real dedicated PostgreSQL business database and a
PostgreSQL-backed **Data API protocol double** for checkpoints. This is useful recovery
evidence, but does not establish live Aurora compatibility or an all-Data-API business
repository. Live Lambda probes use the application's State type in a smaller interrupt
graph; the report names this narrower scope explicitly.

## Reproduce locally

From `backend/`, install the optional validation tools and run against the existing
dedicated test database. Follow the root README to prepare that database first.

```sh
uv sync --locked --group aws-validation
uv run --locked --group aws-validation --env-file .env.example pytest \
  tests/unit/test_data_api_*.py \
  tests/integration/agent/test_data_api_checkpoint.py \
  tests/integration/test_data_api_validation.py
```

Without `TEST_DATABASE_URL`, integration cases are skipped, not passed. Local tests
exercise PostgreSQL semantics plus simulated AWS payload limits and failure injection;
AWS-specific engine behavior still requires the live experiment.

## Terraform initialization and disposable AWS experiment

Temporary infrastructure is created and destroyed with Terraform. `infrastructure/bootstrap/` creates the
persistent `dance-studio-deployer` role and two fixed runtime roles. The approved
bootstrap trusts only the configured account's `aiengineer` user. The deployer cannot
create roles or edit IAM policies: it can only pass the two bounded runtime roles.
Network mutation requires validation Project/Purpose tags in Sydney; named databases,
functions, secrets and logs use `data-api-validation-*`. Lambda code is explicitly
denied network-interface mutations while Lambda service ENI management remains allowed.

Initialize once using the existing user's IAM role-management permissions:

```sh
terraform -chdir=infrastructure/bootstrap init
terraform -chdir=infrastructure/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=infrastructure/bootstrap apply bootstrap.tfplan
```

The user must be permitted to assume `dance-studio-deployer`. These initialization
roles persist for future runs and have no provisioned compute charge. Keep bootstrap
state private and available; do not import existing shared project IAM policies.

From `backend/`, run the experiment with the existing AWS profile. Terraform's provider
assumes the deployment role automatically; temporary credentials are not committed:

```sh
uv sync --locked --group aws-validation
uv run --locked --group aws-validation python -m experiments.data_api live \
  --output-dir experiments/data_api/results/terraform-unique-name
```

The CLI builds a Linux x86-64 Lambda archive using the lockfile's pinned versions,
copies `infrastructure/express-validation/` into a private results directory, and runs
init, saved plan, apply, validation and destroy. Use `--lambda-zip` to reuse a compatible
archive. `template` prints this native Express configuration. The AWS Cloud Control
provider is used because the pinned native AWS provider does not expose Express
creation. Legacy CloudFormation helpers remain for existing regression tests only.

The Free Plan rejected standard private Aurora, so this experiment uses Aurora Express
in Sydney, with zero minimum capacity and a two-ACU maximum. Express has an IAM-authenticated
internet access gateway and no customer VPC. Both Lambda functions are non-VPC and have
no HTTP function URL. There is no NAT or private endpoint. This is an account-plan
constraint and demo choice, not a claim that Express is always preferable.

The runner grants the deployment role IAM database access to `postgres` and the baseline
role access to `baseline`, each scoped to the actual cluster Resource ID. Through verified
TLS, the initializer creates the test database, pgvector extension, fixture schema and
two limited database users. Data API uses a separate password user in Secrets Manager;
Express's master IAM user cannot authenticate to Data API. The direct psycopg baseline
uses IAM authentication and read-only fixture access. The runner enables Data API using RDS's `EnableHttpEndpoint` operation after
initialization. Cloud Control rejected an update that changed only HTTP enablement with
a create-only `WithExpressConfiguration` error; this bounded API call avoids that provider
limitation and needs no additional IAM permission. Temporary exact-cluster IAM grants are removed in
cleanup, including after a partially failed permissions apply. This requires the original
bootstrap user's IAM permissions; the assumed deployer cannot edit its own policies.

Tests use fake model data and compare retrieval with a `1e-6` score tolerance. The
runner records actual engine/extension versions, API counts, bounded response sizes,
zero-capacity metrics and subsequent cold resume. A failed apply still triggers cleanup;
an interrupted child is signaled and reaped before cleanup. The ownership-checked helper
deletes only a matching validation cluster and writer, without final snapshots, before
Terraform destroy. A destroy hook also supports manual Terraform cleanup. Both deletion
and IAM revocation are attempted independently; failures are reported explicitly. Runtime/provider timeouts are not a billing ceiling.

Terraform state contains generated database credentials. Results directories are
created with mode 0700, ignored by Git, and must remain private. If automatic cleanup
fails, run `terraform -chdir=RESULTS/terraform destroy` with the same profile;
non-secret input variables are saved in that run's private `terraform.tfvars.json`.
If the initial apply stopped before recording the destroy hook, invoke
`python -m experiments.data_api.delete_express --name EXACT_RUN_CLUSTER --role DEPLOYER_ARN`
from `backend/` first. Retain state until deletion is verified. Revoke temporary grants with
`terraform -chdir=infrastructure/bootstrap apply -var=express_cluster_resource_id=`
after reviewing a fresh plan. Bootstrap roles
are intentionally separate from temporary resources and are not destroyed by a run.

`report.json` distinguishes passed, failed, incomplete and not_run, with an in_progress
snapshot while waiting for auto-pause and cleanup. A mechanism pass
is not a full migration approval; `migration_ready` remains false.

## Current evidence and decision

On 2026-11-16, Terraform provisioned an Express cluster and both Lambda functions.
The IAM/TLS admin connection succeeded, but database initialization returned PostgreSQL
`InsufficientPrivilege`. No checkpoint, mutex or retrieval probe ran in that attempt.
Terraform deleted all temporary resources without a final snapshot and revoked both
exact-cluster IAM database grants. Diagnostics located the missing `SET ROLE validator` permission when assigning schema
ownership. The initializer now grants this explicitly. A subsequent run completed database
initialization, but Cloud Control rejected endpoint enablement as an Express create-only
property update. The runner now uses the RDS enablement operation described above.
A later run confirmed admin connectivity and initialization again; its first Data API
query returned `HttpEndpointNotEnabledException` immediately after enablement. Initial
readiness now retries this propagation state for up to five minutes, alongside known
resume/unavailability states, while access denial fails immediately. Admin connection
retries retain verified TLS and redact IAM tokens from diagnostics. The next mechanism
rerun is pending cleanup; no live migration readiness is claimed.

Local focused validation passed 60 tests, including actual PostgreSQL recovery/retrieval
and mocked provisioning/permission failure cleanup. The full backend run passed
1,242 tests; focused tests cover subsequent lifecycle changes. The Linux package's
native dependencies imported successfully in AWS's official Python 3.12 Lambda image.
Frontend production build passed; this experiment does not alter application UI or routes.
Independent review identified transaction credential and cleanup-ordering issues, which
were fixed. Local results must not be presented as successful Aurora compatibility.

After live evidence is available, assess the remaining work separately: general ORM
queries and migrations, approval/source revalidation through Data API, durable task
dispatch, upload staging, policy persistence, OAuth and production observability.
In particular, the experiment's fenced sample mutation is not proof that every
existing application write has been converted to fencing.

References: [Aurora Express configuration](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_GettingStartedAurora.AuroraPostgreSQL.ExpressConfig.html),
[Data API access](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html),
[response limits](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.limitations.html),
[transactions](https://docs.aws.amazon.com/rdsdataservice/latest/APIReference/API_BeginTransaction.html),
[automatic pause](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html).
