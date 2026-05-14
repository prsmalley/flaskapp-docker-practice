# flaskapp-docker-practice

A Flask app with a production-grade container image pipeline. Builds
multi-arch OCI images via Docker tooling, scans them at two stages, and
publishes to GHCR. The image is consumed by
[ansible-playground](https://github.com/prsmalley/ansible-playground)'s
deploy automation against AWS infrastructure provisioned by
[terraform-flaskapp-infra](https://github.com/prsmalley/terraform-flaskapp-infra).

This repo owns the **image**. The other two own the infrastructure and
the deploy.

## Repo layout

```
flaskapp/
  app.py             # Flask app: /health, /greet?name=X, /version
  requirements.txt   # Pinned Python deps
  Dockerfile         # Multi-stage, slim base, non-root user, healthcheck
compose-app/
  app.py             # Same app, plus a Redis-backed /counter
  docker-compose.yml # Flask + Redis with a named volume (local dev only)
  Dockerfile         # Identical to flaskapp/
.github/workflows/
  ci.yml             # Lint, scan, test, build verification on every PR
  release.yml        # Multi-arch build + push to GHCR + post-publish scan
```

## Quick start (local development)

### Single container

```bash
cd flaskapp
docker build -t flaskapp:local .
docker run --rm -p 5000:5000 flaskapp:local
```

### Compose stack (with Redis)

```bash
cd compose-app
docker compose up -d --build
curl http://localhost:5000/counter
```

`/counter` increments a Redis-backed counter and persists across container
restarts. `docker compose down -v` wipes state.

**Note:** the Compose stack is a local-dev artifact demonstrating Compose
patterns (service discovery via embedded DNS, named volumes, `depends_on`
semantics). Production deploys a single container; multi-service
orchestration is the job of Kubernetes downstream.

## Endpoints

| Endpoint | Description |
|---|---|
| `/health` | Returns `{"status": "ok"}`. Used by readiness probes. |
| `/greet?name=X` | Returns `{"greeting": "Hi, X"}`. Defaults to `world`. |
| `/version` | Returns `{"version": "1.0.0"}`. |
| `/counter` | INCRs a Redis counter. Compose stack only. |

## Dockerfile highlights

- Multi-stage build — dependencies install in a builder stage; runtime
  image stays clean.
- `python:3.11-slim` pinned by SHA digest for reproducibility.
- Non-root user.
- `HEALTHCHECK` instruction.
- Layer caching — `requirements.txt` copied before app code so dependency
  installs only re-run when deps change.

## Compose stack

`compose-app/docker-compose.yml` runs Flask plus Redis on a Compose-managed
network. Local-dev demonstration of:

- Service discovery via Docker's embedded DNS (Flask reaches Redis by
  hostname).
- Named volume `redis-data` for persistent state across restarts.
- `depends_on` controls startup order, not readiness — the app uses a
  lazy Redis client.
- Redis port isn't published to the host — only reachable inside the
  Compose network.

## CI pipeline (`.github/workflows/ci.yml`)

Six parallel jobs on every PR and on push to `main`. Any failure blocks
the PR.

| Job | What it does |
|---|---|
| **lint** | `ruff` against the Python code. |
| **hadolint** | Lints the Dockerfile. |
| **gitleaks** | Scans full git history for committed secrets. |
| **build-and-scan** | Builds the image, scans with Trivy for HIGH/CRITICAL CVEs. |
| **test** | Runs pytest against `flaskapp/` and `compose-app/`. |
| **semgrep** | SAST for code-level security issues. |

## Release pipeline (`.github/workflows/release.yml`)

Triggers:
- `workflow_run` on CI success on `main` (gates release on CI passing).
- Tag pushes matching `v*.*.*`.

Builds a multi-arch image (`linux/amd64` + `linux/arm64` via QEMU +
Buildx), pushes to GHCR with a tag matrix from `docker/metadata-action`
(short SHA, branch, semver, `latest`), then runs a second Trivy scan
against the just-published artifact.

Pulling a build:

```bash
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:latest
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:sha-abc1234
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:1.2.3
```

## Deployment

This repo releases an image to GHCR  which is pulled and
run by [ansible-playground](https://github.com/prsmalley/ansible-playground),
which currently targets a single-node k3s cluster on AWS EC2 provisioned
by [terraform-flaskapp-infra](https://github.com/prsmalley/terraform-flaskapp-infra).

Three repos, one responsibility each — see
[ARCHITECTURE.md](https://github.com/prsmalley/ansible-playground/blob/main/ARCHITECTURE.md)
in ansible-playground for the end-to-end design.

**Note on Docker vs. Kubernetes:** the image is built with Docker tooling
but the production runtime is **containerd** via k3s. 
