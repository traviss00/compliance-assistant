"""
Logging Configuration Module

Provides structured, lightweight logging for the compliance assistant.
Ensures all operations are auditable and failures are clear and actionable.

Design:
- Lightweight: No verbose/unnecessary output
- Structured: Every log includes check_id for traceability
- Explicit: Failure messages are human-readable and actionable
- Auditable: All significant operations are logged
"""

import logging
import sys
from typing import Optional
from datetime import datetime


class ComplianceLogger:
    """Wrapper around Python's logging with audit trail support."""
    
    # Severity levels (mapped to logging)
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    def __init__(self, name: str = "compliance_assistant"):
        """Initialize logger with structured format."""
        self.logger = logging.getLogger(name)
        
        # Only configure if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def step(self, check_id: str, step_name: str, message: str):
        """Log a step in the compliance workflow."""
        self.logger.info(f"[{check_id}] [{step_name}] {message}")
    
    def step_start(self, check_id: str, step_name: str):
        """Log the start of a workflow step."""
        self.logger.info(f"[{check_id}] ┌─────────────────────────────────────────────┐")
        self.logger.info(f"[{check_id}] │ {step_name.ljust(43)} │")
        self.logger.info(f"[{check_id}] └─────────────────────────────────────────────┘")
    
    def step_end(self, check_id: str, result: str):
        """Log the completion of a workflow step."""
        self.logger.info(f"[{check_id}] ✓ {result}")
    
    def finding(self, check_id: str, severity: str, message: str):
        """Log a compliance finding with severity indicator."""
        if severity == "High":
            icon = "🔴"
        elif severity == "Medium":
            icon = "🟠"
        else:
            icon = "🟢"
        self.logger.info(f"[{check_id}] {icon} {message}")
    
    def error_critical(self, check_id: str, operation: str, error: str, recovery: str):
        """Log a critical error with recovery instructions."""
        self.logger.error(f"[{check_id}] CRITICAL ERROR during {operation}")
        self.logger.error(f"[{check_id}] Error Details: {error}")
        self.logger.error(f"[{check_id}] Recovery: {recovery}")
    
    def error_warning(self, check_id: str, operation: str, error: str, recovery: str):
        """Log a recoverable error with fallback instructions."""
        self.logger.warning(f"[{check_id}] WARNING during {operation}")
        self.logger.warning(f"[{check_id}] Error Details: {error}")
        self.logger.warning(f"[{check_id}] Fallback: {recovery}")
    
    def assessment_complete(self, check_id: str, total_records: int, 
                           breaches_found: int, unique_affected: int):
        """Log the completion of a compliance assessment."""
        self.logger.info(f"[{check_id}] ╔════ ASSESSMENT COMPLETE ════╗")
        self.logger.info(f"[{check_id}] Total Records Processed: {total_records}")
        self.logger.info(f"[{check_id}] Rule Breaches Found: {breaches_found}")
        self.logger.info(f"[{check_id}] Unique Affected Records: {unique_affected}")
        self.logger.info(f"[{check_id}] Status: READY FOR REVIEW")
        self.logger.info(f"[{check_id}] ╚═══════════════════════════╝")


def get_logger() -> ComplianceLogger:
    """Get the global compliance logger instance."""
    return ComplianceLogger()
