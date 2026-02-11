"""
Compliance-as-a-Service: AML/KYC Compliance Assistant PoC

A proof-of-concept multi-step agentic AI system that:
1. Validates and parses customer datasets (CSV)
2. Applies deterministic AML/KYC-style compliance rules
3. Uses an LLM only to interpret and summarise findings
4. Produces human-reviewable risk reports

Key Design Principle: The LLM informs, it does not decide.
All rule breaches are deterministic and auditable.
"""

import os
import io
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pydantic import BaseModel

from .services.agent import ComplianceAgent
from .services.rules import apply_compliance_rules
from .services.llm import summarize_findings
from .services.logging_config import ComplianceLogger
from .services.exceptions import (
    ComplianceError,
    InvalidCSVError,
    EmptyDatasetError,
    FileReadError,
    create_error_response
)

# Configure logging for auditability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = ComplianceLogger("compliance_assistant").logger

app = FastAPI(
    title="Compliance-as-a-Service Assistant",
    description="AML/KYC compliance assistant for regulated financial services",
    version="0.1.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# ============================================================================
# Data Models
# ============================================================================

class ComplianceCheck(BaseModel):
    """Request model for compliance check"""
    dataset_name: str
    record_count: int
    timestamp: str


class ComplianceFinding(BaseModel):
    """Individual compliance rule breach"""
    rule_id: str
    rule_name: str
    severity: str  # Low, Medium, High
    affected_records: int
    description: str


class ComplianceReport(BaseModel):
    """Complete compliance assessment report"""
    check_id: str
    dataset_name: str
    timestamp: str
    total_records: int
    findings: list[ComplianceFinding]
    ai_summary: str
    risk_classification: str  # Low, Medium, High
    next_actions: list[str]
    rule_breach_count: int
    affected_records_unique: int


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI"""
    template_path = Path(__file__).parent / "templates" / "index.html"
    if template_path.exists():
        return template_path.read_text(encoding='utf-8')
    return """
    <html>
        <head><title>Compliance Assistant - Initializing</title></head>
        <body><h1>Compliance Assistant</h1><p>Loading UI...</p></body>
    </html>
    """


@app.post("/api/upload", response_model=ComplianceReport)
async def upload_and_assess(file: UploadFile = File(...)) -> ComplianceReport:
    """
    Main endpoint: Upload CSV dataset and perform compliance assessment.
    
    Flow:
    1. Validate and parse the CSV file
    2. Apply deterministic compliance rules
    3. Summarise findings via LLM
    4. Return structured report
    
    Error Handling:
    - Invalid CSV format → User error (400)
    - Empty dataset → User error (400)
    - Missing required columns → User error (400)
    - Processing error → System error (500)
    - LLM error → Recoverable (returns report with fallback summary)
    """
    check_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    compliance_logger = ComplianceLogger("compliance_assistant")
    
    try:
        # ====================================================================
        # STEP 1: File Read & Validation
        # ====================================================================
        compliance_logger.step(check_id, "FILE_VALIDATION", f"Processing: {file.filename}")
        
        # Check file exists and has content
        if not file.filename:
            raise FileReadError("unknown", "No filename provided")
        
        try:
            contents = await file.read()
        except Exception as e:
            raise FileReadError(file.filename, f"Cannot read file: {str(e)}")
        
        if not contents:
            raise EmptyDatasetError("File is empty")
        
        # Check file encoding (expect UTF-8 or similar)
        try:
            contents_str = contents.decode('utf-8')
        except UnicodeDecodeError:
            # Try alternative encodings
            try:
                contents_str = contents.decode('latin-1')
            except UnicodeDecodeError:
                try:
                    contents_str = contents.decode('cp1252')
                except UnicodeDecodeError:
                    raise FileReadError(file.filename, "Invalid file encoding. Please use UTF-8, Latin-1, or Windows-1252.")
        
        # Parse CSV
        try:
            df = pd.read_csv(io.StringIO(contents_str))
        except pd.errors.ParserError as e:
            raise InvalidCSVError(f"CSV parsing failed: {str(e)}")
        except Exception as e:
            raise InvalidCSVError(f"Unexpected error reading CSV: {str(e)}")
        
        # Validate dataset has records
        if len(df) == 0:
            raise EmptyDatasetError("CSV has headers but no data rows")
        
        compliance_logger.step(
            check_id,
            "FILE_VALIDATION",
            f"✓ Loaded {len(df)} records with {len(df.columns)} columns"
        )
        
        # ====================================================================
        # STEP 2: Apply Compliance Rules
        # ====================================================================
        try:
            compliance_logger.step(check_id, "RULES_APPLICATION", "Initializing compliance agent...")
            
            agent = ComplianceAgent(
                dataset_name=file.filename,
                check_id=check_id,
                logger=compliance_logger.logger
            )
            
            # Run the agent's multi-step flow
            findings = agent.process_dataset(df)
            
            compliance_logger.step(
                check_id,
                "RULES_APPLICATION",
                f"✓ Rules applied. Found {len(findings)} rule breaches."
            )
            
        except ComplianceError as e:
            compliance_logger.logger.error(f"[{check_id}] Compliance error: {e.message}")
            raise HTTPException(
                status_code=400,
                detail=create_error_response(check_id, e)
            )
        except Exception as e:
            compliance_logger.logger.error(f"[{check_id}] Unexpected error during rules application: {str(e)}")
            error = ComplianceError(
                message=f"Rules application failed: {str(e)}",
                user_facing="An error occurred while applying compliance rules. Please try again."
            )
            raise HTTPException(
                status_code=500,
                detail=create_error_response(check_id, error)
            )
        
        # ====================================================================
        # STEP 3: Summarize Findings via LLM
        # ====================================================================
        try:
            compliance_logger.step(check_id, "LLM_SUMMARIZATION", "Generating AI summary...")
            
            ai_summary, risk_classification, next_actions = summarize_findings(
                dataset_info={
                    "filename": file.filename,
                    "total_records": len(df),
                    "columns": df.columns.tolist()
                },
                findings=findings,
                check_id=check_id,
                logger=compliance_logger.logger
            )
            
            compliance_logger.step(
                check_id,
                "LLM_SUMMARIZATION",
                f"✓ Summary complete. Risk classification: {risk_classification}"
            )
            
        except Exception as e:
            # LLM errors are recoverable - fall back to rule-based summary
            compliance_logger.logger.warning(
                f"[{check_id}] LLM summarization failed, using fallback: {str(e)}"
            )
            ai_summary = "AI summary unavailable. Please review findings directly."
            risk_classification = _determine_risk_from_findings(findings)
            next_actions = _generate_fallback_actions(findings)
        
        # ====================================================================
        # STEP 4: Build Compliance Report
        # ====================================================================
        try:
            unique_affected = set()
            for finding in findings:
                unique_affected.update(finding.get("affected_record_indices", []))
            
            report = ComplianceReport(
                check_id=check_id,
                dataset_name=file.filename,
                timestamp=datetime.now().isoformat(),
                total_records=len(df),
                findings=[
                    ComplianceFinding(
                        rule_id=f["rule_id"],
                        rule_name=f["rule_name"],
                        severity=f["severity"],
                        affected_records=len(f.get("affected_record_indices", [])),
                        description=f["description"]
                    )
                    for f in findings
                ],
                ai_summary=ai_summary,
                risk_classification=risk_classification,
                next_actions=next_actions,
                rule_breach_count=len(findings),
                affected_records_unique=len(unique_affected)
            )
            
            compliance_logger.assessment_complete(
                check_id,
                total_records=len(df),
                breaches_found=len(findings),
                unique_affected=len(unique_affected)
            )
            
            return report
            
        except Exception as e:
            compliance_logger.logger.error(
                f"[{check_id}] Report generation failed: {str(e)}"
            )
            error = ComplianceError(
                message=f"Report generation failed: {str(e)}",
                user_facing="An error occurred while generating the report. Please try again."
            )
            raise HTTPException(
                status_code=500,
                detail=create_error_response(check_id, error)
            )
    
    except HTTPException:
        # Re-raise FastAPI HTTPExceptions
        raise
    except ComplianceError as e:
        # Handle known compliance errors
        compliance_logger.logger.error(f"[{check_id}] Compliance error: {e.message}")
        raise HTTPException(
            status_code=400,
            detail=create_error_response(check_id, e)
        )
    except Exception as e:
        # Catch any unexpected errors
        compliance_logger.logger.error(
            f"[{check_id}] Unexpected error during assessment: {str(e)}"
        )
        error = ComplianceError(
            message=f"Unexpected error: {str(e)}",
            user_facing="An unexpected error occurred. Please contact support."
        )
        raise HTTPException(
            status_code=500,
            detail=create_error_response(check_id, error)
        )


def _determine_risk_from_findings(findings: list) -> str:
    """Fallback method to determine risk level from findings when LLM unavailable."""
    if not findings:
        return "Low"
    
    high_count = len([f for f in findings if f.get("severity") == "High"])
    if high_count > 0:
        return "High"
    
    medium_count = len([f for f in findings if f.get("severity") == "Medium"])
    if medium_count >= 3:
        return "High"
    elif medium_count > 0:
        return "Medium"
    
    return "Low"


def _generate_fallback_actions(findings: list) -> list:
    """Generate next actions when LLM summarization fails."""
    actions = []
    
    if not findings:
        actions.append("No immediate actions required")
        return actions
    
    high_severity = [f for f in findings if f.get("severity") == "High"]
    if high_severity:
        actions.append("⚠️ Escalate high-severity findings to compliance officer immediately")
    
    actions.append("Review all findings in the table above")
    actions.append("Document any actions taken for audit trail")
    
    return actions


@app.get("/api/health")
async def health():
    """
    Health check endpoint.
    
    Returns system status and timestamp.
    Use this to verify the service is running and responsive.
    """
    try:
        logger.debug("Health check requested")
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "Compliance Assistant"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    try:
        port = int(os.getenv("PORT", 8000))
        host = os.getenv("HOST", "0.0.0.0")
        
        logger.info(f"Starting Compliance Assistant on {host}:{port}")
        logger.info("Service: Ready to accept compliance assessment requests")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start service: {str(e)}")
        logger.error("Recovery: Check configuration and try again")
        exit(1)
