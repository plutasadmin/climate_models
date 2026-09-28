""" Data model for the Plutas platform. Defines Sequelize/ORM schema and table mapping.

 @file analyzer-model/models/rain_sinhira_model.py
"""

"""
Module for processing heat strike calculations and payouts based on weather data.

This module includes functions for calculating strikes, payouts, and formatting
results for insurance premium calculations. The processing involves multiple 
levels (silver, gold, platinum) and considers dynamic strike and payout thresholds.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.parser import parse
import pytz
from math import ceil
def calculate_thresholds(data, percentiles, delta, min_threshold):
    print("data------", data)
    
    # Ensure we're working with the 'Index' column (which contains your rainfall values)
    if isinstance(data, pd.DataFrame):
        if 'Index' not in data.columns:
            raise ValueError("DataFrame must contain an 'Index' column with rainfall values")
        numeric_data = pd.to_numeric(data['Index'], errors='coerce').dropna()
    else:
        # Handle case where data might be a Series or array-like
        numeric_data = pd.to_numeric(data, errors='coerce').dropna()
    
    if len(numeric_data) == 0:
        raise ValueError("No valid numeric data available for threshold calculation")
    
    strike_value = round(np.percentile(numeric_data, percentiles['strikePercentile'] * 100), 0)
    # exit_value = int(round(np.percentile(numeric_data, percentiles['exitPercentile'] * 100), 5))
    
    print(f"Strike value: {strike_value}")
    print(f"Min threshold for strike: {min_threshold['strike']}")
    
    # Ensure STRIKE >= 0 AND STRIKE > MIN_STRIKE
    if strike_value < min_threshold["strike"]:
        strike_value = min_threshold["strike"]


    return {"strike": strike_value}



def adjust_risk_period_dates(user_inputs,product_defaults):

    # Parse dates
    try:
        start_date = parse(user_inputs["riskStartDate"])
        end_date = parse(user_inputs["riskEndDate"])
    except Exception as e:
        raise ValueError(f"Invalid date format in userInputs: {e}")
    max_number_of_days=product_defaults["max_number_of_days"]
    print("max_number_of_days", max_number_of_days)
    # Calculate original risk period duration
    days_count = (end_date - start_date).days + 1

    # Determine adjustment based on days count
    pricing_default_date = 30

    if days_count < pricing_default_date:
        x = ceil((pricing_default_date - days_count) / 2)
        revised_start_date = start_date - timedelta(days=x)
        revised_end_date = end_date + timedelta(days=x)

    elif days_count > max_number_of_days:
        x = ceil((days_count - max_number_of_days) / 2)
        revised_start_date = start_date + timedelta(days=x)
        revised_end_date = end_date - timedelta(days=x)

    else:
        x = 0
        revised_start_date = start_date
        revised_end_date = end_date

    # Recalculate revised duration
    revised_days_count = (revised_end_date - revised_start_date).days + 1

    # Format dates
    formatted_start_date = revised_start_date.strftime("-%m-%d")
    formatted_end_date = revised_end_date.strftime("-%m-%d")

    # Pricing calculations
    sum_insured = user_inputs['sumInsured']
    per_day = round(sum_insured / days_count)
    calculated_sum_insured = per_day * revised_days_count
    payout_percentage = 1 / revised_days_count

    # Prepare result
    result = {
        'original_start_date': start_date.strftime('%Y-%m-%d'),
        'original_end_date': end_date.strftime('%Y-%m-%d'),
        'days_count': days_count,
        'added_days_each_side': x,
        'revised_start_date': revised_start_date.strftime('%Y-%m-%d'),
        'revised_end_date': revised_end_date.strftime('%Y-%m-%d'),
        'revised_days_count': revised_days_count,
        'formatted_start_date': formatted_start_date,
        'formatted_end_date': formatted_end_date,
        'per_day_amount': per_day,
        'calculated_sum_insured': calculated_sum_insured,
        'payout_percentage': payout_percentage
    }
    print("result",result)
    return result

def calculate_payouts(data, thresholds, user_inputs, product_defaults):
    data = data.copy()

    # Get risk period calculations
    results = adjust_risk_period_dates(user_inputs,product_defaults)
    print("------------------")
    payout_percentage = results['payout_percentage']
    calculated_sum_insured = results['calculated_sum_insured']

    print("\n=== Payout Calculation ===")
    print("Payout Percentage:", payout_percentage)
    print("Calculated Sum Insured:", calculated_sum_insured)

    # Sample payout logic (modify as per business rules)
    payout1 = int(calculated_sum_insured * payout_percentage)# / 100)  # if needed as %
    payout2 = calculated_sum_insured

    payouts = {
        "payout1": payout1,
        "payout2": payout2,
    }
    print("Payouts:", payouts)

    # Apply payout logic dynamically for each level    
    for level, threshold in thresholds.items():
        print(f"\n--- Debug: Level '{level}' with threshold {threshold} ---")
        data[f"{level}_payout"] = np.where(
            data["rainfall"] >= threshold["strike"],
            payouts["payout1"],
            0
        )

    return data


def calculate_max_rainfall(data, primary_pincodes):
    """Calculates the maximum rainfall per date."""
    data["date"] = pd.to_datetime(data["date"])
    primary_pincodes = [str(p) for p in primary_pincodes]

    max_rainfall_per_date = data.groupby("date", as_index=False)["rainfall"].max()
    max_rainfall_per_date["pincode"] = primary_pincodes[0]  
    return max_rainfall_per_date


def process_data(user_inputs, product_defaults, data, additional_pincodes, dataSource, gridPoints):
    primary_pincodes = user_inputs["pincodes"]  
    print("Primary pincodes:", primary_pincodes)

    if not isinstance(primary_pincodes, list):
        primary_pincodes = [primary_pincodes]

    # Count unique pincodes in data
    unique_pincode_count = data["pincode"].nunique()
    print("Unique pincodes in data:", unique_pincode_count)

    # Call calculate_rainfall only if there's more than one pincode
    if unique_pincode_count > 1:
        data = calculate_max_rainfall(data, primary_pincodes)
    else:
        print("Skipping calculate_rainfall as there is only one unique pincode in the data.")

    pincodes = data["pincode"].unique()  
    print("Unique pincodes in data:", pincodes)
    results = adjust_risk_period_dates(user_inputs,product_defaults)
    risk_end_date = results['revised_end_date']
    risk_start_date = results['revised_start_date']
    sumInsured = results['calculated_sum_insured']

    delta = {
        "silver": product_defaults["silver_plan"][0]["silver_strike_exit_delta"],
        "gold": product_defaults["gold_plan"][0]["gold_strike_exit_delta"],
        "platinum": product_defaults["platinum_plan"][0]["platinum_strike_exit_delta"]
    }
    base_premium_percentage = {
        "silver": product_defaults["silver_plan"][0]["silver_base_premium"],
        "gold": product_defaults["gold_plan"][0]["gold_base_premium"],
        "platinum": product_defaults["platinum_plan"][0]["platinum_base_premium"]
    }
    data_variability = {
        "silver": product_defaults["silver_plan"][0]["silver_data_variability"],
        "gold": product_defaults["gold_plan"][0]["gold_data_variability"],
        "platinum": product_defaults["platinum_plan"][0]["platinum_data_variability"]
    }

    priced_loss_ratio = {
        "silver": product_defaults["silver_plan"][0]["silver_priced_loss_ratio"],
        "gold": product_defaults["gold_plan"][0]["gold_priced_loss_ratio"],
        "platinum": product_defaults["platinum_plan"][0]["platinum_priced_loss_ratio"]
    }
    management_loading = {
        "silver": product_defaults["silver_plan"][0]["silver_management_loading"],
        "gold": product_defaults["gold_plan"][0]["gold_management_loading"],
        "platinum": product_defaults["platinum_plan"][0]["platinum_management_loading"]
    }
    min_threshold = {
        "silver": {"strike": product_defaults["silver_plan"][0]["silver_threshold_strike"], "exit": product_defaults["silver_plan"][0]["silver_threshold_exit"]},
        "gold": {"strike": product_defaults["gold_plan"][0]["gold_threshold_strike"], "exit": product_defaults["gold_plan"][0]["gold_threshold_exit"]},
        "platinum": {"strike": product_defaults["platinum_plan"][0]["platinum_threshold_strike"], "exit": product_defaults["platinum_plan"][0]["platinum_threshold_exit"]},
    }

    percentiles = {
        "silver": {"strikePercentile": product_defaults["silver_plan"][0]["silver_strike"], "exitPercentile": product_defaults["silver_plan"][0]["silver_exit"]},
        "gold": {"strikePercentile": product_defaults["gold_plan"][0]["gold_strike"], "exitPercentile": product_defaults["gold_plan"][0]["gold_exit"]},
        "platinum": {"strikePercentile": product_defaults["platinum_plan"][0]["platinum_strike"], "exitPercentile": product_defaults["platinum_plan"][0]["platinum_exit"]},
    }

    min_year, max_year = data['date'].dt.year.min(), data['date'].dt.year.max()
    timezone = pytz.timezone("Asia/Kolkata")
    summary_data = []
    strikes_data = pd.DataFrame()

    for year in range(min_year, max_year + 1):
        # Create timezone-aware datetimes
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

        # Ensure both dates are timezone-aware
        season_start = season_start.astimezone(timezone)
        season_end = season_end.astimezone(timezone)

        # Filter data
        year_data = data[
            (data["date"] >= season_start) & 
            (data["date"] <= season_end) & 
            (data['pincode'].isin(pincodes))
        ].copy()
        
        if not year_data.empty:
            year_data = year_data.rename(columns={"rainfall": "Index"})
            year_data["Year"] = year
            strikes_data = pd.concat([strikes_data, year_data], ignore_index=True)

    if strikes_data.empty:
        raise ValueError(f"No valid strike data found for pincode {pincode}")
    print("strike_data",strikes_data.shape[0])

    thresholds = {
        level: calculate_thresholds(
            strikes_data, 
            percentiles[level], 
            delta=delta[level], 
            min_threshold={
                "strike": min_threshold[level]["strike"], 
                "exit": min_threshold[level]["exit"]
            }
        ) 
        for level in percentiles
    }

    burn_costs = {level: [] for level in percentiles.keys()}
    for year in range(min_year, max_year + 1):
        # Define the season start and end dates
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

        # Ensure both dates are timezone-aware
        season_start = season_start.astimezone(timezone)
        season_end = season_end.astimezone(timezone)

        year_data = data[
            (data["date"] >= season_start) & 
            (data["date"] <= season_end) & 
            (data["pincode"] == pincodes[0])
        ].copy()

        if not year_data.empty:
            year_data = calculate_payouts(year_data, thresholds, user_inputs, product_defaults)
            for level, _ in thresholds.items():
                burn_cost = year_data[f"{level}_payout"].sum()
                burn_cost = min(burn_cost, sumInsured)
                burn_costs[level].append({
                    "year": year, 
                    "totalBurnCost": burn_cost,
                    "rainfall": year_data["rainfall"].max()
                })

    print("Burn Costs:", burn_costs)
    last_premium_rate = None

    weightage_list = product_defaults["weightage"]
    weightage = weightage_list[0]
    six_weights = list(weightage.values())

    print("six_weights", six_weights)
    for level in percentiles.keys():
        weighted_burn_cost = 0  

        burn_costs_values = [bc["totalBurnCost"] for bc in burn_costs[level] if not np.isnan(bc["totalBurnCost"])]
        
        if not burn_costs_values:
            print(f"No valid burn cost data for {level}. Skipping...")
            continue

        print(f"\nBurn Costs for {level}:", burn_costs_values)

        five_year_period_chunks = [burn_costs_values[i:i+5] for i in range(0, len(burn_costs_values), 5)]
        
        print(f"5-Year Chunks for {level}:", five_year_period_chunks)

        for idx, chunk in enumerate(five_year_period_chunks):
            if idx >= len(six_weights):  
                print(f"Skipping extra chunk {idx + 1}, no corresponding weightage.")
                break  

            if chunk:  
                avg_burn_cost = np.mean(chunk)
                contribution = avg_burn_cost * (six_weights[idx] / 100)
                weighted_burn_cost += contribution

                print(f"5-Year Period {idx + 1}: Avg Burn Cost = {avg_burn_cost}, Weighted Contribution = {contribution}")

        print("\nFinal Weighted Burn Cost:", weighted_burn_cost)
        avg_burn_cost = weighted_burn_cost
        std_dev_burn_cost = np.nanstd([bc["totalBurnCost"] for bc in burn_costs[level]], ddof=1)
        std_dev_percent = std_dev_burn_cost / sumInsured if sumInsured > 0 else 0.0
        risk_premium_rate = avg_burn_cost / sumInsured if sumInsured > 0 else 0.0
        net_risk_premium_rate = ((risk_premium_rate / priced_loss_ratio[level]) * (1 + data_variability[level]) / (1 - management_loading[level]) if priced_loss_ratio[level] > 0 and (1 - management_loading[level]) > 0 else 0.0)

        
        print(f"  - Initial Net Risk Premium Rate: {net_risk_premium_rate}")
        print(f" -  premium_difference_percent : {product_defaults['premium_difference_percent']}")
        
        if last_premium_rate is not None:
            print(f"  - Last Premium Rate: {last_premium_rate}")
            premium_diff_threshold = product_defaults["premium_difference_percent"]
            difference = net_risk_premium_rate - last_premium_rate
            
            print(f"  - Difference between current and last premium rate: {difference}")
            print("level", level)
            
            if level == "gold" and difference < premium_diff_threshold:
                print(f"  - Adjusting {level} premium rate (was too close to Silver)")
                net_risk_premium_rate = last_premium_rate + premium_diff_threshold


            elif level == "platinum" and difference < premium_diff_threshold:
                print(f"  - Adjusting {level} premium rate (was too close to Gold)")
                net_risk_premium_rate = last_premium_rate + premium_diff_threshold

            print(f"  - Final Net Risk Premium Rate for {level}: {net_risk_premium_rate}")

        print("net_risk_premium_rate---------", net_risk_premium_rate)
        base_premium = net_risk_premium_rate * user_inputs['sumInsured']
        print(f"  - Base Premium: {base_premium}")
        print(f"  - Directus Base Premium: {base_premium_percentage[level]}")
        print(f" -directus_base_premium * user_inputs['sumInsured'] : {base_premium_percentage[level] * user_inputs['sumInsured']}")
        # If base premium is zero or less than the threshold, adjust it
        if base_premium == 0 or base_premium < (base_premium_percentage[level] * user_inputs['sumInsured']):
            print(f"Base premium is zero or less than directus_base_premium threshold. Adjusting net risk premium rate and recalculating base premium, based on directus_base_premium {base_premium_percentage[level]}")

            # Adjust net risk premium rate and base premium
            net_risk_premium_rate = base_premium_percentage[level]  
            base_premium = base_premium_percentage[level] * user_inputs['sumInsured']  # Directly set the minimum required value

            print(f"  - Adjusted Net Risk Premium Rate:{level} {net_risk_premium_rate}")
            print(f"  - Final Adjusted Base Premium:{level} {base_premium}")

        last_premium_rate = net_risk_premium_rate
        
        yearly_statistics = [
            {
                "year": int(bc["year"]), 
                "rainfall": round(float(np.nan_to_num(bc["rainfall"], nan=0.0)), 2)
            }
            for bc in burn_costs[level]
        ]

        yearly_statistics = sorted(yearly_statistics, key=lambda x: x["rainfall"], reverse=True)[:10]


        print("avg_burn_cost", avg_burn_cost)
        summary_data.append(
            create_level_summary(
                pincodes=pincodes,
                level=level,
                strikes=thresholds,
                avg_burn_cost=avg_burn_cost,
                std_dev=std_dev_burn_cost,
                std_dev_percent=std_dev_percent,
                risk_premium=(risk_premium_rate, net_risk_premium_rate),
                dataVariability=data_variability[level],
                management_loading=management_loading[level],
                delta=delta[level],
                priced_loss_ratio=priced_loss_ratio[level],
                percentiles=percentiles[level],
                yearly_statistics=yearly_statistics,
                product_defaults=product_defaults,
                user_inputs=user_inputs,
                additional_pincodes=additional_pincodes,
                dataSource=dataSource,
                gridPoints=gridPoints,
                base_premium=base_premium
            )
        )
    sanitized_output = sanitize_json(summary_data)
    return sanitized_output

# Function to sanitize JSON output (replace NaN/inf with 0.0)
def sanitize_json(data):
    if isinstance(data, dict):
        return {k: sanitize_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json(v) for v in data]
    elif isinstance(data, float):
        return 0.0 if np.isnan(data) or np.isinf(data) else data
    return data
def calculate_per_day_payout_percentage(user_inputs):
    
    start_date = pd.to_datetime(user_inputs["riskStartDate"])
    end_date = pd.to_datetime(user_inputs["riskEndDate"])
    coverage_days = (end_date - start_date).days + 1

    if coverage_days <= 0:
        raise ValueError("Risk period end date must be after start date.")

    payout_percentage = 1.0 / coverage_days
    print(f"Coverage days: {coverage_days}, Payout percentage: {payout_percentage}")
    return round(payout_percentage * 100, 2)

# Function to create summary for each risk level
def create_level_summary(    pincodes, level, strikes, avg_burn_cost, std_dev, risk_premium, std_dev_percent, 
    dataVariability, management_loading, delta, priced_loss_ratio, percentiles, 
    yearly_statistics, product_defaults, user_inputs, additional_pincodes, 
    dataSource, gridPoints, base_premium
    ):
    # Calculate base premium based on net risk premium rate
    net_risk_premium_rate = risk_premium[1]

    result = adjust_risk_period_dates(user_inputs,product_defaults)
    pricingInsured= result['calculated_sum_insured']
    print("calculated_sum_insured", pricingInsured)



    payout_percentage = calculate_per_day_payout_percentage(user_inputs)

    # Generate coverage details
    coverage_details = {
        "partialCoverage": f"{payout_percentage}% coverage for damages caused by rainfall exceeding {round(strikes[level]['strike'])} mm.",
    }
    
    
    primary_pincodes = user_inputs["pincodes"]
    print("level & threshold", level, strikes[level])

    condition = f"Any day during the coverage period, exceeding the rainfall of {round(strikes[level]['strike'])} mm"
    return {
        "model":"SingleDay HighRain",
        "riskStartDate": user_inputs['riskStartDate'],
        "riskEndDate": user_inputs['riskEndDate'],
        "prsd": result['revised_start_date'],
        "pred": result['revised_end_date'],   
        "pincode": list(map(str, primary_pincodes)),
        "additionalPincodes": additional_pincodes,
        "radius": user_inputs['radius'],
        "level": level,
        "strike": "1 day",
        "averageBurnCost": avg_burn_cost,
        "standardDeviationBurnCost": std_dev,
        "standardDeviationPercent": std_dev_percent,
        "riskPremiumPercentage": risk_premium[0],
        "netRiskPremiumRate": net_risk_premium_rate,
        "sumInsured": user_inputs['sumInsured'],
        "pricingInsured": pricingInsured,
        "basePremium": base_premium,  
        "dataVariability": dataVariability,
        "managementLoading": management_loading,
        "delta": delta,
        "pricedLossRatio": priced_loss_ratio,
        "levelPercentiles": percentiles,
        "calculatedPayoutPercentage": payout_percentage,
        "coverageDetails": coverage_details, 
        "dataSource": dataSource,
        "gridPoints": gridPoints,
        "rainfall_strike": f"{round(strikes[level]['strike'])} mm",
        "condition": condition,
        "statistics": yearly_statistics,
    }


# Function to execute the heat strike calculation
async def execute_rain_strike_calculation(user_inputs, product_defaults, data, dataSource,additional_pincodes):
    print("---------------------------------")
    print("Initial additional pincodes list:", additional_pincodes)
    
    # Check if additional_pincodes is a list and convert it to a DataFrame
    if isinstance(additional_pincodes, list):
        additional_pincodes = pd.DataFrame(additional_pincodes, columns=['pincode'])
        print("Converted additional_pincodes to DataFrame.")

    # Ensure 'pincode' column is treated as a string
    additional_pincodes['pincode'] = additional_pincodes['pincode'].astype(str)

    # Localize the dates directly to IST (Asia/Kolkata)
    if data["date"].dt.tz is None:
        data["date"] = data["date"].dt.tz_localize('Asia/Kolkata')
    else:
        data["date"] = data["date"].dt.tz_convert('Asia/Kolkata')

    # Extract unique pincodes from the DataFrame
    unique_pincodes = additional_pincodes['pincode'].unique().tolist()
    print("Unique pincodes after processing:", unique_pincodes)

    # Get the primary pincode from user inputs
    primary_pincode = str(user_inputs['pincodes'][0])
    print("Primary pincode:", primary_pincode)

    # Copy unique pincodes and remove the primary one
    processed_pincodes = unique_pincodes.copy()
    print("Pincodes before removal of primary:", processed_pincodes)

    if primary_pincode in processed_pincodes:
        processed_pincodes.remove(primary_pincode)
        print(f"Primary pincode {primary_pincode} removed.")

    print("Final additional pincodes to process:", processed_pincodes)

    gridPoints = data['coord_25x25'].dropna().unique().tolist()
    
    formatted_gridPoints = []
    for point in gridPoints:
        lat, lon = map(float, point.split(","))
        
        # Format coordinates and append to the list
        lat_dir = 'N' if lat >= 0 else 'S'
        lon_dir = 'E' if lon >= 0 else 'W'
        formatted_point = f"{lat}°{lat_dir} {lon}°{lon_dir}"
        
        formatted_gridPoints.append(formatted_point)
    return process_data(user_inputs, product_defaults, data, processed_pincodes, dataSource, formatted_gridPoints)






