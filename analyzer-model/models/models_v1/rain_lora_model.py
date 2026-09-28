""" Data model for the Plutas platform. Defines Sequelize/ORM schema and table mapping.

 @file analyzer-model/models/models_v1/rain_lora_model.py
"""

import os
import pandas as pd
import numpy as np
import logging
import pytz
import calendar  
from datetime import datetime

# Dynamic year and season calculation
def get_year_range_and_seasons(data, risk_start_date, risk_end_date, timezone=pytz.timezone("Asia/Kolkata")):
    
    # Convert the 'date' column to timezone-aware
    data["date"] = pd.to_datetime(data["date"]).dt.tz_convert(timezone)

    min_year = data["date"].dt.year.min()
    max_year = min_year + 29  
    season_ranges = []

    for year in range(min_year, max_year + 1):
        season_start = timezone.localize(datetime.strptime(f"{year}-{risk_start_date[5:]}", "%Y-%m-%d"))
        season_end_year = year + 1 if int(risk_end_date[:4]) > int(risk_start_date[:4]) else year
        season_end = timezone.localize(datetime.strptime(f"{season_end_year}-{risk_end_date[5:]}", "%Y-%m-%d"))

        if season_start > season_end:
            new_year = season_end.year + 1
            new_month = season_end.month
            new_day = season_end.day

            if new_month == 2 and new_day == 29 and not calendar.isleap(new_year):
                season_end = timezone.localize(datetime(new_year, 2, 28))
            else:
                season_end = season_end.replace(year=new_year)

        season_ranges.append((season_start, season_end))

    return range(min_year, max_year + 1), season_ranges


# Initialize Constants
def initialize_constants(user_inputs, product_defaults):
    return {
        "Silver_Percentile": {
            "strikePercentile": product_defaults["silver_plan"][0]["silver_strike"],
            "exitPercentile": product_defaults["silver_plan"][0]["silver_exit"]
        },
        "Gold_Percentile": {
            "strikePercentile": product_defaults["gold_plan"][0]["gold_strike"],
            "exitPercentile": product_defaults["gold_plan"][0]["gold_exit"]
        },
        "Platinum_Percentile": {
            "strikePercentile": product_defaults["platinum_plan"][0]["platinum_strike"],
            "exitPercentile": product_defaults["platinum_plan"][0]["platinum_exit"]
        },
        "Silver_Min_threshold": {
            "silver_min_threshold_strike": product_defaults["silver_plan"][0]["silver_threshold_strike"],
            "silver_min_threshold_exit": product_defaults["silver_plan"][0]["silver_threshold_exit"]
        },
        "Gold_Min_threshold": {
            "gold_min_threshold_strike": product_defaults["gold_plan"][0]["gold_threshold_strike"],
            "gold_min_threshold_exit": product_defaults["gold_plan"][0]["gold_threshold_exit"]
        },
        "Platinum_Min_threshold": {
            "platinum_min_threshold_strike": product_defaults["platinum_plan"][0]["platinum_threshold_strike"],
            "platinum_min_threshold_exit": product_defaults["platinum_plan"][0]["platinum_threshold_exit"]
        },
        "management_loading": {
            "Silver": product_defaults["silver_plan"][0]["silver_management_loading"],
            "Gold": product_defaults["gold_plan"][0]["gold_management_loading"],
            "Platinum": product_defaults["platinum_plan"][0]["platinum_management_loading"]
        },
        "data_variability": {
            "Silver": product_defaults["silver_plan"][0]["silver_data_variability"],
            "Gold": product_defaults["gold_plan"][0]["gold_data_variability"],
            "Platinum": product_defaults["platinum_plan"][0]["platinum_data_variability"]
        },
        "priced_Loss_Ratio": {
            "Silver": product_defaults["silver_plan"][0]["silver_priced_loss_ratio"],
            "Gold": product_defaults["gold_plan"][0]["gold_priced_loss_ratio"],
            "Platinum": product_defaults["platinum_plan"][0]["platinum_priced_loss_ratio"]
        },
        "delta": {
            "Silver": product_defaults["silver_plan"][0]["silver_strike_exit_delta"],
            "Gold": product_defaults["gold_plan"][0]["gold_strike_exit_delta"],
            "Platinum": product_defaults["platinum_plan"][0]["platinum_strike_exit_delta"]
        },
        "base_premium_percentage" : {
            "Silver": product_defaults["silver_plan"][0]["silver_base_premium"],
            "Gold": product_defaults["gold_plan"][0]["gold_base_premium"],
            "Platinum": product_defaults["platinum_plan"][0]["platinum_base_premium"]
        },
        "Notional_percent": product_defaults["payout_percentage"],
        "premium_difference_percent": product_defaults["premium_difference_percent"],
        "sumInsured": int(user_inputs["sumInsured"]),
        "risk_start_date": user_inputs["riskStartDate"],
        "risk_end_date": user_inputs["riskEndDate"],
        "radius": user_inputs["radius"],
        "pincodes": user_inputs["pincodes"],
    }


# Calculate Strike and Exit Values
def calculate_thresholds(strikes_data, percentiles, delta, min_thresholds, level):
    
    print(f"\nCalculating {level} Thresholds...")
    print("Raw Strikes Data:", strikes_data)
    
    strike_value = int(np.ceil(np.percentile(strikes_data, percentiles['strikePercentile'] * 100)))
    exit_value = int(np.ceil(np.percentile(strikes_data, percentiles['exitPercentile'] * 100)))
    print(f"Percentile-Based Strike: {strike_value}, Exit: {exit_value}")
    
    min_strike = min_thresholds[f"{level.lower()}_min_threshold_strike"]
    min_exit = min_thresholds[f"{level.lower()}_min_threshold_exit"]
    print(f"Min Strike Threshold: {min_strike}, Min Exit Threshold: {min_exit}")
    
    if strike_value < min_strike:
        print(f"Adjusting Strike Value to Min Threshold: {min_strike}")
        strike_value = min_strike
    
    if exit_value < min_exit:
        print(f"Adjusting Exit Value to Min Threshold: {min_exit}")
        exit_value = min_exit

    if exit_value == strike_value:
        print(f"Adjusting Exit Value: {exit_value} <= Strike Value ({strike_value})")
        exit_value = strike_value + delta
    
    
    print(f"Final {level} Thresholds -> Strike: {strike_value}, Exit: {exit_value}\n")
    
    return {"strike": strike_value, "exit": exit_value}

def calculate_payout_percentage(start_date_str, end_date_str):
    """Calculates payout percentage based on coverage days."""
    start_date = pd.to_datetime(start_date_str)
    end_date = pd.to_datetime(end_date_str)
    coverage_days = (end_date - start_date).days + 1

    print("--------------------------------") 
    print("Start date:", start_date)
    print("End date:", end_date)
    print("Coverage days:", coverage_days)

    if coverage_days <= 0:
        raise ValueError("Risk period end date must be after start date.")

    payout_percentage = 1.0 / coverage_days
    payout_percentage_formatted = round(payout_percentage * 100, 2)

    print(f"Calculated payout percentage in decimal: {payout_percentage:.4f}")
    print(f"Payout percentage: {payout_percentage_formatted:.2f}%")
    
    return payout_percentage_formatted

# Calculate Payout
def calculate_payouts(index_value, thresholds, constants):
    """
    Calculate the payout based on index_value(rainfall), thresholds, and constants.
    Args:
        index_value (float): The observed index value.
        thresholds (dict): Contains 'exit' and 'strike' threshold values.
        constants (dict): Contains payout-related constants like 'sumInsured' and 'Notional_percent'.
    Returns:
        float: The calculated burn cost.
    """
    # Calculate payout percentage and values    
    payout_percentage = calculate_payout_percentage(constants["risk_start_date"], constants["risk_end_date"])
    print("calculated payout_percentage",payout_percentage)
    print("Sum Insured:", constants["sumInsured"])

    print("payout_percentage", payout_percentage)
    print("userInputs_sumInsured", constants["sumInsured"])
    payout1 = constants["sumInsured"] * (payout_percentage / 100)

    # payout1 = constants['sumInsured'] * payout_percentage
    payout2 = constants['sumInsured']
    print(payout1, payout2)
    payout_cost1 = 0  
    payout_cost2 = 0  


    if thresholds["exit"] < index_value <= thresholds["strike"]:
        payout_cost1 = payout1  # Condition 1: Within exit & strike range
    
    if index_value <= thresholds["exit"]:
        payout_cost2 = payout2  # Condition 2: Less than or equal to exit

    # Total Burn Cost
    burn_cost = round(payout_cost1 + payout_cost2, 2)
    return burn_cost


# Generate rainfall Statistics
def get_rainfall_statistics(data):
    # Ensure 'date' is a datetime type
    data['date'] = pd.to_datetime(data['date'])
    # Group by year and get sum of rainfall
    yearly_rainfall = data.groupby(data['date'].dt.year)['rainfall'].sum().reset_index()
    # Rename columns for clarity
    yearly_rainfall.columns = ["year", "Sum_of_Rainfall"]
    # Sort by Total_Rainfall in ascending order (smallest rainfall first) and get the top 10
    top_10_min_rainfall = yearly_rainfall.nsmallest(10, 'Sum_of_Rainfall')
    # Convert to list of dictionaries
    yearly_statistics = top_10_min_rainfall.to_dict(orient="records")
    return yearly_statistics

# ** JSON Serialization **
def sanitize_json(data):
    if isinstance(data, dict):
        return {k: sanitize_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json(v) for v in data]
    elif isinstance(data, float):
        return 0.0 if np.isnan(data) or np.isinf(data) else data
    return data

# Process Data and Generate JSON Output
def process_data(user_inputs, product_defaults, data, pincodes, dataSource, formatted_gridPoints):
    constants = initialize_constants(user_inputs, product_defaults)
    primary_pincode = constants["pincodes"]
    strikes_data = []
    risk_start_date = constants['risk_start_date']
    risk_end_date = constants['risk_end_date']

    years, season_ranges = get_year_range_and_seasons(data, risk_start_date, risk_end_date)

    # Ensure all dates in data are timezone-aware
    timezone = pytz.timezone("Asia/Kolkata")
    data["date"] = pd.to_datetime(data["date"]).dt.tz_convert(timezone)

    print(years, season_ranges)
    print(primary_pincode)

    for year in years:
        print(year)

        # Extract only month & day from risk_start_date & risk_end_date
        season_start = timezone.localize(datetime.strptime(f"{year}-{risk_start_date[5:]}", "%Y-%m-%d"))
        season_end_year = year + 1 if int(risk_end_date[:4]) > int(risk_start_date[:4]) else year
        season_end = timezone.localize(datetime.strptime(f"{season_end_year}-{risk_end_date[5:]}", "%Y-%m-%d"))

        # Ensure season_end is always after season_start
        if season_start > season_end:
            season_end = season_end.replace(year=season_end.year + 1)

        # Debugging: Check the min/max years and dates in dataset
        min_year = data['date'].dt.year.min()
        max_year = data['date'].dt.year.max()
        min_date = data['date'].min()
        max_date = data['date'].max()

        data["pincode"] = data["pincode"].astype(str)  

        dt = data[
            (data["date"] >= season_start) & 
            (data["date"] <= season_end) & 
            (data['pincode'].astype(str).isin(primary_pincode))
        ] 

        total_rainfall = dt["rainfall"].sum() 

        strikes_data.append(total_rainfall)
    
    # Calculate thresholds for each level
    thresholds = {
        level: calculate_thresholds(
            strikes_data,
            constants[f"{level}_Percentile"],
            constants["delta"][level],
            constants[f"{level}_Min_threshold"],
            level
        )
        for level in ["Silver", "Gold", "Platinum"]
    }
    # Generate burn costs for each year
    payout_data = []
    for year, index_value in zip(years, strikes_data):
        payout_data.append({
            "Year": year,
            "Silver_burncost": calculate_payouts(index_value, thresholds["Silver"], constants),
            "Gold_burncost": calculate_payouts(index_value, thresholds["Gold"], constants),
            "Platinum_burncost": calculate_payouts(index_value, thresholds["Platinum"], constants)
        })

    # Convert payout_data to DataFrame
    payout_df = pd.DataFrame(payout_data)
    print(payout_df)
    # Generate rainfall statistics
    yearly_statistics = get_rainfall_statistics(data)

    output_json = []

    for level in ["Silver", "Gold", "Platinum"]:
        column_name = level + "_burncost"

        # Extract non-NaN burn cost values
        burn_costs_values = payout_df[column_name].dropna().tolist()

        # Sum of burn costs
        burn_costs_sum = np.nansum(burn_costs_values)

        # Count of non-NaN values
        count = len(burn_costs_values)

        # Compute average burn cost
        avg_burn_cost = burn_costs_sum / count if count > 0 else None  

        # Compute standard deviation using DataFrame directly
        std_dev = payout_df[column_name].std(skipna=True)

        print(f"{level} - Avg Burn Cost: {avg_burn_cost}, Std Dev: {std_dev}")
        std_dev_percent = (std_dev / constants['sumInsured']) * 100  
        risk_premium =  avg_burn_cost / constants['sumInsured']
        net_risk_premium_rate = ((risk_premium / constants['priced_Loss_Ratio'][level]) * (1 + constants['data_variability'][level]) / (1 - constants['management_loading'][level]) if constants['priced_Loss_Ratio'][level] > 0 and (1 - constants['management_loading'][level]) > 0 else 0.0)

        print("net_risk_premium_rate---------", net_risk_premium_rate)
        base_premium = net_risk_premium_rate * constants["sumInsured"]
        print(f"  - Base Premium: {base_premium}")
        directus_base_premium = constants['base_premium_percentage'][level]
        print(f"  - Directus Base Premium: {directus_base_premium}")
        print(f" -directus_base_premium * constants['sumInsured'] : {directus_base_premium * constants['sumInsured']}")
        # If base premium is zero or less than the threshold, adjust it
        if base_premium == 0 or base_premium < (directus_base_premium * user_inputs['sumInsured']):
            print(f"Base premium is zero or less than directus_base_premium threshold. Adjusting net risk premium rate and recalculating base premium, based on directus_base_premium {directus_base_premium}")

            # Adjust net risk premium rate and base premium
            net_risk_premium_rate = directus_base_premium  
            base_premium = directus_base_premium * user_inputs['sumInsured']  # Directly set the minimum required value

            print(f"  - Adjusted Net Risk Premium Rate: {net_risk_premium_rate}")
            print(f"  - Final Adjusted Base Premium: {base_premium}")

        payout_percentage = calculate_payout_percentage(constants["risk_start_date"], constants["risk_end_date"])
        print("calculated payout_percentage",payout_percentage)

        coverage_details = {
            "partialCoverage": f"{payout_percentage}% coverage for damages caused by rainfall below {thresholds[level]['strike']} mm.",
            "fullCoverage": f"100% coverage for damages caused by rainfall below {thresholds[level]['exit']} mm."
        }

        output_json.append({
            "riskStartDate": user_inputs['riskStartDate'],
            "riskEndDate": user_inputs['riskEndDate'],
            "pincode": list(map(str, constants["pincodes"])),
            "additionalPincodes": pincodes,
            "radius": constants['radius'],
            "level": level,
            "strike": f"{thresholds[level]['strike']} mm",
            "exit": f"{thresholds[level]['exit']} mm",
            "averageBurnCost": avg_burn_cost,
            "standardDeviationBurnCost": std_dev,
            "standardDeviationPercent": std_dev_percent,
            "riskPremiumPercentage": risk_premium,
            "netRiskPremiumRate": net_risk_premium_rate,
            "sumInsured": constants['sumInsured'],
            "basePremium": base_premium,
            "dataVariability": constants["data_variability"][level],
            "managementLoading": constants["management_loading"][level],
            "delta": constants["delta"][level],
            "pricedLossRatio": constants["priced_Loss_Ratio"][level],
            "calculatedPayoutPercentage": payout_percentage,
            "levelPercentiles": constants[f"{level}_Percentile"],
            "coverageDetails": coverage_details,
            "dataSource": dataSource,
            "gridPoints": formatted_gridPoints,
            "statistics": yearly_statistics
        })
    output_json = sanitize_json(output_json)
    return output_json

# Execute Rain Strike Calculation
async def execute_rain_strike_calculation(user_inputs, product_defaults, data, dataSource, additional_pincodes):
    print("Processing additional pincodes...")

    if isinstance(additional_pincodes, list):
        additional_pincodes = pd.DataFrame(additional_pincodes, columns=['pincode'])

    additional_pincodes['pincode'] = additional_pincodes['pincode'].astype(str)
    unique_pincodes = additional_pincodes['pincode'].unique().tolist()
    
    primary_pincode = str(user_inputs['pincodes'][0])
    processed_pincodes = [p for p in unique_pincodes if p != primary_pincode]

    gridPoints = data['coord_25x25'].dropna().unique().tolist()
    formatted_gridPoints = [f"{float(point.split(',')[0])}°{'N' if float(point.split(',')[0]) >= 0 else 'S'} "
                            f"{float(point.split(',')[1])}°{'E' if float(point.split(',')[1]) >= 0 else 'W'}"
                            for point in gridPoints]
    return process_data(user_inputs, product_defaults, data, processed_pincodes, dataSource, formatted_gridPoints)
