"""
Error Handling & Exception Utilities

Defines custom exceptions and error handling patterns for the compliance assistant.
Ensures all failures are explicit, human-readable, and suggest recovery actions.

Design:
- Custom exceptions for different failure modes
- Each exception includes recovery/remediation steps
- Structured error responses for API clients
- Distinction between user errors (bad input) and system errors (infrastructure)
"""

from enum import Enum
from typing import Optional, Dict, Any


class ErrorSeverity(Enum):
    """Classification of error severity."""
    USER_ERROR = "user_error"          # User provided invalid input
    VALIDATION_ERROR = "validation_error"  # Data failed validation
    SYSTEM_ERROR = "system_error"      # System/infrastructure failure
    LLM_ERROR = "llm_error"           # LLM service failure (recoverable)
    UNKNOWN_ERROR = "unknown_error"   # Unexpected error


class ComplianceError(Exception):
    """Base exception for compliance assistant."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.UNKNOWN_ERROR,
        recovery: Optional[str] = None,
        user_facing: Optional[str] = None
    ):
        """
        Initialize a compliance error.
        
        Args:
            message: Technical error message (for logs)
            severity: Error classification
            recovery: Technical recovery steps (for operators)
            user_facing: User-friendly error message (for API response)
        """
        self.message = message
        self.severity = severity
        self.recovery = recovery or "Contact system administrator"
        self.user_facing = user_facing or message
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to API response dictionary."""
        return {
            "error": self.user_facing,
            "severity": self.severity.value,
            "recovery": self.recovery if self.severity != ErrorSeverity.USER_ERROR else None
        }


class InvalidCSVError(ComplianceError):
    """CSV file is malformed or invalid."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid CSV format: {reason}",
            severity=ErrorSeverity.USER_ERROR,
            user_facing=f"Invalid CSV file: {reason}. Please check format and try again.",
            recovery="Verify CSV structure and encoding"
        )


class EmptyDatasetError(ComplianceError):
    """Dataset is empty or has no records."""
    
    def __init__(self, reason: str = "No records found"):
        super().__init__(
            message=f"Dataset is empty: {reason}",
            severity=ErrorSeverity.USER_ERROR,
            user_facing="Dataset contains no records. Please provide a file with at least one customer record.",
            recovery="Ensure CSV has data rows (not just headers)"
        )


class MissingColumnError(ComplianceError):
    """Required column is missing from dataset."""
    
    def __init__(self, column_name: str, available_columns: list):
        super().__init__(
            message=f"Required column '{column_name}' not found",
            severity=ErrorSeverity.VALIDATION_ERROR,
            user_facing=f"Column '{column_name}' is required but not found in the dataset.",
            recovery=f"Add column '{column_name}' to your CSV. Available columns: {', '.join(available_columns)}"
        )


class DataTypeError(ComplianceError):
    """Column has unexpected data type."""
    
    def __init__(self, column_name: str, expected_type: str, actual_value: str):
        super().__init__(
            message=f"Column '{column_name}' has unexpected type",
            severity=ErrorSeverity.VALIDATION_ERROR,
            user_facing=f"Column '{column_name}' has invalid data: expected {expected_type} but got '{actual_value}'.",
            recovery=f"Verify '{column_name}' contains valid {expected_type} values"
        )


class RulesEnginError(ComplianceError):
    """Error during rules engine execution."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Rules engine error: {reason}",
            severity=ErrorSeverity.SYSTEM_ERROR,
            user_facing="An error occurred while applying compliance rules. Please try again.",
            recovery=f"Check logs for details. Error: {reason}"
        )


class LLMServiceError(ComplianceError):
    """LLM service is unavailable or returned error."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"LLM service error: {reason}",
            severity=ErrorSeverity.LLM_ERROR,
            user_facing="AI summary unavailable, but compliance assessment is complete. Review findings directly.",
            recovery=f"System falling back to rule-based summary. Check OpenAI API status. Error: {reason}"
        )


class LLMResponseError(ComplianceError):
    """LLM response is malformed or invalid."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"LLM response validation failed: {reason}",
            severity=ErrorSeverity.LLM_ERROR,
            user_facing="AI summary generation failed, using backup summary. Compliance findings are still available.",
            recovery=f"System using rule-based fallback. Check OpenAI response format. Error: {reason}"
        )


class FileReadError(ComplianceError):
    """Cannot read uploaded file."""
    
    def __init__(self, filename: str, reason: str):
        super().__init__(
            message=f"Cannot read file '{filename}': {reason}",
            severity=ErrorSeverity.USER_ERROR,
            user_facing=f"Cannot read file '{filename}'. Ensure it's a valid CSV file.",
            recovery="Verify file encoding (UTF-8 recommended) and format"
        )


class ProcessingTimeoutError(ComplianceError):
    """Processing took too long."""
    
    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            message=f"Operation '{operation}' exceeded timeout ({timeout_seconds}s)",
            severity=ErrorSeverity.SYSTEM_ERROR,
            user_facing="Processing took too long. Try with a smaller dataset.",
            recovery=f"Reduce dataset size or increase timeout from {timeout_seconds}s"
        )


def create_error_response(
    check_id: str,
    error: ComplianceError,
    additional_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a structured error response for API clients.
    
    Args:
        check_id: Assessment identifier for traceability
        error: The ComplianceError instance
        additional_context: Optional additional information
    
    Returns:
        Dictionary suitable for HTTPException detail
    """
    response = {
        "check_id": check_id,
        "status": "failed",
        "error": error.user_facing,
        "severity": error.severity.value,
    }
    
    if error.severity != ErrorSeverity.USER_ERROR:
        response["recovery"] = error.recovery
    
    if additional_context:
        response["context"] = additional_context
    
    return response
