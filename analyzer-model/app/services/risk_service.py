""" Business logic layer for the Plutas platform. Orchestrates models, integrations, and domain rules.

 @file analyzer-model/app/services/risk_service.py
"""

import asyncio
import json
import logging
import math
import traceback
from datetime import date, datetime
from decimal import Decimal

import numpy as np
import pandas as pd
from pydantic import ValidationError
from app.pydantic_models import CalculateRiskRequest
from risk_analyzer import risk_analyzer
from typing import Callable, List, Optional, Dict, Any, Union
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

# Initialize logger
logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[str, str, int], None]]

def convert_to_fractional_float(value: Union[int, float]) -> float:
    """
    Converts an integer or float percentage value to a fractional float.
    Example: 50 -> 0.5, 75 -> 0.75
    """
    return float(value) / 100


def build_modified_request(request: CalculateRiskRequest) -> Dict[str, Any]:
    """Normalize request payload for the risk analyzer."""
    modified_product_defaults = request.productDefaults.dict() if request.productDefaults else {}

    if modified_product_defaults:
        if "peril" in modified_product_defaults:
            peril_value = modified_product_defaults["peril"]
            if peril_value is not None:
                modified_product_defaults["peril"] = peril_value.strip().lower()

        if "peril_category" in modified_product_defaults:
            peril_category_value = modified_product_defaults["peril_category"]
            if peril_category_value is not None:
                modified_product_defaults["peril_category"] = peril_category_value.strip().replace(" ", "").lower()

        if "payout_percentage" in modified_product_defaults:
            modified_product_defaults["payout_percentage"] = convert_to_fractional_float(
                modified_product_defaults["payout_percentage"]
            )
        if "premium_difference_percent" in modified_product_defaults:
            modified_product_defaults["premium_difference_percent"] = convert_to_fractional_float(
                modified_product_defaults["premium_difference_percent"]
            )

        for plan_type in ["silver_plan", "gold_plan", "platinum_plan"]:
            if plan_type in modified_product_defaults:
                for plan in modified_product_defaults[plan_type]:
                    for key in [
                        "_strike",
                        "_exit",
                        "_priced_loss_ratio",
                        "_data_variability",
                        "_management_loading",
                        "_base_premium",
                        "_std_percentage",
                        "_slope_percentage",
                    ]:
                        full_key = plan_type.split("_")[0] + key
                        if full_key in plan:
                            plan[full_key] = convert_to_fractional_float(plan[full_key])

    return {
        "userInputs": request.userInputs.dict() if request.userInputs else None,
        "productDefaults": modified_product_defaults,
        "maxRadiusAllowedValue": request.maxRadiusAllowedValue,
    }


def _emit_progress(on_progress: ProgressCallback, stage: str, message: str, progress: int) -> None:
    if on_progress:
        on_progress(stage, message, progress)


async def process_risk_analysis(request: CalculateRiskRequest, on_progress: ProgressCallback = None):
    """
    Processes risk analysis asynchronously with data validation and transformation.
    
    Steps:
    1. Logs the incoming request.
    2. Normalizes and modifies `productDefaults` fields.
    3. Converts percentage values to fractional floats.
    4. Calls the risk analyzer asynchronously.
    5. Handles validation errors and unexpected exceptions.
    """
    try:
        logger.debug("Received request for risk calculation.")
        logger.debug("Request payload before conversion: %s", request.dict())

        modified_request = build_modified_request(request)
        logger.debug("Request payload after conversion: %s", modified_request)
        logger.info("Calling the risk analyzer with modified request.")

        _emit_progress(on_progress, "started", "Risk calculation started", 5)
        result = await risk_analyzer.analyze(modified_request, on_progress=on_progress)
        _emit_progress(on_progress, "completed", "Risk calculation completed", 100)

        logger.info("Risk analysis completed successfully.")
        return {"status": "success", "result": result}

    except ValidationError as e:
        # Handle validation errors from Pydantic models
        logger.error(f"Validation error occurred: {e.errors()}")
        raise HTTPException(status_code=422, detail=e.errors())

    except Exception as e:
        # Handle unexpected errors and log full traceback
        error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
        logger.error(f"An unexpected error occurred: {error_message}")
        detail = str(e)
        if "database system is in recovery mode" in detail.lower() or "server closed the connection unexpectedly" in detail.lower():
            raise HTTPException(
                status_code=503,
                detail="Weather data service is temporarily unavailable. Please retry in a few minutes.",
            )
        raise HTTPException(status_code=500, detail=detail)


def _sse_json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return 0.0
        return number
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if pd.isna(value):
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _format_sse_event(event_name: str, payload: Dict[str, Any]) -> str:
    data = json.dumps(payload, default=_sse_json_default, allow_nan=False)
    return f"event: {event_name}\ndata: {data}\n\n"


async def stream_risk_analysis(request: CalculateRiskRequest) -> StreamingResponse:
    """Stream risk analysis progress via Server-Sent Events."""

    async def event_generator():
        progress_queue: asyncio.Queue = asyncio.Queue()
        analysis_task = None

        try:
            # Flush connection immediately so downstream clients (customer-quote) connect fast.
            yield ": connected\n\n"
            yield _format_sse_event(
                "status",
                {"stage": "connected", "message": "Risk analyzer SSE connected", "progress": 1},
            )

            def on_progress(stage: str, message: str, progress: int) -> None:
                progress_queue.put_nowait(
                    {"event": "progress", "stage": stage, "message": message, "progress": progress}
                )

            async def run_analysis() -> None:
                try:
                    result = await process_risk_analysis(request, on_progress=on_progress)
                    await progress_queue.put({"event": "completed", **result})
                except HTTPException as exc:
                    await progress_queue.put(
                        {
                            "event": "failed",
                            "status": "failed",
                            "message": str(exc.detail),
                            "status_code": exc.status_code,
                        }
                    )
                except Exception as exc:
                    await progress_queue.put({"event": "failed", "status": "failed", "message": str(exc)})

            analysis_task = asyncio.create_task(run_analysis())
            yield _format_sse_event(
                "status", {"stage": "started", "message": "Risk calculation started", "progress": 5}
            )

            while True:
                try:
                    payload = await asyncio.wait_for(progress_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    yield _format_sse_event(
                        "ping",
                        {"stage": "keepalive", "message": "keepalive", "progress": None},
                    )
                    continue

                event_name = payload.pop("event", "progress")
                try:
                    yield _format_sse_event(event_name, payload)
                except (TypeError, ValueError) as exc:
                    logger.error("Failed to serialize analyzer SSE payload for event '%s': %s", event_name, exc)
                    yield _format_sse_event(
                        "failed",
                        {
                            "status": "failed",
                            "message": "Risk analysis completed but the result could not be streamed",
                        },
                    )
                    break

                if event_name in {"completed", "failed"}:
                    break
        except Exception as exc:
            logger.error("Analyzer SSE stream failed before completion: %s", exc, exc_info=True)
            yield _format_sse_event("failed", {"status": "failed", "message": str(exc)})
        finally:
            if analysis_task is not None:
                await analysis_task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
