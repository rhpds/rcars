from __future__ import annotations

import logging

import structlog

_LEVEL_MAP = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


def setup_logging(level: str = "INFO", component: str = "api") -> None:
    log_level = _LEVEL_MAP.get(level.upper(), 20)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_component(component),
    ]

    structlog.configure(
        processors=[*shared_processors, structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    # Route standard logging (used by analyzer.py, recommender services)
    # through structlog so all output is JSON on stdout.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.remove_processors_meta, structlog.processors.JSONRenderer()],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)


def _add_component(component: str):
    def processor(logger, method_name, event_dict):
        event_dict["component"] = component
        return event_dict
    return processor


def get_logger() -> structlog.BoundLogger:
    return structlog.get_logger()
