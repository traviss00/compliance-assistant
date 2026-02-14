"""
LLM Integration Module

Responsible for interpreting and summarizing compliance findings.

Design Philosophy:
- LLM is used ONLY for interpretation and explanation
- All decisions remain with deterministic rules
- LLM output is structured and validated before use
- Fallback to rule-based summary if LLM fails (graceful degradation)
- Clear audit trail of what was sent to LLM and what was received
- Support for multiple LLM providers (OpenAI, Hugging Face)

Key Principle: The LLM informs, it does not decide.

Configuration:
- LLM_PROVIDER: Set to "openai" or "huggingface" (optional, defaults to fallback)
- OPENAI_API_KEY: Required if using OpenAI
- HUGGINGFACE_API_KEY: Required if using Hugging Face
"""

import os
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

# Import optional LLM libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def summarize_findings(
    dataset_info: Dict[str, Any],
    findings: List[Dict[str, Any]],
    check_id: str,
    logger: Optional[logging.Logger] = None
) -> Tuple[str, str, List[str]]:
    """
    Summarize compliance findings using an LLM.
    
    This function:
    1. Prepares a structured prompt with deterministic findings
    2. Calls OpenAI API (with fallback if unavailable)
    3. Parses LLM response into structured format
    4. Returns plain-English summary, risk classification, and next actions
    
    The LLM is constrained to:
    - NOT make decisions about rule breaches
    - NOT modify or reinterpret the findings
    - ONLY explain the implications and suggest next steps
    
    Args:
        dataset_info: Dict with dataset metadata (filename, record count, columns)
        findings: List of deterministic rule findings
        check_id: Audit identifier
        logger: Optional logger
    
    Returns:
        Tuple of (summary, risk_classification, next_actions)
    """
    
    if not logger:
        logger = logging.getLogger(__name__)
    
    logger.info(f"[{check_id}] Summarizing {len(findings)} findings via LLM")
    
    # Prepare structured findings for LLM
    findings_summary = _format_findings_for_llm(findings)
    
    # Build the prompt
    prompt = _build_compliance_prompt(dataset_info, findings_summary, findings)
    
    logger.info(f"[{check_id}] LLM Prompt length: {len(prompt)} characters")
    
    # Determine which LLM provider to use
    llm_provider = os.getenv("LLM_PROVIDER", "").lower()
    
    # Try LLM summarization with selected provider
    try:
        if llm_provider == "openai":
            summary, risk, actions = _call_openai(prompt, check_id, logger)
        elif llm_provider == "huggingface":
            summary, risk, actions = _call_huggingface(prompt, check_id, logger)
        else:
            # No valid provider configured, skip to fallback
            raise Exception(f"LLM_PROVIDER not set or invalid: {llm_provider or 'empty'}")
        
        logger.info(f"[{check_id}] LLM ({llm_provider}) summarization successful. Risk: {risk}")
        return summary, risk, actions
    
    except Exception as e:
        logger.warning(f"[{check_id}] LLM call failed: {e}. Using fallback summarization.")
        # Graceful degradation: fall back to rule-based summary
        return _fallback_summarization(findings, logger, check_id)


def _format_findings_for_llm(findings: List[Dict[str, Any]]) -> str:
    """
    Format findings into a clear, structured text representation for the LLM.
    
    This ensures the LLM sees consistent, well-structured information.
    """
    
    if not findings:
        return "No compliance rule breaches detected."
    
    formatted = []
    
    for i, finding in enumerate(findings, 1):
        formatted.append(f"\n{i}. {finding.get('rule_name', 'Unknown Rule')}")
        formatted.append(f"   Rule ID: {finding.get('rule_id', 'N/A')}")
        formatted.append(f"   Severity: {finding.get('severity', 'Unknown')}")
        formatted.append(f"   Affected Records: {len(finding.get('affected_record_indices', []))}")
        formatted.append(f"   Description: {finding.get('description', 'No description')}")
        
        # Include percentage of dataset if available
        if 'percentage_of_dataset' in finding:
            formatted.append(f"   Percentage of Dataset: {finding['percentage_of_dataset']}%")
    
    return "\n".join(formatted)


def _build_compliance_prompt(
    dataset_info: Dict[str, Any],
    findings_summary: str,
    findings: List[Dict[str, Any]]
) -> str:
    """
    Build a structured prompt that constrains LLM behavior.
    
    The prompt:
    - Explicitly states the LLM's role (interpreter, not decision-maker)
    - Provides deterministic findings
    - Requests specific output format
    - Sets clear boundaries (no reinterpretation)
    """
    
    # Calculate aggregates
    total_breaches = len(findings)
    high_severity = len([f for f in findings if f.get('severity') == 'High'])
    medium_severity = len([f for f in findings if f.get('severity') == 'Medium'])
    low_severity = len([f for f in findings if f.get('severity') == 'Low'])
    
    prompt = f"""You are a compliance analyst assistant reviewing AML/KYC (Anti-Money Laundering / Know Your Customer) findings.

IMPORTANT CONSTRAINTS:
- You are analyzing PRE-DETERMINED, DETERMINISTIC findings from compliance rules
- You must NOT reinterpret, override, or challenge these findings
- Your role is to explain implications and suggest next steps for human review
- You must classify overall risk as: Low / Medium / High
- All decisions remain with human compliance officers

DATASET INFORMATION:
- File: {dataset_info.get('filename', 'Unknown')}
- Total Records: {dataset_info.get('total_records', 0)}
- Columns: {len(dataset_info.get('columns', []))}

DETERMINISTIC COMPLIANCE FINDINGS:
{findings_summary}

FINDING SUMMARY:
- Total Rule Breaches: {total_breaches}
- High Severity: {high_severity}
- Medium Severity: {medium_severity}
- Low Severity: {low_severity}

TASK:
Provide a JSON response with exactly this structure (no other text):
{{
  "summary": "A 2-3 sentence plain-English summary of the findings and their implications.",
  "risk_classification": "Low | Medium | High",
  "next_actions": [
    "First action for compliance officer",
    "Second action",
    "Third action"
  ]
}}

Remember:
- Do NOT suggest ignoring any findings
- Do NOT make judgment calls on whether breaches are valid
- Do NOT reinterpret the rules
- Focus on: What should the compliance officer review next?"""
    
    return prompt


def _call_openai(
    prompt: str,
    check_id: str,
    logger: logging.Logger
) -> Tuple[str, str, List[str]]:
    """
    Call OpenAI API to summarize findings.
    
    Error Handling:
    - API key missing → Clear error message
    - Network error → Logged with recovery instructions
    - Invalid JSON response → Validated and sanitized
    - Invalid risk classification → Defaults to Medium
    
    Args:
        prompt: Formatted prompt for the LLM
        check_id: Audit identifier
        logger: Logger instance
    
    Returns:
        Tuple of (summary, risk_classification, next_actions)
    
    Raises:
        Exception: If API call fails (caller will use fallback)
    """
    
    # Check: OpenAI library available
    if not OPENAI_AVAILABLE:
        raise Exception(
            "OpenAI library not installed. Install with: pip install openai"
        )
    
    # Check: API key configured
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception(
            "OPENAI_API_KEY not configured. "
            "Set environment variable: export OPENAI_API_KEY='sk-...'"
        )
    
    # Initialize client
    try:
        client = openai.OpenAI(api_key=api_key)
    except Exception as e:
        raise Exception(f"Failed to initialize OpenAI client: {str(e)}")
    
    logger.info(f"[{check_id}] Calling OpenAI API (model: gpt-4o)...")
    
    try:
        # Call API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a compliance analyst assistant. Respond ONLY with valid JSON, no other text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for consistency
            max_tokens=500,
            timeout=30  # 30 second timeout
        )
        
        # Extract response
        response_text = response.choices[0].message.content.strip()
        logger.info(f"[{check_id}] ✓ LLM response received ({len(response_text)} chars)")
        
        # Validate response is not empty
        if not response_text:
            raise Exception("LLM returned empty response")
        
        # Parse JSON response with error handling
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise Exception(
                f"LLM returned invalid JSON: {str(e)}. "
                f"Response: {response_text[:100]}..."
            )
        
        # Validate response structure
        if not isinstance(response_json, dict):
            raise Exception(f"Expected JSON object, got {type(response_json).__name__}")
        
        # Extract fields with validation
        summary = response_json.get("summary", "")
        if not summary or not isinstance(summary, str):
            logger.warning(f"[{check_id}] Invalid summary field in LLM response")
            summary = "Assessment complete. Review findings below."
        
        risk_classification = str(response_json.get("risk_classification", "Medium")).title()
        if risk_classification not in ["Low", "Medium", "High"]:
            logger.warning(
                f"[{check_id}] Invalid risk classification from LLM: {risk_classification}. "
                f"Defaulting to 'Medium'"
            )
            risk_classification = "Medium"
        
        next_actions = response_json.get("next_actions", [])
        if not isinstance(next_actions, list):
            logger.warning(f"[{check_id}] Invalid next_actions field (not a list), using default")
            next_actions = []
        
        # Validate and clean action items
        next_actions = [str(a).strip() for a in next_actions if a]
        if len(next_actions) == 0:
            next_actions = ["Review findings with compliance officer", "Document any actions taken"]
        
        logger.info(
            f"[{check_id}] ✓ LLM parsing successful. "
            f"Risk: {risk_classification}, Actions: {len(next_actions)}"
        )
        
        return summary, risk_classification, next_actions
    
    except Exception as e:
        # All OpenAI errors propagate up for fallback handling
        logger.warning(f"[{check_id}] OpenAI call failed: {str(e)}")
        raise
    
    except json.JSONDecodeError as e:
        logger.error(f"[{check_id}] Failed to parse LLM response as JSON: {e}")
        raise Exception(f"Invalid JSON response from LLM: {e}")
    
    except Exception as e:
        logger.error(f"[{check_id}] OpenAI API error: {e}")
        raise


def _call_huggingface(
    prompt: str,
    check_id: str,
    logger: logging.Logger
) -> Tuple[str, str, List[str]]:
    """
    Call Hugging Face Inference API to summarize findings.
    
    Supports Hugging Face's free inference API with pooled quota or 
    premium endpoints for dedicated models.
    
    Error Handling:
    - API key missing → Clear error message
    - Network error → Logged with recovery instructions
    - Invalid JSON response → Validated and sanitized
    - Invalid risk classification → Defaults to Medium
    
    Args:
        prompt: Formatted prompt for the LLM
        check_id: Audit identifier
        logger: Logger instance
    
    Returns:
        Tuple of (summary, risk_classification, next_actions)
    
    Raises:
        Exception: If API call fails (caller will use fallback)
    """
    
    # Check: requests library available
    if not REQUESTS_AVAILABLE:
        raise Exception(
            "requests library not installed. Install with: pip install requests"
        )
    
    # Check: API key configured
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        raise Exception(
            "HUGGINGFACE_API_KEY not configured. "
            "Get from: https://huggingface.co/settings/tokens"
        )
    
    # Determine model(s) to try. Allow override via HUGGINGFACE_MODEL env var.
    # Uses the HuggingFace Chat Completions API (OpenAI-compatible endpoint).
    default_models = [
        "google/flan-t5-small",
        "mistralai/Mistral-7B-Instruct-v0.1",
        "meta-llama/Llama-2-7b-chat-hf",
        "meta-llama/Llama-2-13b-chat-hf",
        "moonshotai/Kimi-K2-Instruct-0905:groq"

    ]

    env_model = os.getenv("HUGGINGFACE_MODEL")
    env_fallback = os.getenv("HUGGINGFACE_MODEL_FALLBACK")

    if env_model:
        models_to_try = [m.strip() for m in env_model.split(",") if m.strip()]
    else:
        models_to_try = default_models.copy()

    # If an explicit fallback list provided, append those as well
    if env_fallback:
        models_to_try += [m.strip() for m in env_fallback.split(",") if m.strip()]

    headers = {"Authorization": f"Bearer {api_key}"}

    # Use HuggingFace Chat Completions endpoint (OpenAI-compatible API)
    api_url = "https://router.huggingface.co/v1/chat/completions"

    last_exc = None
    for model_id in models_to_try:
        logger.info(f"[{check_id}] Calling Hugging Face API (model: {model_id})...")

        try:
            # Call HuggingFace Chat Completions API (OpenAI-compatible format)
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a compliance analyst assistant. Respond ONLY with valid JSON, no other text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }

            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()
            logger.info(f"[{check_id}] ✓ Hugging Face response received (model: {model_id})")
            # Successfully got a response; break to continue processing.
            break

        except requests.exceptions.HTTPError as he:
            last_exc = he
            logger.error(f"[{check_id}] Hugging Face API HTTP error for model {model_id}: {he}")
            # Try next model if this one fails
            logger.warning(f"[{check_id}] Model {model_id} failed. Trying next model...")
            continue

        except requests.exceptions.RequestException as re:
            last_exc = re
            logger.error(f"[{check_id}] Hugging Face API request failed for model {model_id}: {re}")
            # Try next model for transient network errors
            continue

    # After trying models, ensure we have a successful response in `result`.
    if 'result' not in locals():
        raise Exception(f"All Hugging Face model attempts failed. Last error: {last_exc}")

    # Handle response format - Chat Completions API returns OpenAI-compatible structure
    if "choices" in result and len(result["choices"]) > 0:
        response_text = result["choices"][0].get("message", {}).get("content", "").strip()
    else:
        raise Exception(f"Unexpected Hugging Face API response format: {result}")

    # Validate response is not empty
    if not response_text:
        raise Exception("Hugging Face returned empty response")

    # Try to extract JSON from response (model may wrap it in extra text)
    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1

    if json_start != -1 and json_end > json_start:
        response_text = response_text[json_start:json_end]

    # Parse JSON response with error handling
    try:
        response_json = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"[{check_id}] Failed to parse Hugging Face response as JSON: {e}")
        raise Exception(
            f"Hugging Face returned invalid JSON: {str(e)}. Response: {response_text[:100]}..."
        )

    # Validate response structure
    if not isinstance(response_json, dict):
        raise Exception(f"Expected JSON object, got {type(response_json).__name__}")

    # Extract fields with validation
    summary = response_json.get("summary", "")
    if not summary or not isinstance(summary, str):
        logger.warning(f"[{check_id}] Invalid summary field in Hugging Face response")
        summary = "Assessment complete. Review findings below."

    risk_classification = str(response_json.get("risk_classification", "Medium")).title()
    if risk_classification not in ["Low", "Medium", "High"]:
        logger.warning(
            f"[{check_id}] Invalid risk classification from Hugging Face: {risk_classification}. Defaulting to 'Medium'"
        )
        risk_classification = "Medium"

    next_actions = response_json.get("next_actions", [])
    if not isinstance(next_actions, list):
        logger.warning(f"[{check_id}] Invalid next_actions field (not a list), using default")
        next_actions = []

    # Validate and clean action items
    next_actions = [str(a).strip() for a in next_actions if a]
    if len(next_actions) == 0:
        next_actions = ["Review findings with compliance officer", "Document any actions taken"]

    logger.info(
        f"[{check_id}] ✓ Hugging Face parsing successful. Risk: {risk_classification}, Actions: {len(next_actions)}"
    )

    return summary, risk_classification, next_actions


def _fallback_summarization(
    findings: List[Dict[str, Any]],
    logger: logging.Logger,
    check_id: str
) -> Tuple[str, str, List[str]]:
    """
    Fallback summarization when LLM is unavailable.
    
    Purpose: Ensure assessment completes even without OpenAI API
    
    Uses rule-based logic to:
    - Generate a brief summary from deterministic findings
    - Classify overall risk level
    - Suggest next actions
    
    This maintains operational continuity and demonstrates graceful degradation.
    """
    
    logger.warning(f"[{check_id}] [FALLBACK] Using rule-based summary (LLM unavailable)")
    
    try:
        # Determine risk classification from findings
        risk_classification = _determine_risk_classification(findings)
        
        # Generate summary text
        summary = _generate_summary_text(findings, risk_classification)
        
        # Generate next actions
        next_actions = _generate_next_actions(findings, risk_classification)
        
        logger.info(
            f"[{check_id}] ✓ Fallback summarization complete. "
            f"Risk: {risk_classification}, Actions: {len(next_actions)}"
        )
        
        return summary, risk_classification, next_actions
    
    except Exception as e:
        # Even fallback can fail - provide bare minimum response
        logger.error(f"[{check_id}] Fallback summarization failed: {str(e)}")
        return (
            "Assessment complete. Review findings table below.",
            "Medium",
            ["Review all findings", "Document actions taken"]
        )


def _determine_risk_classification(findings: List[Dict[str, Any]]) -> str:
    """Determine overall risk level from findings."""
    if not findings:
        return "Low"
    
    high_severity = [f for f in findings if f.get("severity") == "High"]
    if high_severity:
        return "High"
    
    medium_severity = [f for f in findings if f.get("severity") == "Medium"]
    if len(medium_severity) >= 3:
        return "High"
    elif medium_severity:
        return "Medium"
    
    return "Low"


def _generate_summary_text(findings: List[Dict[str, Any]], risk_classification: str) -> str:
    """Generate human-readable summary from findings."""
    if not findings:
        return "No compliance rule breaches detected. Assessment complete."
    
    high_count = len([f for f in findings if f.get("severity") == "High"])
    medium_count = len([f for f in findings if f.get("severity") == "Medium"])
    low_count = len([f for f in findings if f.get("severity") == "Low"])
    
    summary_parts = [
        f"Compliance assessment identified {len(findings)} rule breach(es):"
    ]
    
    if high_count > 0:
        summary_parts.append(f"• {high_count} high-severity finding(s) requiring immediate escalation")
    if medium_count > 0:
        summary_parts.append(f"• {medium_count} medium-severity finding(s) requiring review")
    if low_count > 0:
        summary_parts.append(f"• {low_count} low-severity finding(s) for documentation")
    
    summary_parts.append(f"Overall risk classification: {risk_classification}")
    
    return " ".join(summary_parts)


def _generate_next_actions(findings: List[Dict[str, Any]], risk_classification: str) -> list:
    """Generate suggested next actions based on findings."""
    actions = []
    
    high_severity = [f for f in findings if f.get("severity") == "High"]
    if high_severity:
        actions.append("⚠️ Immediately escalate high-severity findings to compliance officer")
    
    if findings:
        actions.append("Review all findings in the table above with affected record indices")
        actions.append("For each finding, verify the rule application is correct")
    
    actions.append("Document all decisions and actions taken for audit trail")
    
    return actions
