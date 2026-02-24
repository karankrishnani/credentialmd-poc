"""
LangGraph Workflow Definition

Defines the verification workflow graph with nodes and edges.

Graph structure:
START -> npi_lookup -> {board_lookup, leie_lookup} (parallel)
                    -> human_review (if no license or NPI inactive)
{board_lookup, leie_lookup} -> discrepancy_detection (fan-in)
discrepancy_detection -> route_decision
route_decision -> finalize (auto-verify or auto-fail)
               -> human_review (low confidence or flagged)
human_review -> finalize
finalize -> END
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator

from langgraph.graph import StateGraph, END

from graph.state import VerificationState, create_initial_state, state_to_dict
from graph.nodes import (
    npi_lookup,
    board_lookup,
    leie_lookup,
    discrepancy_detection,
    route_decision,
    route_decision_node,
    human_review,
    finalize,
)


def create_workflow_graph() -> StateGraph:
    """
    Create the verification workflow graph.

    Returns:
        StateGraph (not yet compiled)
    """
    # Create the graph with state type
    workflow = StateGraph(VerificationState)

    # Add nodes
    workflow.add_node("npi_lookup", npi_lookup)
    workflow.add_node("parallel_lookups", _parallel_lookups)
    workflow.add_node("discrepancy_detection", discrepancy_detection)
    workflow.add_node("route_decision_node", route_decision_node)
    workflow.add_node("human_review", human_review)
    workflow.add_node("finalize", finalize)

    # Set entry point
    workflow.set_entry_point("npi_lookup")

    # Add conditional edge from npi_lookup
    workflow.add_conditional_edges(
        "npi_lookup",
        _should_proceed_after_npi,
        {
            "proceed": "parallel_lookups",
            "review": "human_review",
        }
    )

    # After parallel lookups, go to discrepancy_detection
    workflow.add_edge("parallel_lookups", "discrepancy_detection")

    # After discrepancy_detection, go to route_decision
    workflow.add_edge("discrepancy_detection", "route_decision_node")

    # Conditional edges from route_decision
    workflow.add_conditional_edges(
        "route_decision_node",
        _get_route_decision,
        {
            "verify": "finalize",
            "flag": "finalize",
            "fail": "finalize",
            "review": "human_review",
        }
    )

    # Human review goes to finalize
    workflow.add_edge("human_review", "finalize")

    # Finalize goes to END
    workflow.add_edge("finalize", END)

    return workflow


async def _parallel_lookups(state: VerificationState) -> Dict[str, Any]:
    """
    Execute board_lookup and leie_lookup in parallel.

    Args:
        state: Current verification state

    Returns:
        Merged updates from both lookups
    """
    # Run both lookups concurrently
    board_result, leie_result = await asyncio.gather(
        board_lookup(state),
        leie_lookup(state),
    )

    # Merge results - combine step_latencies and other fields
    merged = {}

    # Copy all fields from board_result
    merged.update(board_result)

    # Merge in leie_result, being careful about nested dicts and lists
    for key, value in leie_result.items():
        if key == "step_latencies":
            # Merge step latencies
            if "step_latencies" not in merged:
                merged["step_latencies"] = {}
            merged["step_latencies"].update(value)
        elif key == "errors":
            # Merge errors
            if "errors" not in merged:
                merged["errors"] = []
            merged["errors"].extend(value)
        elif key == "source_available":
            # Merge source_available
            if "source_available" not in merged:
                merged["source_available"] = {}
            merged["source_available"].update(value)
        else:
            # Just copy the value
            merged[key] = value

    return merged


def _should_proceed_after_npi(state: VerificationState) -> str:
    """
    Determine whether to proceed to parallel lookups or go to human review.

    Args:
        state: Current verification state

    Returns:
        "proceed" or "review"
    """
    # If HITL already triggered by NPI lookup, go to review
    if state.get("needs_human_review", False):
        return "review"

    # If no license found, can't proceed with DCA lookup
    if not state.get("license_number"):
        return "review"

    return "proceed"


def _get_route_decision(state: VerificationState) -> str:
    """
    Get the routing decision for conditional edges.

    Args:
        state: Current verification state

    Returns:
        Route decision: "verify", "flag", "fail", or "review"
    """
    return route_decision(state)


# Global compiled workflow
_compiled_workflow = None


def get_workflow():
    """
    Get the compiled workflow instance (singleton).

    Returns:
        Compiled workflow
    """
    global _compiled_workflow
    if _compiled_workflow is None:
        workflow = create_workflow_graph()
        _compiled_workflow = workflow.compile()
    return _compiled_workflow


async def run_verification(
    npi: str,
    target_state: str = "CA",
    batch_id: Optional[str] = None,
    verification_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a complete verification for an NPI.

    Args:
        npi: The 10-digit NPI number
        target_state: Target state for license verification
        batch_id: Optional batch ID for bulk verifications
        verification_id: Optional verification ID (generates one if not provided)

    Returns:
        Final state as a dict
    """
    # Create initial state
    if verification_id is None:
        verification_id = str(uuid.uuid4())
    state = create_initial_state(
        npi_number=npi,
        target_state=target_state,
        verification_id=verification_id,
        batch_id=batch_id,
    )

    # Get workflow
    workflow = get_workflow()

    # Run the workflow
    result = await workflow.ainvoke(state)

    return result


async def run_verification_streaming(
    npi: str,
    target_state: str = "CA",
    batch_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run verification with streaming updates.

    Yields status updates as the workflow progresses.

    Args:
        npi: The 10-digit NPI number
        target_state: Target state for license verification
        batch_id: Optional batch ID for bulk verifications

    Yields:
        Status update dicts with step, status, and data
    """
    # Create initial state
    verification_id = str(uuid.uuid4())
    state = create_initial_state(
        npi_number=npi,
        target_state=target_state,
        verification_id=verification_id,
        batch_id=batch_id,
    )

    # Get workflow
    workflow = get_workflow()

    # Yield initial status
    yield {
        "step": "start",
        "status": "processing",
        "verification_id": verification_id,
        "data": {"npi": npi, "target_state": target_state},
    }

    final_state = state

    # Stream workflow execution
    async for event in workflow.astream(state):
        # Extract the node name and state from the event
        if isinstance(event, dict):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    # Merge updates into final_state
                    final_state = {**final_state, **node_output}

                    yield {
                        "step": node_name,
                        "status": final_state.get("verification_status", "processing"),
                        "verification_id": verification_id,
                        "data": {
                            "provider_name": final_state.get("provider_name"),
                            "license_number": final_state.get("license_number"),
                            "confidence_score": final_state.get("confidence_score"),
                            "discrepancies": final_state.get("discrepancies", []),
                            "needs_human_review": final_state.get("needs_human_review", False),
                        },
                    }

    # Yield final status
    yield {
        "step": "complete",
        "status": final_state.get("verification_status", "unknown"),
        "verification_id": verification_id,
        "data": state_to_dict(final_state),
    }


# In-memory storage for verifications (for simple retrieval)
_verification_store: Dict[str, Dict[str, Any]] = {}


def store_verification(state: Dict[str, Any]):
    """Store a verification state for later retrieval."""
    verification_id = state.get("verification_id")
    if verification_id:
        _verification_store[verification_id] = state


def get_verification(verification_id: str) -> Optional[Dict[str, Any]]:
    """Get a verification state by ID."""
    return _verification_store.get(verification_id)
