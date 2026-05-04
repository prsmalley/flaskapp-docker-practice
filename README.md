# flaskapp-docker-practice

A practice repo for Docker, Docker Compose, and CI/CD workflows. A small Flask
app, a production-quality Dockerfile, a multi-container Compose stack, and a
two-pipeline GitHub Actions setup that lints, scans, builds, and ships the
container to GHCR.

## Repo layout

```
flaskapp/
  app.py             # Flask app with /health and /greet?name=X endpoints
  requirements.txt   # Pinned Python deps
  Dockerfile         # Multi-stage, slim base, non-root user, healthcheck
  .dockerignore      # Excludes .git, __pycache__, etc. from build context
compose-app/
  app.py             # Same app, extended with Redis-backed /counter
  requirements.txt   # Adds redis client
  Dockerfile         # Identical to flaskapp/
  docker-compose.yml # Defines app + redis services with named volume
.github/workflows/
  ci.yml             # Lint, scan, build verification on every PR
  release.yml        # Multi-arch image build and push to GHCR on main / tags
```

## Quick start

### Run the single-container app

```bash
cd flaskapp
docker build -t flaskapp:local .
docker run --rm -p 5000:5000 flaskapp:local
```

### Run the Compose stack

```bash
cd compose-app
docker compose up -d --build
curl http://localhost:5000/counter
```

`/counter` increments a Redis-backed counter on each call and persists across
container restarts. To wipe state, `docker compose down -v`.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Returns `{"status": "ok"}` for health checks. |
| `/greet?name=X` | GET | Returns `{"greeting": "Hi, X"}`; defaults to `world`. |
| `/counter` | GET | INCR a Redis counter and return the new value. Compose stack only. |

## Dockerfile highlights

- **Multi-stage build** — dependencies install in a builder stage, runtime
  image stays clean.
- **`python:3.11-slim` pinned by SHA digest** — reproducible across rebuilds.
- **Non-root `appuser`** — defense in depth if the app process is compromised.
- **`HEALTHCHECK`** — Docker / orchestrators can detect a sick container.
- **Layer caching** — `requirements.txt` copied before app code, so dependency
  installs only re-run when deps change.

## Compose stack (`compose-app/docker-compose.yml`)

A two-service stack demonstrating real-world container orchestration patterns:

- **Service discovery via Compose's embedded DNS.** The Flask app reaches Redis
  by hostname (`redis`) — Compose creates a user-defined network for the
  project, registers each service name as an A record, and the Docker daemon's
  embedded DNS server (at `127.0.0.11` inside containers) resolves them.
- **Named volume `redis-data` for persistence.** Mounted at Redis's data
  directory so counter state survives `docker compose down`. `docker compose
  down -v` is required to actually remove it.
- **`depends_on: [redis]`** controls startup *order* but not *readiness*.
  Compose starts Redis before the app, but doesn't wait for Redis to accept
  connections. The app uses a lazy Redis client, so this is safe in practice.
- **Redis port not published to host.** Reachable only from inside the
  Compose network — avoids advertising an unauthenticated Redis externally.

## CI pipeline (`.github/workflows/ci.yml`)

Four parallel jobs run on every pull request and on push to `main`:

| Job | What it does | Why |
|---|---|---|
| **lint** | Runs `ruff` against `flaskapp/` | Catches Python style and syntax issues before review. |
| **hadolint** | Lints the `Dockerfile` | Catches Dockerfile anti-patterns (missing `--no-cache-dir`, unpinned base images, etc.). |
| **gitleaks** | Scans full git history for committed secrets | Backstop in case the local pre-commit hook is bypassed. |
| **build-and-scan** | Builds the Docker image, then scans it with `trivy` for HIGH/CRITICAL CVEs | Verifies the image actually builds and blocks merging if known vulnerabilities ship. |

Any failing job blocks the PR.

## Release pipeline (`.github/workflows/release.yml`)

On push to `main` and on semver tag pushes (`v*.*.*`), builds and pushes a
multi-arch image to GitHub Container Registry.

| Step | What it does |
|---|---|
| **Log in to GHCR** | Authenticates using the workflow's auto-provisioned `GITHUB_TOKEN`|
| **`setup-qemu` + `setup-buildx`** | Enables cross-architecture builds via QEMU emulation, with BuildKit's advanced caching and multi-platform support. |
| **`metadata-action` computes tags** | Generates a tag matrix per push: short SHA (`sha-abc1234`), branch name, semver (when a `v1.2.3` tag is pushed), and `latest` (only on the default branch). |
| **`build-push-action`** | Builds for `linux/amd64` and `linux/arm64`, pushes to `ghcr.io/prsmalley/flaskapp-docker-practice`, and caches layers in GitHub Actions cache. |

Pulling a specific build:

```bash
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:latest
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:sha-abc1234
docker pull ghcr.io/prsmalley/flaskapp-docker-practice:1.2.3
```
