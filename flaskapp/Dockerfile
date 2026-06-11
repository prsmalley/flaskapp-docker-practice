FROM python:3.14-slim@sha256:d7a925f9eb9639a93e455b9f12c167569358818c0f62b51b88edbc8fcf34c421 AS builder
ENV FLASK_HOST=0.0.0.0
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir  --prefix=/install  -r requirements.txt

FROM python:3.14-slim@sha256:d7a925f9eb9639a93e455b9f12c167569358818c0f62b51b88edbc8fcf34c421
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1
CMD ["python", "app.py"]
