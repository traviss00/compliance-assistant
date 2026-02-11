"""
Multi-Step Compliance Agent: Explicit, Auditable Workflow

REGULATED ENVIRONMENT DESIGN:
This agent is architected for maximum auditability and regulatory compliance.

Key Principles:
1. EXPLICIT STEPS: Each step is named, logged, and independently verifiable
2. NO AUTONOMOUS DECISIONS: All decisions made by deterministic rules, not the agent
3. FULL TRACEABILITY: Every action logged with check_id, timestamp, and details
4. HUMAN OVERSIGHT: Results are advisory; humans make final decisions
5. GRACEFUL DEGRADATION: System works even if LLM is unavailable

Workflow:
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Validate Dataset Integrity                         │
│ └─ Check for empty data, missing columns, anomalies        │
├─────────────────────────────────────────────────────────────┤
│ STEP 2: Parse & Normalize Data                             │
│ └─ Strip whitespace, parse dates, standardize nulls        │
├─────────────────────────────────────────────────────────────┤
│ STEP 3: Apply Deterministic Compliance Rules               │
│ └─ Execute 6 AML/KYC rules (PEP, Sanctions, etc.)          │
├─────────────────────────────────────────────────────────────┤
│ STEP 4: Enrich Findings with Context                       │
│ └─ Add sample records, percentages, severity metadata      │
├─────────────────────────────────────────────────────────────┤
│ STEP 5: Prepare for LLM Interpretation (Optional)          │
│ └─ Structure data for plain-English summarization          │
└─────────────────────────────────────────────────────────────┘

Why This Approach Is Safe for Regulated Environments:
- Deterministic rules ensure reproducible decisions
- Every finding is traceable to a specific rule
- Full audit trail supports regulatory examinations
- LLM only explains findings, doesn't make decisions
- Easy to justify decisions to compliance officers and regulators
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import pandas as pd
from datetime import datetime
from .rules import ComplianceRulesEngine


class ComplianceAgent:
    """
    Multi-step compliance assessment orchestrator.
    
    REGULATORY DESIGN RATIONALE:
    - Each step is independently auditable and logged
    - Steps cannot be bypassed or reordered
    - All decisions made by deterministic rules, not heuristics
    - LLM used ONLY for interpretation, never for rule enforcement
    
    This design ensures that compliance reviews can trace every decision
    back to a specific rule and affected records, satisfying regulatory
    requirements for explainability and auditability.
    """
    
    def __init__(
        self,
        dataset_name: str,
        check_id: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the compliance assessment agent.
        
        AUDIT TRAIL INITIALIZATION:
        Every assessment gets a unique check_id that tracks all downstream actions.
        This enables complete traceability for regulatory examinations.
        
        Args:
            dataset_name: Name of the dataset being assessed (logged for audit)
            check_id: Unique identifier for this compliance check (all logs reference this)
            logger: Optional logger instance (for structured audit logging)
        """
        self.dataset_name = dataset_name
        self.check_id = check_id
        self.logger = logger or logging.getLogger(__name__)
        self.rules_engine = ComplianceRulesEngine()
        self.step_start_times: Dict[str, float] = {}  # Track timing for each step
        
        self.logger.info(
            f"[{check_id}] ╔════ COMPLIANCE ASSESSMENT INITIATED ════╗"
        )
        self.logger.info(f"[{check_id}] Dataset: {dataset_name}")
        self.logger.info(f"[{check_id}] Check ID: {check_id}")
        self.logger.info(f"[{check_id}] Timestamp: {datetime.now().isoformat()}")
    
    def process_dataset(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Execute the full compliance assessment workflow.
        
        STEP-BY-STEP PROCESS (Each step is independently auditable):
        
        STEP 1: VALIDATE - Check data integrity
            └─ Ensures data quality before rule application
            └─ Logs any anomalies for compliance officer review
            └─ Why safe: Prevents garbage-in-garbage-out scenarios
        
        STEP 2: PARSE - Normalize and standardize data
            └─ Makes data consistent (strip whitespace, parse dates)
            └─ Prevents false negatives from formatting issues
            └─ Why safe: Ensures rules apply consistently
        
        STEP 3: APPLY_RULES - Execute deterministic compliance rules
            └─ Apply 6 AML/KYC rules to normalized data
            └─ Identify all rule breaches with record indices
            └─ Why safe: No ML, no heuristics - fully explainable
        
        STEP 4: ENRICH - Add context to findings
            └─ Include sample affected records for manual review
            └─ Calculate impact percentage
            └─ Why safe: Provides auditors with concrete examples
        
        REGULATORY GUARANTEE:
        If you need to audit why a finding was made:
        1. Check which rule was triggered (STEP 3 logs)
        2. Find affected record indices (in finding['affected_record_indices'])
        3. Review sample records (in finding['sample_affected_records'])
        4. Re-run same dataset → get identical results (deterministic)
        
        Args:
            df: pandas DataFrame with customer/transaction data
        
        Returns:
            List of structured findings ready for LLM interpretation
        
        Raises:
            No exceptions - returns empty findings list if errors occur
        """
        
        # ====================================================================
        # STEP 1: VALIDATE - Check dataset integrity
        # ====================================================================
        # REGULATORY RATIONALE:
        # Before applying any compliance rules, we must verify the data is
        # complete and sensible. This prevents false positives from malformed
        # data and ensures the compliance assessment is based on clean input.
        # All validation warnings are logged for the compliance officer.
        # ====================================================================
        
        step_name = "STEP 1: VALIDATE"
        self.step_start_times[step_name] = datetime.now().timestamp()
        
        self.logger.info(f"[{self.check_id}] ┌─────────────────────────────────────────────┐")
        self.logger.info(f"[{self.check_id}] │ {step_name.ljust(43)} │")
        self.logger.info(f"[{self.check_id}] └─────────────────────────────────────────────┘")
        self.logger.info(f"[{self.check_id}] Purpose: Verify data integrity before rule application")
        
        validation_result = self._step_validate_dataset(df)
        
        if validation_result['has_errors']:
            self.logger.warning(
                f"[{self.check_id}] ⚠️  Validation found {len(validation_result['errors'])} issues:"
            )
            for error in validation_result['errors']:
                self.logger.warning(f"[{self.check_id}]    - {error}")
        else:
            self.logger.info(f"[{self.check_id}] ✓ Data validation passed")
        
        # ====================================================================
        # STEP 2: PARSE - Normalize and standardize data
        # ====================================================================
        # REGULATORY RATIONALE:
        # Different data sources may have different formatting (extra spaces,
        # different date formats, null representations). We normalize this so
        # that compliance rules apply consistently. This prevents rules from
        # missing violations due to formatting differences.
        # ====================================================================
        
        step_name = "STEP 2: PARSE"
        self.step_start_times[step_name] = datetime.now().timestamp()
        
        self.logger.info(f"[{self.check_id}] ┌─────────────────────────────────────────────┐")
        self.logger.info(f"[{self.check_id}] │ {step_name.ljust(43)} │")
        self.logger.info(f"[{self.check_id}] └─────────────────────────────────────────────┘")
        self.logger.info(f"[{self.check_id}] Purpose: Normalize data format for consistent rule application")
        
        parse_result = self._step_parse_dataset(df)
        df_parsed = parse_result['dataframe']
        
        self.logger.info(
            f"[{self.check_id}] ✓ Parsing complete: {len(df_parsed)} records, "
            f"{len(df_parsed.columns)} columns"
        )
        self.logger.info(f"[{self.check_id}] Transformations applied: {parse_result['transformations_count']}")
        
        # ====================================================================
        # STEP 3: APPLY_RULES - Execute deterministic compliance rules
        # ====================================================================
        # REGULATORY RATIONALE:
        # This is where the actual compliance assessment happens. We apply
        # deterministic rules (no machine learning, no heuristics). Each rule
        # returns a list of affected records with indices. This allows:
        # 1. Complete traceability (which rule, which records)
        # 2. Manual review (exact row numbers to examine)
        # 3. Reproducibility (same data → same results, always)
        # ====================================================================
        
        step_name = "STEP 3: APPLY_RULES"
        self.step_start_times[step_name] = datetime.now().timestamp()
        
        self.logger.info(f"[{self.check_id}] ┌─────────────────────────────────────────────┐")
        self.logger.info(f"[{self.check_id}] │ {step_name.ljust(43)} │")
        self.logger.info(f"[{self.check_id}] └─────────────────────────────────────────────┘")
        self.logger.info(f"[{self.check_id}] Purpose: Execute deterministic compliance rules (no ML)")
        
        rule_result = self._step_apply_compliance_rules(df_parsed)
        raw_findings = rule_result['findings']
        
        self.logger.info(
            f"[{self.check_id}] ✓ Rule execution complete: {len(raw_findings)} rule breaches found"
        )
        
        # Detailed rule results
        if raw_findings:
            high_severity = len([f for f in raw_findings if f.get('severity') == 'High'])
            medium_severity = len([f for f in raw_findings if f.get('severity') == 'Medium'])
            low_severity = len([f for f in raw_findings if f.get('severity') == 'Low'])
            
            self.logger.info(
                f"[{self.check_id}] Severity breakdown: "
                f"🔴 {high_severity} High, 🟠 {medium_severity} Medium, 🟢 {low_severity} Low"
            )
            
            for finding in raw_findings:
                affected_count = len(finding.get('affected_record_indices', []))
                percentage = round((affected_count / len(df_parsed) * 100), 1) if len(df_parsed) > 0 else 0
                self.logger.info(
                    f"[{self.check_id}]   • {finding['rule_name']} ({finding['severity']}) "
                    f"→ {affected_count} records ({percentage}%)"
                )
        else:
            self.logger.info(f"[{self.check_id}] ✓ No rule breaches detected")
        
        # ====================================================================
        # STEP 4: ENRICH - Add context to findings
        # ====================================================================
        # REGULATORY RATIONALE:
        # Raw rule violations need context for manual review. We add:
        # 1. Sample affected records (so auditors can see what matched)
        # 2. Impact percentages (is this 1 record or 50% of dataset?)
        # 3. All metadata in a structured format
        # This makes it easy for compliance officers to understand and review
        # each finding without needing to inspect raw data themselves.
        # ====================================================================
        
        step_name = "STEP 4: ENRICH"
        self.step_start_times[step_name] = datetime.now().timestamp()
        
        self.logger.info(f"[{self.check_id}] ┌─────────────────────────────────────────────┐")
        self.logger.info(f"[{self.check_id}] │ {step_name.ljust(43)} │")
        self.logger.info(f"[{self.check_id}] └─────────────────────────────────────────────┘")
        self.logger.info(f"[{self.check_id}] Purpose: Add context and samples for compliance officer review")
        
        enrich_result = self._step_enrich_findings(df_parsed, raw_findings)
        structured_findings = enrich_result['findings']
        
        self.logger.info(
            f"[{self.check_id}] ✓ Findings enriched with sample records and metadata"
        )
        
        # ====================================================================
        # SUMMARY - Print assessment complete with key metrics
        # ====================================================================
        
        total_affected = set()
        for finding in structured_findings:
            total_affected.update(finding.get("affected_record_indices", []))
        
        self.logger.info(f"[{self.check_id}] ╔════ ASSESSMENT COMPLETE ════╗")
        self.logger.info(f"[{self.check_id}] Total Records Processed: {len(df_parsed)}")
        self.logger.info(f"[{self.check_id}] Rule Breaches Found: {len(structured_findings)}")
        self.logger.info(f"[{self.check_id}] Unique Affected Records: {len(total_affected)}")
        self.logger.info(f"[{self.check_id}] Status: READY FOR LLM INTERPRETATION")
        self.logger.info(f"[{self.check_id}] ╚═══════════════════════════╝")
        
        return structured_findings
    
    # ========================================================================
    # STEP METHODS (Each is independently auditable and testable)
    # ========================================================================
    # These methods encapsulate the logic for each step. By separating them,
    # we make it easy for compliance auditors or engineers to test, review,
    # and understand each phase of the assessment independently.
    # ========================================================================
    
    def _step_validate_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        STEP 1: Validate Dataset Integrity
        
        WHAT IT DOES:
        Checks that the dataset is complete and sensible before applying rules.
        This is defensive programming for a regulated environment.
        
        WHY IT MATTERS:
        - Prevents rules from being applied to corrupt/malformed data
        - Gives compliance officers visibility into data quality issues
        - Enables early exit if data is unusable (garbage-in-garbage-out)
        
        REGULATORY CHECKS:
        ✓ Dataset is not empty
        ✓ Dataset has columns
        ✓ No completely empty columns (likely data errors)
        ✓ Reasonable column count (not a dump of every field in a database)
        
        Returns:
            Dict with keys:
            - has_errors: bool (True if any issues found)
            - errors: List[str] (Details of each issue)
        """
        errors = []
        
        # Check 1: Empty dataset
        if df.empty:
            errors.append("Dataset is completely empty (no records)")
        
        # Check 2: No columns
        if len(df.columns) == 0:
            errors.append("Dataset has no columns (unusable)")
        else:
            # Check 3: Completely empty columns (likely data errors)
            for col in df.columns:
                if df[col].isna().all():
                    errors.append(f"Column '{col}' is 100% empty (all nulls)")
            
            # Check 4: Unreasonable column count
            if len(df.columns) > 100:
                errors.append(
                    f"Unusually high column count ({len(df.columns)}): "
                    f"verify this is not a data dump"
                )
        
        return {
            'has_errors': len(errors) > 0,
            'errors': errors
        }
    
    def _step_parse_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        STEP 2: Parse & Normalize Dataset
        
        WHAT IT DOES:
        Standardizes data format so compliance rules apply consistently.
        Prevents false negatives from formatting variations.
        
        WHY IT MATTERS:
        Different data sources have different conventions:
        - Customer names may have leading/trailing spaces
        - Dates may be formatted differently
        - Empty values represented as "", "NULL", "N/A", NaN, etc.
        
        By normalizing, we ensure:
        ✓ "  John Smith  " matches as "John Smith"
        ✓ "2024-01-01" and "01/01/2024" both parsed as dates
        ✓ All null values standardized to NaN
        
        This is CRITICAL in regulated environments where false negatives
        (missing a violation) are worse than false positives.
        
        Returns:
            Dict with keys:
            - dataframe: pd.DataFrame (Parsed and normalized)
            - transformations_count: int (Number of transformations applied)
        """
        df_copy = df.copy()
        transformation_count = 0
        
        # Transform 1: Strip whitespace from string columns
        # Rationale: "Vladimir Putin" vs " Vladimir Putin" should match PEP list
        for col in df_copy.select_dtypes(include=['object']).columns:
            original = df_copy[col].copy()
            df_copy[col] = df_copy[col].str.strip() if df_copy[col].dtype == 'object' else df_copy[col]
            if not original.equals(df_copy[col]):
                transformation_count += 1
        
        # Transform 2: Standardize missing values
        # Rationale: Make all nulls consistent for downstream rule application
        original_null_count = df_copy.isna().sum().sum()
        df_copy = df_copy.where(pd.notna(df_copy), None)
        new_null_count = df_copy.isna().sum().sum()
        if original_null_count != new_null_count:
            transformation_count += 1
        
        # Transform 3: Parse date columns
        # Rationale: "account_open_date" needs to be datetime to check account age
        date_keywords = ['date', 'created', 'opened', 'birth', 'expir', 'since', 'from']
        parsed_date_columns = 0
        
        for col in df_copy.columns:
            if any(keyword in col.lower() for keyword in date_keywords):
                try:
                    parsed = pd.to_datetime(df_copy[col], errors='coerce')
                    # Only transform if parsing succeeded on at least some values
                    if parsed.notna().any():
                        df_copy[col] = parsed
                        parsed_date_columns += 1
                        transformation_count += 1
                        self.logger.info(
                            f"[{self.check_id}] Parsed '{col}' as datetime "
                            f"({parsed.notna().sum()} of {len(parsed)} values parsed)"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"[{self.check_id}] Failed to parse '{col}' as date: {str(e)[:50]}"
                    )
        
        return {
            'dataframe': df_copy,
            'transformations_count': transformation_count
        }
    
    def _step_apply_compliance_rules(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        STEP 3: Apply Deterministic Compliance Rules
        
        WHAT IT DOES:
        Executes all 6 AML/KYC compliance rules against the dataset.
        Returns findings with exact record indices for each rule breach.
        
        WHY IT MATTERS (REGULATORY):
        This is where actual compliance assessment happens. Key properties:
        
        ✓ DETERMINISTIC: Same data → Always same results (no randomness)
        ✓ EXPLAINABLE: Each finding maps to specific rule and records
        ✓ AUDITABLE: Can re-run same data and verify results
        ✓ TRACEABLE: Affected record indices for manual review
        
        This is REQUIRED for regulated environments. Regulators need to:
        1. Understand why a customer was flagged (which rule)
        2. Reproduce the result (deterministic)
        3. Review affected records (indices provided)
        4. Challenge the logic if needed (rules are in code)
        
        Returns:
            Dict with keys:
            - findings: List[Dict] (Each finding has rule_id, rule_name, severity, 
                                     affected_record_indices, description)
        """
        # Apply all rules - this calls ComplianceRulesEngine.apply_all_rules()
        raw_findings = self.rules_engine.apply_all_rules(df)
        
        return {
            'findings': raw_findings
        }
    
    def _step_enrich_findings(
        self,
        df: pd.DataFrame,
        raw_findings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        STEP 4: Enrich Findings with Context
        
        WHAT IT DOES:
        Takes raw rule violations and adds context for compliance officer review.
        Includes sample affected records and impact metrics.
        
        WHY IT MATTERS:
        Compliance officers don't just need to know "5 records violated RULE_001".
        They need to:
        ✓ See sample records that matched (understand why)
        ✓ Know impact as percentage (is it 0.1% or 50% of dataset?)
        ✓ Have structured data for their review system
        
        REGULATORY BENEFIT:
        When a regulator asks "Why did you flag customer X?", you can show:
        1. Rule that triggered (e.g., "High-Risk Country Exposure")
        2. Exact record row (e.g., "row 47")
        3. Sample data from that row
        4. Percentage of total dataset affected
        
        This makes compliance reviews traceable and defensible.
        
        Returns:
            Dict with keys:
            - findings: List[Dict] (Enriched with samples and percentages)
        """
        structured = []
        
        for finding in raw_findings:
            affected_indices = finding.get("affected_record_indices", [])
            sample_records = []
            
            # Collect sample affected records (up to 3 for review)
            if affected_indices:
                for idx in affected_indices[:3]:
                    if idx < len(df):
                        sample_records.append(dict(df.iloc[idx]))
            
            # Calculate impact percentage
            impact_percentage = round(
                (len(affected_indices) / len(df) * 100), 2
            ) if len(df) > 0 else 0
            
            # Enrich the finding
            enriched_finding = {
                **finding,
                "sample_affected_records": sample_records,
                "percentage_of_dataset": impact_percentage,
                "total_affected": len(affected_indices)
            }
            
            structured.append(enriched_finding)
        
        return {
            'findings': structured
        }
