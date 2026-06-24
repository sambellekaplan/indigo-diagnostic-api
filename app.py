"""
Indigo BioMed - Sample Diagnostic Platform API
------------------------------------------------
This is a lightweight sample application for the IBM Associates
DevOps & Infrastructure Specialist induction case study.

It simulates a stripped-down version of Indigo BioMed's internal
diagnostic data API - the kind of service the DevOps team would
be responsible for deploying, monitoring, and maintaining.

Endpoints:
  GET /          - Welcome message
  GET /health    - Health check (returns 200 if app is running)
  GET /metrics   - Prometheus metrics endpoint
  GET /diagnose  - Simulated diagnostic request (increments counters)
  GET /slow      - Simulated slow endpoint (tests latency metrics)
"""

import time
import random
from flask import Flask, jsonify, Response
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)

app = Flask(__name__)

# ── Prometheus metrics ────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

ACTIVE_REQUESTS = Gauge(
    'http_active_requests',
    'Number of requests currently being processed'
)

DIAGNOSTIC_JOBS = Counter(
    'diagnostic_jobs_total',
    'Total diagnostic jobs processed',
    ['specialty', 'status']
)

APP_INFO = Gauge(
    'app_info',
    'Application metadata',
    ['version', 'environment']
)

# Set static app info metric on startup
APP_INFO.labels(version='1.0.0', environment='dev').set(1)

# ── Routes ────────────────────────────────────────────────────────────────────


@app.route('/')
def index():
    start = time.time()
    ACTIVE_REQUESTS.inc()
    try:
        response = jsonify({
            "service": "Indigo BioMed Diagnostic API",
            "version": "1.0.0",
            "status": "running",
            "message": "Welcome. Use /health to check status, /metrics for Prometheus data."
        })
        REQUEST_COUNT.labels(method='GET', endpoint='/', status='200').inc()
        return response, 200
    finally:
        ACTIVE_REQUESTS.dec()
        REQUEST_LATENCY.labels(endpoint='/').observe(time.time() - start)


@app.route('/health')
def health():
    """
    Health check endpoint.
    Returns 200 when the application is running normally.
    This is what the CI/CD pipeline and load balancer will probe.
    """
    start = time.time()
    ACTIVE_REQUESTS.inc()
    try:
        response = jsonify({
            "status": "healthy",
            "service": "indigo-diagnostic-api",
            "timestamp": time.time()
        })
        REQUEST_COUNT.labels(method='GET', endpoint='/health', status='200').inc()
        return response, 200
    finally:
        ACTIVE_REQUESTS.dec()
        REQUEST_LATENCY.labels(endpoint='/health').observe(time.time() - start)


@app.route('/metrics')
def metrics():
    """
    Prometheus metrics endpoint.
    Prometheus will scrape this URL every 15 seconds.
    Returns all registered metrics in Prometheus text format.
    """
    REQUEST_COUNT.labels(method='GET', endpoint='/metrics', status='200').inc()
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route('/diagnose')
def diagnose():
    """
    Simulated diagnostic processing endpoint.
    Randomly selects a specialty and simulates processing time.
    Occasionally returns an error to generate realistic error rate metrics.
    This gives Prometheus something interesting to scrape.
    """
    start = time.time()
    ACTIVE_REQUESTS.inc()

    specialties = ['cardiology', 'neurology', 'orthopaedics', 'radiology', 'pathology']
    specialty = random.choice(specialties)

    # Simulate ~10% error rate to make Grafana dashboards interesting
    if random.random() < 0.10:
        try:
            DIAGNOSTIC_JOBS.labels(specialty=specialty, status='error').inc()
            REQUEST_COUNT.labels(method='GET', endpoint='/diagnose', status='500').inc()
            return jsonify({
                "status": "error",
                "specialty": specialty,
                "message": "Upstream processing service unavailable"
            }), 500
        finally:
            ACTIVE_REQUESTS.dec()
            REQUEST_LATENCY.labels(endpoint='/diagnose').observe(time.time() - start)

    # Simulate variable processing time (50ms to 400ms)
    processing_time = random.uniform(0.05, 0.4)
    time.sleep(processing_time)

    try:
        DIAGNOSTIC_JOBS.labels(specialty=specialty, status='success').inc()
        REQUEST_COUNT.labels(method='GET', endpoint='/diagnose', status='200').inc()
        return jsonify({
            "status": "success",
            "specialty": specialty,
            "job_id": f"JOB-{random.randint(10000, 99999)}",
            "processing_time_ms": round(processing_time * 1000, 1),
            "result": "Report queued for radiologist review"
        }), 200
    finally:
        ACTIVE_REQUESTS.dec()
        REQUEST_LATENCY.labels(endpoint='/diagnose').observe(time.time() - start)


@app.route('/slow')
def slow():
    """
    Intentionally slow endpoint.
    Use this to test latency panels on your Grafana dashboard.
    Simulates a heavy database query or a slow downstream service.
    """
    start = time.time()
    ACTIVE_REQUESTS.inc()
    try:
        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)
        REQUEST_COUNT.labels(method='GET', endpoint='/slow', status='200').inc()
        return jsonify({
            "status": "ok",
            "message": f"Slow response after {round(delay, 2)}s - this simulates a heavy query",
            "note": "Use /diagnose for normal load testing"
        }), 200
    finally:
        ACTIVE_REQUESTS.dec()
        REQUEST_LATENCY.labels(endpoint='/slow').observe(time.time() - start)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 55)
    print("  Indigo BioMed Diagnostic API — Starting up")
    print("=" * 55)
    print("  Health check : http://localhost:5000/health")
    print("  Metrics      : http://localhost:5000/metrics")
    print("  Diagnose     : http://localhost:5000/diagnose")
    print("  Slow endpoint: http://localhost:5000/slow")
    print("=" * 55)
    app.run(host='0.0.0.0', port=5000, debug=False)
