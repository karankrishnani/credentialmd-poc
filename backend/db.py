"""
DuckDB Database Connection and Operations

Handles connection to the DuckDB database for LEIE lookups and verification logging.
The database is created by scripts/init_db.py and used at runtime by the app.
"""

import duckdb
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

from config import DUCKDB_PATH


# Global connection (DuckDB is in-process, so this is safe)
_connection: Optional[duckdb.DuckDBPyConnection] = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Get or create the DuckDB connection.

    Returns:
        DuckDB connection instance
    """
    global _connection
    if _connection is None:
        # Ensure data directory exists
        DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _connection = duckdb.connect(str(DUCKDB_PATH))
    return _connection


def close_connection():
    """Close the database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def check_leie_by_npi(npi: str) -> Optional[Dict[str, Any]]:
    """
    Check if an NPI is on the LEIE exclusion list.

    Args:
        npi: The 10-digit NPI number

    Returns:
        Dict with LEIE record if found, None otherwise
    """
    conn = get_connection()
    result = conn.execute(
        "SELECT * FROM leie WHERE NPI = ? LIMIT 1",
        [npi]
    ).fetchone()

    if result is None:
        return None

    # Get column names
    columns = [desc[0] for desc in conn.description]
    return dict(zip(columns, result))


def check_leie_by_name(
    last_name: str,
    first_name: str,
    state: str = "CA"
) -> Optional[Dict[str, Any]]:
    """
    Check if a physician is on the LEIE by name and state.

    This is the fallback lookup when NPI is not in the exclusion record.

    Args:
        last_name: Physician's last name
        first_name: Physician's first name
        state: 2-letter state code

    Returns:
        Dict with LEIE record if found, None otherwise
    """
    conn = get_connection()
    result = conn.execute(
        """
        SELECT * FROM leie
        WHERE UPPER(LASTNAME) = UPPER(?)
          AND UPPER(FIRSTNAME) = UPPER(?)
          AND STATE = ?
        LIMIT 1
        """,
        [last_name, first_name, state]
    ).fetchone()

    if result is None:
        return None

    columns = [desc[0] for desc in conn.description]
    return dict(zip(columns, result))


def insert_verification_log(verification: Dict[str, Any]) -> str:
    """
    Insert a verification record into the log.

    Args:
        verification: Dict with verification data

    Returns:
        The verification ID
    """
    conn = get_connection()

    # Ensure the table exists (it should be created by init_db.py)
    _ensure_verification_log_table(conn)

    # Serialize JSON fields
    verification_copy = verification.copy()
    for field in ['discrepancies', 'npi_raw', 'board_raw', 'leie_record',
                  'source_available', 'retry_counts', 'errors', 'human_review_links']:
        if field in verification_copy and verification_copy[field] is not None:
            verification_copy[field] = json.dumps(verification_copy[field])

    conn.execute(
        """
        INSERT INTO verification_log (
            id, npi_number, target_state, provider_name, license_number,
            verification_status, confidence_score, confidence_reasoning,
            discrepancies, npi_raw, board_raw, leie_match, leie_record,
            source_available, needs_human_review, human_review_reason,
            human_review_links, human_decision, human_notes,
            latency_npi_ms, latency_board_ms, latency_leie_ms, latency_llm_ms,
            llm_tokens_used, cost_usd, retry_counts, errors, batch_id
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        [
            verification_copy.get('id'),
            verification_copy.get('npi_number'),
            verification_copy.get('target_state', 'CA'),
            verification_copy.get('provider_name'),
            verification_copy.get('license_number'),
            verification_copy.get('verification_status'),
            verification_copy.get('confidence_score'),
            verification_copy.get('confidence_reasoning'),
            verification_copy.get('discrepancies'),
            verification_copy.get('npi_raw'),
            verification_copy.get('board_raw'),
            verification_copy.get('leie_match', False),
            verification_copy.get('leie_record'),
            verification_copy.get('source_available'),
            verification_copy.get('needs_human_review', False),
            verification_copy.get('human_review_reason'),
            verification_copy.get('human_review_links'),
            verification_copy.get('human_decision'),
            verification_copy.get('human_notes'),
            verification_copy.get('latency_npi_ms'),
            verification_copy.get('latency_board_ms'),
            verification_copy.get('latency_leie_ms'),
            verification_copy.get('latency_llm_ms'),
            verification_copy.get('llm_tokens_used', 0),
            verification_copy.get('cost_usd', 0.0),
            verification_copy.get('retry_counts'),
            verification_copy.get('errors'),
            verification_copy.get('batch_id'),
        ]
    )

    return verification_copy.get('id')


def update_verification_log(verification_id: str, updates: Dict[str, Any]):
    """
    Update an existing verification record.

    Args:
        verification_id: The verification ID to update
        updates: Dict of field:value pairs to update
    """
    conn = get_connection()

    # Serialize JSON fields
    updates_copy = updates.copy()
    for field in ['discrepancies', 'npi_raw', 'board_raw', 'leie_record',
                  'source_available', 'retry_counts', 'errors', 'human_review_links']:
        if field in updates_copy and updates_copy[field] is not None:
            updates_copy[field] = json.dumps(updates_copy[field])

    # Build dynamic UPDATE statement
    set_clauses = []
    values = []
    for key, value in updates_copy.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)

    values.append(verification_id)

    conn.execute(
        f"UPDATE verification_log SET {', '.join(set_clauses)} WHERE id = ?",
        values
    )


def get_verification_log(verification_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a verification record by ID.

    Args:
        verification_id: The verification ID

    Returns:
        Dict with verification data, or None if not found
    """
    conn = get_connection()
    result = conn.execute(
        "SELECT * FROM verification_log WHERE id = ?",
        [verification_id]
    ).fetchone()

    if result is None:
        return None

    columns = [desc[0] for desc in conn.description]
    row = dict(zip(columns, result))

    # Parse JSON fields
    for field in ['discrepancies', 'npi_raw', 'board_raw', 'leie_record',
                  'source_available', 'retry_counts', 'errors', 'human_review_links']:
        if field in row and row[field] is not None:
            try:
                row[field] = json.loads(row[field])
            except (json.JSONDecodeError, TypeError):
                pass

    return row


def get_hitl_queue() -> List[Dict[str, Any]]:
    """
    Get all verifications pending human review.

    Returns:
        List of verification records needing review
    """
    conn = get_connection()
    results = conn.execute(
        """
        SELECT * FROM verification_log
        WHERE needs_human_review = true AND human_decision IS NULL
        ORDER BY created_at ASC
        """
    ).fetchall()

    columns = [desc[0] for desc in conn.description]
    rows = []
    for result in results:
        row = dict(zip(columns, result))
        # Parse JSON fields
        for field in ['discrepancies', 'npi_raw', 'board_raw', 'leie_record',
                      'source_available', 'retry_counts', 'errors', 'human_review_links']:
            if field in row and row[field] is not None:
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        rows.append(row)

    return rows


def get_metrics() -> Dict[str, Any]:
    """
    Get aggregated metrics from verification_log.

    Returns:
        Dict with metrics data
    """
    conn = get_connection()

    # Total verifications
    total = conn.execute(
        "SELECT COUNT(*) FROM verification_log"
    ).fetchone()[0]

    if total == 0:
        return {
            "total_verifications": 0,
            "avg_cost_usd": 0.0,
            "avg_latency_ms": {"npi": 0, "dca": 0, "leie": 0, "llm": 0},
            "failure_rates": {"npi": 0.0, "dca": 0.0, "leie": 0.0},
            "outcome_distribution": {"verified": 0, "flagged": 0, "failed": 0, "escalated": 0}
        }

    # Average cost
    avg_cost = conn.execute(
        "SELECT AVG(cost_usd) FROM verification_log WHERE cost_usd IS NOT NULL"
    ).fetchone()[0] or 0.0

    # Average latencies
    avg_npi = conn.execute(
        "SELECT AVG(latency_npi_ms) FROM verification_log WHERE latency_npi_ms IS NOT NULL"
    ).fetchone()[0] or 0
    avg_dca = conn.execute(
        "SELECT AVG(latency_board_ms) FROM verification_log WHERE latency_board_ms IS NOT NULL"
    ).fetchone()[0] or 0
    avg_leie = conn.execute(
        "SELECT AVG(latency_leie_ms) FROM verification_log WHERE latency_leie_ms IS NOT NULL"
    ).fetchone()[0] or 0
    avg_llm = conn.execute(
        "SELECT AVG(latency_llm_ms) FROM verification_log WHERE latency_llm_ms IS NOT NULL"
    ).fetchone()[0] or 0

    # Outcome distribution
    outcomes = conn.execute(
        """
        SELECT verification_status, COUNT(*) as count
        FROM verification_log
        GROUP BY verification_status
        """
    ).fetchall()
    outcome_dist = {row[0]: row[1] for row in outcomes}

    return {
        "total_verifications": total,
        "avg_cost_usd": round(avg_cost, 4),
        "avg_latency_ms": {
            "npi": int(avg_npi),
            "dca": int(avg_dca),
            "leie": int(avg_leie),
            "llm": int(avg_llm)
        },
        "failure_rates": {
            "npi": 0.0,  # TODO: Calculate from errors
            "dca": 0.0,
            "leie": 0.0
        },
        "outcome_distribution": {
            "verified": outcome_dist.get("verified", 0),
            "flagged": outcome_dist.get("flagged", 0),
            "failed": outcome_dist.get("failed", 0),
            "escalated": outcome_dist.get("escalated", 0)
        }
    }


def _ensure_verification_log_table(conn: duckdb.DuckDBPyConnection):
    """Create the verification_log table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verification_log (
            id VARCHAR PRIMARY KEY,
            npi_number VARCHAR NOT NULL,
            target_state VARCHAR NOT NULL DEFAULT 'CA',
            provider_name VARCHAR,
            license_number VARCHAR,
            verification_status VARCHAR NOT NULL,
            confidence_score FLOAT,
            confidence_reasoning TEXT,
            discrepancies JSON,
            npi_raw JSON,
            board_raw JSON,
            leie_match BOOLEAN DEFAULT FALSE,
            leie_record JSON,
            source_available JSON,
            needs_human_review BOOLEAN DEFAULT FALSE,
            human_review_reason TEXT,
            human_review_links JSON,
            human_decision VARCHAR,
            human_notes TEXT,
            latency_npi_ms INTEGER,
            latency_board_ms INTEGER,
            latency_leie_ms INTEGER,
            latency_llm_ms INTEGER,
            llm_tokens_used INTEGER DEFAULT 0,
            cost_usd FLOAT DEFAULT 0.0,
            retry_counts JSON,
            errors JSON,
            batch_id VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
