""" Climate risk analyzer module: App.

 @file analyzer-model/app/app.py
"""

from fastapi import FastAPI
from app.routes import risk_analysis, weather_update, health
from logging_setup import setup_logging

# Setup logging configuration
setup_logging()

# Initialize FastAPI app with metadata
app = FastAPI(
    title="Risk Analyzer",
    version="1.0.0",
    description="""
    The **Risk Analyzer API** analyzes potential risks based on user inputs and product defaults. 
    Designed for risk modeling and insurance calculations, it provides endpoints to perform advanced risk analysis.
    
    **Comprehensive Risk Evaluation**: Analyze various risk factors, including location-based perils, insured amounts, and customizable plans.
    
    **Features:**
    - **Health Check Endpoint**: Verify if the API is up and running.
    - **Risk Calculation Endpoint**: Perform detailed risk analysis based on inputs.
    - **Risk Calculation Stream (SSE)**: Stream long-running risk analysis with progress events (recommended for policies >400 days).
    - **Weather Update Endpoint**: Update weather data (rainfall, heatwave, cold wave) based on pincode and date.

    ### Documentation
    - **Swagger UI**: `/model/docs` (Interactive API testing)
    - **ReDoc**: `/model/redoc` (Detailed schema documentation)
    """,
    docs_url="/model/docs",  # Swagger UI documentation endpoint
    redoc_url="/model/redoc",  # ReDoc schema documentation endpoint
    openapi_url="/model/openapi.json",  # OpenAPI schema endpoint
)

# Register routes for different API functionalities with appropriate prefixes and tags
app.include_router(health.router, prefix="/model", tags=["Health Check"])  # Health check endpoint
app.include_router(risk_analysis.router, prefix="/model", tags=["Risk Analysis"])  # Risk analysis functionality
app.include_router(weather_update.router, prefix="/model", tags=["Weather Data"])  # Weather data updates

# ✅ Override the root URL to provide API usage guidance
@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint that provides a welcome message and guides users to the API documentation.
    This endpoint is not included in the OpenAPI schema.
    """
    return {"message": "Welcome to the Risk Analyzer API. Go to /model/docs for Swagger UI."}
