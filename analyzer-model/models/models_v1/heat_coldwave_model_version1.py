""" Data model for the Plutas platform. Defines Sequelize/ORM schema and table mapping.

 @file analyzer-model/models/models_v1/heat_coldwave_model_version1.py
"""

"""
This module processes temperature data to calculate insurance strikes and payouts
for different levels (silver, gold, platinum). It involves data aggregation, 
strike threshold calculation, payout assignment, and summary generation for each level.

Key functionalities:
- Calculate strike thresholds using percentiles.
- Assign payouts based on strikes and temperature ranges.
- Summarize payout and strike data into a JSON-like structure.
- Process data for multiple pincodes.

Dependencies: pandas, numpy, datetime, pytz, psycopg2, math
"""

import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import psycopg2
import math

# Calculate strike thresholds based on percentiles
def calculate_strikes(data, strike_percentile, exit_percentile):
    """
    Calculate strike and exit thresholds using percentiles of the Index column.
    If the strike and exit thresholds are the same, the exit threshold is incremented by 1.

    Args:
        data (DataFrame): Input data with an "Index" column.
        strike_percentile (float): Percentile for strike threshold (0-1).
        exit_percentile (float): Percentile for exit threshold (0-1).

    Returns:
        dict: Strike and exit thresholds.
    """
    strike = np.percentile(data["Index"], strike_percentile * 100)
    exit = np.percentile(data["Index"], exit_percentile * 100)
    
    if strike == exit:
        exit = exit + 1
    strike = round(strike, 1)
    exit = round(exit, 1)

    return {"strike": strike, "exit": exit}
    return {"strike": strike, "exit": exit}

# Calculate payouts based on strikes and temperature ranges
def calculate_payouts(data, strikes, payout1, payout2):
    """
    Assign payout costs for each insurance level (silver, gold, platinum) 
    based on temperature ranges and predefined strike thresholds.

    Args:
        data (DataFrame): Input data with "Min_Temp" column.
        strikes (dict): Strike and exit thresholds for each level.
        payout1 (float): Partial payout amount.
        payout2 (float): Full payout amount.

    Returns:
        DataFrame: Updated data with calculated payout columns.
    """
    # Assign payouts for "silver" level
    data = data.assign(
        silver_pay_cost=np.where(
            (data["Min_Temp"] >= strikes["silver"]["strike"]) & (data["Min_Temp"] < strikes["silver"]["exit"]),
            payout1,
            np.where(data["Min_Temp"] >= strikes["silver"]["exit"], payout2, 0),
        ),
        # Assign payouts for "gold" level
        gold_pay_cost=np.where(
            (data["Min_Temp"] >= strikes["gold"]["strike"]) & (data["Min_Temp"] < strikes["gold"]["exit"]),
            payout1,
            np.where(data["Min_Temp"] >= strikes["gold"]["exit"], payout2, 0),
        ),
        # Assign payouts for "platinum" level
        platinum_pay_cost=np.where(
            (data["Min_Temp"] >= strikes["platinum"]["strike"]) & (data["Min_Temp"] < strikes["platinum"]["exit"]),
            payout1,
            np.where(data["Min_Temp"] >= strikes["platinum"]["exit"], payout2, 0),
        ),
    )
    return data

# Process data for a specific pincode
def process_pincode(data, pincode, user_inputs, product_defaults):
    """
    Process temperature data for a specific pincode to calculate strike thresholds and payouts.

    Args:
        data (DataFrame): Weather data with columns like "date", "pincode", "Min_Temp".
        pincode (str): Target pincode for processing.
        user_inputs (dict): User-provided inputs including risk dates and insured amount.
        product_defaults (dict): Product default parameters for calculations.

    Returns:
        tuple: Payout data (DataFrame) and strike thresholds (dict).
    """
    risk_start_date = user_inputs["riskStartDate"]
    risk_end_date = user_inputs["riskEndDate"]

    timezone = pytz.timezone("Asia/Kolkata")  # Set the timezone for calculations
    strikes_data = pd.DataFrame()  # DataFrame to store strike thresholds
    payout_data = pd.DataFrame()  # DataFrame to store calculated payouts

    # Determine year range in the dataset
    min_year, max_year = data["date"].dt.year.min(), data["date"].dt.year.max()

    # Iterate through each year in the range
    for year in range(min_year, max_year + 1):
        # Define the season start and end dates
        season_start = timezone.localize(datetime.strptime(f"{year}-{risk_start_date[5:]}", "%Y-%m-%d"))
        
        # For season_end, adjust to the next year
        season_end_year = year + 1 if int(risk_end_date[:4]) > int(risk_start_date[:4]) else year
        season_end = timezone.localize(datetime.strptime(f"{season_end_year}-{risk_end_date[5:]}", "%Y-%m-%d"))
        
        # print to verify values before comparison
        # print(f"Year: {year}, season_start: {season_start}, season_end: {season_end}")
        
        if season_start > season_end:
            new_year = season_end.year + 1
            new_month = season_end.month
            new_day = season_end.day
            
            # Check if February 29 needs adjustment
            if new_month == 2 and new_day == 29 and not calendar.isleap(new_year):
                # Adjust to February 28 for non-leap years
                season_end = timezone.localize(datetime(new_year, 2, 28))
            else:
                # Default case
                season_end = season_end.replace(year=new_year)
            
            # print(f"Year: {year}, Updated season_start: {season_start.strftime('%Y-%m-%d')}, Updated season_end: {season_end.strftime('%Y-%m-%d')}")
        # else:
            # print(f"Year: {year}, season_start: {season_start.strftime('%Y-%m-%d')}, season_end: {season_end.strftime('%Y-%m-%d')}")
        
        # print(f"Adjusted season_start: {season_start}, season_end: {season_end}")

        season_start, season_end = season_start.replace(tzinfo=None), season_end.replace(tzinfo=None)

        # Filter data for the current year and pincode
        year_data = data[(data["date"] >= season_start) & (data["date"] <= season_end) & (data["pincode"] == pincode)]

        if not year_data.empty:  # If data is present for the year
            # Calculate the maximum temperature and add year information
            Min_Temp_strike = year_data.groupby("pincode", as_index=False)["Min_Temp"].max().rename(columns={"Min_Temp": "Index"})
            Min_Temp_strike["Year"] = year
            strikes_data = pd.concat([strikes_data, Min_Temp_strike], ignore_index=True)

    if strikes_data.empty:  # If no strike data is found
        raise ValueError(f"No valid strike data found for pincode {pincode}")

    # Calculate strikes for each insurance level
    strikes = {
        "silver": calculate_strikes(strikes_data, product_defaults["plan_details"][0]["silver_strike1"], product_defaults["plan_details"][0]["silver_exit"]),
        "gold": calculate_strikes(strikes_data, product_defaults["plan_details"][0]["gold_strike1"], product_defaults["plan_details"][0]["gold_exit"]),
        "platinum": calculate_strikes(strikes_data, product_defaults["plan_details"][0]["platinum_strike1"], product_defaults["plan_details"][0]["platinum_exit"]),
    }


    # Define payout amounts
    payout1 = product_defaults["payout_percentage"] * user_inputs["sumInsured"]
    payout2 = user_inputs["sumInsured"]

    # Calculate payouts for each year
    for year in range(min_year, max_year + 1):
        # Define the season start and end dates
        season_start = timezone.localize(datetime.strptime(f"{year}-{risk_start_date[5:]}", "%Y-%m-%d"))
        
        # For season_end, adjust to the next year
        season_end_year = year + 1 if int(risk_end_date[:4]) > int(risk_start_date[:4]) else year
        season_end = timezone.localize(datetime.strptime(f"{season_end_year}-{risk_end_date[5:]}", "%Y-%m-%d"))
        
        # print to verify values before comparison
        # print(f"Year: {year}, season_start: {season_start}, season_end: {season_end}")
        
        if season_start > season_end:
            new_year = season_end.year + 1
            new_month = season_end.month
            new_day = season_end.day
            
            # Check if February 29 needs adjustment
            if new_month == 2 and new_day == 29 and not calendar.isleap(new_year):
                # Adjust to February 28 for non-leap years
                season_end = timezone.localize(datetime(new_year, 2, 28))
            else:
                # Default case
                season_end = season_end.replace(year=new_year)
            
            # print(f"Year: {year}, Updated season_start: {season_start.strftime('%Y-%m-%d')}, Updated season_end: {season_end.strftime('%Y-%m-%d')}")
        # else:
            # print(f"Year: {year}, season_start: {season_start.strftime('%Y-%m-%d')}, season_end: {season_end.strftime('%Y-%m-%d')}")
        
        # print(f"Adjusted season_start: {season_start}, season_end: {season_end}")

        season_start, season_end = season_start.replace(tzinfo=None), season_end.replace(tzinfo=None)


        # Filter data for the current season and pincode
        year_data = data[(data["date"] >= season_start) & (data["date"] <= season_end) & (data["pincode"] == pincode)]
        if not year_data.empty:  # If data is present
            # Calculate payouts based on temperature ranges and strikes
            year_data = calculate_payouts(year_data, strikes, payout1, payout2)
            # Aggregate payouts by geographical levels
            burn_cost = year_data.groupby(["state", "district", "pincode"], as_index=False).agg(
                {col: "sum" for col in ["silver_pay_cost", "gold_pay_cost", "platinum_pay_cost"]}
            )
            burn_cost["Year"] = year
            payout_data = pd.concat([payout_data, burn_cost], ignore_index=True)

    return payout_data, strikes  # Return calculated payout data and strike thresholds

# Create JSON-like summary for payouts and strikes
def create_level_summary(payout_data, strikes, product_defaults, user_inputs):
    """
    Summarize payouts and strike information for each insurance level.

    Args:
        payout_data (DataFrame): Calculated payout data for different levels.
        strikes (dict): Strike thresholds for each level.
        product_defaults (dict): Default parameters for calculations.
        user_inputs (dict): User inputs including insured amount.

    Returns:
        list: JSON-like structure summarizing payout and strike data for each level.
    """
    levels = ["silver", "gold", "platinum"]  # Define the insurance levels
    # Define variability factors for each level
    # data_variability = {
    #     "silver": product_defaults["data_variability_silver"],
    #     "gold": product_defaults["data_variability_gold"],
    #     "platinum": product_defaults["data_variability_platinum"],
    # }
    data_variability = {
        "silver": product_defaults["data_variability"],
        "gold": product_defaults["data_variability"] + 0.02,
        "platinum": product_defaults["data_variability"] + 0.04,
    }

    formatted_output = []  # Initialize a list to store formatted summaries

    # Iterate through each insurance level
    for level in levels:
        level_column = f"{level}_pay_cost"  # Column name for the current level's payouts
        # Calculate average and standard deviation of burn costs
        average_burn_cost = np.nan_to_num(payout_data[level_column].mean(), nan=0.0)
        std_dev_burn_cost = np.nan_to_num(payout_data[level_column].std(), nan=0.0)
        # Calculate risk premium percentage as a ratio of average burn cost to the sum insured
        risk_premium_percentage = np.nan_to_num(average_burn_cost / user_inputs["sumInsured"], nan=0.0)
        # Calculate the net risk premium rate
        net_risk_premium_rate = np.nan_to_num(
            (risk_premium_percentage / product_defaults["priced_loss_ration"])
            * (1 + data_variability[level])
            / (1 - product_defaults["management_loading"]),
            nan=0.0,
        )
        # Calculate the base premium
        base_premium = net_risk_premium_rate * user_inputs["sumInsured"]

        # Generate year-wise statistics for the current level
        statistics = [
            {
                "year": int(row["Year"]),
                "totalBurnCost": np.nan_to_num(row[level_column], nan=0.0),
            }
            for _, row in payout_data.iterrows()
        ]
        coverage_details = {
            "partialCoverage": f"{int(product_defaults['payout_percentage'] * 100)}% coverage for damages caused by heat exceeding {strikes[level]['strike']} °C ",
            "fullCoverage": f"100% coverage for damages caused by rainfall exceeding {strikes[level]['exit']} °C ",
        }

        # Append a formatted summary for the current level
        formatted_output.append({
            "pincode": payout_data["pincode"].iloc[0],  # Pincode for the data
            "level": level,  # Current insurance level
            "strike": f"{strikes[level]['strike']} °C",  # Strike threshold
            "exit": f"{strikes[level]['exit']} °C",  # Exit threshold
            "averageBurnCost": average_burn_cost,
            "standardDeviationBurnCost": std_dev_burn_cost,
            "standardDeviationPercent": std_dev_burn_cost / average_burn_cost if average_burn_cost > 0 else 0,
            "riskPremiumPercentage": risk_premium_percentage,
            "netRiskPremiumRate": net_risk_premium_rate,
            "sum_insured": user_inputs["sumInsured"],
            "basePremium": base_premium,
            "dataVariability": data_variability[level],
            "coverageDetails": coverage_details,
            "statistics": statistics,
        })

    return formatted_output  

# Process data for all pincodes
def process_data(user_inputs, product_defaults, data):
    """
    Process temperature data for all pincodes and generate final formatted outputs.

    Args:
        user_inputs (dict): User-provided inputs such as risk dates and insured amount.
        product_defaults (dict): Default parameters for insurance calculations.
        data (DataFrame): Weather data containing columns like "date", "pincode", "Min_Temp".

    Returns:
        list: JSON-like structure summarizing results for all pincodes.
    """
    try:
        data["date"] = pd.to_datetime(data["date"])  # Ensure the "date" column is in datetime format
        pincodes = data["pincode"].unique()  # Extract unique pincodes from the data
        all_formatted_output = []  # Initialize a list to store results for all pincodes

        # Process each pincode individually
        for pincode in pincodes:
            # Calculate payouts and strikes for the current pincode
            payout_data, strikes = process_pincode(data, pincode, user_inputs, product_defaults)
            # Create a summary for the processed data
            formatted_output = create_level_summary(payout_data, strikes, product_defaults, user_inputs)
            # Append the formatted output to the overall results
            all_formatted_output.extend(formatted_output)

        print("Processing completed successfully!")  # Log the successful processing
        return all_formatted_output  # Return the final results

    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Log any errors encountered during processing
        return None  # Return None in case of an error

# Main function to execute heat strike calculations
def execute_heat_strike_calculation(user_inputs, product_defaults, data):
    """
    Wrapper function to execute the heat strike calculation process.

    Args:
        user_inputs (dict): User-provided inputs including insured amount and risk dates.
        product_defaults (dict): Default parameters for insurance calculations.
        data (DataFrame): Weather data containing columns like "date", "pincode", "Min_Temp".

    Returns:
        list: JSON-like structure summarizing results for all pincodes.
    """
    return process_data(user_inputs, product_defaults, data)  # Delegate to the main processing function
