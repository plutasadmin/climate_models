""" Data model for the Plutas platform. Defines Sequelize/ORM schema and table mapping.

 @file analyzer-model/models/rain_hira_model.py
"""

"""
This module performs risk analysis calculations based on rainfall data.
It includes functions for calculating thresholds, burn costs, payouts, and generating a summary report.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.parser import parse
import pytz
from scipy.stats import norm, lognorm, expon, gamma
import numpy as np
import math
import calendar
from math import ceil
def calculate_max_rainfall(data, primary_pincodes):
    """Calculates the maximum rainfall per date."""
    data["date"] = pd.to_datetime(data["date"])
    primary_pincodes = [str(p) for p in primary_pincodes]

    max_rainfall_per_date = data.groupby("date", as_index=False)["rainfall"].max()
    max_rainfall_per_date["pincode"] = primary_pincodes[0]  
    return max_rainfall_per_date

# Function to calculate rolling sums of rainfall for a given window
def calculate_rolling_sum(data, window):
    """Calculates rolling sum of rainfall for a given window size."""
    data = data.copy()

    if window is None or not isinstance(window, int):
        window = 1  # Default to 1 if invalid
    if not data.empty:
        data["Rain_rolling"] = data["rainfall"].rolling(window=window, min_periods=1).sum()
    else:
        data["Rain_rolling"] = np.nan
    return data


# Function to calculate thresholds for strikes and exits based on percentiles or distribution fitting
def calculate_thresholds(strikes_data, percentiles, consec_days, delta, min_threshold):
    """
    Calculate strike and exit values based on consecutive days setting.
    Fits multiple distributions to the strike data and selects the best fit for simulation.
    """
    if strikes_data.empty or strikes_data['Index'].isna().all():
        print("Invalid data for strikes:", strikes_data)  # Debugging invalid data
        return {"strike": np.nan, "exit": np.nan}  # Return NaN thresholds for invalid data

    # Remove NaN values from the 'Index' column
    strikes_data = strikes_data['Index'].dropna()

    # For single-day analysis, directly calculate percentiles
    strike_value = int(np.ceil(round(np.percentile(strikes_data, percentiles['strikePercentile'] * 100), 5)))
    exit_value = int(np.ceil(round(np.percentile(strikes_data, percentiles['exitPercentile'] * 100), 5)))
    print(f"Strike value: {strike_value}, Exit value: {exit_value}")
    print(f"Min threshold for strike: {min_threshold['strike']}, Min threshold for exit: {min_threshold['exit']}")
    
    # Ensure STRIKE >= 0 AND STRIKE > MIN_STRIKE
    if strike_value < min_threshold["strike"]:
        strike_value = min_threshold["strike"]

    # Ensure EXIT >= 0 AND EXIT > MIN_EXIT
    if exit_value < min_threshold["exit"]:
        exit_value = min_threshold["exit"]    
    
    print("delta",delta)
    
    # Adjust exit only when strike and exit match
    if strike_value == exit_value:
        exit_value += delta

    if consec_days == 1:
        return {
            "strike": strike_value,
            "exit": exit_value
        }
    else:
        # Define statistical distributions for fitting
        distributions = {
            "Normal": norm,         
            "Lognormal": lognorm,   
            "Exponential": expon,   
            "Gamma": gamma          
        }
        
        fits = {}  # Store parameters for each fitted distribution
        aics = {}  # Store Akaike Information Criterion (AIC) for each distribution

        # Fit each distribution and calculate AIC
        for name, dist in distributions.items():
            try:
                if name in ["Lognormal", "Gamma"]:
                    params = dist.fit(strikes_data, floc=0)  # Fix location for lognormal and gamma
                else:
                    params = dist.fit(strikes_data)

                # Calculate log-likelihood and AIC
                log_likelihood = np.sum(dist.logpdf(strikes_data, *params))
                k = len(params)  # Number of parameters
                aic = -2 * log_likelihood + 2 * k  # AIC formula
                fits[name] = params  # Store distribution parameters
                aics[name] = aic     # Store AIC value
            except Exception as e:
                print(f"Failed to fit {name} distribution: {e}")  # Debugging distribution fitting errors
                continue

        # Select the distribution with the lowest AIC
        best_fit_name = min(aics, key=aics.get)
        best_fit_params = fits[best_fit_name]  
        best_fit_distribution = distributions[best_fit_name]  

        print(f"Best fit distribution: {best_fit_name}")

        # Generate simulated data based on the best-fit distribution
        if best_fit_name == "Normal":
            simulated_data = np.random.normal(*best_fit_params, size=10000)
        elif best_fit_name == "Lognormal":
            simulated_data = np.random.lognormal(*best_fit_params, size=10000)
        elif best_fit_name == "Exponential":
            simulated_data = np.random.exponential(scale=best_fit_params[1], size=10000)
        elif best_fit_name == "Gamma":
            # Explicitly unpack and pass parameters to np.random.gamma
            shape, location, scale = best_fit_params[:3]  # Unpack the three parameters
            simulated_data = np.random.gamma(shape, scale, size=10000) 

        # Calculate thresholds from the simulated data
        strike_value = int(np.ceil(np.percentile(simulated_data, percentiles["strikePercentile"] * 100)))
        exit_value = int(np.ceil(np.percentile(simulated_data, percentiles["exitPercentile"] * 100)))

        # Ensure STRIKE >= 0 AND STRIKE > MIN_STRIKE
        if strike_value < min_threshold["strike"]:
            strike_value = min_threshold["strike"]

        # Ensure EXIT >= 0 AND EXIT > MIN_EXIT
        if exit_value < min_threshold["exit"]:
            exit_value = min_threshold["exit"]    

        print("delta",delta)

        # Adjust exit only when strike and exit match
        if strike_value == exit_value:
            exit_value += delta

        return {
            "strike": strike_value,
            "exit": exit_value
        }

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
    if days_count < max_number_of_days:
        x = ceil((max_number_of_days - days_count) / 2)
        revised_start_date = start_date - timedelta(days=x)
        revised_end_date = end_date + timedelta(days=x)
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
    payout_percentage = round(1 / revised_days_count, 4) 

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
    payout1 = calculated_sum_insured * (payout_percentage)# / 100)  # if needed as %
    payout2 = calculated_sum_insured

    payouts = {
        "payout1": payout1,
        "payout2": payout2,
    }
    print("Payouts:", payouts)

    for level, threshold in thresholds.items():
        data[f"{level}_payout"] = np.where(
            (data["Rain_rolling"] >= threshold["strike"]) &
            (data["Rain_rolling"] < threshold["exit"]),
            payouts["payout1"],
            np.where(
                data["Rain_rolling"] >= threshold["exit"],
                payouts["payout2"],
                0
            ),
        )
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

# Function to create a summary for each level and pincode
def create_level_summary(
    pincodes, level, strikes, avg_burn_cost, std_dev, risk_premium, std_dev_percent, 
    dataVariability, management_loading, delta, priced_loss_ratio, percentiles, 
    yearly_statistics, product_defaults, user_inputs, additional_pincodes, 
    dataSource, gridPoints, directus_base_premium
): 
    """Create a summary dictionary for a specific level."""
    # Calculate base premium based on net risk premium rate
    net_risk_premium_rate = risk_premium[1]

    print("net_risk_premium_rate---------", net_risk_premium_rate)
    base_premium = net_risk_premium_rate * user_inputs['sumInsured']
    print(f"  - Base Premium: {base_premium}")
    print(f"  - Directus Base Premium: {directus_base_premium}")
    print(f" -directus_base_premium * user_inputs['sumInsured'] : {directus_base_premium * user_inputs['sumInsured']}")
    # If base premium is zero or less than the threshold, adjust it
    if base_premium == 0 or base_premium < (directus_base_premium * user_inputs['sumInsured']):
        print(f"Base premium is zero or less than directus_base_premium threshold. Adjusting net risk premium rate and recalculating base premium, based on directus_base_premium {directus_base_premium}")

        # Adjust net risk premium rate and base premium
        net_risk_premium_rate = directus_base_premium  
        base_premium = directus_base_premium * user_inputs['sumInsured']  # Directly set the minimum required value

        print(f"  - Adjusted Net Risk Premium Rate: {net_risk_premium_rate}")
        print(f"  - Final Adjusted Base Premium: {base_premium}")

    payout_percentage = calculate_per_day_payout_percentage(user_inputs)


    coverage_details = {
        "partialCoverage": f"{payout_percentage}% coverage for damages caused by rainfall exceeding {strikes[level]['strike']} mm.",
        "fullCoverage": f"100% coverage for damages caused by rainfall exceeding {strikes[level]['exit']} mm."
    }
    
    primary_pincodes = user_inputs["pincodes"]
    print("level & threshold", level, strikes[level])
    
    return {
        "model":"HighRain",
        "riskStartDate": user_inputs['riskStartDate'],
        "riskEndDate": user_inputs['riskEndDate'],
        "pincode": list(map(str, primary_pincodes)),
        "additionalPincodes": additional_pincodes,
        "radius": user_inputs['radius'],
        "level": level,
        "strike": f"{strikes[level]['strike']} mm",
        "exit": f"{strikes[level]['exit']} mm",
        "averageBurnCost": avg_burn_cost,
        "standardDeviationBurnCost": std_dev,
        "standardDeviationPercent": std_dev_percent,
        "riskPremiumPercentage": risk_premium[0],
        "netRiskPremiumRate": net_risk_premium_rate,
        "sumInsured": user_inputs['sumInsured'],
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
        "statistics": yearly_statistics,
    }

# Function to process rainfall data for multiple pincodes and levels
def process_data(user_inputs, product_defaults, data, additional_pincodes, dataSource, gridPoints):
    primary_pincodes = user_inputs["pincodes"]  
    print("Primary pincodes:", primary_pincodes)

    if not isinstance(primary_pincodes, list):
        primary_pincodes = [primary_pincodes]

    # Count unique pincodes in data
    unique_pincode_count = data["pincode"].nunique()
    print("Unique pincodes in data:", unique_pincode_count)

    # Call calculate_max_rainfall only if there's more than one pincode
    if unique_pincode_count > 1:
        data = calculate_max_rainfall(data, primary_pincodes)
    else:
        print("Skipping calculate_max_rainfall as there is only one unique pincode in the data.")

    pincodes = data["pincode"].unique()  
    print("Unique pincodes in data:", pincodes)

    results = adjust_risk_period_dates(user_inputs,product_defaults)
    risk_end_date = results['revised_end_date']
    risk_start_date = results['revised_start_date']
    sumInsured = results['calculated_sum_insured']
    consec_days = product_defaults["index_days"]

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
        "silver": {"silver_threshold_strike": product_defaults["silver_plan"][0]["silver_threshold_strike"], "silver_threshold_exit": product_defaults["silver_plan"][0]["silver_threshold_exit"]},
        "gold": {"gold_threshold_strike": product_defaults["gold_plan"][0]["gold_threshold_strike"], "gold_threshold_exit": product_defaults["gold_plan"][0]["gold_threshold_exit"]},
        "platinum": {"platinum_threshold_strike": product_defaults["platinum_plan"][0]["platinum_threshold_strike"], "platinum_threshold_exit": product_defaults["platinum_plan"][0]["platinum_threshold_exit"]},
    }

    percentiles = {
        "silver": {"strikePercentile": product_defaults["silver_plan"][0]["silver_strike"], "exitPercentile": product_defaults["silver_plan"][0]["silver_exit"]},
        "gold": {"strikePercentile": product_defaults["gold_plan"][0]["gold_strike"], "exitPercentile": product_defaults["gold_plan"][0]["gold_exit"]},
        "platinum": {"strikePercentile": product_defaults["platinum_plan"][0]["platinum_strike"], "exitPercentile": product_defaults["platinum_plan"][0]["platinum_exit"]},
    }

    min_year, max_year = data['date'].dt.year.min(), data['date'].dt.year.max()
    timezone = pytz.timezone("Asia/Kolkata")
    summary_data = []
    # # # Convert pincode column to string type for comparison
    # data['pincode'] = data['pincode'].astype(str)        
    strikes_data = pd.DataFrame()

    for year in range(min_year, max_year + 1):
        season_start = timezone.localize(datetime.strptime(f"{year}-{risk_start_date[5:]}", "%Y-%m-%d"))
        season_end_year = year + 1 if int(risk_end_date[:4]) > int(risk_start_date[:4]) else year
        season_end = timezone.localize(datetime.strptime(f"{season_end_year}-{risk_end_date[5:]}", "%Y-%m-%d"))

        # Adjust for invalid season ranges
        if season_start > season_end:
            new_year = season_end.year + 1
            season_end = season_end.replace(year=new_year)

        year_data = data[
            (data["date"] >= season_start) & 
            (data["date"] <= season_end) & 
            (data['pincode'].isin(pincodes))] #(data['pincode'] == pincode_id)]

        year_data = calculate_rolling_sum(year_data, window=consec_days)

        if year_data["Rain_rolling"].isna().all():
            continue
        er_strike_year = year_data.groupby("pincode").agg(Index=("Rain_rolling", "max")).reset_index()
        er_strike_year["Year"] = year
        strikes_data = pd.concat([strikes_data, er_strike_year])

    thresholds = {
        level: calculate_thresholds(
            strikes_data, 
            percentiles[level], 
            consec_days=consec_days, 
            delta=delta[level], 
            min_threshold={
                "strike": min_threshold[level][f"{level}_threshold_strike"], 
                "exit": min_threshold[level][f"{level}_threshold_exit"]
            }
        ) 
        for level in percentiles
    }

    # Calculate burn costs and summaries for each level
    burn_costs = {level: [] for level in percentiles.keys()}
    print("min_year",min_year ,"max_year",max_year)
    for year in range(min_year, max_year):
        season_start = timezone.localize(datetime.strptime(f"{year}-{risk_start_date[5:]}", "%Y-%m-%d"))
        season_end_year = year + 1 if int(risk_end_date[:4]) > int(risk_start_date[:4]) else year
        season_end = timezone.localize(datetime.strptime(f"{season_end_year}-{risk_end_date[5:]}", "%Y-%m-%d"))

        if season_start > season_end:
            new_year = season_end.year + 1
            season_end = season_end.replace(year=new_year)

        year_data = data[(data["date"] >= season_start) & 
                        (data["date"] <= season_end) & 
                        (data['pincode'].isin(pincodes))]
        year_data = calculate_rolling_sum(year_data, window=consec_days)
        year_data = calculate_payouts(year_data, thresholds,user_inputs, product_defaults)
        # Compute Max_Rainfall for the year
        Max_Rainfall = year_data["rainfall"].max()  

        for level, _ in thresholds.items():
            burn_cost = year_data[f"{level}_payout"].sum()
            burn_cost = min(burn_cost, sumInsured)
            burn_costs[level].append({"year": year, "totalBurnCost": burn_cost,
            "Max_Rainfall": Max_Rainfall})
    print("Burn Costs:", burn_costs)
    last_premium_rate = None

    # Extract weightage from productDefaults
    weightage_list = product_defaults["weightage"]
    weightage = weightage_list[0]  # Extract first (and only) weightage dictionary
    six_weights = list(weightage.values())  # Convert to list of weights

    print("six_weights",six_weights)
    for level in percentiles.keys():
        # Reset weighted sum for each level
        weighted_burn_cost = 0  

        # Extract valid burn costs (excluding NaN values)
        burn_costs_values = [bc["totalBurnCost"] for bc in burn_costs[level] if not np.isnan(bc["totalBurnCost"])]
        
        if not burn_costs_values:
            print(f"No valid burn cost data for {level}. Skipping...")
            continue

        print(f"\nBurn Costs for {level}:", burn_costs_values)

        # Split into 5-year chunks properly
        five_year_period_chunks = [burn_costs_values[i:i+5] for i in range(0, len(burn_costs_values), 5)]
        
        print(f"5-Year Chunks for {level}:", five_year_period_chunks)

        # Compute weighted burn cost
        for idx, chunk in enumerate(five_year_period_chunks):
            if idx >= len(six_weights):  
                print(f"Skipping extra chunk {idx + 1}, no corresponding weightage.")
                break  

            if chunk:  
                avg_burn_cost = np.mean(chunk)  # Average burn cost per 5-year period
                contribution = avg_burn_cost * (six_weights[idx] / 100)  # Applying weight
                weighted_burn_cost += contribution

                print(f"5-Year Period {idx + 1}: Avg Burn Cost = {avg_burn_cost}, Weighted Contribution = {contribution}")


        print("\nFinal Weighted Burn Cost:", weighted_burn_cost)
        avg_burn_cost = weighted_burn_cost  # Assigning the final weighted burn cost
        std_dev_burn_cost = np.nanstd([bc["totalBurnCost"] for bc in burn_costs[level]], ddof=1)
        std_dev_percent = std_dev_burn_cost / sumInsured if sumInsured > 0 else 0.0
        risk_premium_rate = avg_burn_cost / sumInsured if sumInsured > 0 else 0.0
        net_risk_premium_rate = ((risk_premium_rate / priced_loss_ratio[level]) * (1 + data_variability[level]) / (1 - management_loading[level]) if priced_loss_ratio[level] > 0 and (1 - management_loading[level]) > 0 else 0.0)

        
        print(f"  - Initial Net Risk Premium Rate: {net_risk_premium_rate}")
        print(f" -  premium_difference_percent : {product_defaults['premium_difference_percent']}")
        # Adjust the rates
        if last_premium_rate is not None:
            print(f"  - Last Premium Rate: {last_premium_rate}")
            premium_diff_threshold = product_defaults["premium_difference_percent"] 
            print(f"  - premium_diff_threshold: {premium_diff_threshold}")
            difference = net_risk_premium_rate - last_premium_rate  
            
            print(f"  - Difference between current and last premium rate: {difference}")
            print("level",level)
            # Check the difference between Silver and Gold
            if level == "gold" and difference < premium_diff_threshold:
                print(f"  - Adjusting {level} premium rate (was too close to Silver)")
                print(last_premium_rate , premium_diff_threshold)
                # net_risk_premium_rate = last_premium_rate * (1 + premium_diff_threshold)  # Increase Gold rate 
                net_risk_premium_rate = last_premium_rate + premium_diff_threshold

            # Check the difference between Gold and Platinum
            elif level == "platinum" and difference < premium_diff_threshold:
                print(f"  - Adjusting {level} premium rate (was too close to Gold)")
                print(last_premium_rate , premium_diff_threshold)
                # net_risk_premium_rate = last_premium_rate * (1 + premium_diff_threshold)  # Increase Gold rate 
                net_risk_premium_rate = last_premium_rate + premium_diff_threshold

            print(f"  - Final Net Risk Premium Rate for {level}: {net_risk_premium_rate}")

        last_premium_rate = net_risk_premium_rate  # Storing the current rate to compare with the next one

        
        ### yearly statistics and filter top 10 by average rainfall
        yearly_statistics = [
            {
                "year": int(bc["year"]), 
                "Max_Rainfall": round(float(np.nan_to_num(bc["Max_Rainfall"], nan=0.0)), 2) 
            }
            for bc in burn_costs[level]
        ]
        
        ### Sort yearly statistics by average rainfall in descending order
        yearly_statistics = sorted(yearly_statistics, key=lambda x: x["Max_Rainfall"], reverse=True)[:10]

        print("avg_burn_cost",avg_burn_cost)
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
                directus_base_premium=base_premium_percentage[level]
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

# Main function to execute rainfall strike calculations

async def execute_rain_strike_calculation(user_inputs, product_defaults, data, dataSource,additional_pincodes):
    print("---------------------------------")
    print("Initial additional pincodes list:", additional_pincodes)
    
    # Check if additional_pincodes is a list and convert it to a DataFrame
    if isinstance(additional_pincodes, list):
        additional_pincodes = pd.DataFrame(additional_pincodes, columns=['pincode'])
        print("Converted additional_pincodes to DataFrame.")

    # Ensure 'pincode' column is treated as a string
    additional_pincodes['pincode'] = additional_pincodes['pincode'].astype(str)

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
