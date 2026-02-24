"""
CredentialMD Configuration

Loads configuration from environment variables with sensible defaults.
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Mock Mode - default to True for development/testing
MOCK_MODE = os.getenv("CREDENTIALMD_MOCK_MODE", "true").lower() == "true"

# Logging configuration
LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

# Backend server configuration
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

# Frontend configuration
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3000"))

# Database configuration
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", str(PROJECT_ROOT / "data" / "credentialmd.duckdb")))

# LEIE CSV configuration
if MOCK_MODE:
    DEFAULT_LEIE_PATH = str(PROJECT_ROOT / "data" / "UPDATED_test.csv")
else:
    DEFAULT_LEIE_PATH = str(PROJECT_ROOT / "data" / "oig" / "UPDATED.csv")
LEIE_CSV_PATH = Path(os.getenv("LEIE_CSV_PATH", DEFAULT_LEIE_PATH))

# Target state for verification (CA for POC, but designed to be extensible)
TARGET_STATE = os.getenv("TARGET_STATE", "CA")

# NPI Registry API
NPI_API_BASE_URL = "https://npiregistry.cms.hhs.gov/api/"
NPI_API_VERSION = "2.1"
NPI_RATE_LIMIT_DELAY = 1.0  # seconds between requests for bulk operations

# CA DCA Search
DCA_SEARCH_URL = "https://search.dca.ca.gov/"
DCA_BOARD_CODE = "800"  # Medical Board of California
DCA_LICENSE_TYPE = "289"  # Physician's and Surgeon's
DCA_HEADED = os.getenv("DCA_HEADED", "true").lower() == "true"
DCA_CHROME_USER_DATA_DIR = os.getenv("DCA_CHROME_USER_DATA_DIR") or None
DCA_MAX_RETRIES = int(os.getenv("DCA_MAX_RETRIES", "0"))

# Retry configuration
MAX_RETRIES = 4
BASE_RETRY_DELAY = 1.0  # seconds
RATE_LIMIT_RETRY_DELAY = 10.0  # seconds for HTTP 429

# LLM configuration
LLM_MODEL = "claude-opus-4-20250514"

# Confidence thresholds
CONFIDENCE_AUTO_VERIFY = 90  # >= this score = auto-verified
CONFIDENCE_FLAG_REVIEW = 70  # >= this score but < auto_verify = flagged
# < 70 = escalated to human review

# Cost estimation (per 1K tokens, approximate)
COST_PER_1K_INPUT_TOKENS = 0.015  # Claude Opus input
COST_PER_1K_OUTPUT_TOKENS = 0.075  # Claude Opus output


def get_config_summary() -> dict:
    """Return a summary of current configuration for debugging."""
    return {
        "mock_mode": MOCK_MODE,
        "log_level": LOG_LEVEL_NAME,
        "backend_host": BACKEND_HOST,
        "backend_port": BACKEND_PORT,
        "duckdb_path": str(DUCKDB_PATH),
        "leie_csv_path": str(LEIE_CSV_PATH),
        "target_state": TARGET_STATE,
        "llm_model": LLM_MODEL,
    }
