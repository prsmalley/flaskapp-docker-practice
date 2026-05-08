# flaskapp-docker-practice

A small Flask app and multi-container Compose stack with a production-quality Dockerfile and a two-pipeline
CI/CD setup that lints, scans, builds, and ships the container to GHCR. Deployment handled by Ansible in a separate repo linked below.



## Repo layout

```
flaskapp/
  app.py             # Flask app: /health, /greet?name=X, /version
  requirements.txt   # Pinned Python deps
  Dockerfile         # Multi-stage, slim base, non-root user, healthcheck
compose-app/
  app.py             # Same app, plus a Redis-backed /counter
  docker-compose.yml # Flask + Redis with a named volume
  Dockerfile         # Identical to flaskapp/
.github/workflows/
  ci.yml             # Lint, scan, test, build verification on every PR
  release.yml        # Multi-arch build + push to GHCR + post-publish scan
```

## Quick start

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

## Endpoints

| Endpoint | Description |
|---|---|
| `/health` | Returns `{"status": "ok"}`. |
| `/greet?name=X` | Returns `{"greeting": "Hi, X"}`. Defaults to `world`. |
| `/version` | Returns `{"version": "1.0.0"}`. |
| `/counter` | INCRs a Redis counter. Compose stack only. |

## Dockerfile highlights

- Multi-stage build — dependencies in a builder stage, runtime image stays
  clean.
- `python:3.11-slim` pinned by SHA digest.
- Non-root user.
- `HEALTHCHECK` instruction.
- Layer caching — `requirements.txt` copied before app code so dependency
  installs only re-run when deps change.

## Compose stack

`compose-app/docker-compose.yml` runs Flask plus Redis on a Compose-managed
network.

- Flask reaches Redis by hostname (`redis`) — Compose registers each
  service name in Docker's embedded DNS.
- Named volume `redis-data` keeps counter state across restarts.
- `depends_on` controls startup order, not readiness. The app uses a lazy
  Redis client.
- Redis port isn't published to the host — only reachable from inside the
  Compose network.

## CI pipeline (`.github/workflows/ci.yml`)

Six parallel jobs on every PR and on push to `main`. Any failure blocks the
PR.

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

Builds a multi-arch image (amd64 + arm64 via QEMU + Buildx), pushes to GHCR
with a tag matrix from `docker/metadata-action` (short SHA, branch, semver,
`latest`), then runs a second Trivy scan against the just-published artifact.

Pulling a build:

```bash
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:latest
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:sha-abc1234
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:1.2.3
```

## Deployment

Images are deployed by [ansible-playground](https://github.com/prsmalley/ansible-playground),
a separate repo containing the Ansible playbook and a self-hosted GitHub
Actions runner. The deploy workflow pulls a specific image tag from GHCR
and runs it on the target host with a `/health` check.

Why two repos: separation of concerns. This repo owns the app and the
image. ansible-playground owns the host configuration and deploy logic.
