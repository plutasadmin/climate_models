""" Route definitions for the Plutas platform. Maps HTTP paths to controllers/middleware.

 @file analyzer-model/app/routes/health.py
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/filestore/health")
async def health_check():
    """
    Health check endpoint to verify if the API is running properly.

    ### Response
    - `status`: Always returns "healthy" if the API is functioning.
    """
    return {"status": "healthy"}
