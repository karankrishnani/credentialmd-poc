"""
Verification State Dataclass

Defines the VerificationState that flows through the LangGraph workflow.
The state is intentionally NOT locked to California - the target_state field
makes the pipeline reusable for any state.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class VerificationState:
    """
    State object that flows through the LangGraph verification workflow.

    This state captures all input, intermediate results, and output data
    for a single physician verification.
    """

    # Input
    npi_number: str
    target_state: str = "CA"  # Scoped to CA for POC, but extensible

    # Verification ID (assigned when created)
    verification_id: Optional[str] = None
    batch_id: Optional[str] = None

    # NPI results
    npi_response: Optional[Dict[str, Any]] = None
    npi_found: bool = False
    npi_active: bool = False
    provider_name: Optional[str] = None  # "LAST, FIRST MIDDLE"
    provider_first_name: Optional[str] = None
    provider_last_name: Optional[str] = None
    provider_credential: Optional[str] = None  # "M.D.", "D.O.", etc.
    provider_specialty: Optional[str] = None  # from primary taxonomy desc
    license_number: Optional[str] = None  # extracted for target_state
    license_state: Optional[str] = None  # should match target_state
    all_taxonomies: List[Dict[str, Any]] = field(default_factory=list)
    all_addresses: List[Dict[str, Any]] = field(default_factory=list)

    # State board results (DCA for CA, extensible for other states)
    board_license_status: Optional[str] = None  # "Current/Active", "License Revoked", etc.
    board_expiration_date: Optional[str] = None
    board_name_on_license: Optional[str] = None
    board_secondary_status: Optional[str] = None
    board_has_disciplinary_action: bool = False
    board_has_public_documents: bool = False
    board_detail_url: Optional[str] = None
    board_city: Optional[str] = None
    board_raw: Optional[Dict[str, Any]] = None

    # LEIE results
    leie_match: bool = False
    leie_record: Optional[Dict[str, Any]] = None

    # Agent reasoning
    discrepancies: List[str] = field(default_factory=list)
    confidence_score: Optional[float] = None
    confidence_reasoning: Optional[str] = None
    verification_status: str = "pending"
    # Statuses: pending, npi_lookup, license_check, exclusion_check,
    #           analyzing, verified, flagged, failed, escalated

    # HITL
    needs_human_review: bool = False
    human_review_reason: Optional[str] = None
    human_review_links: List[Dict[str, str]] = field(default_factory=list)  # [{"label": "...", "url": "..."}]
    human_decision: Optional[str] = None  # approved, rejected, needs_info
    human_notes: Optional[str] = None

    # Metrics
    step_latencies: Dict[str, int] = field(default_factory=dict)  # {"npi_ms": 320, "dca_ms": 2100, ...}
    llm_tokens_used: int = 0
    cost_usd: float = 0.0
    errors: List[str] = field(default_factory=list)
    retry_counts: Dict[str, int] = field(default_factory=dict)  # {"npi": 0, "dca": 2, "leie": 0}

    # Source availability (for graceful degradation)
    source_available: Dict[str, bool] = field(
        default_factory=lambda: {"npi": True, "dca": True, "leie": True}
    )

    # Timestamps
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for API responses and persistence."""
        return {
            "id": self.verification_id,
            "npi_number": self.npi_number,
            "target_state": self.target_state,
            "batch_id": self.batch_id,
            "provider_name": self.provider_name,
            "provider_first_name": self.provider_first_name,
            "provider_last_name": self.provider_last_name,
            "provider_credential": self.provider_credential,
            "provider_specialty": self.provider_specialty,
            "license_number": self.license_number,
            "license_state": self.license_state,
            "verification_status": self.verification_status,
            "confidence_score": self.confidence_score,
            "confidence_reasoning": self.confidence_reasoning,
            "discrepancies": self.discrepancies,
            "npi_found": self.npi_found,
            "npi_active": self.npi_active,
            "npi_raw": self.npi_response,
            "board_license_status": self.board_license_status,
            "board_expiration_date": self.board_expiration_date,
            "board_name_on_license": self.board_name_on_license,
            "board_secondary_status": self.board_secondary_status,
            "board_has_disciplinary_action": self.board_has_disciplinary_action,
            "board_raw": self.board_raw,
            "leie_match": self.leie_match,
            "leie_record": self.leie_record,
            "source_available": self.source_available,
            "needs_human_review": self.needs_human_review,
            "human_review_reason": self.human_review_reason,
            "human_review_links": self.human_review_links,
            "human_decision": self.human_decision,
            "human_notes": self.human_notes,
            "step_latencies": self.step_latencies,
            "llm_tokens_used": self.llm_tokens_used,
            "cost_usd": self.cost_usd,
            "retry_counts": self.retry_counts,
            "errors": self.errors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def set_hitl_escalation(self, reason: str):
        """
        Mark this verification for human-in-the-loop review.

        Args:
            reason: Human-readable reason for escalation
        """
        self.needs_human_review = True
        self.human_review_reason = reason
        self.verification_status = "escalated"

        # Add helpful lookup links
        self.human_review_links = [
            {
                "label": "Look up on NPI Registry",
                "url": f"https://npiregistry.cms.hhs.gov/api/?version=2.1&number={self.npi_number}"
            },
            {
                "label": "Search CA DCA",
                "url": "https://search.dca.ca.gov/?BD=800"
            }
        ]
