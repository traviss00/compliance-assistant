"""
AML/KYC Compliance Rules Engine

Deterministic rule application for customer risk assessment.

Design Philosophy:
- Each rule is explicit, auditable, and independently testable
- No machine learning or subjective scoring (LLM is used only to explain findings)
- Rules are based on illustrative compliance scenarios, not real regulations
- All rule breaches include affected record indices for auditability

Rules Implemented:
1. PEP (Politically Exposed Person) List Check
2. Sanctions List Match
3. High-Risk Country Exposure
4. Unusual Transaction Patterns
5. Account Age Verification
6. Document Verification Status
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd


class ComplianceRulesEngine:
    """
    Applies deterministic AML/KYC compliance rules to customer datasets.
    """
    
    # Illustrative data - replace with real lists in production
    PEP_LIST = {
        "vladimir putin", "kim jong-un", "bashar al-assad",
        "nicolas maduro", "xi jinping"
    }
    
    SANCTIONS_LIST = {
        "iran", "north korea", "syria", "cuba"
    }
    
    HIGH_RISK_COUNTRIES = {
        "iran", "north korea", "syria", "yemen", "somalia"
    }
    
    def __init__(self):
        """Initialize the rules engine"""
        self.rules_applied = []
    
    def apply_all_rules(self, df) -> List[Dict[str, Any]]:
        """
        Apply all compliance rules to dataset.
        
        Returns:
            List of findings, each containing:
            - rule_id: Unique rule identifier
            - rule_name: Human-readable rule name
            - severity: "Low", "Medium", or "High"
            - description: What the rule checks
            - affected_record_indices: List of row indices with breaches
        """
        findings = []
        
        # Rule 1: PEP Check
        findings.extend(self._check_pep_list(df))
        
        # Rule 2: Sanctions Check
        findings.extend(self._check_sanctions_list(df))
        
        # Rule 3: High-Risk Country Exposure
        findings.extend(self._check_high_risk_countries(df))
        
        # Rule 4: Unusual Transaction Patterns
        findings.extend(self._check_unusual_transactions(df))
        
        # Rule 5: Account Age
        findings.extend(self._check_account_age(df))
        
        # Rule 6: Document Verification
        findings.extend(self._check_document_verification(df))
        
        return findings
    
    # ========================================================================
    # Individual Rule Implementations
    # ========================================================================
    
    def _check_pep_list(self, df) -> List[Dict[str, Any]]:
        """Rule 1: Check customer names against PEP list"""
        findings = []
        
        if "customer_name" not in df.columns:
            return findings
        
        breached_indices = []
        for idx, name in enumerate(df["customer_name"]):
            if pd.isna(name):
                continue
            name_lower = str(name).lower().strip()
            if name_lower in self.PEP_LIST:
                breached_indices.append(idx)
        
        if breached_indices:
            findings.append({
                "rule_id": "RULE_001",
                "rule_name": "Politically Exposed Person (PEP) List Check",
                "severity": "High",
                "description": "Customer name matches known PEP list. Requires enhanced due diligence.",
                "affected_record_indices": breached_indices
            })
        
        return findings
    
    def _check_sanctions_list(self, df) -> List[Dict[str, Any]]:
        """Rule 2: Check for sanctions list hits"""
        findings = []
        
        # Check both country and entity name if available
        country_col = next((col for col in df.columns 
                          if col.lower() in ["country", "jurisdiction", "country_of_origin"]), None)
        entity_col = next((col for col in df.columns 
                         if col.lower() in ["entity_name", "business_name", "company_name"]), None)
        
        breached_indices = []
        for idx in df.index:
            hit = False
            
            # Check country column
            if country_col and pd.notna(df.loc[idx, country_col]):
                country = str(df.loc[idx, country_col]).lower().strip()
                if country in self.SANCTIONS_LIST:
                    hit = True
            
            # Check entity column
            if entity_col and pd.notna(df.loc[idx, entity_col]):
                entity = str(df.loc[idx, entity_col]).lower().strip()
                if any(country in entity for country in self.SANCTIONS_LIST):
                    hit = True
            
            if hit:
                breached_indices.append(idx)
        
        if breached_indices:
            findings.append({
                "rule_id": "RULE_002",
                "rule_name": "Sanctions List Match",
                "severity": "High",
                "description": "Customer or related entity matches sanctions list. Transaction blocking required.",
                "affected_record_indices": breached_indices
            })
        
        return findings
    
    def _check_high_risk_countries(self, df) -> List[Dict[str, Any]]:
        """Rule 3: Check for high-risk country exposure"""
        findings = []
        
        country_col = next((col for col in df.columns 
                          if col.lower() in ["country", "jurisdiction", "country_of_origin"]), None)
        
        if not country_col:
            return findings
        
        breached_indices = []
        for idx, country in enumerate(df[country_col]):
            if pd.isna(country):
                continue
            country_lower = str(country).lower().strip()
            if country_lower in self.HIGH_RISK_COUNTRIES:
                breached_indices.append(idx)
        
        if breached_indices:
            findings.append({
                "rule_id": "RULE_003",
                "rule_name": "High-Risk Country Exposure",
                "severity": "Medium",
                "description": "Customer operates in high-risk jurisdiction. Enhanced monitoring required.",
                "affected_record_indices": breached_indices
            })
        
        return findings
    
    def _check_unusual_transactions(self, df) -> List[Dict[str, Any]]:
        """Rule 4: Check for unusual transaction patterns"""
        findings = []
        
        # Look for transaction amount column
        amount_col = next((col for col in df.columns 
                         if col.lower() in ["transaction_amount", "amount", "value", "transaction_value"]), None)
        
        if not amount_col:
            return findings
        
        # Convert to numeric, handling errors
        try:
            amounts = pd.to_numeric(df[amount_col], errors='coerce')
        except:
            return findings
        
        # Rule: Amounts over $1M are flagged as potentially unusual
        threshold = 1_000_000
        breached_indices = amounts[amounts > threshold].index.tolist()
        
        if breached_indices:
            findings.append({
                "rule_id": "RULE_004",
                "rule_name": "Unusual Transaction Patterns",
                "severity": "Medium",
                "description": f"Transaction amount exceeds ${threshold:,} threshold. Review for structuring/layering.",
                "affected_record_indices": breached_indices
            })
        
        return findings
    
    def _check_account_age(self, df) -> List[Dict[str, Any]]:
        """Rule 5: Check account age (new accounts are higher risk)"""
        findings = []
        
        # Look for account opening date column
        date_col = next((col for col in df.columns 
                       if col.lower() in ["account_open_date", "onboarding_date", "creation_date"]), None)
        
        if not date_col:
            return findings
        
        try:
            dates = pd.to_datetime(df[date_col], errors='coerce')
        except:
            return findings
        
        # Flag accounts opened within last 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        breached_indices = df[dates > cutoff_date].index.tolist()
        
        if breached_indices:
            findings.append({
                "rule_id": "RULE_005",
                "rule_name": "Account Age Verification",
                "severity": "Low",
                "description": "Account opened within last 30 days. Verify customer identity and source of funds.",
                "affected_record_indices": breached_indices
            })
        
        return findings
    
    def _check_document_verification(self, df) -> List[Dict[str, Any]]:
        """Rule 6: Check document verification status"""
        findings = []
        
        # Look for verification status column
        status_col = next((col for col in df.columns 
                         if col.lower() in ["verification_status", "kyc_status", "doc_status"]), None)
        
        if not status_col:
            return findings
        
        # Flag incomplete/pending verifications
        unverified_statuses = ["pending", "incomplete", "rejected", "expired", ""]
        breached_indices = df[
            df[status_col].fillna("").str.lower().isin(unverified_statuses)
        ].index.tolist()
        
        if breached_indices:
            findings.append({
                "rule_id": "RULE_006",
                "rule_name": "Document Verification Status",
                "severity": "Medium",
                "description": "Customer documentation not verified or verification expired. Complete KYC process required.",
                "affected_record_indices": breached_indices
            })
        
        return findings


def apply_compliance_rules(df, logger=None) -> List[Dict[str, Any]]:
    """
    Convenience function to apply all compliance rules to a dataset.
    
    Args:
        df: pandas DataFrame with customer data
        logger: optional logger instance
    
    Returns:
        List of findings
    """
    import pandas as pd
    
    engine = ComplianceRulesEngine()
    findings = engine.apply_all_rules(df)
    
    if logger:
        logger.info(f"Compliance rules applied. Found {len(findings)} rule breaches.")
    
    return findings
