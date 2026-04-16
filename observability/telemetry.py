"""
ACGS-2 OpenTelemetry Core Configuration
Constitutional Hash: 608508a9bd224290

Provides unified telemetry configuration for distributed tracing,
metrics collection, and constitutional compliance tracking.
"""

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from types import TracebackType
from typing import Any, ContextManager, Literal, Protocol, cast

from enhanced_agent_bus._compat.constants import CONSTITUTIONAL_HASH
from enhanced_agent_bus.bus_types import JSONDict

from .structured_logging import get_logger


class _TelemetrySectionProtocol(Protocol):
    otlp_endpoint: object
    export_traces: object
    export_metrics: object
    trace_sample_rate: object


class _TelemetrySettingsProtocol(Protocol):
    env: object
    telemetry: _TelemetrySectionProtocol


class _SpanProtocol(Protocol):
    def set_attribute(self, key: str, value: object) -> None: ...
    def add_event(self, name: str, attributes: JSONDict | None = None) -> None: ...
    def record_exception(self, exception: BaseException | None) -> None: ...
    def set_status(self, status: object) -> None: ...


class _SpanContextProtocol(Protocol):
    def __enter__(self) -> _SpanProtocol: ...
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool | None: ...


class _TracerProtocol(Protocol):
    def start_as_current_span(
        self, name: str, **kwargs: object
    ) -> ContextManager[_SpanProtocol]: ...


class _CounterProtocol(Protocol):
    def add(self, amount: int, attributes: JSONDict | None = None) -> None: ...


class _HistogramProtocol(Protocol):
    def record(self, value: float, attributes: JSONDict | None = None) -> None: ...


class _MeterProtocol(Protocol):
    def create_counter(self, name: str, **kwargs: object) -> _CounterProtocol: ...
    def create_histogram(self, name: str, **kwargs: object) -> _HistogramProtocol: ...
    def create_up_down_counter(self, name: str, **kwargs: object) -> _CounterProtocol: ...


try:
    from enhanced_agent_bus._compat.config import settings as _imported_settings
except ImportError:
    settings: _TelemetrySettingsProtocol | None = None
else:
    settings = cast(_TelemetrySettingsProtocol, _imported_settings)

logger = get_logger(__name__)
_module = sys.modules.get(__name__)
if _module is not None:
    sys.modules.setdefault("enhanced_agent_bus.observability.telemetry", _module)
    sys.modules.setdefault("packages.enhanced_agent_bus.observability.telemetry", _module)
# Check OpenTelemetry availability
OTEL_AVAILABLE = False
_trace_api: Any | None = None
_metrics_api: Any | None = None
_tracer_provider_cls: Any | None = None
_meter_provider_cls: Any | None = None
_resource_cls: Any | None = None
_periodic_metric_reader_cls: Any | None = None
_batch_span_processor_cls: Any | None = None
_simple_span_processor_cls: Any | None = None
_set_global_textmap: Any | None = None
_otel_attributes_module: Any | None = None

try:
    from opentelemetry import metrics as _imported_metrics_api
    from opentelemetry import trace as _imported_trace_api
    from opentelemetry.propagate import set_global_textmap as _imported_set_global_textmap
    from opentelemetry.sdk.metrics import MeterProvider as _imported_meter_provider_cls
    from opentelemetry.sdk.metrics.export import (
        PeriodicExportingMetricReader as _imported_periodic_metric_reader_cls,
    )
    from opentelemetry.sdk.resources import Resource as _imported_resource_cls
    from opentelemetry.sdk.trace import TracerProvider as _imported_tracer_provider_cls
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor as _imported_batch_span_processor_cls,
    )
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor as _imported_simple_span_processor_cls,
    )

    import enhanced_agent_bus._compat.otel_attributes as _imported_otel_attributes_module

    _metrics_api = _imported_metrics_api
    _trace_api = _imported_trace_api
    _set_global_textmap = _imported_set_global_textmap
    _meter_provider_cls = _imported_meter_provider_cls
    _periodic_metric_reader_cls = _imported_periodic_metric_reader_cls
    _resource_cls = _imported_resource_cls
    _tracer_provider_cls = _imported_tracer_provider_cls
    _batch_span_processor_cls = _imported_batch_span_processor_cls
    _simple_span_processor_cls = _imported_simple_span_processor_cls
    _otel_attributes_module = _imported_otel_attributes_module

    OTEL_AVAILABLE = True
    logger.info(f"[{CONSTITUTIONAL_HASH}] OpenTelemetry SDK available")
except ImportError:
    logger.warning(
        f"[{CONSTITUTIONAL_HASH}] OpenTelemetry not available, using no-op implementations"
    )


def _get_env_default() -> str:
    """Get environment from centralized config or fallback."""
    if settings is not None:
        return str(settings.env)
    import os

    return os.getenv("ENVIRONMENT", "development")


def _get_otlp_endpoint() -> str:
    """Get OTLP endpoint from centralized config or fallback."""
    if settings is not None:
        return str(settings.telemetry.otlp_endpoint)
    import os

    return os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")


def _get_export_traces() -> bool:
    """Get export_traces from centralized config or default."""
    if settings is not None:
        return bool(settings.telemetry.export_traces)
    return True


def _get_export_metrics() -> bool:
    """Get export_metrics from centralized config or default."""
    if settings is not None:
        return bool(settings.telemetry.export_metrics)
    return True


def _get_trace_sample_rate() -> float:
    """Get trace sample rate from centralized config or default."""
    if settings is not None:
        sample_rate = settings.telemetry.trace_sample_rate
        if isinstance(sample_rate, bool):
            return 1.0 if sample_rate else 0.0
        if isinstance(sample_rate, int | float):
            return float(sample_rate)
        return float(str(sample_rate))
    return 1.0


@dataclass
class TelemetryConfig:
    """Configuration for OpenTelemetry setup."""

    service_name: str = "acgs2-agent-bus"
    service_version: str = "2.0.0"
    environment: str = field(default_factory=_get_env_default)

    # Collector endpoints
    otlp_endpoint: str = field(default_factory=_get_otlp_endpoint)

    # Export settings
    export_traces: bool = field(default_factory=_get_export_traces)
    export_metrics: bool = field(default_factory=_get_export_metrics)
    batch_span_processor: bool = True  # False = SimpleSpanProcessor for debugging

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH

    # Sampling
    trace_sample_rate: float = field(default_factory=_get_trace_sample_rate)


class NoOpSpan:
    """No-op span for when OpenTelemetry is not available."""

    def set_attribute(self, key: str, value: object) -> None:
        pass

    def add_event(self, name: str, attributes: JSONDict | None = None) -> None:
        pass

    def record_exception(self, exception: BaseException | None) -> None:
        pass

    def set_status(self, status: object) -> None:
        pass

    def __enter__(self) -> "NoOpSpan":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> Literal[False]:
        return False


class NoOpTracer:
    """No-op tracer for when OpenTelemetry is not available."""

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: object) -> Iterator[NoOpSpan]:
        yield NoOpSpan()

    def start_span(self, name: str, **kwargs: object) -> NoOpSpan:
        return NoOpSpan()


class _CrossModuleNoOpType(type):
    """Treat equivalent no-op telemetry classes from dual import paths as compatible."""

    def __instancecheck__(cls, instance: object) -> bool:
        instance_cls = instance.__class__
        if type.__instancecheck__(cls, instance):
            return True
        return instance_cls.__name__ == cls.__name__ and instance_cls.__module__.endswith(
            ".observability.telemetry"
        )


class NoOpCounter(metaclass=_CrossModuleNoOpType):
    """No-op counter for when OpenTelemetry is not available."""

    def add(self, amount: int, attributes: JSONDict | None = None) -> None:
        pass


class NoOpHistogram(metaclass=_CrossModuleNoOpType):
    """No-op histogram for when OpenTelemetry is not available."""

    def record(self, value: float, attributes: JSONDict | None = None) -> None:
        pass


class NoOpUpDownCounter(metaclass=_CrossModuleNoOpType):
    """No-op up-down counter for when OpenTelemetry is not available."""

    def add(self, amount: int, attributes: JSONDict | None = None) -> None:
        pass


class NoOpMeter:
    """No-op meter for when OpenTelemetry is not available."""

    def create_counter(self, name: str, **kwargs: object) -> NoOpCounter:
        return NoOpCounter()

    def create_histogram(self, name: str, **kwargs: object) -> NoOpHistogram:
        return NoOpHistogram()

    def create_up_down_counter(self, name: str, **kwargs: object) -> NoOpUpDownCounter:
        return NoOpUpDownCounter()

    def create_observable_gauge(
        self,
        name: str,
        callbacks: object = None,
        **kwargs: object,
    ) -> None:
        return None


# Global registries
_tracers: dict[str, _TracerProtocol] = {}
_meters: dict[str, _MeterProtocol] = {}
_configured = False


def _get_resource_attributes(config: TelemetryConfig) -> dict[str, str]:
    """Get resource attributes for telemetry configuration."""
    get_resource_attributes = getattr(_otel_attributes_module, "get_resource_attributes", None)
    if callable(get_resource_attributes):
        return dict(
            get_resource_attributes(
                service_name=config.service_name,
                service_version=config.service_version,
                environment=config.environment,
                additional_attributes={"constitutional.hash": config.constitutional_hash},
            )
        )
    return {
        "service.name": config.service_name,
        "service.version": config.service_version,
        "deployment.environment": config.environment,
        "constitutional.hash": config.constitutional_hash,
    }


def _configure_trace_provider(config: TelemetryConfig, resource: Any) -> Any:
    """Configure trace provider with exporters."""
    if _tracer_provider_cls is None:
        return None
    trace_provider = _tracer_provider_cls(resource=resource)

    if not config.export_traces:
        return trace_provider

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint)

        if _batch_span_processor_cls is None or _simple_span_processor_cls is None:
            return trace_provider
        processor: Any
        if config.batch_span_processor:
            processor = _batch_span_processor_cls(exporter)
        else:
            processor = _simple_span_processor_cls(exporter)

        trace_provider.add_span_processor(processor)
        logger.info(
            f"[{CONSTITUTIONAL_HASH}] Configured OTLP trace export to {config.otlp_endpoint}"
        )
    except ImportError:
        logger.warning(
            f"[{CONSTITUTIONAL_HASH}] OTLP exporter not available, traces will not be exported"
        )

    return trace_provider


def _configure_meter_provider(config: TelemetryConfig, resource: Any) -> Any:
    """Configure meter provider with exporters."""
    if _meter_provider_cls is None:
        return None
    if not config.export_metrics:
        return _meter_provider_cls(resource=resource)

    try:
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )

        metric_exporter = OTLPMetricExporter(endpoint=config.otlp_endpoint)
        if _periodic_metric_reader_cls is None:
            return _meter_provider_cls(resource=resource)
        reader = _periodic_metric_reader_cls(metric_exporter)
        meter_provider = _meter_provider_cls(resource=resource, metric_readers=[reader])
        logger.info(
            f"[{CONSTITUTIONAL_HASH}] Configured OTLP metric export to {config.otlp_endpoint}"
        )
        return meter_provider
    except ImportError:
        logger.warning(
            f"[{CONSTITUTIONAL_HASH}] OTLP metric exporter not available, "
            "metrics will not be exported"
        )
        return _meter_provider_cls(resource=resource)


def _configure_propagation() -> None:
    """Configure trace propagation."""
    try:
        from opentelemetry.propagators.b3 import B3MultiFormat

        if _set_global_textmap is not None:
            _set_global_textmap(B3MultiFormat())
        logger.info(f"[{CONSTITUTIONAL_HASH}] Configured B3 trace propagation")
    except ImportError:
        logger.warning(f"[{CONSTITUTIONAL_HASH}] B3 propagator not available")


def _setup_telemetry_providers(config: TelemetryConfig) -> None:
    """Set up trace and meter providers with configuration."""
    if _resource_cls is None or _trace_api is None or _metrics_api is None:
        return
    resource_attrs = _get_resource_attributes(config)
    resource = _resource_cls.create(resource_attrs)

    # Configure and set trace provider
    trace_provider = _configure_trace_provider(config, resource)
    if trace_provider is not None:
        _trace_api.set_tracer_provider(trace_provider)

    # Configure and set meter provider
    meter_provider = _configure_meter_provider(config, resource)
    if meter_provider is not None:
        _metrics_api.set_meter_provider(meter_provider)

    # Configure propagation
    _configure_propagation()

    logger.info(f"[{CONSTITUTIONAL_HASH}] OpenTelemetry configured for {config.service_name}")


def configure_telemetry(
    config: TelemetryConfig | None = None,
) -> tuple[_TracerProtocol, _MeterProtocol]:
    """
    Configure OpenTelemetry for a service.

    Args:
        config: Telemetry configuration

    Returns:
        Tuple of (tracer, meter) for the service
    """
    global _configured

    if config is None:
        config = TelemetryConfig()

    if not OTEL_AVAILABLE:
        logger.warning(
            f"[{CONSTITUTIONAL_HASH}] OpenTelemetry not available, returning no-op implementations"
        )
        return cast(_TracerProtocol, NoOpTracer()), cast(_MeterProtocol, NoOpMeter())

    if not _configured:
        _setup_telemetry_providers(config)
        _configured = True

    # Get or create tracer and meter
    if _trace_api is None or _metrics_api is None:
        return cast(_TracerProtocol, NoOpTracer()), cast(_MeterProtocol, NoOpMeter())

    tracer = cast(
        _TracerProtocol,
        _trace_api.get_tracer(config.service_name, config.service_version),
    )
    meter = cast(
        _MeterProtocol,
        _metrics_api.get_meter(config.service_name, config.service_version),
    )

    _tracers[config.service_name] = tracer
    _meters[config.service_name] = meter

    return tracer, meter


def get_tracer(service_name: str | None = None) -> _TracerProtocol:
    """
    Get a tracer for the specified service.

    Args:
        service_name: Service name (defaults to acgs2-agent-bus)

    Returns:
        Tracer instance (or NoOpTracer if OTEL unavailable)
    """
    if service_name and service_name in _tracers:
        return _tracers[service_name]

    if not OTEL_AVAILABLE:
        return cast(_TracerProtocol, NoOpTracer())

    # Auto-configure if not done
    if not _configured:
        configure_telemetry()

    name = service_name or "acgs2-agent-bus"
    if name not in _tracers:
        if _trace_api is None:
            return cast(_TracerProtocol, NoOpTracer())
        _tracers[name] = cast(_TracerProtocol, _trace_api.get_tracer(name))

    return _tracers[name]


def get_meter(service_name: str | None = None) -> _MeterProtocol:
    """
    Get a meter for the specified service.

    Args:
        service_name: Service name (defaults to acgs2-agent-bus)

    Returns:
        Meter instance (or NoOpMeter if OTEL unavailable)
    """
    if service_name and service_name in _meters:
        return _meters[service_name]

    if not OTEL_AVAILABLE:
        return cast(_MeterProtocol, NoOpMeter())

    # Auto-configure if not done
    if not _configured:
        configure_telemetry()

    name = service_name or "acgs2-agent-bus"
    if name not in _meters:
        if _metrics_api is None:
            return cast(_MeterProtocol, NoOpMeter())
        _meters[name] = cast(_MeterProtocol, _metrics_api.get_meter(name))

    return _meters[name]


class TracingContext:
    """
    Context manager for creating spans with constitutional hash.

    Example:
        with TracingContext("process_message") as span:
            span.set_attribute("message.id", msg_id)
            # ... processing
    """

    def __init__(
        self,
        name: str,
        service_name: str | None = None,
        attributes: JSONDict | None = None,
    ) -> None:
        self.name = name
        self.tracer = get_tracer(service_name)
        self.attributes = attributes or {}
        self._span: _SpanProtocol | None = None
        self._context: ContextManager[_SpanProtocol] | None = None

    def __enter__(self) -> _SpanProtocol:
        context = self.tracer.start_as_current_span(self.name)
        self._context = context
        span = context.__enter__()
        self._span = span

        # Always add constitutional hash
        span.set_attribute("constitutional.hash", CONSTITUTIONAL_HASH)
        span.set_attribute("timestamp", datetime.now(UTC).isoformat())

        # Add tenant ID if available from context
        try:
            from ..multi_tenancy.context import get_current_tenant_id

            tenant_id = get_current_tenant_id()
            if tenant_id:
                span.set_attribute("tenant.id", tenant_id)
        except (ImportError, ValueError):
            pass

        # Add custom attributes
        for key, value in self.attributes.items():
            span.set_attribute(key, value)

        return span

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        if exc_type is not None and self._span:
            self._span.record_exception(exc_val if isinstance(exc_val, BaseException) else None)
            if OTEL_AVAILABLE:
                from opentelemetry.trace import Status, StatusCode

                self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))

        if self._context:
            return self._context.__exit__(exc_type, exc_val, exc_tb)
        return False


class MetricsRegistry:
    """
    Registry for commonly used metrics with constitutional hash tagging.

    Example:
        registry = MetricsRegistry("agent_bus")
        registry.record_latency("message_processing", 5.2)
        registry.increment_counter("messages_processed")
    """

    def __init__(self, service_name: str = "acgs2-agent-bus") -> None:
        self.service_name = service_name
        self.meter = get_meter(service_name)
        self._counters: dict[str, _CounterProtocol] = {}
        self._histograms: dict[str, _HistogramProtocol] = {}
        self._gauges: dict[str, _CounterProtocol] = {}

    def get_counter(self, name: str, description: str = "") -> _CounterProtocol:
        """Get or create a counter metric."""
        if name not in self._counters:
            full_name = f"acgs2.{self.service_name}.{name}"
            self._counters[name] = self.meter.create_counter(
                name=full_name,
                description=description,
            )
        return self._counters[name]

    def get_histogram(
        self, name: str, unit: str = "ms", description: str = ""
    ) -> _HistogramProtocol:
        """Get or create a histogram metric."""
        if name not in self._histograms:
            full_name = f"acgs2.{self.service_name}.{name}"
            self._histograms[name] = self.meter.create_histogram(
                name=full_name,
                unit=unit,
                description=description,
            )
        return self._histograms[name]

    def get_gauge(self, name: str, description: str = "") -> _CounterProtocol:
        """Get or create an up-down counter (gauge-like behavior)."""
        if name not in self._gauges:
            full_name = f"acgs2.{self.service_name}.{name}"
            self._gauges[name] = self.meter.create_up_down_counter(
                name=full_name,
                description=description,
            )
        return self._gauges[name]

    def increment_counter(
        self,
        name: str,
        amount: int = 1,
        attributes: dict[str, object] | None = None,
    ) -> None:
        """Increment a counter with constitutional hash attribute."""
        counter = self.get_counter(name)
        attrs: dict[str, object] = {"constitutional_hash": CONSTITUTIONAL_HASH}
        if attributes:
            attrs.update(attributes)
        counter.add(amount, attrs)

    def record_latency(
        self,
        name: str,
        value_ms: float,
        attributes: dict[str, object] | None = None,
    ) -> None:
        """Record a latency value in milliseconds."""
        histogram = self.get_histogram(name, unit="ms")
        attrs: dict[str, object] = {"constitutional_hash": CONSTITUTIONAL_HASH}
        if attributes:
            attrs.update(attributes)
        histogram.record(value_ms, attrs)

    def set_gauge(
        self,
        name: str,
        delta: int,
        attributes: dict[str, object] | None = None,
    ) -> None:
        """Adjust a gauge value."""
        gauge = self.get_gauge(name)
        attrs: dict[str, object] = {"constitutional_hash": CONSTITUTIONAL_HASH}
        if attributes:
            attrs.update(attributes)
        gauge.add(delta, attrs)
