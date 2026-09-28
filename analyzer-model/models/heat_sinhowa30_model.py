""" Data model for the Plutas platform. Defines Sequelize/ORM schema and table mapping.

 @file analyzer-model/models/heat_sinhowa30_model.py
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
from scipy import stats
import statsmodels.api as sm
from math import ceil
import calendar

import logging
from math import ceil
from datetime import timedelta
from dateutil.parser import parse

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_thresholds(data, percentiles, min_threshold, std_percentage, slope_percentage):
    if isinstance(data, pd.DataFrame):
        if 'Max_Temp' not in data.columns:
            raise ValueError("DataFrame must contain a 'Max_Temp' column with temperature values")
        numeric_data = pd.to_numeric(data['Max_Temp'], errors='coerce').dropna()
    else:
        numeric_data = pd.to_numeric(data, errors='coerce').dropna()
    
    if len(numeric_data) == 0:
        raise ValueError("No valid numeric data available for threshold calculation")
    
    if isinstance(data, pd.DataFrame):
        numeric_data = data[['Year', 'Max_Temp']].copy()
        numeric_data['Max_Temp'] = pd.to_numeric(numeric_data['Max_Temp'], errors='coerce')
        numeric_data = numeric_data.dropna()
    
    # Calculate linear regression slope
    X = sm.add_constant(numeric_data['Year'])
    model = sm.OLS(numeric_data['Max_Temp'], X).fit()
    slope = max(0, model.params['Year'])
    
    # Calculate standard deviation
    std_dev = numeric_data['Max_Temp'].std()
    
    # Calculate base percentile value
    # base_value = round(np.percentile(numeric_data['Max_Temp'], percentiles['strikePercentile'] * 100), 1)
    base_value = ceil(np.percentile(numeric_data['Max_Temp'], percentiles['strikePercentile'] * 100) * 10) / 10
    # Calculate threshold with adjustments
    strike_value = base_value + (std_dev * std_percentage) + (slope * slope_percentage)
    strike_value = round(strike_value, 1)
    
    # Apply minimum threshold constraint
    strike_value = max(strike_value, min_threshold["strike"])
    
    print(f"  [calculate_thresholds] base_value={base_value}, std_dev={std_dev:.4f}, slope={slope:.4f}")
    print(f"  [calculate_thresholds] std_adjustment={std_dev * std_percentage:.4f}, slope_adjustment={slope * slope_percentage:.4f}")
    print(f"  [calculate_thresholds] strike_value (before min)={round(base_value + (std_dev * std_percentage) + (slope * slope_percentage), 1)}, min_threshold={min_threshold['strike']}, final_strike={strike_value}")

    return {
        "strike": strike_value,
        "slope": slope,
        "std_dev": std_dev
    }


def adjust_risk_period_dates(user_inputs, product_defaults):
    logger.info("Starting adjust_risk_period_dates")

    # Log inputs
    logger.info(f"user_inputs: {user_inputs}")
    logger.info(f"product_defaults: {product_defaults}")

    # Parse dates
    try:
        start_date = parse(user_inputs["riskStartDate"])
        end_date = parse(user_inputs["riskEndDate"])
        logger.info(f"Parsed start_date: {start_date}, end_date: {end_date}")
    except Exception as e:
        logger.error("Date parsing failed", exc_info=True)
        raise ValueError(f"Invalid date format in userInputs: {e}")

    max_number_of_days = product_defaults["max_number_of_days"]
    logger.info(f"max_number_of_days: {max_number_of_days}")

    # Calculate original risk period duration
    days_count = (end_date - start_date).days + 1
    logger.info(f"Original days_count: {days_count}")

    # Determine adjustment
    pricing_default_date = 30
    if days_count < pricing_default_date:
        x = ceil((pricing_default_date - days_count) / 2)
        revised_start_date = start_date - timedelta(days=x)
        revised_end_date = end_date + timedelta(days=x)

    elif days_count > max_number_of_days:
        # optional: shrink (only if needed)
        x = ceil((days_count - max_number_of_days) / 2)
        revised_start_date = start_date + timedelta(days=x)
        revised_end_date = end_date - timedelta(days=x)


        logger.info("Adjustment applied")
        logger.info(f"Days added on each side: {x}")
    else:
        x = 0
        revised_start_date = start_date
        revised_end_date = end_date

        logger.info("No adjustment needed")

    logger.info(f"Revised start_date: {revised_start_date}")
    logger.info(f"Revised end_date: {revised_end_date}")

    # Recalculate revised duration
    revised_days_count = (revised_end_date - revised_start_date).days + 1
    logger.info(f"Revised days_count: {revised_days_count}")

    # Format dates
    formatted_start_date = revised_start_date.strftime("-%m-%d")
    formatted_end_date = revised_end_date.strftime("-%m-%d")

    logger.info(f"Formatted start_date: {formatted_start_date}")
    logger.info(f"Formatted end_date: {formatted_end_date}")

    # Pricing calculations
    sum_insured = user_inputs['sumInsured']
    per_day = round(sum_insured / days_count)
    calculated_sum_insured = per_day * revised_days_count
    payout_percentage = round(1 / revised_days_count, 4)

    logger.info(f"sum_insured: {sum_insured}")
    logger.info(f"per_day: {per_day}")
    logger.info(f"calculated_sum_insured: {calculated_sum_insured}")
    logger.info(f"payout_percentage: {payout_percentage}")

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

    logger.info(f"Final result: {result}")
    logger.info("Completed adjust_risk_period_dates")

    return result




def calculate_payouts(data, thresholds, user_inputs, plan_defaults, current_year, nth_year,product_defaults):
    data = data.copy()

    # Get risk period calculations
    results = adjust_risk_period_dates(user_inputs,product_defaults)
    payout_percentage = results['payout_percentage']
    calculated_sum_insured = results['calculated_sum_insured']

    temperature_anomaly = plan_defaults["temperature_anomaly"]

    payout1 = round(calculated_sum_insured * payout_percentage)
    payout2 = calculated_sum_insured

    payouts = {
        "payout1": payout1,
        "payout2": payout2,
    }

    # Ensure 'Year' column exists
    data['Year'] = pd.to_datetime(data['date']).dt.year

    # Calculate adjustment factor
    adjustment_factor = (nth_year - current_year) + 1
    anomaly_adjustment = temperature_anomaly * adjustment_factor
    detrended_temp = round(data['Max_Temp'] + anomaly_adjustment, 2)

    # Assign to all rows (since adjustment is scalar across the subset)
    data['Detrend_Max_Temp'] = detrended_temp
    # Apply payout logic for each threshold level
    for level, threshold in thresholds.items():
        data[f"{level}_payout"] = np.where(
            data["Detrend_Max_Temp"] >= threshold["strike"],
            payouts["payout1"],
            0
        )

    return data

def calculate_max_temperature(data, primary_pincodes):

    data["date"] = pd.to_datetime(data["date"])

    data["pincode"] = data["pincode"].astype(str)
    primary_pincodes = [str(p) for p in primary_pincodes]


    # Compute the maximum  for each date across all pincodes
    max_temperature_per_date = data.groupby("date")["Max_Temp"].max().reset_index()

    primary_pincode_data = max_temperature_per_date.copy()
    primary_pincode_data["pincode"] = primary_pincodes[0]


    return primary_pincode_data


def process_data(user_inputs, product_defaults, data, additional_pincodes, dataSource, gridPoints):
    primary_pincodes = user_inputs["pincodes"]  

    if not isinstance(primary_pincodes, list):
        primary_pincodes = [primary_pincodes]

    # Count unique pincodes in data
    unique_pincode_count = data["pincode"].nunique()

    # Call calculate_Max_Temp only if there's more than one pincode
    if unique_pincode_count > 1:
        data = calculate_max_temperature(data, primary_pincodes)
    else:
        print("Skipping calculate_Max_Temp as there is only one unique pincode in the data.")

    pincodes = data["pincode"].unique()  
    results = adjust_risk_period_dates(user_inputs,product_defaults)
    risk_end_date = results['revised_end_date']
    risk_start_date = results['revised_start_date']
    sumInsured = results['calculated_sum_insured']

    # ── DATA SUMMARY ──────────────────────────────────────────────────────────
    print("\n" + "█"*60)
    print("  DATA BEING USED FOR CALCULATION")
    print("█"*60)
    print(f"  Pincodes in dataset          : {list(pincodes)}")
    print(f"  Total rows in dataset        : {len(data)}")
    print(f"  Raw date range in dataset    : {data['date'].min().strftime('%Y-%m-%d')}  →  {data['date'].max().strftime('%Y-%m-%d')}")
    print(f"  Unique years in dataset      : {sorted(data['date'].dt.year.unique().tolist())}")
    print(f"  Total unique years           : {data['date'].dt.year.nunique()}")
    print()
    print(f"  ── Risk Period (user input) ──────────────────────────────")
    print(f"  User riskStartDate           : {user_inputs['riskStartDate']}")
    print(f"  User riskEndDate             : {user_inputs['riskEndDate']}")
    print(f"  Original days count          : {results['days_count']}")
    print()
    print(f"  ── Risk Period (after max_number_of_days adjustment) ─────")
    print(f"  max_number_of_days           : {product_defaults['max_number_of_days']}")
    print(f"  Days added each side         : {results['added_days_each_side']}")
    print(f"  Revised riskStartDate        : {results['revised_start_date']}")
    print(f"  Revised riskEndDate          : {results['revised_end_date']}")
    print(f"  Revised days count           : {results['revised_days_count']}")
    print()
    print(f"  ── Season window applied per year ───────────────────────")
    print(f"  Season start pattern         : YYYY{risk_start_date[4:]}")
    print(f"  Season end pattern           : YYYY{risk_end_date[4:]}")
    print()
    print(f"  ── Sum Insured ───────────────────────────────────────────")
    print(f"  User sumInsured              : {user_inputs['sumInsured']}")
    print(f"  Per-day amount               : {results['per_day_amount']}")
    print(f"  Pricing sumInsured (revised) : {sumInsured}")
    print("█"*60 + "\n")

    # Plan-specific parameters
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
    std_percentage = {
        "silver": product_defaults["silver_plan"][0]["silver_std_percentage"],
        "gold": product_defaults["gold_plan"][0]["gold_std_percentage"],
        "platinum": product_defaults["platinum_plan"][0]["platinum_std_percentage"]
    }
    slope_percentage = {
        "silver": product_defaults["silver_plan"][0]["silver_slope_percentage"],
        "gold": product_defaults["gold_plan"][0]["gold_slope_percentage"],
        "platinum": product_defaults["platinum_plan"][0]["platinum_slope_percentage"]
    }
    temperature_anomaly = {
        "silver": product_defaults["silver_plan"][0]["silver_temperature_anomaly"],
        "gold": product_defaults["gold_plan"][0]["gold_temperature_anomaly"],
        "platinum": product_defaults["platinum_plan"][0]["platinum_temperature_anomaly"]
    }

    min_year, max_year = data['date'].dt.year.min(), data['date'].dt.year.max()
    weather_start_date = data['date'].min()
    weather_end_date = data['date'].max()
    years_considered = (max_year - min_year) + 1
    print(
        "Validate weather data range:",
        weather_start_date.strftime("%Y-%m-%d"),
        "to",
        weather_end_date.strftime("%Y-%m-%d")
    )
    print("Validate total years considered:", years_considered)
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
            print(f"  [SEASON DATA] year={year} | window={season_start.strftime('%Y-%m-%d')} → {season_end.strftime('%Y-%m-%d')} | rows={len(year_data)} | MaxTemp={year_data['Max_Temp'].max():.1f} MinTemp={year_data['Max_Temp'].min():.1f}")
            year_data["Year"] = year
            strikes_data = pd.concat([strikes_data, year_data], ignore_index=True)
        else:
            print(f"  [SEASON DATA] year={year} | window={season_start.strftime('%Y-%m-%d')} → {season_end.strftime('%Y-%m-%d')} | rows=0  ⚠ NO DATA — year skipped")
    
    print(f"\n  [STRIKES_DATA TOTAL] {len(strikes_data)} rows across {strikes_data['Year'].nunique() if not strikes_data.empty else 0} years used for threshold calculation")

    if strikes_data.empty:
        raise ValueError(f"No valid strike data found for pincode {pincodes[0]}")

    # Calculate thresholds and store slope/std_dev
    thresholds = {}
    slopes = {}
    std_devs = {}
    
    for level in percentiles.keys():
        print(f"\n[THRESHOLD CALCULATION] Level={level}")
        threshold_result = calculate_thresholds(
            strikes_data, 
            percentiles[level], 
            min_threshold={
                "strike": min_threshold[level]["strike"], 
                "exit": min_threshold[level]["exit"]
            },
            std_percentage=std_percentage[level],
            slope_percentage=slope_percentage[level]
        )
        thresholds[level] = threshold_result
        slopes[level] = threshold_result.get('slope', 0)
        std_devs[level] = threshold_result.get('std_dev', 0)
        print(f"  [THRESHOLD RESULT] level={level} => strike={threshold_result['strike']}, slope={slopes[level]:.4f}, std_dev={std_devs[level]:.4f}")

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
            for level in percentiles.keys():
                plan_defaults = {
                    "temperature_anomaly": temperature_anomaly[level],
                }
                level_data = calculate_payouts(
                    year_data.copy(), 
                    {level: thresholds[level]}, 
                    user_inputs, 
                    plan_defaults,
                    current_year=year, 
                    nth_year=max_year,
                    product_defaults=product_defaults
                )
                burn_cost = level_data[f"{level}_payout"].sum()
                burn_cost = min(burn_cost, sumInsured)
                burn_costs[level].append({
                    "year": year, 
                    "totalBurnCost": burn_cost,
                    "Max_Temp": level_data["Max_Temp"].max()
                })

    last_premium_rate = None

    # Convert burn_costs to DataFrame for easier processing
    burn_dfs = {}
    for level in percentiles.keys():
        if burn_costs.get(level):
            burn_dfs[level] = pd.DataFrame(burn_costs[level])
            burn_dfs[level]['Year'] = burn_dfs[level]['year'] 

    # Dynamic bracket calculation
    years_per_bracket = 5
    weightage = product_defaults["weightage"][0]
    six_weights = list(weightage.values())

    for level in percentiles.keys():
        print(f"\n{'='*60}")
        print(f"[PREMIUM CALCULATION] Level={level.upper()}")
        print(f"{'='*60}")

        if level not in burn_dfs or burn_dfs[level].empty:
            print(f"  [SKIP] No valid burn cost data for {level}.")
            summary_data.append({
                'level': level,
                'avg_burn_cost': 0,
                'std_dev': 0,
                'risk_premium_rate': 0,
                'net_risk_premium_rate': 0
            })
            continue
        
        df = burn_dfs[level].copy()
        
        # Get year range and create dynamic brackets
        min_year = df['Year'].min()
        max_year = df['Year'].max()

        print(f"  [BURN COST] Year range: {min_year} - {max_year}")
        print(f"  [BURN COST] All yearly burn costs:\n{df[['Year','totalBurnCost','Max_Temp']].to_string(index=False)}")
        
        # Calculate number of complete 5-year brackets
        n_brackets = ((max_year - min_year) // years_per_bracket) + 1
        
        # Generate bins and labels
        bins = [min_year + i*years_per_bracket for i in range(n_brackets + 1)]
        labels = [
            f"{bins[i]}-{bins[i+1]-1}" 
            for i in range(len(bins)-1)
        ]

        print(f"  [BRACKETS] n_brackets={n_brackets}, bins={bins}, labels={labels}")
        
        # Apply brackets
        df['Bracket'] = pd.cut(
            df['Year'], 
            bins=bins, 
            right=False, 
            labels=labels,
            include_lowest=True
        )
        
        # Calculate bracket averages
        bracket_avg = df.groupby('Bracket', observed=True)['totalBurnCost'].mean().reset_index()
        bracket_avg.columns = ['Bracket', f'avg_{level}_burn_cost']

        print(f"  [BRACKET AVERAGES]:\n{bracket_avg.to_string(index=False)}")
        
        # Handle weights - use the first n weights where n is number of brackets
        if n_brackets > len(six_weights):
            weights = six_weights + [six_weights[-1]] * (n_brackets - len(six_weights))
        else:
            weights = six_weights[:n_brackets]
        
        # Normalize weights to sum to 1
        weights = [w/sum(weights) for w in weights]

        print(f"  [WEIGHTS] raw={six_weights[:n_brackets]}, normalized={[round(w, 4) for w in weights]}")
        
        # Calculate weighted average
        weighted_avg = (bracket_avg[f'avg_{level}_burn_cost'] * weights).sum()
        avg_burn_cost = weighted_avg

        print(f"  [WEIGHTED AVG BURN COST] = {avg_burn_cost:.4f}")

        # Calculate statistics
        std_dev_burn_cost = df['totalBurnCost'].std(ddof=1)
        std_dev_percent = std_dev_burn_cost / sumInsured if sumInsured > 0 else 0
        risk_premium_rate = avg_burn_cost / sumInsured if sumInsured > 0 else 0
        net_risk_premium_rate = (
            (risk_premium_rate / priced_loss_ratio[level]) * 
            (1 + data_variability[level]) / 
            (1 - management_loading[level])
        ) if priced_loss_ratio[level] > 0 and (1 - management_loading[level]) > 0 else 0

        print(f"\n  [PREMIUM RATE INPUTS]")
        print(f"    sumInsured (pricing)      = {sumInsured}")
        print(f"    avg_burn_cost             = {avg_burn_cost:.4f}")
        print(f"    std_dev_burn_cost         = {std_dev_burn_cost:.4f}")
        print(f"    std_dev_percent           = {std_dev_percent:.6f}")
        print(f"    risk_premium_rate         = avg_burn_cost / sumInsured = {avg_burn_cost:.4f} / {sumInsured} = {risk_premium_rate:.6f}")
        print(f"    priced_loss_ratio         = {priced_loss_ratio[level]}")
        print(f"    data_variability          = {data_variability[level]}")
        print(f"    management_loading        = {management_loading[level]}")
        print(f"  [FORMULA] net_risk_premium_rate = (risk_premium_rate / priced_loss_ratio) * (1 + data_variability) / (1 - management_loading)")
        print(f"  [FORMULA] = ({risk_premium_rate:.6f} / {priced_loss_ratio[level]}) * (1 + {data_variability[level]}) / (1 - {management_loading[level]})")
        print(f"  [RESULT]  net_risk_premium_rate (pre-adjustment) = {net_risk_premium_rate:.6f}")
        
        print(f"  - Initial Net Risk Premium Rate: {net_risk_premium_rate}")
        print(f" -  premium_difference_percent : {product_defaults['premium_difference_percent']}")
        
        if last_premium_rate is not None:
            print(f"\n  [TIER ADJUSTMENT CHECK] level={level}, last_premium_rate={last_premium_rate:.6f}")
            print(f"  - Last Premium Rate: {last_premium_rate}")
            premium_diff_threshold = product_defaults["premium_difference_percent"]
            difference = net_risk_premium_rate - last_premium_rate
            
            print(f"  - Difference between current and last premium rate: {difference:.6f} (threshold={premium_diff_threshold})")
            print("level", level)
            
            if level == "gold" and difference < premium_diff_threshold:
                print(f"  [ADJUST] {level} rate too close to silver. Forcing net_risk_premium_rate = {last_premium_rate:.6f} + {premium_diff_threshold} = {last_premium_rate + premium_diff_threshold:.6f}")
                net_risk_premium_rate = last_premium_rate + premium_diff_threshold

            elif level == "platinum" and difference < premium_diff_threshold:
                print(f"  [ADJUST] {level} rate too close to gold. Forcing net_risk_premium_rate = {last_premium_rate:.6f} + {premium_diff_threshold} = {last_premium_rate + premium_diff_threshold:.6f}")
                net_risk_premium_rate = last_premium_rate + premium_diff_threshold

            print(f"  - Final Net Risk Premium Rate for {level}: {net_risk_premium_rate:.6f}")

        print("net_risk_premium_rate---------", net_risk_premium_rate)
        base_premium = net_risk_premium_rate * user_inputs['sumInsured']

        print(f"\n  [BASE PREMIUM CALCULATION]")
        print(f"    net_risk_premium_rate     = {net_risk_premium_rate:.6f}")
        print(f"    user sumInsured           = {user_inputs['sumInsured']}")
        print(f"    base_premium              = net_risk_premium_rate * sumInsured = {base_premium:.4f}")
        print(f"    min_base_premium (config) = base_premium_percentage * sumInsured = {base_premium_percentage[level]} * {user_inputs['sumInsured']} = {base_premium_percentage[level] * user_inputs['sumInsured']:.4f}")
        print(f"  - Base Premium: {base_premium}")
        print(f"  - Directus Base Premium: {base_premium_percentage[level]}")
        print(f" -directus_base_premium * user_inputs['sumInsured'] : {base_premium_percentage[level] * user_inputs['sumInsured']}")
        
        # If base premium is zero or less than the threshold, adjust it
        if base_premium == 0 or base_premium < (base_premium_percentage[level] * user_inputs['sumInsured']):
            print(f"\n  [BASE PREMIUM FLOOR TRIGGERED] base_premium={base_premium:.4f} < floor={base_premium_percentage[level] * user_inputs['sumInsured']:.4f}")
            print(f"Base premium is zero or less than directus_base_premium threshold. Adjusting net risk premium rate and recalculating base premium, based on directus_base_premium {base_premium_percentage[level]}")

            # Adjust net risk premium rate and base premium
            net_risk_premium_rate = base_premium_percentage[level]  
            base_premium = base_premium_percentage[level] * user_inputs['sumInsured']  # Directly set the minimum required value

            print(f"  - Adjusted Net Risk Premium Rate:{level} {net_risk_premium_rate}")
            print(f"  - Final Adjusted Base Premium:{level} {base_premium}")

        last_premium_rate = net_risk_premium_rate
        print(f"\n  [FINAL] level={level}, net_risk_premium_rate={net_risk_premium_rate:.6f}, base_premium={base_premium:.4f}")
        print(f"  [CARRY FORWARD] last_premium_rate updated to {last_premium_rate:.6f} for next tier comparison")
        
        yearly_statistics = [
            {
                "year": int(bc["year"]), 
                "Max_Temp": round(float(np.nan_to_num(bc["Max_Temp"], nan=0.0)), 2)
            }
            for bc in burn_costs[level]
        ]

        yearly_statistics = sorted(yearly_statistics, key=lambda x: x["Max_Temp"], reverse=True)[:10]

        print("avg_burn_cost", avg_burn_cost)
        summary_data.append(
            create_level_summary(
                pincodes=pincodes,
                level=level,
                strikes=thresholds,
                avg_burn_cost=avg_burn_cost,
                std_dev=std_dev_burn_cost,
                risk_premium=(risk_premium_rate, net_risk_premium_rate),
                std_dev_percent=std_dev_percent,
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
                base_premium=base_premium,
                slope=slopes[level],
                std_dev_temp=std_devs[level]
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

def create_level_summary(pincodes, level, strikes, avg_burn_cost, std_dev, risk_premium, std_dev_percent, 
                       dataVariability, management_loading, delta, priced_loss_ratio, percentiles, 
                       yearly_statistics, product_defaults, user_inputs, additional_pincodes, 
                       dataSource, gridPoints, base_premium, slope, std_dev_temp):
    # Calculate base premium based on net risk premium rate
    net_risk_premium_rate = risk_premium[1]

    result = adjust_risk_period_dates(user_inputs,product_defaults)
    pricingInsured= result['calculated_sum_insured']
    print("calculated_sum_insured", pricingInsured)


    payout_percentage = calculate_per_day_payout_percentage(user_inputs)

    # Generate coverage details
    coverage_details = {
        "partialCoverage": f"{payout_percentage}% coverage for damages caused by temperature exceeding {strikes[level]['strike']} °C.",
    }
    
    primary_pincodes = user_inputs["pincodes"]
    print("level & threshold", level, strikes[level])

    condition = f"Any day during the coverage period, exceeding the temperature of {strikes[level]['strike']} °C"
    
    return {
        "model": "SingleDay HeatWave 30days",
        "riskStartDate": user_inputs['riskStartDate'],
        "riskEndDate": user_inputs['riskEndDate'],
        "prsd": result['revised_start_date'],
        "pred": result['revised_end_date'],   
        "pincode": list(map(str, primary_pincodes)),
        "additionalPincodes": additional_pincodes,
        "radius": user_inputs['radius'],
        "level": level,
        "strike": "1 day",
        "slope": slope, 
        "std_dev": std_dev_temp  ,
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
        "benchmarkTemperature": f"{strikes[level]['strike']} °C",
        "condition": condition,
        "statistics": yearly_statistics
    }

# Function to execute the heat strike calculation
async def execute_heat_strike_calculation(user_inputs, product_defaults, data, dataSource,additional_pincodes):
    print("---------------------------------")
    print("Initial additional pincodes list:", additional_pincodes)
    
    # Check if additional_pincodes is a list and convert it to a DataFrame
    if isinstance(additional_pincodes, list):
        additional_pincodes = pd.DataFrame(additional_pincodes, columns=['pincode'])
        print("Converted additional_pincodes to DataFrame.")

    # Ensure 'pincode' column is treated as a string
    additional_pincodes['pincode'] = additional_pincodes['pincode'].astype(str)

    # Localize the dates directly to IST (Asia/Kolkata)
    data["date"] = data["date"].dt.tz_localize('Asia/Kolkata')

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