""" Data model for the Plutas platform. Defines Sequelize/ORM schema and table mapping.

 @file analyzer-model/models/models_v1/heat_howa_model.py
"""

import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import calendar
from itertools import groupby
import math
# Constants and data setup
def initialize_constants(user_inputs, product_defaults):
    return {
        "Silver_Percentile": {
            "silver_strike": product_defaults["silver_plan"][0]["silver_strike"],
            "silver_exit": product_defaults["silver_plan"][0]["silver_exit"]
        },
        "Gold_Percentile": {
            "gold_strike": product_defaults["gold_plan"][0]["gold_strike"],
            "gold_exit": product_defaults["gold_plan"][0]["gold_exit"]
        },
        "Platinum_Percentile": {
            "platinum_strike": product_defaults["platinum_plan"][0]["platinum_strike"],
            "platinum_exit": product_defaults["platinum_plan"][0]["platinum_exit"]
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
        "base_premium_percentage" : {
            "silver": product_defaults["silver_plan"][0]["silver_base_premium"],
            "gold": product_defaults["gold_plan"][0]["gold_base_premium"],
            "platinum": product_defaults["platinum_plan"][0]["platinum_base_premium"]
        },
        "Notional_percent": product_defaults["payout_percentage"],
        "management_loading" : {
            "silver": product_defaults["silver_plan"][0]["silver_management_loading"],
            "gold": product_defaults["gold_plan"][0]["gold_management_loading"],  
            "platinum": product_defaults["platinum_plan"][0]["platinum_management_loading"]  
        },
        "data_variability" : {
            "silver": product_defaults["silver_plan"][0]["silver_data_variability"],
            "gold": product_defaults["gold_plan"][0]["gold_data_variability"],  
            "platinum": product_defaults["platinum_plan"][0]["platinum_data_variability"]  
        },
        "priced_Loss_Ratio" : {
            "silver": product_defaults["silver_plan"][0]["silver_priced_loss_ratio"],
            "gold": product_defaults["gold_plan"][0]["gold_priced_loss_ratio"],  
            "platinum": product_defaults["platinum_plan"][0]["platinum_priced_loss_ratio"]  
        },
        "delta" : {
            "silver": product_defaults["silver_plan"][0]["silver_strike_exit_delta"],
            "gold": product_defaults["gold_plan"][0]["gold_strike_exit_delta"],  
            "platinum": product_defaults["platinum_plan"][0]["platinum_strike_exit_delta"]  
        },
        "weightage": product_defaults["weightage"],
        "premium_difference_percent": product_defaults["premium_difference_percent"],
        "Sum_Insured": int(user_inputs["sumInsured"]),
        "risk_start_date": user_inputs["riskStartDate"],
        "risk_end_date": user_inputs["riskEndDate"],
        "radius": user_inputs["radius"],
        "pincodes": user_inputs["pincodes"],
    }

# Dynamic year and season calculation
def get_year_range_and_seasons(data, risk_start_date, risk_end_date, timezone=pytz.UTC):
    min_year = data["date"].dt.year.min()
    # max_year = data["date"].dt.year.max()
    season_ranges = []
    
    max_year = min_year+29
    print(min_year)
    print(max_year)
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
        
        season_ranges.append((season_start.replace(tzinfo=None), season_end.replace(tzinfo=None)))
    return range(min_year, max_year + 1), season_ranges

# Step 1: Calculate average and standard deviation of temperature
def calculate_temp_statistics(data, pincode_id, year_range, season_ranges):
    Avg_Max_Temp = []  # Empty list initially
    for (year, (season_start, season_end)) in zip(year_range, season_ranges):
        dt = data[(data['date'] >= season_start) & (data['date'] <= season_end) & (data['pincode'].isin(pincode_id))] #(data['pincode'] == pincode_id)]
        # Assuming `pincode_list` is a list of pincodes to filter
        Temp_Max_Average = dt.groupby("pincode").agg(
            Max_Temp_Average=("Max_Temp", "mean"),
            Max_Temp_maximum=("Max_Temp", "max")
        ).reset_index()
        Temp_Max_Average['Year'] = year
        Avg_Max_Temp.append(Temp_Max_Average)

    Avg_Max_Temp_df = pd.concat(Avg_Max_Temp, ignore_index=True)  

    if Avg_Max_Temp_df.empty:
        return Avg_Max_Temp_df, pd.DataFrame()  

    stats = Avg_Max_Temp_df.groupby("pincode").agg(
        Mean_Temp=("Max_Temp_Average", "mean"),
        SD_Temp=("Max_Temp_Average", "std")
    ).reset_index()
    print(stats)
    # stats = stats.round(2)
    stats = stats.applymap(lambda x: round_half_up(x, 2))

    print("stats----",stats)
    stats['Upper_1_SD'] = stats['Mean_Temp'] + stats['SD_Temp']
    stats['Upper_2_SD'] = stats['Mean_Temp'] + 2 * stats['SD_Temp']
    stats['Upper_3_SD'] = stats['Mean_Temp'] + 3 * stats['SD_Temp']
    stats = stats.round(2)
    print("stats---->>upped sd")
    print(stats)
    print("============")
    print(Avg_Max_Temp_df)
    return Avg_Max_Temp_df, stats

def round_half_up(number, decimals=0):
    try:
        number = float(number)  # Convert to float if it's a string
        multiplier = 10 ** decimals
        return math.floor(number * multiplier + 0.5) / multiplier
    except ValueError:
        raise TypeError("Input must be a number (int or float)")

# Step 2: Calculate strike and exit thresholds
def calculate_strikes(data, pincode_id, year_range, stats, season_ranges, constants):
    strikes_data = []
    
    for (year, (season_start, season_end)) in zip(year_range, season_ranges):
        dt = data[(data['date'] >= season_start) & (data['date'] <= season_end) & (data['pincode'].isin(pincode_id))].copy()
        dt.loc[:, 'dd'] = (dt['Max_Temp'] >= stats['Upper_2_SD'].values[0]).astype(int)
        dt = dt.sort_values(by='date')
        
        # Applying Run-Length Encoding (RLE) on the sorted 'dd' column
        rle = [(k, len(list(g))) for k, g in groupby(dt['dd'])]

        max_run = max([length for value, length in rle if value == 1], default=0)
        strikes_data.append({"Year": year, "Index": max_run})

    strikes_df = pd.DataFrame(strikes_data)  
    # Calculate Silver, Gold, and Platinum strikes
    silver_strikes = {
        "strike": int(np.ceil(np.quantile(strikes_df["Index"], constants["Silver_Percentile"]["silver_strike"]))),
        "exit": int(np.ceil(np.quantile(strikes_df["Index"], constants["Silver_Percentile"]["silver_exit"])))
    }
    gold_strikes = {
        "strike": int(np.ceil(np.quantile(strikes_df["Index"], constants["Gold_Percentile"]["gold_strike"]))),
        "exit": int(np.ceil(np.quantile(strikes_df["Index"], constants["Gold_Percentile"]["gold_exit"])))
    }
    platinum_strikes = {
        "strike": int(np.ceil(np.quantile(strikes_df["Index"], constants["Platinum_Percentile"]["platinum_strike"]))),
        "exit": int(np.ceil(np.quantile(strikes_df["Index"], constants["Platinum_Percentile"]["platinum_exit"])))
    }

    # Apply minimum thresholds and ensure conditions
    for level, strikes in [("Silver", silver_strikes), ("Gold", gold_strikes), ("Platinum", platinum_strikes)]:
        print(f"Level: {level}, Initial Strike: {strikes['strike']}, Initial Exit: {strikes['exit']}")
        min_thresholds = constants[f"{level}_Min_threshold"]

        # Ensure STRIKE >= 0 AND STRIKE > MIN_STRIKE
        if strikes["strike"] < min_thresholds[f"{level.lower()}_min_threshold_strike"]:
            print(f"Updating {level} strike from {strikes['strike']} to {min_thresholds[f'{level.lower()}_min_threshold_strike']}")
            strikes["strike"] = min_thresholds[f"{level.lower()}_min_threshold_strike"]

        # Ensure EXIT >= 0 AND EXIT > MIN_EXIT
        if strikes["exit"] < min_thresholds[f"{level.lower()}_min_threshold_exit"]:
            print(f"Updating {level} exit from {strikes['exit']} to {min_thresholds[f'{level.lower()}_min_threshold_exit']}")
            strikes["exit"] = min_thresholds[f"{level.lower()}_min_threshold_exit"]

        print(f"Updated {level} Strike: {strikes['strike']}, Exit: {strikes['exit']}")

        # Add delta to exit only when strike and exit match
        delta = constants["delta"][level.lower()]
        if strikes["strike"] == strikes["exit"]:
            print(f"{level} strike and exit are the same, increasing exit by delta {delta}")
            strikes["exit"] += delta
            print(f"Updated {level} exit: {strikes['exit']}")

    return {
        "Silver": silver_strikes,
        "Gold": gold_strikes,
        "Platinum": platinum_strikes
    }

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

# Step 3: Calculate payouts
def calculate_payouts(data, pincode_id, year_range, stats, strikes, Sum_Insured, Notional_percent, risk_start_date, risk_end_date):
    print("notional percent",Notional_percent)
    # Calculate payout percentage and values    
    Notional_percent = calculate_payout_percentage(risk_start_date, risk_end_date)
    print("calculated notional percent",Notional_percent)
    
    print("Sum Insured:", Sum_Insured)
    Notional_payout = Sum_Insured * (Notional_percent / 100)

    print("Notional payout:", Notional_payout)
    
    Max_payout = Sum_Insured
    payout_data = pd.DataFrame()

    for year in year_range:
        # Define start and end dates for the risk period
        risk_start_datetime = pd.to_datetime(f"{year}-{risk_start_date[5:]}")
        risk_end_datetime = pd.to_datetime(f"{year}-{risk_end_date[5:]}")

        # Filter data for the specific year and pincode
        dt = data[(data['date'] >= risk_start_datetime) & (data['date'] <= risk_end_datetime) & (data['pincode'].isin(pincode_id))].copy() #(data['pincode'] == pincode_id)] # Use copy to avoid SettingWithCopyWarning

        # Filter `stats` DataFrame to find the row for the current `pincode_id`
        # stats_row = stats[stats['pincode'] == pincode_id]
        # Extract the Upper_2_SD value
        upper_2_sd = stats['Upper_2_SD'].values[0]

        # Calculate 'dd' column and RLE logic for consecutive runs
        dt['dd'] = (dt['Max_Temp'] >= upper_2_sd).astype(int)
        dt = dt.sort_values(by='date')

        rle = [(k, sum(1 for _ in g)) for k, g in groupby(dt['dd'])]

        max_run = max([length for value, length in rle if value == 1], default=0)

        # Calculate burn costs for Silver, Gold, and Platinum
        Silver_Burn_Cost = calculate_burn_cost(max_run, strikes['Silver'], Notional_payout, Max_payout)
        Gold_Burn_Cost = calculate_burn_cost(max_run, strikes['Gold'], Notional_payout, Max_payout)
        Platinum_Burn_Cost = calculate_burn_cost(max_run, strikes['Platinum'], Notional_payout, Max_payout)

        # Append results for the year
        payout_row = {
            "Year": year,
            "Silver_Burn_Cost": Silver_Burn_Cost,
            "Gold_Burn_Cost": Gold_Burn_Cost,
            "Platinum_Burn_Cost": Platinum_Burn_Cost
        }
        payout_data = pd.concat([payout_data, pd.DataFrame([payout_row])], ignore_index=True)

    return payout_data

def calculate_burn_cost(Index, strike_data, Notional_payout, Max_payout):
    # Calculate payouts based on Index and strike thresholds
    pay_con1 = Notional_payout if (Index >= strike_data['strike'] and Index < strike_data['exit']) else 0
    pay_con2 = Max_payout if Index >= strike_data['exit'] else 0
    print(f"Pay_con1: {pay_con1}, Pay_con2: {pay_con2}")
    return round(pay_con1 + pay_con2, 2)




def calculate_max_temperature(data, primary_pincodes):
    print("----------------")

    data["date"] = pd.to_datetime(data["date"])

    data["pincode"] = data["pincode"].astype(str)
    primary_pincodes = [str(p) for p in primary_pincodes]

    print("Unique pincodes in data:", data["pincode"].unique())
    print("Primary pincodes:", primary_pincodes)

    # Compute the maximum rainfall for each date across all pincodes
    max_temperature_per_date = data.groupby("date")["Max_Temp"].max().reset_index()
    print("max temperature Per Date:\n", max_temperature_per_date.head())

    primary_pincode_data = max_temperature_per_date.copy()
    primary_pincode_data["pincode"] = primary_pincodes[0]

    print("Primary Pincode Data After Assigning max Temperature:\n", primary_pincode_data.head())

    return primary_pincode_data


def process_data(user_inputs, product_defaults, data, additional_pincodes, dataSource, gridPoints):

    constants = initialize_constants(user_inputs, product_defaults)
    
    primary_pincodes = constants["pincodes"]  
    print("Primary pincodes:", primary_pincodes)

    if not isinstance(primary_pincodes, list):
        primary_pincodes = [primary_pincodes]

    # Count unique pincodes in data
    unique_pincode_count = data["pincode"].nunique()
    print("Unique pincodes in data:", unique_pincode_count)

    # Call calculate_max_rainfall only if there's more than one pincode
    if unique_pincode_count > 1:
        data = calculate_max_temperature(data, primary_pincodes)
    else:
        print("Skipping calculate_max_temperature as there is only one unique pincode in the data.")

    pincodes = data["pincode"].unique()  
    
    year_range, season_ranges = get_year_range_and_seasons(
        data, constants["risk_start_date"], constants["risk_end_date"]
    )

    premium_results = []

    # for pincode_id in pincodes:
    Avg_Max_Temp, stats = calculate_temp_statistics(
        data, pincodes, year_range, season_ranges
    )
    strikes = calculate_strikes(
        data, pincodes, year_range, stats, season_ranges, constants
    )
    payout_data = calculate_payouts(
        data, pincodes, year_range, stats, strikes, constants["Sum_Insured"], 
        constants["Notional_percent"], constants["risk_start_date"], constants["risk_end_date"]
    )
    
    payout_data = payout_data.to_dict(orient="records")  # Convert to a list of dictionaries

    yearly_statistics = [
        {
            "year": int(row["Year"]),
            "Max_Temp": row["Max_Temp_maximum"],
        }
        for _, row in Avg_Max_Temp.iterrows()
    ]

    # Sort yearly statistics by maximum temperature in descending order and keep top 10
    yearly_statistics = sorted(yearly_statistics, key=lambda x: x["Max_Temp"], reverse=True)[:10]

    # Premium calculations for Silver, Gold, and Platinum
    levels = ["Silver", "Gold", "Platinum"]
    last_premium_rate = None
    weightage_list = product_defaults["weightage"]
    weightage = weightage_list[0]  # Extract first (and only) weightage dictionary
    six_weights = list(weightage.values())  # Convert to list of weights

    print("six_weights",six_weights)

    for i, level in enumerate(levels):
        print(f"\nCalculating premium for {level}...")  
        # Reset weighted sum for each level
        weighted_burn_cost = 0  

        # Filter and transform the statistics for the current level
        level_stats = [
            {
                "Year": item["Year"],
                "Burn_Cost": item[f"{level}_Burn_Cost"] 
            }
            for item in payout_data
        ]
        # burn_costs_values = [item["Burn_Cost"] for item in payout_data if not np.isnan(item["Burn_Cost"])]
        burn_costs_values = [item["Burn_Cost"] for item in level_stats]

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

        # Calculate  std dev for this level
        # avg_burn_cost = np.mean([item["Burn_Cost"] for item in level_stats])
        std_dev = np.std([item["Burn_Cost"] for item in level_stats])            
        risk_premium_pct = avg_burn_cost / constants["Sum_Insured"]

        # Correctly calculate rates without repetitions
        level_variability = constants["data_variability"][level.lower()]
        level_management_loading = constants["management_loading"][level.lower()]
        level_priced_Loss_Ratio = constants["priced_Loss_Ratio"][level.lower()]
        level_percentiles= constants[f"{level}_Percentile"]
        level_delta = constants["delta"][level.lower()]
        directus_base_premium = constants["base_premium_percentage"][level.lower()]
        net_risk_premium_rate = ((risk_premium_pct / level_priced_Loss_Ratio) * (1 + level_variability)) / (1 - level_management_loading)
        
        print(f"  - Initial Net Risk Premium Rate: {net_risk_premium_rate}")
        print(f" -  premium_difference_percent : {constants['premium_difference_percent']}")
        # Adjusting the rates
        if last_premium_rate is not None:
            print(f"  - Last Premium Rate: {last_premium_rate}")
            premium_diff_threshold = constants["premium_difference_percent"] ## decimal format
            difference = net_risk_premium_rate - last_premium_rate  # difference

            print(f"  - Difference from {levels[i-1]}: {difference:.6f} (Threshold: {premium_diff_threshold:.6f})")

            # Check the difference between Silver and Gold
            if level == "Gold" and difference < premium_diff_threshold:
                print(f"  - Adjusting {level} premium rate (was too close to Silver)")
                # net_risk_premium_rate = last_premium_rate * (1 + premium_diff_threshold)  # Increase Gold rate 
                net_risk_premium_rate = last_premium_rate + premium_diff_threshold

            # Check the difference between Gold and Platinum
            elif level == "Platinum" and difference < premium_diff_threshold:
                print(f"  - Adjusting {level} premium rate (was too close to Gold)")
                # net_risk_premium_rate = last_premium_rate * (1 + premium_diff_threshold)  # Increase Platinum rate 
                net_risk_premium_rate = last_premium_rate + premium_diff_threshold

            print(f"  - Final Net Risk Premium Rate for {level}: {net_risk_premium_rate}")

        last_premium_rate = net_risk_premium_rate  # Storing the current rate to compare with the next one

        
        # strike and exit values from the strikes dictionary
        strike = strikes[level]["strike"]
        exit = strikes[level]["exit"]

        strike_label = "day" if strike == 1 else "days"
        exit_label = "day" if exit == 1 else "days"

        # Notional_percent = round(constants["Notional_percent"] * 100)
        Notional_percent = calculate_payout_percentage(constants["risk_start_date"], constants["risk_end_date"])

        primary_pincodes = user_inputs["pincodes"]
        condition = f"Continuous hot days during the coverage period, exceeding the benchmark temperature of {stats['Upper_2_SD'].values[0]} °C"
        
        # If base premium is zero, or less than base premium percentage use base premium percentage
        print("net_risk_premium_rate---------", net_risk_premium_rate)
        base_premium = net_risk_premium_rate * constants["Sum_Insured"]
        print(f"  - Base Premium: {base_premium}")
        print(f"  - Directus Base Premium: {directus_base_premium}")
        print(f" -directus_base_premium * constants['Sum_Insured'] : {directus_base_premium * constants['Sum_Insured']}")
        # If base premium is zero or less than the threshold, adjust it
        if base_premium == 0 or base_premium < (directus_base_premium * constants["Sum_Insured"]):
            print(f"Base premium is zero or less than directus_base_premium threshold. Adjusting net risk premium rate and recalculating base premium, based on directus_base_premium {directus_base_premium}")

            # Adjust net risk premium rate and base premium
            net_risk_premium_rate = directus_base_premium  
            base_premium = directus_base_premium * constants["Sum_Insured"]  

            print(f"  - Adjusted Net Risk Premium Rate: {net_risk_premium_rate}")
            print(f"  - Final Adjusted Base Premium: {base_premium}")

        premium_results.append({
            "riskStartDate": constants['risk_start_date'],
            "riskEndDate": constants['risk_end_date'],
            "pincode": list(map(str, primary_pincodes)), 
            "additionalPincodes": additional_pincodes,
            "radius": constants['radius'],
            "level": level.lower(),
            "strike": f"{strike} {strike_label}",
            "exit": f"{exit} {exit_label}",
            "averageBurnCost": avg_burn_cost,
            "standardDeviationBurnCost": std_dev,
            "standardDeviationPercent": std_dev / avg_burn_cost if avg_burn_cost != 0 else 0,
            "riskPremiumPercentage": risk_premium_pct,
            "netRiskPremiumRate": net_risk_premium_rate,
            "sumInsured": constants["Sum_Insured"],
            "basePremium": base_premium,
            "dataVariability": level_variability,
            "managementLoading": level_management_loading,
            "pricedLossRatio": level_priced_Loss_Ratio,
            "levelPercentiles": level_percentiles,
            "delta": level_delta,
            "coverageDetails": {
                "partialCoverage": f"{Notional_percent}% coverage for damages caused by the temperature exceeding the benchmark of {stats['Upper_2_SD'].values[0]} °C for {strike} {strike_label}.",
                "fullCoverage": f"100% coverage for damages caused by the temperature exceeding the benchmark of {stats['Upper_2_SD'].values[0]} °C for {exit} {exit_label}."
            },
            "calculatedPayoutPercentage": Notional_percent,
            "dataSource": dataSource,
            "gridPoints": gridPoints,
            "benchmarkTemperature": f"{stats['Upper_2_SD'].values[0]} °C",
            "condition": condition,
            "statistics": yearly_statistics
        })
    
    return premium_results

# Function to execute the heat  calculation
async def execute_heat_strike_calculation(user_inputs, product_defaults, data,dataSource,additional_pincodes):
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

    return process_data(user_inputs, product_defaults, data, processed_pincodes,dataSource,formatted_gridPoints)
