#!/usr/bin/env python3
"""
Database Initialization Script

This script initializes the DuckDB database by:
1. Creating (or recreating) the database file
2. Loading the LEIE CSV into the leie table
3. Creating the verification_log table
4. Creating indexes for fast lookups

Usage:
    python scripts/init_db.py                          # loads real CSV
    python scripts/init_db.py --test                   # loads test CSV
    python scripts/init_db.py --csv path/to/custom.csv # loads custom CSV
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb


def init_database(csv_path: Path, db_path: Path, verbose: bool = True):
    """
    Initialize the DuckDB database with LEIE data.

    Args:
        csv_path: Path to the LEIE CSV file
        db_path: Path to the DuckDB database file
        verbose: Whether to print progress messages
    """
    if verbose:
        print(f"Initializing database at: {db_path}")
        print(f"Loading LEIE data from: {csv_path}")

    # Ensure directories exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Check CSV exists
    if not csv_path.exists():
        raise FileNotFoundError(f"LEIE CSV not found: {csv_path}")

    # Connect to database (creates if doesn't exist)
    conn = duckdb.connect(str(db_path))

    try:
        # Load LEIE CSV into table (replace if exists)
        if verbose:
            print("Loading LEIE table...")

        conn.execute(f"""
            CREATE OR REPLACE TABLE leie AS
            SELECT * FROM read_csv_auto('{csv_path}')
        """)

        # Create indexes for fast lookups
        if verbose:
            print("Creating indexes...")

        # Index on NPI for primary lookup
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_leie_npi ON leie(NPI)
        """)

        # Index on name for fallback lookup
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_leie_name ON leie(LASTNAME, FIRSTNAME)
        """)

        # Index on state for filtering
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_leie_state ON leie(STATE)
        """)

        # Create verification_log table
        if verbose:
            print("Creating verification_log table...")

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

        # Print summary
        if verbose:
            leie_count = conn.execute("SELECT COUNT(*) FROM leie").fetchone()[0]
            print(f"\nDatabase initialized successfully!")
            print(f"  LEIE records: {leie_count}")

            # Show sample rows
            print(f"\nSample LEIE records:")
            samples = conn.execute("""
                SELECT LASTNAME, FIRSTNAME, NPI, STATE, EXCLTYPE, EXCLDATE
                FROM leie
                LIMIT 5
            """).fetchall()
            for row in samples:
                print(f"  {row[0]}, {row[1]} | NPI: {row[2] or 'N/A'} | {row[3]} | {row[4]} | {row[5]}")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Initialize EverCred POC database"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use test LEIE CSV (data/UPDATED_test.csv)"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Path to custom LEIE CSV file"
    )
    parser.add_argument(
        "--db",
        type=str,
        help="Path to DuckDB database file"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress output messages"
    )

    args = parser.parse_args()

    # Determine paths
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"

    # CSV path
    if args.csv:
        csv_path = Path(args.csv)
    elif args.test:
        csv_path = data_dir / "UPDATED_test.csv"
    else:
        csv_path = data_dir / "UPDATED.csv"

    # Database path
    if args.db:
        db_path = Path(args.db)
    else:
        db_path = data_dir / "evercred.duckdb"

    # Initialize
    try:
        init_database(csv_path, db_path, verbose=not args.quiet)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
