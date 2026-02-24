"""
Mock CA DCA License Search Responses

This module contains synthetic DCA responses for testing.
The structure matches what would be parsed from the real CA DCA search results.

Real DCA DOM Structure Reference:
- Name format: "LASTNAME, FIRSTNAME MIDDLENAME"
- License number format: "A 128437" (with space)
- License statuses: "Current/Active", "License Revoked", "License Surrendered", "Delinquent", "Deceased"
- Secondary status examples: "Probation", "Probation Completed"
"""

from typing import Optional, Dict, Any


class DCASourceUnavailableError(Exception):
    """Raised when DCA source is unavailable (e.g., CAPTCHA blocked)"""
    pass


MOCK_DCA_RESPONSES: Dict[str, Optional[Dict[str, Any]]] = {
    # MOUSTAFA ABOSHADY - clean, active (NPI 1003127655)
    "A128437": {
        "license_type": "Physician and Surgeon A",
        "license_number": "A 128437",
        "license_status": "Current/Active",
        "expiration_date": "2026-03-31",
        "secondary_status": None,
        "name": "ABOSHADY, MOUSTAFA MOATAZ",
        "city": "LONG BEACH",
        "state": "California",
        "county": "LOS ANGELES",
        "zip": "90804",
        "detail_url": "/details/8002/A/128437/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },

    # SARAH CHEN - clean, active (NPI 1588667638)
    "B999001": {
        "license_type": "Physician and Surgeon A",
        "license_number": "B 999001",
        "license_status": "Current/Active",
        "expiration_date": "2027-06-30",
        "secondary_status": None,
        "name": "CHEN, SARAH",
        "city": "SAN FRANCISCO",
        "state": "California",
        "county": "SAN FRANCISCO",
        "zip": "94115",
        "detail_url": "/details/8002/B/999001/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },

    # JAMES WILLIAMS - clean, active (NPI 1497758544)
    "C999002": {
        "license_type": "Physician and Surgeon A",
        "license_number": "C 999002",
        "license_status": "Current/Active",
        "expiration_date": "2026-12-31",
        "secondary_status": None,
        "name": "WILLIAMS, JAMES R",
        "city": "SAN DIEGO",
        "state": "California",
        "county": "SAN DIEGO",
        "zip": "92103",
        "detail_url": "/details/8002/C/999002/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },

    # JENNIFER MISMATCH - active but name differs from NPI (NPI 2222222222)
    # NPI shows "JENNIFER MISMATCH" but DCA shows "JENNY MISMATCH-JONES"
    "D999003": {
        "license_type": "Physician and Surgeon A",
        "license_number": "D 999003",
        "license_status": "Current/Active",
        "expiration_date": "2026-09-30",
        "secondary_status": None,
        "name": "MISMATCH-JONES, JENNY",  # Name differs from NPI
        "city": "OAKLAND",
        "state": "California",
        "county": "ALAMEDA",
        "zip": "94612",
        "detail_url": "/details/8002/D/999003/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },

    # DAVID EXPIREDLICENSE - delinquent, expired (NPI 3333333333)
    "E999004": {
        "license_type": "Physician and Surgeon A",
        "license_number": "E 999004",
        "license_status": "Delinquent",
        "expiration_date": "2024-06-30",  # In the past
        "secondary_status": None,
        "name": "EXPIREDLICENSE, DAVID",
        "city": "SACRAMENTO",
        "state": "California",
        "county": "SACRAMENTO",
        "zip": "95816",
        "detail_url": "/details/8002/E/999004/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },

    # ANNA LOWCONFIDENCE - license on probation with disciplinary action (NPI 4444444444)
    "F999005": {
        "license_type": "Physician and Surgeon A",
        "license_number": "F 999005",
        "license_status": "Current/Active",
        "expiration_date": "2025-12-31",
        "secondary_status": "Probation",  # Concerning secondary status
        "name": "LOWCONFIDENCE, ANNA M",
        "city": "FRESNO",
        "state": "California",
        "county": "FRESNO",
        "zip": "93721",
        "detail_url": "/details/8002/F/999005/mock-hash",
        "has_disciplinary_action": True,  # Disciplinary flag
        "has_public_documents": True
    },

    # ROBERT EXCLUDED - has DCA license but will fail LEIE (NPI 1234567001)
    "G999006": {
        "license_type": "Physician and Surgeon A",
        "license_number": "G 999006",
        "license_status": "Current/Active",
        "expiration_date": "2027-01-15",
        "secondary_status": None,
        "name": "EXCLUDED, ROBERT J",
        "city": "LOS ANGELES",
        "state": "California",
        "county": "LOS ANGELES",
        "zip": "90001",
        "detail_url": "/details/8002/G/999006/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },

    # LISA BANNEDBERG - has DCA license but will fail LEIE (NPI 1234567002)
    "H999007": {
        "license_type": "Physician and Surgeon A",
        "license_number": "H 999007",
        "license_status": "Current/Active",
        "expiration_date": "2027-02-28",
        "secondary_status": None,
        "name": "BANNEDBERG, LISA M",
        "city": "SAN DIEGO",
        "state": "California",
        "county": "SAN DIEGO",
        "zip": "92101",
        "detail_url": "/details/8002/H/999007/mock-hash",
        "has_disciplinary_action": False,
        "has_public_documents": False
    },
}

# Special case: license that triggers DCA source unavailable
DCA_UNAVAILABLE_LICENSES = {"B777777"}


def get_mock_dca_response(license_number: str) -> Optional[Dict[str, Any]]:
    """
    Get mock DCA response for a license number.

    Args:
        license_number: The CA license number (e.g., "A128437")

    Returns:
        Dict with DCA response data, or None if not found

    Raises:
        DCASourceUnavailableError: If license is in the unavailable list (simulates CAPTCHA)
    """
    # Strip spaces for matching (DCA displays "A 128437" but we may receive "A128437")
    normalized = license_number.replace(" ", "").upper()

    # Check if this is a simulated unavailable case
    if normalized in DCA_UNAVAILABLE_LICENSES:
        raise DCASourceUnavailableError(
            f"DCA source unavailable for license {license_number}. "
            "CAPTCHA challenge could not be bypassed after multiple retries."
        )

    # Look up in mock data
    return MOCK_DCA_RESPONSES.get(normalized)
