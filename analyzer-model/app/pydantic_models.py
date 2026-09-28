""" Climate risk analyzer module: Pydantic Models.

 @file analyzer-model/app/pydantic_models.py
"""

from typing import List, Optional
from pydantic import BaseModel, Field, StrictInt, root_validator, validator

### =========================
###    REQUEST MODELS
### =========================

class UserInputs(BaseModel):
    """
    Model to capture user input parameters for risk assessment.
    """
    pincodes: Optional[List[str]] = Field(None, description="List of pincodes for the areas being analyzed.")
    radius: Optional[float] = Field(0, description="Radius around the specified location(s) for risk assessment.")
    riskStartDate: Optional[str] = Field(None, description="Start date for the risk analysis period (format: YYYY-MM-DD).")
    riskEndDate: Optional[str] = Field(None, description="End date for the risk analysis period (format: YYYY-MM-DD).")
    sumInsured: StrictInt = Field(None, description="The total amount insured under the policy.")
    to_pincode: Optional[str] = Field(None, description="The destination pincode for the risk assessment.")

    @validator("sumInsured", pre=True)
    def validate_sumInsured(cls, value):
        if isinstance(value, float):
            raise ValueError(f"Expected an integer, but got a float: {value}")
        if isinstance(value, str):
            raise ValueError(f"Expected an integer, but got a string: '{value}'")
        return value

class silverPlanDetails(BaseModel):
    """
    Model for capturing details of the Silver plan.
    """
    silver_strike: StrictInt = Field(None, description="Threshold value for the first silver plan trigger.")
    silver_exit: StrictInt = Field(None, description="Exit point for the silver plan.")
    silver_management_loading: Optional[float] = Field(
        None, description="Management overhead applied during pricing."
    )
    silver_priced_loss_ratio: StrictInt = Field(None, description="The loss ratio used in pricing calculations.")
    silver_data_variability: Optional[float] = Field(None, description="Overall variability in data used for risk analysis.")
    silver_threshold_strike: StrictInt = Field(None, description="Threshold value for the silver if the strike is 0.")
    silver_threshold_exit: StrictInt = Field(None, description="Exit point for the silver if the exit is 0.")
    silver_strike_exit_delta: StrictInt = Field(None, description="Adjustment applied if strike and exit values match.")
    silver_base_premium: Optional[float] = Field(None, description="The base premium for the silver plan.")
    silver_std_percentage: Optional[float] = Field(
        0, description="Standard deviation percentage for the silver plan."
    )
    silver_slope_percentage: Optional[float] = Field(
        0, description="Slope percentage for the silver plan."
    )
    silver_temperature_anomaly: Optional[float] = Field(
        0, description="Temperature anomaly percentage for the silver plan.")
    
    @validator(
        "silver_strike",
        "silver_exit",
        "silver_priced_loss_ratio",
        "silver_threshold_strike",
        "silver_threshold_exit",
        "silver_strike_exit_delta",
        pre=True,
    )
    def check_integer_type(cls, value, field):
        if isinstance(value, float):
            raise ValueError(f"Expected an integer for {field.name}, but got a float: {value}")
        if isinstance(value, str):
            raise ValueError(f"Expected an integer for {field.name}, but got a string: '{value}'")
        return value


class goldPlanDetails(BaseModel):
    """
    Model for capturing details of the Gold plan.
    """
    gold_strike: StrictInt = Field(None, description="Threshold value for the first gold plan trigger.")
    gold_exit: StrictInt = Field(None, description="Exit point for the gold plan.")
    gold_management_loading: Optional[float] = Field(
        None, description="Management overhead applied during pricing."
    )
    gold_priced_loss_ratio: StrictInt = Field(None, description="The loss ratio used in pricing calculations.")
    gold_data_variability: Optional[float] = Field(None, description="Overall variability in data used for risk analysis.")
    gold_threshold_strike: StrictInt = Field(None, description="Threshold value for the gold if the strike is 0.")
    gold_threshold_exit: StrictInt = Field(None, description="Exit point for the gold if the exit is 0.")
    gold_strike_exit_delta: StrictInt = Field(None, description="Adjustment applied if strike and exit values match.")
    gold_base_premium: Optional[float] = Field(None, description="The base premium for the gold plan.")
    gold_std_percentage: Optional[float] = Field(
        0, description="Standard deviation percentage for the gold plan."
    )
    gold_slope_percentage: Optional[float] = Field(
        0, description="Slope percentage for the gold plan."
    )
    gold_temperature_anomaly: Optional[float] = Field(
        0, description="Temperature anomaly percentage for the gold plan.")

    @validator(
        "gold_strike",
        "gold_exit",
        "gold_priced_loss_ratio",
        "gold_threshold_strike",
        "gold_threshold_exit",
        "gold_strike_exit_delta",
        pre=True,
    )
    def check_integer_type(cls, value, field):
        return silverPlanDetails.check_integer_type(value, field)


class platinumPlanDetails(BaseModel):
    """
    Model for capturing details of the Platinum plan.
    """
    platinum_strike: StrictInt = Field(None, description="Threshold value for the first platinum plan trigger.")
    platinum_exit: StrictInt = Field(None, description="Exit point for the platinum plan.")
    platinum_management_loading: Optional[float] = Field(
        None, description="Management overhead applied during pricing."
    )
    platinum_priced_loss_ratio: StrictInt = Field(None, description="The loss ratio used in pricing calculations.")
    platinum_data_variability: Optional[float] = Field(None, description="Overall variability in data used for risk analysis.")
    platinum_threshold_strike: StrictInt = Field(None, description="Threshold value for the platinum if the strike is 0.")
    platinum_threshold_exit: StrictInt = Field(None, description="Exit point for the platinum if the exit is 0.")
    platinum_strike_exit_delta: StrictInt = Field(None, description="Adjustment applied if strike and exit values match.")
    platinum_base_premium: Optional[float] = Field(None, description="The base premium for the platinum plan.")
    platinum_std_percentage: Optional[float] = Field(
        0, description="Standard deviation percentage for the platinum plan."
    )
    platinum_slope_percentage: Optional[float] = Field(
        0, description="Slope percentage for the platinum plan."
    )
    platinum_temperature_anomaly: Optional[float] = Field(
        0, description="Temperature anomaly percentage for the platinum plan.")
    

    @validator(
        "platinum_strike",
        "platinum_exit",
        "platinum_priced_loss_ratio",
        "platinum_threshold_strike",
        "platinum_threshold_exit",
        "platinum_strike_exit_delta",
        pre=True,
    )
    def check_integer_type(cls, value, field):
        return silverPlanDetails.check_integer_type(value, field)


class weightageDetails(BaseModel):
    """
    Model for capturing weightage allocation across different year periods.
    """
    weightage_0_5_years: StrictInt = Field(None, description="Weightage for the first 0-5 years")
    weightage_6_10_years: StrictInt = Field(None, description="Weightage for the 6-10 year period")
    weightage_11_15_years: StrictInt = Field(None, description="Weightage for the 11-15 year period")
    weightage_16_20_years: StrictInt = Field(None, description="Weightage for the 16-20 year period")
    weightage_21_25_years: StrictInt = Field(None, description="Weightage for the 21-25 year period")
    weightage_26_30_years: StrictInt = Field(None, description="Weightage for the 26-30 year period")

    @validator("*", pre=True)
    def check_integer_type(cls, value, field):
        return silverPlanDetails.check_integer_type(value, field)

    @root_validator
    def check_weightage_sum(cls, values):
        total_weight = sum(values.values())
        if total_weight < 0 or total_weight > 100:
            raise ValueError(f"Total weightage must be between 0 and 100. Provided: {total_weight}")
        return values


class ProductDefaults(BaseModel):
    """
    Model capturing the default values for different product parameters.
    """
    peril: str = Field(..., min_length=1, description="The peril or hazard being analyzed (e.g., rain, heat). Peril type is required and cannot be empty")
    peril_category: Optional[str] = Field(None, description="The category of the peril (e.g., high rain, low rain, heatwave).")
    industry: Optional[str] = Field(None, description="The industry for which the risk is being analyzed.")
    silver_plan: Optional[List[silverPlanDetails]] = Field(None, description="Details of Silver plan.")
    gold_plan: Optional[List[goldPlanDetails]] = Field(None, description="Details of Gold plan.")
    platinum_plan: Optional[List[platinumPlanDetails]] = Field(None, description="Details of Platinum plan.")
    weightage: Optional[List[weightageDetails]] = Field(None, description="Weightage allocation for different year periods.")
    index_days: StrictInt = Field(1, description="The number of days used for rolling sum rainfall data.")
    payout_percentage: StrictInt = Field(1, description="The percentage of payout for each risk event.")
    premium_difference_percent: StrictInt = Field(None, description="The percentage difference between the premium plans.")
    max_number_of_days = StrictInt = Field(30, description="The maximum number of days for risk assessment.")
    @validator("index_days", "payout_percentage", "premium_difference_percent", pre=True)

    def check_integer_values(cls, value, field):

        if isinstance(value, float):

            raise ValueError(f"Expected an integer for {field.name}, but got a float: {value}")

        if isinstance(value, str):

            raise ValueError(f"Expected an integer for {field.name}, but got a string: '{value}'")

        return value


class CalculateRiskRequest(BaseModel):
    """
    Model for calculating risk, combining user inputs and product defaults.
    """
    userInputs: Optional[UserInputs] = Field(None, description="Inputs provided by the user for risk calculation.")
    productDefaults: Optional[ProductDefaults] = Field(None, description="Defaults for product plans, variability, and payouts.")
    maxRadiusAllowedValue: StrictInt = Field(None, description="Maximum radius allowed for risk assessment.")


class WeatherUpdate(BaseModel):
    """
    Model representing a weather update entry.
    """
    climatetype: str
    pincode: int
    date: str
    value: float
    source: str
