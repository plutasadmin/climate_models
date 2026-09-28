""" Business logic layer for the Plutas platform. Orchestrates models, integrations, and domain rules.

 @file analyzer-model/app/services/update_weather_data.py
"""

import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv  
from fastapi import HTTPException  

load_dotenv()

# Function to update weather data in the database
def update_weather_data(climatetype: str, pincode: int, date: str, value: float, source: str):
    """
    Updates weather data in the appropriate database based on the given climate type, pincode, date, and source.

    Parameters:
        climatetype (str): The type of climate data (e.g., "rainfall", "heatwave", "coldwave").
        pincode (int): The pincode for which the weather data should be updated.
        date (str): The date of the weather data in "DD-MM-YYYY" format.
        value (float): The new weather value to be updated.
        source (str): The source of the data ("imd" for rainfall, "era5" for heatwave/coldwave).

    Returns:
        dict: A success message if the update is successful.

    Raises:
        HTTPException (404): If no records were updated (invalid pincode or date).
        HTTPException (500): For any other unexpected errors.
    """
    try:
        # Determine database configuration based on the data source
        if source == "imd":
            DB_CONFIG = {
                "database": os.getenv("IMD_DATABASE_NAME"),
                "user": os.getenv("DATABASE_USER"),
                "password": os.getenv("DATABASE_PASSWORD"),
                "host": os.getenv("DATABASE_HOST"),
                "port": os.getenv("DATABASE_PORT")
            }
            print("Using IMD database for rainfall data.")
        elif source == "era5":
            DB_CONFIG = {
                "database": os.getenv("ERA5_DATABASE_NAME"),
                "user": os.getenv("DATABASE_USER"),
                "password": os.getenv("DATABASE_PASSWORD"),
                "host": os.getenv("DATABASE_HOST"),
                "port": os.getenv("DATABASE_PORT")
            }
            print("Using ERA5 database for heatwave and coldwave data.")
        else:
            # Raise an error if an invalid source is provided
            raise ValueError(f"Unknown source: {source}")

        print(f"Selected database: {DB_CONFIG['database']} for source: {source}")

        # Convert the provided date string to a datetime object
        date_obj = datetime.strptime(date, "%d-%m-%Y").date()

        # Establish a database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Construct the SQL query based on climate type and source
        if climatetype == "rainfall" and source == "imd":
            query = """
                UPDATE imd_rainfall_processed
                SET updated_rain = %s, remarks = 'Updated via API'
                WHERE pincode = %s AND date = %s;
            """
        elif climatetype == "heatwave" and source == "era5":
            query = """
                UPDATE era5_heat_processed
                SET max_temperature = %s, remarks = 'Updated via API'
                WHERE pincode = %s AND date = %s;
            """
        elif climatetype == "coldwave" and source == "era5":
            query = """
                UPDATE era5_heat_processed
                SET min_temperature = %s, remarks = 'Updated via API'
                WHERE pincode = %s AND date = %s;
            """
        else:
            # Raise an error if an invalid climatetype-source combination is provided
            raise ValueError("Invalid climatetype or source combination.")

        # Execute the SQL update query
        cursor.execute(query, (value, pincode, date_obj))
        conn.commit()

        # Check if any records were updated
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="No records updated. Check pincode and date.")

        # Close database connection
        cursor.close()
        conn.close()

        return {"message": "Weather data updated successfully."}

    except Exception as e:
        # Handle unexpected errors and raise a 500 internal server error
        raise HTTPException(status_code=500, detail=str(e))
