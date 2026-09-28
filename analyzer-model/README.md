
# Risk Analyzer API

The **Risk Analyzer API** is built with FastAPI to analyze environmental risks based on user-provided parameters, such as region, date range, and risk type.

## Folder Structure

```plaintext
risk_analyzer/
├── app/
│   └── app.py                # Main FastAPI application with versioned endpoints
├── data_service/
│   └── data_service.py       # Service layer for fetching data from the database
├── era5/
│   └── era5.py               # Logic for retrieving ERA5 data
├── imd/
│   └── imd.py                # Logic for retrieving IMD data
├── models/
│   ├── testmodel1.py         # Sample model for risk calculations
│   ├── testmodel_temperature.py  # model for temperature-specific calculations
│   └── json_files/           # JSON configurations for risk models
├── run_server.py             # Python dependencies
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

## How to Run

1. **Install Dependencies**:
   Create a virtual environment, activate it:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use venv\Scripts\activate
   ```

1. **Navigate to the Project Directory**:
   ```bash
   cd plutas-analyzer-model

   Create a virtual environment, activate it, and install dependencies:

   pip install -r requirements.txt
   ```

2. **Install Dependencies**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the FastAPI Server**:
   Start the FastAPI server with Uvicorn:

   ```bash
   uvicorn app.app:app --reload
   ```

   or 

   Run using 'python run_server.py'

4. **Access the API**:
   - **Swagger UI**: `http://127.0.0.1:8080/docs`
   - **API Root**: `http://127.0.0.1:8080/calculate_risk`
