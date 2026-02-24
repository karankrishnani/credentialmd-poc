"""
OIG LEIE Exclusion List Query Module

Handles lookups against the LEIE (List of Excluded Individuals/Entities)
stored in DuckDB.

The LEIE database is loaded by scripts/init_db.py from the OIG CSV file.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import db


@dataclass
class LEIELookupResult:
    """Result of an LEIE lookup."""

    # Match found
    leie_match: bool = False
    match_type: Optional[str] = None  # "npi" or "name"
    leie_record: Optional[Dict[str, Any]] = None

    # Multiple matches (potential ambiguity)
    multiple_matches: bool = False
    match_count: int = 0

    # Metrics
    latency_ms: int = 0


def lookup_leie(
    npi: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    state: str = "CA"
) -> LEIELookupResult:
    """
    Check if a physician is on the LEIE exclusion list.

    Lookup strategy:
    1. Primary: Lookup by NPI (most reliable)
    2. Fallback: Lookup by name + state if NPI not found

    Args:
        npi: The 10-digit NPI number
        first_name: Physician's first name (for fallback lookup)
        last_name: Physician's last name (for fallback lookup)
        state: 2-letter state code (for fallback lookup)

    Returns:
        LEIELookupResult with match information
    """
    start_time = time.time()
    result = LEIELookupResult()

    # Primary lookup: by NPI
    npi_match = db.check_leie_by_npi(npi)

    if npi_match:
        result.leie_match = True
        result.match_type = "npi"
        result.leie_record = npi_match
        result.match_count = 1
        result.latency_ms = int((time.time() - start_time) * 1000)
        return result

    # Fallback lookup: by name + state
    if first_name and last_name:
        name_match = db.check_leie_by_name(last_name, first_name, state)

        if name_match:
            result.leie_match = True
            result.match_type = "name"
            result.leie_record = name_match
            result.match_count = 1

            # Check for multiple name matches (potential ambiguity)
            all_name_matches = _check_multiple_name_matches(last_name, first_name, state)
            if len(all_name_matches) > 1:
                result.multiple_matches = True
                result.match_count = len(all_name_matches)

    result.latency_ms = int((time.time() - start_time) * 1000)
    return result


def _check_multiple_name_matches(
    last_name: str,
    first_name: str,
    state: str
) -> List[Dict[str, Any]]:
    """
    Check if there are multiple LEIE matches for a name + state combination.

    This is used to detect ambiguous matches that may need HITL review.

    Args:
        last_name: Physician's last name
        first_name: Physician's first name
        state: 2-letter state code

    Returns:
        List of all matching LEIE records
    """
    conn = db.get_connection()
    results = conn.execute(
        """
        SELECT * FROM leie
        WHERE UPPER(LASTNAME) = UPPER(?)
          AND UPPER(FIRSTNAME) = UPPER(?)
          AND STATE = ?
        """,
        [last_name, first_name, state]
    ).fetchall()

    if not results:
        return []

    columns = [desc[0] for desc in conn.description]
    return [dict(zip(columns, row)) for row in results]


def is_excluded(leie_result: LEIELookupResult) -> bool:
    """
    Check if the LEIE lookup indicates the physician is excluded.

    An LEIE match is an automatic fail - the physician cannot be verified.

    Args:
        leie_result: Result from lookup_leie()

    Returns:
        True if physician is on the exclusion list
    """
    return leie_result.leie_match


def format_exclusion_reason(leie_record: Dict[str, Any]) -> str:
    """
    Format a human-readable reason for the LEIE exclusion.

    Args:
        leie_record: The LEIE record dict

    Returns:
        Formatted exclusion reason string
    """
    name = f"{leie_record.get('LASTNAME', 'Unknown')}, {leie_record.get('FIRSTNAME', '')}"
    excl_date = leie_record.get('EXCLDATE', 'Unknown')
    excl_type = leie_record.get('EXCLTYPE', 'Unknown')
    state = leie_record.get('STATE', 'Unknown')

    return (
        f"LEIE Exclusion: {name.strip()} excluded on {excl_date} "
        f"under authority {excl_type} (State: {state})"
    )
