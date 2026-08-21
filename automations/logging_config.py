#!/usr/bin/env python3
"""
logging_config.py — Structured logging configuration for JARVIS.

Provides consistent JSON logging with correlation IDs across all services.
"""

import logging
import sys
import json
import uuid
from contextvars import ContextVar
from typing import Optional
from pythonjsonlogger import jsonlogger


# Context variables for correlation IDs
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
job_id_var: ContextVar[Optional[str]] = ContextVar("job_id", default=None)
portal_var: ContextVar[Optional[str]] = ContextVar("portal", default=None)


class CorrelationFilter(logging.Filter):
    """Add correlation IDs to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        record.job_id = job_id_var.get() or "-"
        record.portal = portal_var.get() or "-"
        return True


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with correlation IDs."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["request_id"] = getattr(record, "request_id", "-")
        log_record["job_id"] = getattr(record, "job_id", "-")
        log_record["portal"] = getattr(record, "portal", "-")
        log_record["service"] = getattr(record, "service", "jarvis")


def setup_logging(level: str = "INFO", json_output: bool = True) -> logging.Logger:
    """
    Configure structured logging for JARVIS services.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_output: If True, output JSON; else human-readable
    
    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add correlation filter
    correlation_filter = CorrelationFilter()
    root_logger.addFilter(correlation_filter)
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(correlation_filter)
    
    if json_output:
        formatter = StructuredFormatter(
            "%(timestamp)s %(levelname)s %(name)s %(message)s "
            "%(request_id)s %(job_id)s %(portal)s %(service)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "req=%(request_id)s job=%(job_id)s portal=%(portal)s | "
            "%(message)s"
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    return root_logger


def set_correlation_ids(request_id: Optional[str] = None, 
                        job_id: Optional[str] = None, 
                        portal: Optional[str] = None):
    """Set correlation IDs for the current context."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    if job_id:
        job_id_var.set(job_id)
    if portal:
        portal_var.set(portal)


def clear_correlation_ids():
    """Clear correlation IDs."""
    request_id_var.set(None)
    job_id_var.set(None)
    portal_var.set(None)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


# Context manager for correlation IDs
class correlation_context:
    """Context manager for setting correlation IDs."""
    
    def __init__(self, request_id: Optional[str] = None, 
                 job_id: Optional[str] = None, 
                 portal: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.job_id = job_id
        self.portal = portal
        self.prev_request_id = None
        self.prev_job_id = None
        self.prev_portal = None
    
    def __enter__(self):
        self.prev_request_id = request_id_var.get()
        self.prev_job_id = job_id_var.get()
        self.prev_portal = portal_var.get()
        set_correlation_ids(self.request_id, self.job_id, self.portal)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.prev_request_id is not None:
            request_id_var.set(self.prev_request_id)
        else:
            request_id_var.set(None)
        if self.prev_job_id is not None:
            job_id_var.set(self.prev_job_id)
        else:
            job_id_var.set(None)
        if self.prev_portal is not None:
            portal_var.set(self.prev_portal)
        else:
            portal_var.set(None)


# Auto-setup on import
if __name__ != "__main__":
    setup_logging()