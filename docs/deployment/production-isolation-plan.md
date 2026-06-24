# Production Execution Isolation — Plan (ecs_fargate)

How we move hosted execution off the no-isolation pilot (`EXECUTION_BACKEND=direct`)
onto isolated, container-per-run execution, while keeping local and production running the
**same container model**.

## The model (local ↔ production parity)

Execution = run the candidate's tests in a throwaway, locked-down container. The container
**is** the isolation boundary; only the launcher differs per environment:

| | Local | Production (target) |
|---|---|---|
| Mode (`EXECUTION_BACKEND`) | `http_worker` | `ecs_fargate` |
| Launcher | `apps/worker` → `docker run` per run | `ECSFargateExecutionProvider` → ECS `RunTask` per run |
| Isolation | Docker: `--network none`, cpu/mem/pids caps, read-only fs | Fargate task: awsvpc, no inbound, scoped egress |
| Test runtime | `ASSESSMENT_RUNTIME_IMAGE` (mounted workspace) | `signalloop-assessment-runner` image (S3 in/out) |
| Pilot shortcut | `direct` (in-process, NO isolation) | `direct` (current Render — to be replaced) |

`direct` stays only as a no-container fallback (e.g. quick local iteration, or hosts that
can't run containers). It is **not** the production target.

## What already exists (code complete)

- `ECSFargateExecutionProvider` (`apps/api/signalloop_api/execution.py`): uploads the run
  payload to S3 → `ecs run_task` (FARGATE, awsvpc) → waits for stop → reads `output.json`
  from S3 → returns the standard `TestRun` result shape with timings. **Implemented.**
  (The `infra/aws/ecs/README.md` "next step" note is stale — this provider is done.)
- Fargate runner (`apps/runner/`): batch entrypoint reads `SIGNALLOOP_RUNNER_INPUT` (S3),
  materializes files with the same path-safety rules as the worker (rejects
  `evaluator/`, `hidden_tests/`, traversal), runs pytest, writes `SIGNALLOOP_RUNNER_OUTPUT`
  (S3). `apps/runner/Dockerfile` builds it. **Implemented.**
- Infra templates (`infra/aws/ecs/`): `task-definition.runner.template.json`, task-role and
  API-caller IAM policies, build/push commands. **Scaffolded.**
- All `AWS_*` / `SIGNALLOOP_RUN_BUCKET` settings exist in `config.py`, gated by
  `require_ecs_settings()`.

## What's missing (go-live work)

### 1. AWS provisioning (one-time)
- ECR repo `signalloop-assessment-runner`; S3 run bucket (lifecycle-expire `runs/` prefix).
- ECS cluster; CloudWatch log group `/ecs/signalloop-assessment-runner`.
- IAM: task **execution** role (ECR pull + logs); task role (S3 read/write scoped to the run
  bucket prefix — see `runner-task-role-policy.json`).
- VPC subnets + a security group for the task (see egress note below).

### 2. Build & push the runner image
Per `infra/aws/ecs/README.md` (`docker buildx build --platform linux/amd64 ... --push apps/runner`).
Register the Fargate task definition from the template (account id, region, image URI, roles,
log group).

### 3. Wire the hosted API
Set on the API service (Render): `EXECUTION_BACKEND=ecs_fargate`, `AWS_REGION`,
`AWS_ECS_CLUSTER`, `AWS_ECS_RUNNER_TASK_DEFINITION`, `AWS_ECS_RUNNER_CONTAINER`,
`AWS_ECS_SUBNET_IDS`, `AWS_ECS_SECURITY_GROUP_IDS`, `AWS_ECS_ASSIGN_PUBLIC_IP`,
`SIGNALLOOP_RUN_BUCKET`. Because Render is outside AWS, the API needs AWS credentials with
the `render-api-runner-policy.json` permissions (ECS `RunTask`/`DescribeTasks` + S3
get/put on the run prefix).

### 4. Validate end-to-end
One public run + one hidden run + one candidate-verification run against the deployed task;
confirm result shape and timings match the local worker path.

## Two decisions to make before flipping the switch

### A. Runtime parity (correctness)
"Passes locally" must equal "passes in prod," so the Fargate runner must run the **same
Python + pytest + dependency versions** as the local assessment runtime image. Today they're
pinned independently (`apps/runner/Dockerfile` vs `ASSESSMENT_RUNTIME_IMAGE`). Action: build
the runner image **FROM** the shared assessment runtime base (or pin identical versions) so
there's a single source of truth for the test environment.

### B. Latency vs. isolation per run-type (UX) — the important one
A per-run Fargate task has tens of seconds of startup. That's fine for **submission-time**
hidden + verification runs, but poor UX for the **interactive "Run public tests"** button —
which is exactly why the pilot chose `direct`. Options:
1. **Split by run-type**: interactive public runs on a fast path (worker/`direct` or a warm
   runner); hidden + verification (submission-time) on `ecs_fargate`. Best UX; most isolation
   where it matters (hidden tests + scoring).
2. **Warm pool**: keep N runner tasks warm to hide cold start. More cost/complexity.
3. **Accept the latency** uniformly. Simplest; degrades the Run button.

Recommendation: option 1 — isolate the scored/hidden path first (highest integrity value),
keep public-test feedback fast. This needs a small change to select the backend per call
rather than one global `EXECUTION_BACKEND`.

### C. Egress lockdown (isolation property)
Local uses `--network none`. Preserve "no internet for candidate code" in Fargate: task SG
with no general egress; reach S3/ECR/logs via VPC endpoints (or a tightly scoped NAT). Don't
`assignPublicIp` unless required for image pull.

## Out of scope here
Actual AWS provisioning (needs account access/credentials) — this doc is the checklist for
that workstream. See `infra/aws/ecs/README.md` for the concrete commands and
`docs/deployment/aws-ecs-fargate-execution.md` for the deployment guide.
