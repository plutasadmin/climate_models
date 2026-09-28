""" Climate risk analyzer module: Data Service.

 @file analyzer-model/data_service/data_service.py
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from .imd import imd
from .era5 import era5
from .near_by_pincodes.radius import find_nearby_pincodes
from typing import Dict, Tuple, List, Optional
from .near_by_pincodes.to_pincode import calculate_distance 

logger = logging.getLogger(__name__)
load_dotenv()

# Mapping peril types to their respective data sources
PERIL_CONFIGS = {
    "rain": {
        "database": os.getenv("IMD_DATABASE_NAME"),
        "fetch_function": imd.fetch_imd_data,
        "log_message": "Using IMD database for rainfall data.",
    },
    "heat": {
        "database": os.getenv("ERA5_DATABASE_NAME"),
        "fetch_function": era5.fetch_era5_data,
        "log_message": "Using ERA5 database for heat data.",
    },
}

def get_db_config(peril: str) -> Optional[Dict[str, str]]:
    """
    Retrieves the database configuration based on the peril type.
    """
    peril_info = PERIL_CONFIGS.get(peril)
    if not peril_info:
        logger.warning(f"No configuration found for peril type: {peril}")
        return None
    
    return {
        "database": peril_info["database"],
        "user": os.getenv("DATABASE_USER"),
        "password": os.getenv("DATABASE_PASSWORD"),
        "host": os.getenv("DATABASE_HOST"),
        "port": os.getenv("DATABASE_PORT"),
    }

async def fetchdata(params: Dict, peril: str) -> Tuple[Optional[Dict], Optional[str], Optional[List[str]]]:
    """
    Fetches climate data based on the specified peril type and input parameters.
    """
    try:
        logger.debug(f"Received parameters for data service : {params}")        

        if peril not in PERIL_CONFIGS:
            logger.error(f"Unsupported peril type requested: {peril}")
            raise ValueError(f"Unsupported peril type: {peril}")

        config = get_db_config(peril)
        if not config or not config["database"]:
            logger.error(f"Missing database configuration for peril: {peril}")
            raise ValueError(f"Missing database configuration for peril: {peril}")

        logger.info(PERIL_CONFIGS[peril]["log_message"])
        logger.info(f"Selected database: {config['database']} for peril: {peril}")

        # Extract user inputs and product defaults
        user_inputs = params.get("userInputs", {})
        product_defaults = params.get("productDefaults", {})

        pincodes = user_inputs.get("pincodes", [])
        radius = user_inputs.get("radius")
        to_pincode = user_inputs.get("to_pincode")
        max_allowed_radius = params.get("maxRadiusAllowedValue")

        if not pincodes:
            logger.warning("No pincodes provided in userInputs.")
            return None, None, None

        if not to_pincode:
            if radius:
                logger.info(f"No to_pincode provided. Using given radius: {radius} km.")
            else:
                logger.warning("Neither to_pincode nor radius was provided. Fetching data only for given pincodes.")

        if to_pincode and pincodes:
            logger.info(f"Calculating distance between {pincodes[0]} and {to_pincode} ...")
            radius = await calculate_distance(pincodes[0], to_pincode, config)
            logger.debug(f"Calculated radius: {radius} km")



        logger.debug(f"Checking radius: {radius} vs max allowed: {max_allowed_radius}")

        if radius and radius > max_allowed_radius:
            message = f"Radius cannot be greater than {max_allowed_radius} km"
            logger.warning(message)
            raise ValueError(message)

        if radius and radius > 0:
            logger.info(f"Finding nearby pincodes within {radius} km...")
            pincodes = await find_nearby_pincodes(pincodes, radius, config, to_pincode=to_pincode)
            logger.debug(f"Nearby pincodes found: {pincodes}")

        fetch_function = PERIL_CONFIGS[peril]["fetch_function"]
        logger.info(f"Fetching data for peril '{peril}' with pincodes: {pincodes}")
        result, dataSource, pincodes = await asyncio.to_thread(fetch_function, pincodes, config)

        if result is None or result.empty:
            message = f"No data available for the provided inputs: pincodes={pincodes}, peril={peril}."
            logger.warning(message)
            raise ValueError(message)

        logger.info(f"Data fetched successfully for peril '{peril}'.")
        return result, dataSource, pincodes

    except ValueError as ve:
        logger.error(f"Configuration or validation error: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching data: {str(e)}", exc_info=True)
        raise
