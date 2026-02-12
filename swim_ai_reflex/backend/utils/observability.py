"""
AquaForge.ai - Observability Module

Provides structured logging (structlog), request-ID propagation,
OpenTelemetry distributed tracing, and Prometheus metrics.

All integrations are designed to degrade gracefully: if a third-party
package is missing the application will still start with stdlib logging.
"""

from __future__ import annotations

import contextvars
import logging
import os
import time
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# ---------------------------------------------------------------------------
# Context variable that carries the current request_id across async frames
# ---------------------------------------------------------------------------
_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Return the request-id for the current async context (or ``None``)."""
    return _request_id_ctx.get(None)


# =========================================================================
# 1. STRUCTURED LOGGING  (structlog)
# =========================================================================


def setup_logging(*, log_level: str = "INFO", environment: str = "development") -> None:
    """Configure *structlog* for the entire process."""
    try:
        import structlog
    except ImportError:
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logging.getLogger(__name__).debug(
            "structlog not installed -- falling back to stdlib logging"
        )
        return

    is_production = environment.lower() == "production"

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.PATHNAME,
            ]
        ),
        _inject_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def _inject_request_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Structlog processor: add ``request_id`` from the context variable."""
    rid = _request_id_ctx.get(None)
    if rid is not None:
        event_dict["request_id"] = rid
    return event_dict


def get_logger(name: str | None = None):
    """Return a logger instance."""
    try:
        import structlog

        return structlog.get_logger(name)
    except ImportError:
        return logging.getLogger(name)


# =========================================================================
# 2. REQUEST-ID MIDDLEWARE
# =========================================================================


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    FastAPI / Starlette middleware that propagates request IDs.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = _request_id_ctx.set(request_id)
        try:
            try:
                import structlog

                structlog.contextvars.clear_contextvars()
                structlog.contextvars.bind_contextvars(request_id=request_id)
            except ImportError:
                pass

            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            _request_id_ctx.reset(token)


# =========================================================================
# 3. OPENTELEMETRY SETUP
# =========================================================================


def setup_telemetry(app: FastAPI) -> None:
    """Bootstrap OpenTelemetry tracing when OTEL_EXPORTER_OTLP_ENDPOINT is set."""
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        _stdlib_log().info(
            "OTEL_EXPORTER_OTLP_ENDPOINT not set -- OpenTelemetry tracing disabled"
        )
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({SERVICE_NAME: "aquaforge-api"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()

        _stdlib_log().info("OpenTelemetry tracing enabled (endpoint=%s)", otlp_endpoint)
    except ImportError as exc:
        _stdlib_log().warning(
            "OpenTelemetry packages not installed (%s) -- tracing disabled", exc
        )
    except Exception as exc:  # noqa: BLE001
        _stdlib_log().warning(
            "Failed to initialise OpenTelemetry: %s -- tracing disabled", exc
        )


# =========================================================================
# 4. PROMETHEUS METRICS
# =========================================================================

_REQUESTS_TOTAL = None
_REQUEST_DURATION = None


def _ensure_metrics():
    """Create Prometheus collectors on first use (idempotent)."""
    global _REQUESTS_TOTAL, _REQUEST_DURATION  # noqa: PLW0603

    if _REQUESTS_TOTAL is not None:
        return True

    try:
        from prometheus_client import Counter, Histogram

        _REQUESTS_TOTAL = Counter(
            "aquaforge_http_requests_total",
            "Total HTTP requests received",
            ["method", "endpoint", "status"],
        )
        _REQUEST_DURATION = Histogram(
            "aquaforge_http_request_duration_seconds",
            "HTTP request latency in seconds",
            ["method", "endpoint"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        return True
    except ImportError:
        return False


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record per-request metrics (count + latency histogram)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not _ensure_metrics():
            return await call_next(request)

        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        status = str(response.status_code)
        _REQUESTS_TOTAL.labels(method=method, endpoint=path, status=status).inc()
        _REQUEST_DURATION.labels(method=method, endpoint=path).observe(elapsed)

        return response


def metrics_endpoint(request: Request) -> Response:
    """Serve Prometheus text exposition format at ``/metrics``."""
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
    except ImportError:
        return Response(
            content="prometheus-client is not installed",
            status_code=501,
            media_type="text/plain",
        )


# =========================================================================
# Helpers
# =========================================================================


def _stdlib_log() -> logging.Logger:
    """Return a stdlib logger for internal messages."""
    return logging.getLogger("aquaforge.observability")
