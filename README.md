# flaskapp-docker-practice

A simple practice repo for docker and CI workflows. A small Flask app, a production-quality Dockerfile, and a CI pipeline that lints, scans, and builds the container on every pull request.

## Repo layout

```
flaskapp/
  app.py             # Flask app with /health and /greet?name=X endpoints
  requirements.txt   # Pinned Python deps (Flask only)
  Dockerfile         # Multi-stage, slim base, non-root user, healthcheck
  .dockerignore      # Excludes .git, __pycache__, etc. from build context
.github/workflows/
  ci.yml             # Runs on every PR and push to main
```

## Dockerfile highlights

- **Multi-stage build** — dependencies install in a builder stage, runtime image stays clean.
- **`python:3.11-slim` pinned by SHA digest** — reproducible across rebuilds.
- **Non-root `appuser`** — defense in depth if the app process is compromised.
- **`HEALTHCHECK`** — Docker / orchestrators can detect a sick container.
- **Layer caching** — `requirements.txt` copied before app code, so dependency installs only re-run when deps change.

## CI pipeline (`.github/workflows/ci.yml`)

Four parallel jobs run on every pull request and on push to `main`:

| Job | What it does | Why |
|---|---|---|
| **lint** | Runs `ruff` against `flaskapp/` | Catches Python style and syntax issues before review. |
| **hadolint** | Lints the `Dockerfile` | Catches Dockerfile anti-patterns (missing `--no-cache-dir`, unpinned base images, etc.). |
| **gitleaks** | Scans full git history for committed secrets | Backstop in case the local pre-commit hook is bypassed. |
| **build-and-scan** | Builds the Docker image, then scans it with `trivy` for HIGH/CRITICAL CVEs | Verifies the image actually builds and blocks merging if known vulnerabilities ship. |

The workflow fails fast — any failing job blocks the PR.
