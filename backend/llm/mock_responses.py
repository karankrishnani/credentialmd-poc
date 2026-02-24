"""
Mock LLM Responses for Discrepancy Detection and Confidence Scoring

The MockLLMProvider returns these canned responses based on pattern matching
against keywords in the system prompt or input content.

Claude is called at exactly ONE point in the workflow: discrepancy_detection.
The response must be valid JSON with: discrepancies, confidence_score, reasoning.
"""

import json
import random
from typing import Dict, Any, Optional


# Pattern-based mock responses
# The key is a tuple of keywords to match (any match triggers this response)
MOCK_RESPONSES: Dict[str, Dict[str, Any]] = {
    # LEIE Exclusion - automatic failure
    "leie_match": {
        "discrepancies": ["Physician found on OIG LEIE exclusion list"],
        "confidence_score": 0,
        "reasoning": "Physician found on OIG LEIE exclusion list. This is an automatic "
                     "verification failure regardless of other source findings. Federal "
                     "exclusion prohibits participation in Medicare, Medicaid, and all "
                     "federal healthcare programs."
    },

    # License Revoked - critical finding
    "license_revoked": {
        "discrepancies": [
            "State board shows license revoked but NPI shows active status",
            "License revocation indicates serious disciplinary action"
        ],
        "confidence_score": 15,
        "reasoning": "License revocation is a critical finding that indicates the physician "
                     "has had their medical license revoked by the state board. Despite the "
                     "NPI record showing active enumeration status, this physician cannot "
                     "legally practice medicine. Verification fails due to revoked license."
    },

    # License Surrendered
    "license_surrendered": {
        "discrepancies": [
            "State board shows license surrendered",
            "License surrender may indicate disciplinary action or voluntary cessation"
        ],
        "confidence_score": 20,
        "reasoning": "License surrender indicates the physician has voluntarily given up "
                     "their medical license. This may be the result of pending disciplinary "
                     "action or personal decision. The physician cannot legally practice "
                     "medicine in this state."
    },

    # License Delinquent - concerning but not critical
    "license_delinquent": {
        "discrepancies": [
            "License renewal is delinquent, may indicate lapsed credentials",
            "Expiration date has passed without renewal"
        ],
        "confidence_score": 55,
        "reasoning": "Delinquent license status suggests the physician has not completed "
                     "the renewal process. While this may be an administrative oversight, "
                     "practicing with a delinquent license is prohibited. The physician "
                     "should complete renewal before verification can be approved."
    },

    # Source Unavailable - degraded confidence
    "source_unavailable": {
        "discrepancies": [
            "DCA source was unavailable, license status could not be verified",
            "Verification proceeded with incomplete data"
        ],
        "confidence_score": 55,
        "reasoning": "Unable to verify license status from the California DCA due to "
                     "source unavailability (likely CAPTCHA challenge). NPI record shows "
                     "active status and no LEIE exclusion was found. However, without DCA "
                     "confirmation, verification confidence is reduced. Human review "
                     "recommended to manually verify license status."
    },

    # Name Mismatch - moderate concern
    "name_mismatch": {
        "discrepancies": [
            "Name mismatch between NPI and DCA records",
            "First name or surname differs between sources"
        ],
        "confidence_score": 72,
        "reasoning": "NPI and DCA records show a name discrepancy. This could indicate "
                     "a legal name change, maiden/married name variation, nickname usage, "
                     "or data entry variation. License status is active and no LEIE "
                     "exclusion exists. The name variation may be legitimate but requires "
                     "human review to confirm identity."
    },

    # No Primary Taxonomy - minor concern
    "no_primary_taxonomy": {
        "discrepancies": [
            "No primary taxonomy designation for target state",
            "License found but not marked as primary practice specialty"
        ],
        "confidence_score": 78,
        "reasoning": "A California license was found in the NPI record but it is not "
                     "marked as the primary taxonomy. This may indicate the physician "
                     "primarily practices in another state. DCA confirms active license "
                     "status and no LEIE exclusion was found. Reduced confidence due to "
                     "non-primary designation."
    },

    # Probation Status - concerning
    "probation": {
        "discrepancies": [
            "License shows secondary status of Probation",
            "Physician may have disciplinary action on record"
        ],
        "confidence_score": 60,
        "reasoning": "The physician's license has a secondary status of 'Probation', "
                     "indicating ongoing disciplinary oversight by the medical board. "
                     "While the primary license status is active, probation status "
                     "requires additional scrutiny. Public disciplinary documents "
                     "should be reviewed before verification approval."
    },

    # Disciplinary Action on Record
    "disciplinary_action": {
        "discrepancies": [
            "Public disciplinary action on record with state board",
            "Additional review of disciplinary documents recommended"
        ],
        "confidence_score": 65,
        "reasoning": "The DCA records indicate this physician has a public disciplinary "
                     "action on record. While the license remains active, the nature and "
                     "severity of the disciplinary action should be reviewed. The public "
                     "documents available from DCA should be examined before final "
                     "verification decision."
    },

    # Clean Case - all clear
    "clean": {
        "discrepancies": [],
        "confidence_score": 97,
        "reasoning": "All three data sources are consistent. NPI record shows active "
                     "status with a valid California license. DCA confirms Current/Active "
                     "license status with matching name. No LEIE exclusion found. High "
                     "confidence in verification. Physician is in good standing."
    },

    # Default fallback
    "default": {
        "discrepancies": ["Unable to fully assess verification due to incomplete data"],
        "confidence_score": 50,
        "reasoning": "Insufficient data for high confidence verification. Some source "
                     "data may be missing or inconsistent. Human review recommended to "
                     "manually verify physician credentials across all sources."
    }
}


def get_mock_llm_response(prompt: str, system: str = "") -> str:
    """
    Get a mock LLM response based on pattern matching.

    The function looks for keywords in the combined prompt and system message
    to determine which canned response to return.

    Args:
        prompt: The user prompt content
        system: The system prompt content

    Returns:
        JSON string with discrepancies, confidence_score, and reasoning
    """
    combined = (prompt + " " + system).lower()

    # Check patterns in order of priority
    if "leie" in combined and ("match" in combined or "exclusion" in combined or "excluded" in combined):
        response = MOCK_RESPONSES["leie_match"]
    elif "license revoked" in combined or "revoked" in combined:
        response = MOCK_RESPONSES["license_revoked"]
    elif "license surrendered" in combined or "surrendered" in combined:
        response = MOCK_RESPONSES["license_surrendered"]
    elif "delinquent" in combined:
        response = MOCK_RESPONSES["license_delinquent"]
    elif "source_unavailable" in combined or "unavailable" in combined:
        response = MOCK_RESPONSES["source_unavailable"]
    elif "name" in combined and ("mismatch" in combined or "differ" in combined or "discrepancy" in combined):
        response = MOCK_RESPONSES["name_mismatch"]
    elif "no primary" in combined or "no ca" in combined or "no california" in combined:
        response = MOCK_RESPONSES["no_primary_taxonomy"]
    elif "probation" in combined:
        response = MOCK_RESPONSES["probation"]
    elif "disciplinary" in combined:
        response = MOCK_RESPONSES["disciplinary_action"]
    elif "current/active" in combined and "no discrepancies" not in combined:
        response = MOCK_RESPONSES["clean"]
    elif "clean" in combined or "verified" in combined:
        response = MOCK_RESPONSES["clean"]
    else:
        response = MOCK_RESPONSES["default"]

    return json.dumps(response)


def estimate_mock_tokens(prompt: str, system: str = "") -> int:
    """
    Estimate token count for a mock LLM call.

    In mock mode, we simulate realistic token counts to make
    latency and cost metrics meaningful.

    Args:
        prompt: The user prompt content
        system: The system prompt content

    Returns:
        Estimated token count (200-500 range)
    """
    # Base tokens from prompt length (rough estimate: 4 chars per token)
    input_tokens = (len(prompt) + len(system)) // 4

    # Output tokens (mock responses are ~100-200 tokens)
    output_tokens = random.randint(100, 200)

    return input_tokens + output_tokens


class MockLLMProvider:
    """
    Mock LLM provider for testing without Claude API calls.

    Returns canned responses based on pattern matching in the prompt.
    Simulates realistic token counts and small delays.
    """

    def __init__(self):
        self.total_tokens_used = 0

    async def query(self, prompt: str, system: str = "") -> str:
        """
        Query the mock LLM.

        Args:
            prompt: The user prompt
            system: The system prompt

        Returns:
            JSON response string
        """
        import asyncio

        # Simulate realistic latency (100-300ms)
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # Track token usage
        tokens = estimate_mock_tokens(prompt, system)
        self.total_tokens_used += tokens

        return get_mock_llm_response(prompt, system)

    def get_tokens_used(self) -> int:
        """Get total tokens used in this session."""
        return self.total_tokens_used

    def reset_tokens(self):
        """Reset token counter."""
        self.total_tokens_used = 0
