""" Climate risk analyzer module: Risk Analyzer.

 @file analyzer-model/risk_analyzer/risk_analyzer.py
"""

import asyncio
import json
import os
import pandas as pd
from data_service import data_service
from models import rain_hira_model, rain_lora_model, heat_howa_model, heat_cowa_model,heat_sinhowa_model,rain_sinhira_model,heat_sinhowa30_model,heat_sincowa_model
import logging

logger = logging.getLogger(__name__)

# Determine the project root directory (assuming 'dags' is the root)
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Define the path to the model configuration file
CONFIG_FILE_PATH = os.path.join(base_dir, "model_config.json")

# Load model configurations from JSON file
try:
    with open(CONFIG_FILE_PATH, 'r') as config_file:
        model_config = json.load(config_file)
    logger.info("Loaded model configuration successfully.")
except FileNotFoundError:
    logger.error(f"Configuration file not found at {CONFIG_FILE_PATH}")
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_FILE_PATH}")

# Map model names to their corresponding module references
models = {
    "rain_hira_model": rain_hira_model,
    "rain_lora_model": rain_lora_model,
    "heat_howa_model": heat_howa_model,
    "heat_cowa_model": heat_cowa_model,
    "heat_sinhowa_model": heat_sinhowa_model,
    "rain_sinhira_model": rain_sinhira_model,
    "heat_sinhowa30_model": heat_sinhowa30_model,
    "heat_sincowa_model": heat_sincowa_model
}


def _run_model_sync(model, peril, user_inputs, product_defaults, data, dataSource, pincodes):
    """Run model pricing in a worker thread without blocking the event loop."""
    if peril == "rain":
        coro = model.execute_rain_strike_calculation(
            user_inputs, product_defaults, data, dataSource, pincodes
        )
    elif peril == "heat":
        coro = model.execute_heat_strike_calculation(
            user_inputs, product_defaults, data, dataSource, pincodes
        )
    else:
        raise ValueError(f"Unknown peril type: {peril}")

    # Model executors are async wrappers around sync pricing code; isolate loop per worker thread.
    return asyncio.run(coro)

async def analyze(params, on_progress=None):
    """
    Analyzes weather risk data based on user input and predefined models.

    Parameters:
        params (dict): A dictionary containing user inputs and product defaults.

    Returns:
        dict: Model execution results.

    Raises:
        ValueError: If required data is missing or an unknown peril type is encountered.
        Exception: Logs any unexpected errors and re-raises them.
    """
    try:
        # Log the incoming parameters for debugging
        logger.debug(f"Received parameters for statistical model : {params}")        
        # Extract inputs from the request parameters
        user_inputs = params.get("userInputs")
        product_defaults = params.get("productDefaults")
        peril = product_defaults['peril']

        if on_progress:
            on_progress("fetching_data", "Fetching weather data for analysis", 20)

        # Fetch data using the data service
        logger.info("Fetching data...")
        data, dataSource, pincodes = await data_service.fetchdata(params, peril)  
        logger.info("Data fetch complete.")

        if on_progress:
            on_progress("data_fetched", "Weather data fetched successfully", 45)

        # Ensure data is available for processing
        if data is None or data.empty:
            error_message = "No data found for the provided pincode. Unable to proceed with analysis."
            logger.error(error_message)
            raise ValueError(error_message)

        # Log key details from the input parameters
        logger.debug(f"Peril: '{product_defaults['peril']}'")
        logger.debug(f"Peril Category: '{product_defaults['peril_category']}'")

        # Construct the model name based on peril and category
        model_name = f"{product_defaults['peril']}_{product_defaults['peril_category']}_model"
        logger.info(f"Generated model name: {model_name}")

        # Retrieve the corresponding model configuration
        model_info = model_config['models'].get(model_name)

        # If no specific model is found, attempt to use the default model for the peril
        if not model_info:
            default_model_name = f"default_{product_defaults['peril']}"
            logger.warning(f"Model '{model_name}' not found. Using default model: '{default_model_name}'.")
            model_info = model_config['models'].get(default_model_name)

        # If no model is available, raise an error
        if not model_info:
            error_message = f"No model found for '{model_name}' or default model for '{product_defaults['peril']}'"
            logger.error(error_message)
            raise ValueError(error_message)

        # Retrieve the model name from the config and find its reference in the model mappings
        model_name = model_info['model']
        logger.info(f"Selected model: '{model_name}'")  # Log the selected model
        model = models.get(model_name)

        # If the model reference is not found, raise an error
        if not model:
            error_message = f"Model '{model_name}' not found in the model mappings."
            logger.error(error_message)
            raise ValueError(error_message)

        # Execute the appropriate model function based on the peril type
        if on_progress:
            on_progress("running_model", f"Running pricing model '{model_name}'", 65)

        if product_defaults['peril'] == 'rain':
            logger.info(f"Executing rain strike calculation for '{model_name}'")
            model_result = await asyncio.to_thread(
                _run_model_sync,
                model,
                product_defaults['peril'],
                user_inputs,
                product_defaults,
                data,
                dataSource,
                pincodes,
            )
        elif product_defaults['peril'] == 'heat':
            logger.info(f"Executing heat strike calculation for '{model_name}'")
            model_result = await asyncio.to_thread(
                _run_model_sync,
                model,
                product_defaults['peril'],
                user_inputs,
                product_defaults,
                data,
                dataSource,
                pincodes,
            )
        else:
            error_message = f"Unknown peril type: {product_defaults['peril']}"
            logger.error(error_message)
            raise ValueError(error_message)

        # Log successful execution
        logger.info("Model execution completed successfully.")

        return model_result

    except Exception as e:
        # Log the error with traceback details for debugging
        logger.error(f"An error occurred during analysis: {str(e)}", exc_info=True)
        raise