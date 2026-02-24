"""
Verification State TypedDict

Defines the VerificationState that flows through the LangGraph workflow.
The state is intentionally NOT locked to California - the target_state field
makes the pipeline reusable for any state.
"""

from typing import Optional, List, Dict, Any, TypedDict, Annotated
from datetime import datetime
import operator


class VerificationState(TypedDict, total=False):
    """
    State object that flows through the LangGraph verification workflow.

    This state captures all input, intermediate results, and output data
    for a single physician verification.
    """

    # Input
    npi_number: str
    target_state: str  # Scoped to CA for POC, but extensible

    # Verification ID (assigned when created)
    verification_id: Optional[str]
    batch_id: Optional[str]

    # NPI results
    npi_response: Optional[Dict[str, Any]]
    npi_found: bool
    npi_active: bool
    provider_name: Optional[str]  # "LAST, FIRST MIDDLE"
    provider_first_name: Optional[str]
    provider_last_name: Optional[str]
    provider_credential: Optional[str]  # "M.D.", "D.O.", etc.
    provider_specialty: Optional[str]  # from primary taxonomy desc
    license_number: Optional[str]  # extracted for target_state
    license_state: Optional[str]  # should match target_state
    all_taxonomies: List[Dict[str, Any]]
    all_addresses: List[Dict[str, Any]]

    # State board results (DCA for CA, extensible for other states)
    board_license_status: Optional[str]  # "Current/Active", "License Revoked", etc.
    board_expiration_date: Optional[str]
    board_name_on_license: Optional[str]
    board_secondary_status: Optional[str]
    board_has_disciplinary_action: bool
    board_has_public_documents: bool
    board_detail_url: Optional[str]
    board_city: Optional[str]
    board_raw: Optional[Dict[str, Any]]

    # LEIE results
    leie_match: bool
    leie_record: Optional[Dict[str, Any]]

    # Agent reasoning
    discrepancies: List[str]
    confidence_score: Optional[float]
    confidence_reasoning: Optional[str]
    verification_status: str
    # Statuses: pending, npi_lookup, license_check, exclusion_check,
    #           analyzing, verified, flagged, failed, escalated

    # HITL
    needs_human_review: bool
    human_review_reason: Optional[str]
    human_review_links: List[Dict[str, str]]  # [{"label": "...", "url": "..."}]
    human_decision: Optional[str]  # approved, rejected, needs_info
    human_notes: Optional[str]

    # Metrics
    step_latencies: Dict[str, int]  # {"npi_ms": 320, "dca_ms": 2100, ...}
    llm_tokens_used: int
    cost_usd: float
    errors: List[str]
    retry_counts: Dict[str, int]  # {"npi": 0, "dca": 2, "leie": 0}

    # Source availability (for graceful degradation)
    source_available: Dict[str, bool]

    # Timestamps
    created_at: Optional[str]
    completed_at: Optional[str]


def create_initial_state(
    npi_number: str,
    target_state: str = "CA",
    verification_id: Optional[str] = None,
    batch_id: Optional[str] = None,
) -> VerificationState:
    """Create a new VerificationState with default values."""
    return VerificationState(
        npi_number=npi_number,
        target_state=target_state,
        verification_id=verification_id,
        batch_id=batch_id,
        npi_response=None,
        npi_found=False,
        npi_active=False,
        provider_name=None,
        provider_first_name=None,
        provider_last_name=None,
        provider_credential=None,
        provider_specialty=None,
        license_number=None,
        license_state=None,
        all_taxonomies=[],
        all_addresses=[],
        board_license_status=None,
        board_expiration_date=None,
        board_name_on_license=None,
        board_secondary_status=None,
        board_has_disciplinary_action=False,
        board_has_public_documents=False,
        board_detail_url=None,
        board_city=None,
        board_raw=None,
        leie_match=False,
        leie_record=None,
        discrepancies=[],
        confidence_score=None,
        confidence_reasoning=None,
        verification_status="pending",
        needs_human_review=False,
        human_review_reason=None,
        human_review_links=[],
        human_decision=None,
        human_notes=None,
        step_latencies={},
        llm_tokens_used=0,
        cost_usd=0.0,
        errors=[],
        retry_counts={},
        source_available={"npi": True, "dca": True, "leie": True},
        created_at=datetime.utcnow().isoformat(),
        completed_at=None,
    )


def state_to_dict(state: VerificationState) -> Dict[str, Any]:
    """Convert state to dictionary for API responses."""
    return {
        "id": state.get("verification_id"),
        "npi_number": state.get("npi_number"),
        "target_state": state.get("target_state"),
        "batch_id": state.get("batch_id"),
        "provider_name": state.get("provider_name"),
        "provider_first_name": state.get("provider_first_name"),
        "provider_last_name": state.get("provider_last_name"),
        "provider_credential": state.get("provider_credential"),
        "provider_specialty": state.get("provider_specialty"),
        "license_number": state.get("license_number"),
        "license_state": state.get("license_state"),
        "verification_status": state.get("verification_status"),
        "confidence_score": state.get("confidence_score"),
        "confidence_reasoning": state.get("confidence_reasoning"),
        "discrepancies": state.get("discrepancies", []),
        "npi_found": state.get("npi_found", False),
        "npi_active": state.get("npi_active", False),
        "npi_raw": state.get("npi_response"),
        "board_license_status": state.get("board_license_status"),
        "board_expiration_date": state.get("board_expiration_date"),
        "board_name_on_license": state.get("board_name_on_license"),
        "board_secondary_status": state.get("board_secondary_status"),
        "board_has_disciplinary_action": state.get("board_has_disciplinary_action", False),
        "board_raw": state.get("board_raw"),
        "leie_match": state.get("leie_match", False),
        "leie_record": state.get("leie_record"),
        "source_available": state.get("source_available", {}),
        "needs_human_review": state.get("needs_human_review", False),
        "human_review_reason": state.get("human_review_reason"),
        "human_review_links": state.get("human_review_links", []),
        "human_decision": state.get("human_decision"),
        "human_notes": state.get("human_notes"),
        "step_latencies": state.get("step_latencies", {}),
        "llm_tokens_used": state.get("llm_tokens_used", 0),
        "cost_usd": state.get("cost_usd", 0.0),
        "retry_counts": state.get("retry_counts", {}),
        "errors": state.get("errors", []),
        "created_at": state.get("created_at"),
        "completed_at": state.get("completed_at"),
    }


def set_hitl_escalation(state: VerificationState, reason: str) -> VerificationState:
    """
    Mark this verification for human-in-the-loop review.

    Args:
        state: Current state
        reason: Human-readable reason for escalation

    Returns:
        Updated state
    """
    state["needs_human_review"] = True
    state["human_review_reason"] = reason
    state["verification_status"] = "escalated"

    # Add helpful lookup links
    npi = state.get("npi_number", "")
    state["human_review_links"] = [
        {
            "label": "Look up on NPI Registry",
            "url": f"https://npiregistry.cms.hhs.gov/api/?version=2.1&number={npi}"
        },
        {
            "label": "Search CA DCA",
            "url": "https://search.dca.ca.gov/?BD=800"
        }
    ]

    return state
