"""
LangGraph Workflow Nodes

Defines the node functions for the verification workflow:
1. npi_lookup - Query NPI Registry (rule-based parsing, NO LLM)
2. board_lookup - Query CA DCA license search
3. leie_lookup - Query LEIE exclusion list
4. discrepancy_detection - Use Claude to analyze findings (ONLY LLM call)
5. route_decision - Rule-based routing based on confidence
6. human_review - LangGraph interrupt for HITL
7. finalize - Compile report and persist to database
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)

from graph.state import VerificationState, set_hitl_escalation


def _extract_json(text: str) -> str | None:
    text = (text or "").strip()
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text
from sources.npi import lookup_npi
from sources.dca import lookup_dca_license
from sources.leie import lookup_leie, is_excluded, format_exclusion_reason
from llm.provider import get_llm_provider
from config import (
    CONFIDENCE_AUTO_VERIFY,
    CONFIDENCE_FLAG_REVIEW,
    COST_PER_1K_INPUT_TOKENS,
    COST_PER_1K_OUTPUT_TOKENS,
)
import db


async def npi_lookup(state: VerificationState) -> Dict[str, Any]:
    """
    Node 1: Query NPI Registry API.

    This is a RULE-BASED node - NO LLM is called here.
    Parses the NPI response to extract license information.

    Returns partial state updates.
    """
    updates = {"verification_status": "npi_lookup"}
    start_time = time.time()

    try:
        npi_number = state.get("npi_number", "")
        target_state = state.get("target_state", "CA")
        logger.info("[NPI] Starting lookup for NPI=%s state=%s", npi_number, target_state)

        result = await lookup_npi(npi_number, target_state)

        logger.info(
            "[NPI] Result: found=%s active=%s license=%s latency=%dms",
            result.npi_found, result.npi_active, result.license_number, result.latency_ms,
        )

        # Update state from NPI lookup result
        updates["npi_response"] = result.raw_response
        updates["npi_found"] = result.npi_found
        updates["npi_active"] = result.npi_active
        updates["provider_name"] = result.provider_name
        updates["provider_first_name"] = result.provider_first_name
        updates["provider_last_name"] = result.provider_last_name
        updates["provider_credential"] = result.provider_credential
        updates["provider_specialty"] = result.provider_specialty
        updates["license_number"] = result.license_number
        updates["license_state"] = result.license_state
        updates["all_taxonomies"] = result.all_taxonomies
        updates["all_addresses"] = result.all_addresses

        # Record latency and retries
        step_latencies = dict(state.get("step_latencies", {}))
        step_latencies["npi_ms"] = result.latency_ms
        updates["step_latencies"] = step_latencies

        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts["npi"] = result.retry_count
        updates["retry_counts"] = retry_counts

        # Add warnings to discrepancies
        discrepancies = list(state.get("discrepancies", []))
        if result.warnings:
            discrepancies.extend(result.warnings)
        updates["discrepancies"] = discrepancies

        # Check for HITL triggers
        if result.needs_hitl:
            logger.warning("[HITL] NPI lookup triggered escalation: %s", result.hitl_reason)
            updates["needs_human_review"] = True
            updates["human_review_reason"] = result.hitl_reason
            updates["verification_status"] = "escalated"
            updates["human_review_links"] = [
                {
                    "label": "Look up on NPI Registry",
                    "url": f"https://npiregistry.cms.hhs.gov/api/?version=2.1&number={npi_number}"
                },
                {
                    "label": "Search CA DCA",
                    "url": "https://search.dca.ca.gov/?BD=800"
                }
            ]

    except Exception as e:
        logger.error("[NPI] Lookup failed for NPI=%s: %s", state.get("npi_number"), e, exc_info=True)
        source_available = dict(state.get("source_available", {"npi": True, "dca": True, "leie": True}))
        source_available["npi"] = False
        updates["source_available"] = source_available

        errors = list(state.get("errors", []))
        errors.append(f"NPI lookup error: {str(e)}")
        updates["errors"] = errors

        updates["needs_human_review"] = True
        updates["human_review_reason"] = f"NPI source error: {str(e)}"
        updates["verification_status"] = "escalated"

        step_latencies = dict(state.get("step_latencies", {}))
        step_latencies["npi_ms"] = int((time.time() - start_time) * 1000)
        updates["step_latencies"] = step_latencies

    return updates


async def board_lookup(state: VerificationState) -> Dict[str, Any]:
    """
    Node 2: Query CA DCA license search.

    Runs in PARALLEL with leie_lookup.
    """
    updates = {"verification_status": "license_check"}

    # Skip if no license number was found in NPI lookup
    license_number = state.get("license_number")
    if not license_number:
        logger.info("[DCA] Skipping board lookup — no license number from NPI")
        source_available = dict(state.get("source_available", {"npi": True, "dca": True, "leie": True}))
        source_available["dca"] = False
        updates["source_available"] = source_available

        errors = list(state.get("errors", []))
        errors.append("No license number to look up in DCA")
        updates["errors"] = errors
        return updates

    try:
        target_state = state.get("target_state", "CA")
        logger.info("[DCA] Starting board lookup for license=%s", license_number)
        result = await lookup_dca_license(license_number, target_state)

        logger.info(
            "[DCA] Result: status=%s expiry=%s disciplinary=%s latency=%dms",
            result.license_status, result.expiration_date,
            result.has_disciplinary_action, result.latency_ms,
        )

        # Update state from DCA lookup result
        updates["board_license_status"] = result.license_status
        updates["board_expiration_date"] = result.expiration_date
        updates["board_name_on_license"] = result.name_on_license
        updates["board_secondary_status"] = result.secondary_status
        updates["board_has_disciplinary_action"] = result.has_disciplinary_action
        updates["board_has_public_documents"] = result.has_public_documents
        updates["board_detail_url"] = result.detail_url
        updates["board_city"] = result.city
        updates["board_raw"] = result.raw_response

        # Record latency and retries
        step_latencies = dict(state.get("step_latencies", {}))
        step_latencies["dca_ms"] = result.latency_ms
        updates["step_latencies"] = step_latencies

        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts["dca"] = result.retry_count
        updates["retry_counts"] = retry_counts

        # Check source availability
        if not result.source_available:
            logger.warning("[DCA] Source unavailable: %s", result.error_message)
            source_available = dict(state.get("source_available", {"npi": True, "dca": True, "leie": True}))
            source_available["dca"] = False
            updates["source_available"] = source_available

            errors = list(state.get("errors", []))
            errors.append(f"DCA source unavailable: {result.error_message}")
            updates["errors"] = errors

    except Exception as e:
        logger.error("[DCA] Lookup failed for license=%s: %s", license_number, e, exc_info=True)
        source_available = dict(state.get("source_available", {"npi": True, "dca": True, "leie": True}))
        source_available["dca"] = False
        updates["source_available"] = source_available

        errors = list(state.get("errors", []))
        errors.append(f"DCA lookup error: {str(e)}")
        updates["errors"] = errors

    return updates


async def leie_lookup(state: VerificationState) -> Dict[str, Any]:
    """
    Node 3: Query LEIE exclusion list.

    Runs in PARALLEL with board_lookup.
    """
    updates = {}

    try:
        npi_number = state.get("npi_number", "")
        first_name = state.get("provider_first_name")
        last_name = state.get("provider_last_name")
        target_state = state.get("target_state", "CA")
        logger.info("[LEIE] Starting exclusion check NPI=%s name=%s,%s state=%s",
                     npi_number, last_name, first_name, target_state)

        result = lookup_leie(
            npi=npi_number,
            first_name=first_name,
            last_name=last_name,
            state=target_state,
        )

        # Update state from LEIE lookup result
        updates["leie_match"] = result.leie_match
        updates["leie_record"] = result.leie_record

        if result.leie_match:
            logger.warning("[LEIE] Exclusion match found: type=%s latency=%dms",
                           result.match_type, result.latency_ms)
        else:
            logger.info("[LEIE] No exclusion match, latency=%dms", result.latency_ms)

        # Record latency
        step_latencies = dict(state.get("step_latencies", {}))
        step_latencies["leie_ms"] = result.latency_ms
        updates["step_latencies"] = step_latencies

    except Exception as e:
        logger.error("[LEIE] Lookup failed: %s", e, exc_info=True)
        source_available = dict(state.get("source_available", {"npi": True, "dca": True, "leie": True}))
        source_available["leie"] = False
        updates["source_available"] = source_available

        errors = list(state.get("errors", []))
        errors.append(f"LEIE lookup error: {str(e)}")
        updates["errors"] = errors

    return updates


async def discrepancy_detection(state: VerificationState) -> Dict[str, Any]:
    """
    Node 4: Use Claude to analyze findings.

    THIS IS THE ONLY NODE THAT CALLS THE LLM.
    """
    updates = {"verification_status": "analyzing"}
    start_time = time.time()

    logger.info("[LLM] Starting discrepancy detection")

    # Build the prompt with all collected evidence
    evidence = _build_evidence_summary(state)

    system_prompt = """You are a healthcare credentialing verification specialist.
Given the following evidence from three verification sources (NPI Registry, CA DCA License Search, and OIG LEIE Exclusion List), identify any discrepancies or concerns and assign a confidence score from 0 to 100.

Scoring guidelines:
- 90-100: All sources consistent, no concerns, provider is clearly in good standing
- 70-89: Minor concerns or discrepancies that need attention but are not disqualifying
- 50-69: Significant concerns or missing data that require human review
- 0-49: Major discrepancies or disqualifying conditions found

If any source is unavailable, reduce confidence accordingly (typically by 20-30 points).
If the license status is not "Current/Active" or "Licensed - Current", this is a major concern.
If there are disciplinary actions, reduce confidence significantly.

Respond with valid JSON only, in this exact format:
{"discrepancies": ["description 1", "description 2"], "confidence_score": 85, "reasoning": "Brief explanation of your assessment"}"""

    user_prompt = f"""Analyze the following verification evidence and provide your assessment:

{evidence}

Remember: Respond with valid JSON only."""

    try:
        logger.debug("[LLM] Evidence length=%d, system prompt length=%d", len(evidence), len(system_prompt))
        llm = get_llm_provider()
        response = await llm.query(user_prompt, system_prompt)

        # Record token usage
        updates["llm_tokens_used"] = llm.get_tokens_used()
        logger.info("[LLM] Response: tokens=%d length=%d latency=%dms",
                     llm.get_tokens_used(), len(response) if response else 0,
                     int((time.time() - start_time) * 1000))

        step_latencies = dict(state.get("step_latencies", {}))
        step_latencies["llm_ms"] = int((time.time() - start_time) * 1000)
        updates["step_latencies"] = step_latencies

        # Parse LLM response (try raw first, then extract from markdown code blocks)
        to_parse = _extract_json(response) or response
        try:
            parsed = json.loads(to_parse)
            discrepancies = list(state.get("discrepancies", []))
            discrepancies.extend(parsed.get("discrepancies", []))
            updates["discrepancies"] = discrepancies
            updates["confidence_score"] = parsed.get("confidence_score", 50)
            updates["confidence_reasoning"] = parsed.get("reasoning", "")
            logger.info("[LLM] Parsed: confidence=%s discrepancies=%d",
                         parsed.get("confidence_score"), len(parsed.get("discrepancies", [])))
        except json.JSONDecodeError as e:
            logger.warning(
                "[LLM] JSON parse failed: %s. Raw response (first 500 chars): %s",
                e, repr(response[:500]) if response else "None",
            )
            errors = list(state.get("errors", []))
            errors.append("Failed to parse LLM response as JSON")
            updates["errors"] = errors
            updates["confidence_score"] = 50
            updates["confidence_reasoning"] = "Unable to parse LLM response"

    except Exception as e:
        logger.error("[LLM] Discrepancy detection failed: %s", e, exc_info=True)
        errors = list(state.get("errors", []))
        errors.append(f"LLM error: {str(e)}")
        updates["errors"] = errors
        updates["confidence_score"] = 50
        updates["confidence_reasoning"] = f"LLM error: {str(e)}"

        step_latencies = dict(state.get("step_latencies", {}))
        step_latencies["llm_ms"] = int((time.time() - start_time) * 1000)
        updates["step_latencies"] = step_latencies

    # Calculate cost
    updates["cost_usd"] = _calculate_cost(updates.get("llm_tokens_used", 0))
    logger.debug("[LLM] Estimated cost: $%.6f", updates["cost_usd"])

    return updates


def route_decision(state: VerificationState) -> str:
    """
    Node 5: Rule-based routing decision.

    NO LLM is called here. Pure rule-based logic.

    Returns:
        "verify", "flag", "fail", or "review"
    """
    logger.debug("[ROUTE] Inputs: leie_match=%s board_status=%s needs_review=%s confidence=%s",
                  state.get("leie_match"), state.get("board_license_status"),
                  state.get("needs_human_review"), state.get("confidence_score"))

    # Rule 1: LEIE match is automatic failure
    if state.get("leie_match", False):
        logger.info("[ROUTE] Decision=fail (Rule 1: LEIE match)")
        return "fail"

    # Rule 2: License Revoked is automatic failure
    board_status = state.get("board_license_status") or ""
    if board_status == "License Revoked":
        logger.info("[ROUTE] Decision=fail (Rule 2: License Revoked)")
        return "fail"

    # Rule 3: Already flagged for HITL
    if state.get("needs_human_review", False):
        logger.info("[ROUTE] Decision=review (Rule 3: HITL flagged)")
        return "review"

    # Rule 4: Source unavailable - escalate to human review
    source_available = state.get("source_available", {"npi": True, "dca": True, "leie": True})
    if not all(source_available.values()):
        unavailable = [k for k, v in source_available.items() if not v]
        logger.info("[ROUTE] Decision=review (Rule 4: source unavailable: %s)", ", ".join(unavailable))
        return "review"

    # Get confidence score (default to 50 if not set)
    confidence = state.get("confidence_score") or 50

    # Rule 5: High confidence - auto-verify
    if confidence >= CONFIDENCE_AUTO_VERIFY and not state.get("discrepancies"):
        logger.info("[ROUTE] Decision=verify (Rule 5: confidence=%d)", confidence)
        return "verify"

    # Rule 6: Medium confidence - flag for review
    if confidence >= CONFIDENCE_FLAG_REVIEW:
        logger.info("[ROUTE] Decision=flag (Rule 6: confidence=%d)", confidence)
        return "flag"

    # Rule 7: Low confidence - escalate to human
    logger.info("[ROUTE] Decision=review (Rule 7: low confidence=%d)", confidence)
    return "review"


async def route_decision_node(state: VerificationState) -> Dict[str, Any]:
    """
    Wrapper node for route_decision that updates state based on routing.
    """
    updates = {}

    # Apply routing logic
    decision = route_decision(state)
    logger.info("[ROUTE] Decision node: decision=%s", decision)

    if decision == "fail":
        updates["verification_status"] = "failed"
        # Auto-fail cases skip the LLM — set confidence to 100 since
        # LEIE exclusion and license revocation are deterministic failures
        if state.get("confidence_score") is None:
            updates["confidence_score"] = 100
        leie_record = state.get("leie_record")
        if leie_record:
            updates["confidence_reasoning"] = "Automatic failure: OIG LEIE exclusion match"
            discrepancies = list(state.get("discrepancies", []))
            discrepancies.append(format_exclusion_reason(leie_record))
            updates["discrepancies"] = discrepancies
        elif (state.get("board_license_status") or "") == "License Revoked":
            updates["confidence_reasoning"] = "Automatic failure: state board license revoked"
            discrepancies = list(state.get("discrepancies", []))
            discrepancies.append(
                "AUTOMATIC FAIL: State board license status is 'License Revoked'. "
                "Physician cannot legally practice medicine."
            )
            updates["discrepancies"] = discrepancies

    elif decision == "flag":
        updates["verification_status"] = "flagged"
        source_available = state.get("source_available", {"npi": True, "dca": True, "leie": True})
        if not all(source_available.values()):
            unavailable = [k for k, v in source_available.items() if not v]
            discrepancies = list(state.get("discrepancies", []))
            discrepancies.append(f"Source(s) unavailable: {', '.join(unavailable)}")
            updates["discrepancies"] = discrepancies

    elif decision == "verify":
        updates["verification_status"] = "verified"

    elif decision == "review":
        updates["verification_status"] = "escalated"
        updates["needs_human_review"] = True
        if not state.get("human_review_reason"):
            source_available = state.get("source_available", {"npi": True, "dca": True, "leie": True})
            if not all(source_available.values()):
                unavailable = [k.upper() for k, v in source_available.items() if not v]
                updates["human_review_reason"] = f"Data source unavailable: {', '.join(unavailable)}"
                discrepancies = list(state.get("discrepancies", []))
                discrepancies.append(f"Source(s) unavailable: {', '.join(unavailable)}")
                updates["discrepancies"] = discrepancies
            else:
                confidence = state.get("confidence_score") or 50
                updates["human_review_reason"] = f"Low confidence score ({confidence})"

    return updates


async def human_review(state: VerificationState) -> Dict[str, Any]:
    """
    Node 6: Human-in-the-loop interrupt.

    Marks the state as needing human review.
    """
    logger.info("[HITL] Entering human review: reason=%s", state.get("human_review_reason", "Routed to human review"))
    updates = {"verification_status": "escalated"}

    if not state.get("needs_human_review"):
        updates["needs_human_review"] = True
        updates["human_review_reason"] = "Routed to human review"

    return updates


async def finalize(state: VerificationState) -> Dict[str, Any]:
    """
    Node 7: Finalize verification.

    - Compile final verification report
    - Calculate total cost
    - Persist results to DuckDB verification_log table
    """
    logger.info("[FINALIZE] Starting finalization: id=%s status=%s human_decision=%s",
                 state.get("verification_id"), state.get("verification_status"),
                 state.get("human_decision"))
    updates = {"completed_at": datetime.utcnow().isoformat()}

    # If human review approved, set to verified
    if state.get("human_decision") == "approved":
        updates["verification_status"] = "verified"
    elif state.get("human_decision") == "rejected":
        updates["verification_status"] = "failed"

    # Persist to database
    try:
        # Merge state with updates
        final_state = dict(state)
        final_state.update(updates)

        verification_data = {
            "id": final_state.get("verification_id"),
            "npi_number": final_state.get("npi_number"),
            "target_state": final_state.get("target_state", "CA"),
            "provider_name": final_state.get("provider_name"),
            "license_number": final_state.get("license_number"),
            "verification_status": final_state.get("verification_status", "pending"),
            "confidence_score": final_state.get("confidence_score"),
            "confidence_reasoning": final_state.get("confidence_reasoning"),
            "discrepancies": final_state.get("discrepancies", []),
            "npi_raw": final_state.get("npi_response"),
            "board_raw": final_state.get("board_raw"),
            "leie_match": final_state.get("leie_match", False),
            "leie_record": final_state.get("leie_record"),
            "source_available": final_state.get("source_available", {}),
            "needs_human_review": final_state.get("needs_human_review", False),
            "human_review_reason": final_state.get("human_review_reason"),
            "human_review_links": final_state.get("human_review_links", []),
            "human_decision": final_state.get("human_decision"),
            "human_notes": final_state.get("human_notes"),
            "latency_npi_ms": final_state.get("step_latencies", {}).get("npi_ms"),
            "latency_board_ms": final_state.get("step_latencies", {}).get("dca_ms"),
            "latency_leie_ms": final_state.get("step_latencies", {}).get("leie_ms"),
            "latency_llm_ms": final_state.get("step_latencies", {}).get("llm_ms"),
            "llm_tokens_used": final_state.get("llm_tokens_used", 0),
            "cost_usd": final_state.get("cost_usd", 0.0),
            "retry_counts": final_state.get("retry_counts", {}),
            "errors": final_state.get("errors", []),
            "batch_id": final_state.get("batch_id"),
        }

        db.insert_verification_log(verification_data)
        logger.info("[FINALIZE] Persisted to DB: id=%s status=%s confidence=%s cost=$%.6f",
                     verification_data["id"], verification_data["verification_status"],
                     verification_data["confidence_score"], verification_data.get("cost_usd", 0))

    except Exception as e:
        logger.error("[FINALIZE] Database persist failed: %s", e, exc_info=True)
        errors = list(state.get("errors", []))
        errors.append(f"Database error: {str(e)}")
        updates["errors"] = errors

    return updates


def _build_evidence_summary(state: VerificationState) -> str:
    """
    Build a formatted evidence summary for the LLM prompt.
    """
    lines = []

    # NPI Evidence
    lines.append("=== NPI Registry Evidence ===")
    lines.append(f"NPI Number: {state.get('npi_number')}")
    lines.append(f"NPI Found: {state.get('npi_found', False)}")
    lines.append(f"NPI Active: {state.get('npi_active', False)}")
    lines.append(f"Provider Name: {state.get('provider_name')}")
    lines.append(f"Credential: {state.get('provider_credential')}")
    lines.append(f"Specialty: {state.get('provider_specialty')}")
    lines.append(f"License Number: {state.get('license_number')}")
    lines.append(f"License State: {state.get('license_state')}")
    source_available = state.get("source_available", {})
    lines.append(f"Source Available: {source_available.get('npi', True)}")
    lines.append("")

    # DCA Evidence
    lines.append("=== CA DCA License Evidence ===")
    lines.append(f"License Status: {state.get('board_license_status')}")
    lines.append(f"Expiration Date: {state.get('board_expiration_date')}")
    lines.append(f"Name on License: {state.get('board_name_on_license')}")
    lines.append(f"Secondary Status: {state.get('board_secondary_status')}")
    lines.append(f"Has Disciplinary Action: {state.get('board_has_disciplinary_action', False)}")
    lines.append(f"Has Public Documents: {state.get('board_has_public_documents', False)}")
    lines.append(f"Source Available: {source_available.get('dca', True)}")
    lines.append("")

    # LEIE Evidence
    lines.append("=== LEIE Exclusion Check ===")
    lines.append(f"LEIE Match Found: {state.get('leie_match', False)}")
    leie_record = state.get("leie_record")
    if state.get("leie_match") and leie_record:
        lines.append(f"Exclusion Record: {json.dumps(leie_record)}")
    lines.append(f"Source Available: {source_available.get('leie', True)}")
    lines.append("")

    # Prior discrepancies
    discrepancies = state.get("discrepancies", [])
    if discrepancies:
        lines.append("=== Prior Discrepancies/Warnings ===")
        for disc in discrepancies:
            lines.append(f"- {disc}")
        lines.append("")

    # Errors
    errors = state.get("errors", [])
    if errors:
        lines.append("=== Errors Encountered ===")
        for err in errors:
            lines.append(f"- {err}")

    return "\n".join(lines)


def _calculate_cost(tokens_used: int) -> float:
    """
    Calculate the cost in USD for LLM usage.
    """
    if tokens_used == 0:
        return 0.0

    # Rough estimate: assume 50% input, 50% output
    input_tokens = tokens_used // 2
    output_tokens = tokens_used - input_tokens

    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT_TOKENS
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS

    return round(input_cost + output_cost, 6)
