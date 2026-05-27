import time
from flask import Flask, request
import os
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from prometheus_client import CONTENT_TYPE_LATEST

app = Flask(__name__)
REQUEST_COUNT = Counter(
        'flaskapp_requests_total',
        'Total HTTP requests by method, endpoint, and status code',
        ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
        'flaskapp_request_latency_seconds',
        'HTTP request latency in seconds by endpoint',
        ['endpoint']
)

@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def record_metrics(response):
    if request.endpoint == 'metrics':
            return response

    REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
            endpoint=request.endpoint or 'unknown'
    ).observe(
            time.time() - request._start_time
    )
    return response

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route("/health")
def health ():
    return {"status": "ok"}

@app.route("/greet")
def greet():
    name = request.args.get("name", "world")
    return {"greeting": "Hi, " + name}

@app.route("/version")
def version():
    return {"version": "1.0.0"}





##Landing Page#
LANDING_PAGE = """<!DOCTYPE html>
<html>
<head>
  <title>flaskapp</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 4rem auto; padding: 0 1rem; }
    code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
    li { margin: 0.5rem 0; }
  </style>
</head>
<body>
  <h1>flaskapp</h1>
  <p>A Flask app deployed to a k3s cluster on AWS EC2 via Cloudflare Tunnel.
     Part of a <a href="https://github.com/prsmalley/ansible-playground/blob/main/ARCHITECTURE.md">three-repo CI/CD portfolio</a>.</p>
  <h2>Endpoints</h2>
  <ul>
    <li><a href="/health"><code>/health</code></a> — readiness check</li>
    <li><a href="/greet?name=world"><code>/greet?name=X</code></a> — greeting</li>
    <li><a href="/version"><code>/version</code></a> — version info</li>
    <li><a href="/metrics"><code>/metrics</code></a> — Prometheus metrics</li>
  </ul>
  <h2>Source</h2>
  <ul>
    <li><a href="https://github.com/prsmalley/flaskapp-docker-practice">flaskapp-docker-practice</a> — image pipeline</li>
    <li><a href="https://github.com/prsmalley/terraform-flaskapp-infra">terraform-flaskapp-infra</a> — AWS infra</li>
    <li><a href="https://github.com/prsmalley/ansible-playground">ansible-playground</a> — cluster bootstrap + deploy</li>
  </ul>
</body>
</html>
"""

@app.route('/')
def index():
    return LANDING_PAGE, 200, {'Content-Type': 'text/html; charset=utf-8'}#


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    app.run(host=host, port=5000)
