""" Route definitions for the Plutas platform. Maps HTTP paths to controllers/middleware.

 @file analyzer-model/app/routes/weather_update.py
"""

from fastapi import APIRouter
from app.pydantic_models import WeatherUpdate
from app.services.update_weather_data import update_weather_data

router = APIRouter()

@router.put("/update_weather_data")
async def update_weather(request: WeatherUpdate):
    """
    Updates weather data based on the given request parameters.

    - **climatetype**: Type of climate data ("rainfall", "heatwave", "coldwave").
    - **pincode**: Pincode of the location.
    - **date**: Date in "DD-MM-YYYY" format.
    - **value**: Rainfall amount, max temperature, or min temperature.
    - **source**: Data source ("imd" for rainfall, "era5" for temperature).
    
    Returns a success message if the update is performed successfully.

    ### Example Request:
    ```json
    {
        "climatetype": "rainfall",
        "pincode": 500072,
        "date": "01-01-2025",
        "value": 22,
        "source": "imd"
    }
    ```
    """ 
    return update_weather_data(request.climatetype, request.pincode, request.date, request.value, request.source)