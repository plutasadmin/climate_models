""" Climate risk analyzer module: Run Server.

 @file analyzer-model/run_server.py
"""

import uvicorn  # Import the Uvicorn ASGI server

if __name__ == "__main__":
    """
    Starts the Uvicorn ASGI server to run the FastAPI/Starlette application.
    
    Parameters:
        - "app.app:app" → Path to the FastAPI/Starlette application instance.
            - 'app' (first) refers to the package/module.
            - 'app' (second) is the FastAPI instance inside the module.
        - host="0.0.0.0" → Makes the app accessible from any IP address.
        - port=8080 → Runs the server on port 8080.
        - reload=True → Enables auto-reloading on code changes (useful in development).
        - log_level="debug" (commented) → Enables detailed debugging logs when uncommented.
    """
    uvicorn.run("app.app:app", host="0.0.0.0", port=8080, reload=True)## log_level="debug")  # Run the server
