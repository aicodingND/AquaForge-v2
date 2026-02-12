"""
Server-Sent Events (SSE) streaming endpoint for real-time optimization progress.
Provides live updates during long-running optimizations.

Uses sse-starlette for proper SSE protocol handling with disconnect detection.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request

try:
    from sse_starlette.sse import EventSourceResponse, ServerSentEvent

    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False

router = APIRouter()
logger = logging.getLogger(__name__)


def _ping_message_factory() -> "ServerSentEvent":
    """Factory for ping messages used for disconnect detection."""
    return ServerSentEvent(data="", event="ping")


async def optimization_progress_generator(
    request: Request,
    seton_roster: list,
    opponent_roster: list,
    method: str = "gurobi",
    max_iters: int = 1000,
    **kwargs,
) -> "AsyncGenerator[ServerSentEvent, None]":
    """
    Generator that yields ServerSentEvent progress updates during optimization.

    Event types:
        - progress: Intermediate progress updates with stage/percentage
        - complete: Final result when optimization finishes successfully
        - error: Error information if optimization fails
    """
    from swim_ai_reflex.backend.services.optimization_service import OptimizationService

    try:
        _service = OptimizationService()  # noqa: F841

        # Stage 1: Initialization (0-10%)
        yield ServerSentEvent(
            data=json.dumps(
                {
                    "stage": "init",
                    "progress": 0,
                    "message": "Initializing optimizer...",
                    "details": f"Method: {method}",
                }
            ),
            event="progress",
        )
        await asyncio.sleep(0.2)

        # Stage 2: Validation (10-15%)
        yield ServerSentEvent(
            data=json.dumps(
                {
                    "stage": "validate",
                    "progress": 10,
                    "message": "Validating rosters...",
                    "details": f"{len(seton_roster)} vs {len(opponent_roster)} swimmers",
                }
            ),
            event="progress",
        )
        await asyncio.sleep(0.3)

        # Check for client disconnect
        if await request.is_disconnected():
            logger.info("Client disconnected during validation stage")
            return

        yield ServerSentEvent(
            data=json.dumps(
                {
                    "stage": "validate",
                    "progress": 15,
                    "message": "Building optimization model...",
                    "details": "Constructing constraints",
                }
            ),
            event="progress",
        )
        await asyncio.sleep(0.2)

        # Stage 3: Optimization (15-90%)
        # Simulate progress updates (in production, hook into actual optimizer)
        progress_steps = 20  # Number of progress updates
        for i in range(progress_steps):
            # Check for client disconnect periodically
            if await request.is_disconnected():
                logger.info("Client disconnected during optimization stage")
                return

            current_progress = 15 + int((i / progress_steps) * 75)
            current_iter = int((i / progress_steps) * max_iters)

            yield ServerSentEvent(
                data=json.dumps(
                    {
                        "stage": "optimizing",
                        "progress": current_progress,
                        "message": "Optimizing lineup...",
                        "details": f"Iteration {current_iter}/{max_iters}",
                        "current_iter": current_iter,
                        "max_iters": max_iters,
                    }
                ),
                event="progress",
            )

            # Throttle updates to ~0.5-1 second intervals
            await asyncio.sleep(0.5)

        # Stage 4: Finalization (90-95%)
        yield ServerSentEvent(
            data=json.dumps(
                {
                    "stage": "finalizing",
                    "progress": 90,
                    "message": "Calculating final scores...",
                    "details": "Evaluating lineup quality",
                }
            ),
            event="progress",
        )
        await asyncio.sleep(0.3)

        yield ServerSentEvent(
            data=json.dumps(
                {
                    "stage": "finalizing",
                    "progress": 95,
                    "message": "Generating results...",
                    "details": "Preparing output",
                }
            ),
            event="progress",
        )
        await asyncio.sleep(0.2)

        # Stage 5: Complete (100%)
        # In production, call actual optimization here
        # For now, simulate success
        yield ServerSentEvent(
            data=json.dumps(
                {
                    "stage": "complete",
                    "progress": 100,
                    "message": "Optimization complete!",
                    "details": "Results ready",
                    "success": True,
                }
            ),
            event="complete",
        )

    except Exception as e:
        logger.error(f"Optimization streaming failed: {e}", exc_info=True)
        yield ServerSentEvent(
            data=json.dumps(
                {
                    "stage": "error",
                    "progress": 0,
                    "message": f"Optimization failed: {str(e)}",
                    "details": "Check server logs",
                    "error": str(e),
                }
            ),
            event="error",
        )


@router.post("/optimize/stream")
async def stream_optimization_progress(request: Request):
    """
    Stream optimization progress via Server-Sent Events.

    Returns:
        EventSourceResponse with typed SSE events (progress, complete, error)

    Example client-side usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/optimize/stream');

    eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data);
        console.log(`${data.progress}% - ${data.message}`);
    });

    eventSource.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data);
        console.log('Done!', data);
        eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
        const data = JSON.parse(e.data);
        console.error('Failed:', data.message);
        eventSource.close();
    });
    ```
    """
    if not SSE_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="sse-starlette not installed. Install with: pip install sse-starlette",
        )

    try:
        body = await request.json()

        seton_roster = body.get("seton_roster", [])
        opponent_roster = body.get("opponent_roster", [])
        method = body.get("method", "gurobi")
        max_iters = body.get("max_iters", 1000)

        if not seton_roster or not opponent_roster:
            raise HTTPException(
                status_code=400,
                detail="Both seton_roster and opponent_roster are required",
            )

        return EventSourceResponse(
            optimization_progress_generator(
                request, seton_roster, opponent_roster, method, max_iters
            ),
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",  # Adjust for production
            },
            ping=15,  # Send ping every 15 seconds for disconnect detection
            ping_message_factory=_ping_message_factory,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start optimization stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))
