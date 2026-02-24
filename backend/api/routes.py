"""
FastAPI Route Definitions

API endpoints for verification, batch processing, metrics, and HITL.
"""

import re
import uuid
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from graph.workflow import (
    run_verification,
    run_verification_streaming,
    get_verification,
    store_verification,
)
from graph.state import create_initial_state, state_to_dict
import db


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class VerifyRequest(BaseModel):
    """Request body for single verification."""
    npi: str = Field(..., description="10-digit NPI number")

    @field_validator("npi")
    @classmethod
    def validate_npi(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\d{10}$", v):
            raise ValueError("NPI must be exactly 10 digits")
        return v


class VerifyResponse(BaseModel):
    """Response for verification initiation."""
    verification_id: str
    status: str


class ReviewRequest(BaseModel):
    """Request body for human review decision."""
    decision: str = Field(..., description="approved, rejected, or needs_info")
    notes: Optional[str] = Field(None, description="Reviewer notes")

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ["approved", "rejected", "needs_info"]:
            raise ValueError("Decision must be: approved, rejected, or needs_info")
        return v


class BatchRequest(BaseModel):
    """Request body for batch verification."""
    npis: List[str] = Field(..., description="List of 10-digit NPI numbers")

    @field_validator("npis")
    @classmethod
    def validate_npis(cls, v: List[str]) -> List[str]:
        if len(v) > 20:
            raise ValueError("Maximum 20 NPIs per batch")
        if len(v) == 0:
            raise ValueError("At least one NPI required")

        validated = []
        for npi in v:
            npi = npi.strip()
            if not re.match(r"^\d{10}$", npi):
                raise ValueError(f"Invalid NPI format: {npi}")
            validated.append(npi)
        return validated


class BatchResponse(BaseModel):
    """Response for batch initiation."""
    batch_id: str
    total: int
    status: str


# =============================================================================
# In-memory stores for verifications and batches
# =============================================================================

_verifications: Dict[str, Dict[str, Any]] = {}  # verification_id -> state dict
_batches: Dict[str, Dict[str, Any]] = {}  # batch_id -> batch data


# =============================================================================
# Verification Endpoints
# =============================================================================

@router.post("/verify", response_model=VerifyResponse)
async def start_verification(request: VerifyRequest, background_tasks: BackgroundTasks):
    """
    Start a single physician verification.

    Body: { "npi": "1003127655" }
    Response: { "verification_id": "uuid", "status": "processing" }
    """
    verification_id = str(uuid.uuid4())

    # Create initial state for tracking
    initial_state = create_initial_state(
        npi_number=request.npi,
        verification_id=verification_id,
    )
    _verifications[verification_id] = dict(initial_state)

    # Run verification in background
    async def run_and_store():
        import traceback as tb
        try:
            result = await run_verification(
                npi=request.npi,
                target_state="CA",
                verification_id=verification_id,
            )
            _verifications[verification_id] = result
            store_verification(result)
        except Exception as e:
            # Update the state with error and full traceback
            _verifications[verification_id]["verification_status"] = "failed"
            errors = _verifications[verification_id].get("errors", [])
            errors.append(f"Exception: {repr(e)}")
            errors.append(f"Full traceback: {tb.format_exc()}")
            _verifications[verification_id]["errors"] = errors
            print(f"ERROR in run_and_store: {tb.format_exc()}")

    background_tasks.add_task(run_and_store)

    return VerifyResponse(
        verification_id=verification_id,
        status="processing"
    )


@router.get("/verify/{verification_id}")
async def get_verification_status(verification_id: str):
    """
    Get current verification status and results.

    Response: Full verification state as JSON
    """
    # Check in-memory store first
    state = _verifications.get(verification_id)
    if state:
        return state_to_dict(state)

    # Check database
    db_record = db.get_verification_log(verification_id)
    if db_record:
        return db_record

    raise HTTPException(status_code=404, detail="Verification not found")


@router.get("/verify/{verification_id}/stream")
async def stream_verification(verification_id: str):
    """
    Stream verification status updates via SSE.

    Events: { "step": "npi_lookup", "status": "complete", "data": {...} }
    """
    # Check if verification exists
    state = _verifications.get(verification_id)
    if not state:
        raise HTTPException(status_code=404, detail="Verification not found")

    async def event_generator():
        # Yield current state immediately
        yield {
            "event": "status",
            "data": {
                "step": "current",
                "status": state.get("verification_status", "pending"),
                "verification_id": verification_id,
                "data": state_to_dict(state),
            }
        }

        # Poll for updates
        last_status = state.get("verification_status", "pending")
        max_polls = 60  # 1 minute max

        for _ in range(max_polls):
            await asyncio.sleep(1)

            current_state = _verifications.get(verification_id)
            if not current_state:
                break

            current_status = current_state.get("verification_status", "pending")
            if current_status != last_status:
                last_status = current_status
                yield {
                    "event": "status",
                    "data": {
                        "step": "update",
                        "status": current_status,
                        "verification_id": verification_id,
                        "data": state_to_dict(current_state),
                    }
                }

            # Check if complete
            if current_status in ["verified", "failed", "flagged", "escalated"]:
                if current_state.get("completed_at"):
                    yield {
                        "event": "complete",
                        "data": state_to_dict(current_state),
                    }
                    break

    return EventSourceResponse(event_generator())


@router.post("/verify/{verification_id}/review")
async def submit_review(verification_id: str, request: ReviewRequest):
    """
    Submit human review decision and resume workflow.

    Body: { "decision": "approved", "notes": "Verified manually via DCA" }
    """
    # Get verification state
    state = _verifications.get(verification_id)
    if not state:
        # Check database
        db_record = db.get_verification_log(verification_id)
        if not db_record:
            raise HTTPException(status_code=404, detail="Verification not found")
        state = dict(db_record)

    # Check if this verification needs review
    if not state.get("needs_human_review", False):
        raise HTTPException(
            status_code=400,
            detail="Verification is not pending human review"
        )

    # Update state with human decision
    state["human_decision"] = request.decision
    state["human_notes"] = request.notes
    state["needs_human_review"] = False
    state["completed_at"] = datetime.utcnow().isoformat()

    # Update verification status based on decision
    if request.decision == "approved":
        state["verification_status"] = "verified"
    elif request.decision == "rejected":
        state["verification_status"] = "failed"
    else:  # needs_info
        state["verification_status"] = "escalated"

    # Store updated state
    _verifications[verification_id] = state

    # Update database
    try:
        db.update_verification_log(verification_id, {
            "human_decision": request.decision,
            "human_notes": request.notes,
            "needs_human_review": False,
            "verification_status": state["verification_status"],
            "completed_at": state["completed_at"],
        })
    except Exception:
        # If DB update fails, still return success (in-memory is updated)
        pass

    return state_to_dict(state)


# =============================================================================
# Batch Endpoints
# =============================================================================

async def _run_batch_internal(npis: List[str], background_tasks: BackgroundTasks) -> BatchResponse:
    """Internal function to create and run a batch."""
    # Create batch
    batch_id = str(uuid.uuid4())
    _batches[batch_id] = {
        "npis": npis,
        "results": [],
        "status": "processing",
        "total": len(npis),
        "completed": 0,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Run batch in background
    async def run_batch():
        batch = _batches[batch_id]

        for i, npi in enumerate(npis):
            try:
                # Run single verification
                result = await run_verification(
                    npi=npi,
                    target_state="CA",
                    batch_id=batch_id,
                )
                batch["results"].append(state_to_dict(result))
            except Exception as e:
                # Record error
                batch["results"].append({
                    "npi_number": npi,
                    "verification_status": "failed",
                    "errors": [str(e)],
                })

            batch["completed"] = i + 1

            # Throttle: 1 second between NPIs for rate limiting
            if i < len(npis) - 1:
                await asyncio.sleep(1)

        batch["status"] = "completed"
        batch["completed_at"] = datetime.utcnow().isoformat()

    background_tasks.add_task(run_batch)

    return BatchResponse(
        batch_id=batch_id,
        total=len(npis),
        status="processing"
    )


@router.post("/batch", response_model=BatchResponse)
async def start_batch(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start batch verification of multiple NPIs via JSON.

    Body: { "npis": ["1003127655", "1234567890", ...] }
    """
    npis = request.npis

    if not npis:
        raise HTTPException(
            status_code=400,
            detail="No valid NPIs found"
        )

    return await _run_batch_internal(npis, background_tasks)


@router.post("/batch/upload", response_model=BatchResponse)
async def start_batch_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Start batch verification via CSV file upload.

    Multipart form with CSV file (single column: npi)
    """
    npis = []

    content = await file.read()
    lines = content.decode("utf-8").strip().split("\n")
    for line in lines:
        line = line.strip()
        # Skip header row
        if line.lower() == "npi":
            continue
        # Extract NPI (handle CSV with multiple columns)
        npi = line.split(",")[0].strip().strip('"')
        if re.match(r"^\d{10}$", npi):
            npis.append(npi)

    if len(npis) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 NPIs per batch"
        )

    if not npis:
        raise HTTPException(
            status_code=400,
            detail="No valid NPIs found in CSV"
        )

    return await _run_batch_internal(npis, background_tasks)


@router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """
    Get batch verification status and results.

    Response: { "batch_id": "...", "total": 10, "completed": 4, "results": [...] }
    """
    batch = _batches.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    return {
        "batch_id": batch_id,
        "total": batch["total"],
        "completed": batch["completed"],
        "status": batch["status"],
        "results": batch["results"],
    }


@router.get("/batch/{batch_id}/stream")
async def stream_batch(batch_id: str):
    """
    Stream batch progress updates via SSE.
    """
    batch = _batches.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    async def event_generator():
        last_completed = 0

        while True:
            current_batch = _batches.get(batch_id)
            if not current_batch:
                break

            # Yield new results
            while last_completed < current_batch["completed"]:
                result = current_batch["results"][last_completed] if last_completed < len(current_batch["results"]) else None
                yield {
                    "event": "progress",
                    "data": {
                        "batch_id": batch_id,
                        "completed": last_completed + 1,
                        "total": current_batch["total"],
                        "result": result,
                    }
                }
                last_completed += 1

            # Check if complete
            if current_batch["status"] == "completed":
                yield {
                    "event": "complete",
                    "data": {
                        "batch_id": batch_id,
                        "total": current_batch["total"],
                        "completed": current_batch["completed"],
                        "results": current_batch["results"],
                    }
                }
                break

            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@router.get("/batch/{batch_id}/export")
async def export_batch_results(batch_id: str):
    """
    Export batch results as CSV.
    """
    batch = _batches.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Build CSV
    lines = [
        "npi,provider_name,license_number,verification_status,confidence_score,discrepancies"
    ]

    for result in batch["results"]:
        npi = result.get("npi_number", "")
        name = result.get("provider_name", "")
        license_num = result.get("license_number", "")
        status = result.get("verification_status", "")
        confidence = result.get("confidence_score", "")
        discrepancies = ";".join(result.get("discrepancies", []))

        # Escape CSV fields
        name = f'"{name}"' if name and "," in name else (name or "")
        discrepancies = f'"{discrepancies}"' if discrepancies and "," in discrepancies else discrepancies

        lines.append(f"{npi},{name},{license_num},{status},{confidence},{discrepancies}")

    csv_content = "\n".join(lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=batch_{batch_id}.csv"
        }
    )


# =============================================================================
# Metrics Endpoint
# =============================================================================

@router.get("/metrics")
async def get_metrics():
    """
    Get aggregated verification metrics.

    Response: {
        "total_verifications": 42,
        "avg_cost_usd": 0.18,
        "avg_latency_ms": { "npi": 320, "dca": 2100, "leie": 5, "llm": 1200 },
        "failure_rates": { "npi": 0.02, "dca": 0.08, "leie": 0.001 },
        "outcome_distribution": { "verified": 30, "flagged": 8, "failed": 4 }
    }
    """
    return db.get_metrics()


@router.get("/metrics/stream")
async def stream_metrics():
    """
    Stream metrics updates via SSE.

    Pushes updated metrics every 2 seconds while any batch is processing,
    or every 10 seconds when idle. This allows the dashboard to show
    real-time updates during batch processing.
    """
    async def event_generator():
        last_metrics = None
        idle_count = 0
        max_idle = 30  # Stop after 5 minutes of idle (30 * 10 seconds)

        while True:
            # Check if any batch is processing
            any_processing = any(
                batch.get("status") == "processing"
                for batch in _batches.values()
            )

            # Get current metrics
            current_metrics = db.get_metrics()

            # Only send if metrics changed or first time
            if current_metrics != last_metrics:
                yield {
                    "event": "metrics",
                    "data": current_metrics,
                }
                last_metrics = current_metrics
                idle_count = 0
            else:
                idle_count += 1

            # Stop if idle for too long
            if idle_count >= max_idle:
                yield {
                    "event": "close",
                    "data": {"reason": "idle_timeout"},
                }
                break

            # Poll faster during batch processing, slower when idle
            if any_processing:
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(10)

    return EventSourceResponse(event_generator())


# =============================================================================
# HITL Queue Endpoint
# =============================================================================

@router.get("/hitl/queue")
async def get_hitl_queue():
    """
    Get verifications pending human review.

    Response: Array of verifications with needs_human_review=true and human_decision=null.
    """
    # Combine DB queue with in-memory queue
    db_queue = db.get_hitl_queue()

    # Add any in-memory verifications that need review
    memory_queue = [
        state_to_dict(state)
        for state in _verifications.values()
        if state.get("needs_human_review", False) and state.get("human_decision") is None
    ]

    # Deduplicate by verification_id
    seen_ids = set()
    combined = []

    for item in memory_queue + db_queue:
        item_id = item.get("id") or item.get("verification_id")
        if item_id and item_id not in seen_ids:
            seen_ids.add(item_id)
            combined.append(item)

    return combined
