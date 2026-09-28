import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from app.app import app
from app.services.risk_service import process_risk_analysis
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport  # ✅ Import ASGITransport for FastAPI
from unittest.mock import patch
from fastapi.exceptions import HTTPException
from unittest.mock import patch
from pydantic import ValidationError, BaseModel


client = TestClient(app)


@pytest.mark.asyncio
async def test_calculate_risk_success():
    test_payload = {
        "userInputs": {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincodes": ["500072"],
            "sumInsured": 30000,
            "radius": 0
        },
        "productDefaults": {
            "peril": "rain",
            "peril_category": "hot wave",
            "index_days": 1,
            "premium_difference_percent": 50,
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
                    "silver_strike_exit_delta": 4,
                    "silver_base_premium": 10
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
                    "gold_strike_exit_delta": 2,
                    "gold_base_premium": 15
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
                    "platinum_strike_exit_delta": 3,
                    "platinum_base_premium": 20
                }
            ],
            "weightage": [
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

    mock_result = {
    "status": "success",
    "result": [
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "silver",
            "strike": "10 mm",
            "exit": "14 mm",
            "averageBurnCost": 690.0,
            "standardDeviationBurnCost": 5485.718134235103,
            "standardDeviationPercent": 0.18285727114117012,
            "riskPremiumPercentage": 0.023,
            "netRiskPremiumRate": 0.1,
            "sumInsured": 30000,
            "basePremium": 3000.0,
            "dataVariability": 0.03,
            "managementLoading": 0.17,
            "delta": 4,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.95,
                "exitPercentile": 0.98
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 10 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 14 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        },
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "gold",
            "strike": "9 mm",
            "exit": "13 mm",
            "averageBurnCost": 1500.0,
            "standardDeviationBurnCost": 7611.243951073873,
            "standardDeviationPercent": 0.2537081317024624,
            "riskPremiumPercentage": 0.05,
            "netRiskPremiumRate": 0.15,
            "sumInsured": 30000,
            "basePremium": 4500.0,
            "dataVariability": 0.05,
            "managementLoading": 0.17,
            "delta": 2,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.9,
                "exitPercentile": 0.92
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 9 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 13 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        },
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "platinum",
            "strike": "10 mm",
            "exit": "14 mm",
            "averageBurnCost": 690.0,
            "standardDeviationBurnCost": 5485.718134235103,
            "standardDeviationPercent": 0.18285727114117012,
            "riskPremiumPercentage": 0.023,
            "netRiskPremiumRate": 0.2,
            "sumInsured": 30000,
            "basePremium": 6000.0,
            "dataVariability": 0.07,
            "managementLoading": 0.17,
            "delta": 3,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.85,
                "exitPercentile": 0.89
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 10 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 14 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        }
    ]
}

    # Patch the function where it is being called in the endpoint
    with patch("app.routes.risk_analysis.process_risk_analysis", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_result

        async with AsyncClient(base_url="http://127.0.0.1:8080", transport=ASGITransport(app=app)) as client:
            response = await client.post("/model/calculate_risk", json=test_payload)

        assert response.status_code == 200
        assert response.json() == mock_result
        mock_process.assert_called_once()
        
        
    
@pytest.fixture
def sample_request():
    """Fixture for a valid risk analysis request payload."""
    return {
        "userInputs": {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincodes": ["500072"],
            "sumInsured": 30000,
            "radius": 0
        },
        "productDefaults": {
            "peril": "rain",
            "peril_category": "hot wave",
            "index_days": 1,
            "premium_difference_percent": 50,
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
                    "silver_strike_exit_delta": 4,
                    "silver_base_premium": 10
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
                    "gold_strike_exit_delta": 2,
                    "gold_base_premium": 15
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
                    "platinum_strike_exit_delta": 3,
                    "platinum_base_premium": 20
                }
            ],
            "weightage": [
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

@patch("app.services.risk_service.process_risk_analysis", new_callable=AsyncMock)
def test_calculate_risk_success(mock_process_risk_analysis, client, sample_request):
    """Test successful risk analysis request."""
    mock_process_risk_analysis.return_value =     {
    "status": "success",
    "result": [
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "silver",
            "strike": "10 mm",
            "exit": "14 mm",
            "averageBurnCost": 690.0,
            "standardDeviationBurnCost": 5485.718134235103,
            "standardDeviationPercent": 0.18285727114117012,
            "riskPremiumPercentage": 0.023,
            "netRiskPremiumRate": 0.1,
            "sumInsured": 30000,
            "basePremium": 3000.0,
            "dataVariability": 0.03,
            "managementLoading": 0.17,
            "delta": 4,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.95,
                "exitPercentile": 0.98
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 10 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 14 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        },
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "gold",
            "strike": "9 mm",
            "exit": "13 mm",
            "averageBurnCost": 1500.0,
            "standardDeviationBurnCost": 7611.243951073873,
            "standardDeviationPercent": 0.2537081317024624,
            "riskPremiumPercentage": 0.05,
            "netRiskPremiumRate": 0.15,
            "sumInsured": 30000,
            "basePremium": 4500.0,
            "dataVariability": 0.05,
            "managementLoading": 0.17,
            "delta": 2,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.9,
                "exitPercentile": 0.92
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 9 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 13 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        },
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "platinum",
            "strike": "10 mm",
            "exit": "14 mm",
            "averageBurnCost": 690.0,
            "standardDeviationBurnCost": 5485.718134235103,
            "standardDeviationPercent": 0.18285727114117012,
            "riskPremiumPercentage": 0.023,
            "netRiskPremiumRate": 0.2,
            "sumInsured": 30000,
            "basePremium": 6000.0,
            "dataVariability": 0.07,
            "managementLoading": 0.17,
            "delta": 3,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.85,
                "exitPercentile": 0.89
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 10 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 14 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        }
    ]
}


    response = client.post("/model/calculate_risk", json=sample_request)
    assert response.status_code == 200
    assert response.json() ==     {
    "status": "success",
    "result": [
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "silver",
            "strike": "10 mm",
            "exit": "14 mm",
            "averageBurnCost": 690.0,
            "standardDeviationBurnCost": 5485.718134235103,
            "standardDeviationPercent": 0.18285727114117012,
            "riskPremiumPercentage": 0.023,
            "netRiskPremiumRate": 0.1,
            "sumInsured": 30000,
            "basePremium": 3000.0,
            "dataVariability": 0.03,
            "managementLoading": 0.17,
            "delta": 4,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.95,
                "exitPercentile": 0.98
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 10 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 14 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        },
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "gold",
            "strike": "9 mm",
            "exit": "13 mm",
            "averageBurnCost": 1500.0,
            "standardDeviationBurnCost": 7611.243951073873,
            "standardDeviationPercent": 0.2537081317024624,
            "riskPremiumPercentage": 0.05,
            "netRiskPremiumRate": 0.15,
            "sumInsured": 30000,
            "basePremium": 4500.0,
            "dataVariability": 0.05,
            "managementLoading": 0.17,
            "delta": 2,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.9,
                "exitPercentile": 0.92
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 9 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 13 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        },
        {
            "riskStartDate": "2025-05-30",
            "riskEndDate": "2025-05-30",
            "pincode": [
                "500072"
            ],
            "additionalPincodes": [],
            "radius": 0.0,
            "level": "platinum",
            "strike": "10 mm",
            "exit": "14 mm",
            "averageBurnCost": 690.0,
            "standardDeviationBurnCost": 5485.718134235103,
            "standardDeviationPercent": 0.18285727114117012,
            "riskPremiumPercentage": 0.023,
            "netRiskPremiumRate": 0.2,
            "sumInsured": 30000,
            "basePremium": 6000.0,
            "dataVariability": 0.07,
            "managementLoading": 0.17,
            "delta": 3,
            "pricedLossRatio": 0.75,
            "levelPercentiles": {
                "strikePercentile": 0.85,
                "exitPercentile": 0.89
            },
            "coverageDetails": {
                "partialCoverage": "10% coverage for damages caused by rainfall exceeding 10 mm.",
                "fullCoverage": "100% coverage for damages caused by rainfall exceeding 14 mm."
            },
            "dataSource": "IMD Gridded Rainfall Data (0.25° x 0.25°)",
            "gridPoints": [
                "17.5°N 78.5°E"
            ],
            "statistics": [
                {
                    "year": 2013,
                    "Max_Rainfall": 14.07
                },
                {
                    "year": 2018,
                    "Max_Rainfall": 13.81
                },
                {
                    "year": 2021,
                    "Max_Rainfall": 4.87
                },
                {
                    "year": 2015,
                    "Max_Rainfall": 2.09
                },
                {
                    "year": 2008,
                    "Max_Rainfall": 1.65
                },
                {
                    "year": 2014,
                    "Max_Rainfall": 1.27
                },
                {
                    "year": 2002,
                    "Max_Rainfall": 1.04
                },
                {
                    "year": 2020,
                    "Max_Rainfall": 0.56
                },
                {
                    "year": 2011,
                    "Max_Rainfall": 0.3
                },
                {
                    "year": 1995,
                    "Max_Rainfall": 0.0
                }
            ]
        }
    ]
}



def test_calculate_risk_invalid_request(client):
    """Test risk analysis endpoint with missing required fields."""
    invalid_request = {"userInputs": {}, "productDefaults": {}}  # Still invalid, but structured

    response = client.post("/model/calculate_risk", json=invalid_request)

    assert response.status_code == 422  # Expecting 422 Unprocessable Entity


@patch("app.routes.risk_analysis.process_risk_analysis", new_callable=AsyncMock)
async def test_calculate_risk_server_error(mock_process_risk_analysis, sample_request):
    """Test handling of unexpected server errors."""

    # Debugging: Ensure mock is being called
    print("Mock process_risk_analysis is being used")

    # Force the function to raise an exception
    mock_process_risk_analysis.side_effect = Exception("Something went wrong")

    response = client.post("/model/calculate_risk", json=sample_request)

    print(response.status_code, response.json())  # Debug output

    assert response.status_code == 500  # Expecting Internal Server Error




# Dummy Pydantic Model to create ValidationError
class DummyModel(BaseModel):
    some_field: int

# 1️⃣ Test ValidationError
@patch("app.routes.risk_analysis.process_risk_analysis")
def test_calculate_risk_validation_error(mock_process_risk_analysis, client):
    """Test if the endpoint correctly handles a ValidationError."""

    try:
        DummyModel(some_field="invalid_string")  # This will raise a ValidationError
    except ValidationError as e:
        mock_process_risk_analysis.side_effect = e  # Assign the caught ValidationError

    response = client.post("/model/calculate_risk", json={})  # Sending empty data

    assert response.status_code == 422
    assert "value is not a valid integer" in str(response.json()["detail"])




# 2️⃣ Test HTTPException
@patch("app.routes.risk_analysis.process_risk_analysis")
def test_calculate_risk_http_exception(mock_process_risk_analysis, client):
    """Test if the endpoint correctly handles HTTPException."""
    
    # Make the function raise an HTTPException
    mock_process_risk_analysis.side_effect = HTTPException(status_code=400, detail="Bad Request")

    response = client.post("/model/calculate_risk", json={"invalid": "data"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Bad Request"
