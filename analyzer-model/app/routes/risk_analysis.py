""" Route definitions for the Plutas platform. Maps HTTP paths to controllers/middleware.

 @file analyzer-model/app/routes/risk_analysis.py
"""

from fastapi import APIRouter, HTTPException
from app.pydantic_models import CalculateRiskRequest
from app.services.risk_service import process_risk_analysis, stream_risk_analysis
import logging
from pydantic import ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/calculate_risk",
    summary="Calculate risk (synchronous)",
    description="""
Calculate risk based on user inputs and product defaults.

Returns the full pricing result in a single JSON response.
For long-running policies (>400 days), prefer `POST /model/calculate_risk/stream`.
    """,
)
async def calculate_risk(request: CalculateRiskRequest):
    """
    Endpoint to calculate risk based on user inputs and product defaults.

    ### Request Body
    - **userInputs:** (optional) Inputs provided by the user for risk calculation.
    - **productDefaults:** (optional) Defaults for the product plans, variability, and payouts.

    ### Response
    - `status`: Status of the risk calculation (e.g., "success").
    - `result`: Results of the risk analysis, containing calculated risk metrics.
    
	### Example Request
    ```
    {
    "userInputs": {
        "riskStartDate": "2025-05-01",
        "riskEndDate": "2025-05-30",
        "pincodes": ["500072"],
                    "sumInsured": 30000,
                    "radius": 0
                },
                "productDefaults": {
                    "peril": "heat",
                    "peril_category": "hot wave",
                    "index_days":1,
                    "premium_difference_percent":50,
                    "payout_percentage": 10,
                    "silver_plan": [
                    {
                        "silver_strike": 95,
                        "silver_exit": 98,
                        "silver_priced_loss_ratio": 75,
                        "silver_data_variability": 3,
                        "silver_management_loading": 17,
                        "silver_threshold_strike": 8,
                        "silver_threshold_exit": 12,
                        "silver_strike_exit_delta":4,
                        "silver_base_premium":10
                    }
                    ],
                    "gold_plan": [
                    {
                        "gold_strike": 90,
                        "gold_exit": 92,
                        "gold_priced_loss_ratio": 75,
                        "gold_data_variability": 5,
                        "gold_management_loading": 17,
                        "gold_threshold_strike": 9,
                        "gold_threshold_exit": 13,
                        "gold_strike_exit_delta":2,
                        "gold_base_premium":15
                    }
                    ],
                    "platinum_plan": [
                    {
                        "platinum_strike": 85,
                        "platinum_exit": 89,
                        "platinum_priced_loss_ratio": 75,
                        "platinum_data_variability": 7,
                        "platinum_management_loading": 17,
                        "platinum_threshold_strike": 10,
                        "platinum_threshold_exit": 14,
                        "platinum_strike_exit_delta":3,
                        "platinum_base_premium":20
                    }
                    ],
                    "weightage" : [
                    {
                        "weightage_0_5_years": 10,
                        "weightage_6_10_years": 20,
                        "weightage_11_15_years": 20,
                        "weightage_16_20_years": 10,
                        "weightage_21_25_years": 15,
                        "weightage_26_30_years": 25
                    }
                ]
                    }
                }
	
	"""

    try:
        return await process_risk_analysis(request)
    except ValidationError as e:
        logger.error(f"Validation error in /calculate_risk: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /calculate_risk: {str(e)}")
        raise HTTPException(status_code=500, detail="Risk analysis failed.")


@router.post(
    "/calculate_risk/stream",
    summary="Stream risk calculation via SSE",
    description="""
Stream risk calculation progress using **Server-Sent Events (SSE)**.

Use this endpoint for **long-running policies** (e.g. duration >400 days) to avoid gateway timeouts.
The request body is identical to `POST /model/calculate_risk`.

### SSE Events

| Event | Description |
|-------|-------------|
| `status` | Job started |
| `progress` | Intermediate progress (`stage`, `message`, `progress`) |
| `completed` | Final result (`status`, `result`) |
| `failed` | Error details (`status`, `message`) |

### Progress stages

- `started` → `fetching_data` → `data_fetched` → `running_model` → `completed`

### Example SSE payload

```
event: progress
data: {"stage":"fetching_data","message":"Fetching weather data for analysis","progress":20}

event: completed
data: {"status":"success","result":[...]}
```

**Note:** Swagger UI cannot render SSE streams interactively. Use `curl -N` or a frontend `fetch` stream reader for testing.
    """,
    responses={
        200: {
            "description": "SSE stream of risk calculation progress and final result",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "example": 'event: completed\ndata: {"status":"success","result":[]}\n\n',
                    }
                }
            },
        },
        422: {"description": "Validation error"},
        500: {"description": "Risk analysis failed"},
    },
)
async def calculate_risk_stream(request: CalculateRiskRequest):
    """Stream risk calculation progress via Server-Sent Events (SSE)."""
    return await stream_risk_analysis(request)