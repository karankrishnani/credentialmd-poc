"""
NPI Registry API Client

Handles lookups against the NPI Registry API with retry logic.
NPI parsing is ENTIRELY rule-based - no LLM calls.

API Documentation: https://npiregistry.cms.hhs.gov/api-page
API Endpoint: https://npiregistry.cms.hhs.gov/api/?version=2.1&number={npi}
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

from config import (
    NPI_API_BASE_URL,
    NPI_API_VERSION,
    MAX_RETRIES,
    BASE_RETRY_DELAY,
    RATE_LIMIT_RETRY_DELAY,
    MOCK_MODE,
)
from sources.npi_mock_data import get_mock_npi_response


class NPILookupError(Exception):
    """Base exception for NPI lookup errors."""
    pass


class NPINotFoundError(NPILookupError):
    """Raised when NPI number is not found in the registry."""
    pass


class NPIInactiveError(NPILookupError):
    """Raised when NPI is found but marked as inactive/deactivated."""
    pass


class NoStateLicenseError(NPILookupError):
    """Raised when no license is found for the target state."""
    pass


class MultipleLicensesError(NPILookupError):
    """Raised when multiple different license numbers are found for target state."""
    pass


class SourceUnavailableError(NPILookupError):
    """Raised when the NPI API is unavailable after all retries."""
    pass


@dataclass
class NPILookupResult:
    """Result of an NPI lookup with parsed data."""

    # Raw response
    raw_response: Dict[str, Any]

    # Parsed fields
    npi_found: bool = False
    npi_active: bool = False
    provider_name: Optional[str] = None  # "LAST, FIRST MIDDLE"
    provider_first_name: Optional[str] = None
    provider_last_name: Optional[str] = None
    provider_credential: Optional[str] = None
    provider_specialty: Optional[str] = None
    license_number: Optional[str] = None
    license_state: Optional[str] = None
    all_taxonomies: List[Dict[str, Any]] = None
    all_addresses: List[Dict[str, Any]] = None

    # HITL escalation info
    needs_hitl: bool = False
    hitl_reason: Optional[str] = None

    # Warnings (non-blocking issues)
    warnings: List[str] = None

    # Metrics
    latency_ms: int = 0
    retry_count: int = 0

    def __post_init__(self):
        if self.all_taxonomies is None:
            self.all_taxonomies = []
        if self.all_addresses is None:
            self.all_addresses = []
        if self.warnings is None:
            self.warnings = []


async def lookup_npi(
    npi: str,
    target_state: str = "CA"
) -> NPILookupResult:
    """
    Look up a physician by NPI number.

    This function queries the NPI Registry API and performs RULE-BASED parsing
    to extract license information. No LLM is called.

    Args:
        npi: The 10-digit NPI number
        target_state: The 2-letter state code to filter taxonomies (default: CA)

    Returns:
        NPILookupResult with parsed physician data

    Raises:
        SourceUnavailableError: If API is unavailable after all retries
    """
    start_time = time.time()
    retry_count = 0
    logger.info("NPI: Looking up NPI=%s state=%s mock=%s", npi, target_state, MOCK_MODE)

    # Validate NPI format
    if not npi or not npi.isdigit() or len(npi) != 10:
        raise ValueError(f"Invalid NPI format: {npi}. Must be 10 digits.")

    # Get response (mock or real)
    if MOCK_MODE:
        raw_response = get_mock_npi_response(npi)
        latency_ms = int((time.time() - start_time) * 1000)
    else:
        raw_response, retry_count = await _fetch_npi_with_retry(npi)
        latency_ms = int((time.time() - start_time) * 1000)

    # Parse the response using rule-based logic
    result = _parse_npi_response(raw_response, npi, target_state)
    result.latency_ms = latency_ms
    result.retry_count = retry_count

    logger.info("NPI: Result for NPI=%s: found=%s active=%s name=%s license=%s",
                 npi, result.npi_found, result.npi_active, result.provider_name, result.license_number)
    if result.needs_hitl:
        logger.warning("NPI: HITL escalation for NPI=%s: %s", npi, result.hitl_reason)

    return result


async def _fetch_npi_with_retry(npi: str) -> Tuple[Dict[str, Any], int]:
    """
    Fetch NPI data from the registry with exponential backoff retry.

    Args:
        npi: The 10-digit NPI number

    Returns:
        Tuple of (response dict, retry count)

    Raises:
        SourceUnavailableError: If all retries exhausted
    """
    url = f"{NPI_API_BASE_URL}?version={NPI_API_VERSION}&number={npi}"
    retry_count = 0

    async with httpx.AsyncClient() as client:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.get(url, timeout=30.0)

                # Success
                if response.status_code == 200:
                    return response.json(), retry_count

                # Rate limited - special delay
                if response.status_code == 429:
                    if attempt < MAX_RETRIES:
                        retry_count += 1
                        logger.warning("NPI: API rate limited. Waiting %ss before retry %d/%d",
                                        RATE_LIMIT_RETRY_DELAY, attempt + 1, MAX_RETRIES)
                        await asyncio.sleep(RATE_LIMIT_RETRY_DELAY)
                        continue

                # Client error (4xx) - do not retry
                if 400 <= response.status_code < 500:
                    raise NPILookupError(f"NPI API client error: {response.status_code}")

                # Server error (5xx) - retry with backoff
                if response.status_code >= 500:
                    if attempt < MAX_RETRIES:
                        retry_count += 1
                        delay = BASE_RETRY_DELAY * (2 ** attempt)  # 1s, 2s, 4s, 8s
                        logger.warning("NPI: API error %d. Retry %d/%d in %ss",
                                        response.status_code, attempt + 1, MAX_RETRIES, delay)
                        await asyncio.sleep(delay)
                        continue

            except httpx.TimeoutException:
                if attempt < MAX_RETRIES:
                    retry_count += 1
                    delay = BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning("NPI: API timeout. Retry %d/%d in %ss", attempt + 1, MAX_RETRIES, delay)
                    await asyncio.sleep(delay)
                    continue

            except httpx.RequestError as e:
                if attempt < MAX_RETRIES:
                    retry_count += 1
                    delay = BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning("NPI: API request error: %s. Retry %d/%d in %ss", e, attempt + 1, MAX_RETRIES, delay)
                    await asyncio.sleep(delay)
                    continue

    # All retries exhausted
    raise SourceUnavailableError("NPI Registry API unavailable after all retries")


def _parse_npi_response(
    response: Dict[str, Any],
    npi: str,
    target_state: str
) -> NPILookupResult:
    """
    Parse NPI API response using RULE-BASED logic.

    NO LLM is called in this function. All parsing is deterministic.

    Args:
        response: Raw NPI API response
        npi: The NPI number
        target_state: Target state for license extraction

    Returns:
        NPILookupResult with parsed data
    """
    result = NPILookupResult(raw_response=response)

    # Check if NPI was found
    result_count = response.get("result_count", 0)
    logger.debug("NPI: Parsing response for NPI=%s result_count=%d", npi, result_count)
    if result_count == 0 or not response.get("results"):
        result.npi_found = False
        result.needs_hitl = True
        result.hitl_reason = "NPI not found"
        return result

    result.npi_found = True

    # Get the first (and should be only) result
    npi_data = response["results"][0]
    basic = npi_data.get("basic", {})

    # Check NPI status
    status = basic.get("status", "")
    result.npi_active = status == "A"

    if not result.npi_active:
        result.needs_hitl = True
        result.hitl_reason = f"NPI inactive/deactivated (status: {status})"

    # Extract provider name
    first_name = basic.get("first_name", "").strip()
    last_name = basic.get("last_name", "").strip()
    middle_name = basic.get("middle_name", "").strip()
    logger.debug("NPI: Name extraction: first=%s last=%s middle=%s", first_name, last_name, middle_name)

    result.provider_first_name = first_name
    result.provider_last_name = last_name

    if middle_name and middle_name != "--":
        result.provider_name = f"{last_name}, {first_name} {middle_name}"
    else:
        result.provider_name = f"{last_name}, {first_name}"

    # Extract credential
    credential = basic.get("credential", "")
    if credential and credential != "--":
        result.provider_credential = credential

    # Store all taxonomies and addresses
    result.all_taxonomies = npi_data.get("taxonomies", [])
    result.all_addresses = npi_data.get("addresses", [])

    # =========================================================================
    # RULE-BASED LICENSE EXTRACTION
    # =========================================================================

    # Filter taxonomies for target state
    state_taxonomies = [
        t for t in result.all_taxonomies
        if t.get("state", "").upper() == target_state.upper()
    ]
    logger.debug("NPI: Taxonomy filtering: total=%d state_%s=%d",
                  len(result.all_taxonomies), target_state, len(state_taxonomies))

    # Case 1: No taxonomies for target state
    if not state_taxonomies:
        result.needs_hitl = True
        result.hitl_reason = f"No {target_state} license in NPI"
        return result

    # Case 2: Find primary taxonomy for target state
    primary_taxonomies = [
        t for t in state_taxonomies
        if t.get("primary", False) is True
    ]

    if len(primary_taxonomies) == 1:
        # Exactly one primary - use it
        primary = primary_taxonomies[0]
        result.license_number = primary.get("license", "")
        result.license_state = primary.get("state", target_state)
        result.provider_specialty = primary.get("desc", "")

    elif len(primary_taxonomies) > 1:
        # Multiple primaries - check if they have same license number
        license_numbers = set(t.get("license", "") for t in primary_taxonomies)

        if len(license_numbers) == 1:
            # Same license number - use first primary
            primary = primary_taxonomies[0]
            result.license_number = primary.get("license", "")
            result.license_state = primary.get("state", target_state)
            result.provider_specialty = primary.get("desc", "")
        else:
            # Multiple different license numbers - HITL
            result.needs_hitl = True
            result.hitl_reason = f"Multiple {target_state} license numbers found: {', '.join(license_numbers)}"
            # Still set the first one for partial data
            primary = primary_taxonomies[0]
            result.license_number = primary.get("license", "")
            result.license_state = primary.get("state", target_state)
            result.provider_specialty = primary.get("desc", "")
            return result

    else:
        # No primary taxonomy for target state - take first state entry with warning
        first_state_taxonomy = state_taxonomies[0]
        result.license_number = first_state_taxonomy.get("license", "")
        result.license_state = first_state_taxonomy.get("state", target_state)
        result.provider_specialty = first_state_taxonomy.get("desc", "")
        result.warnings.append("No primary taxonomy designation for target state")

    return result
