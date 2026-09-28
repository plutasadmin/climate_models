""" Climate risk analyzer module: Logging Setup.

 @file analyzer-model/logging_setup.py
"""

from logging.handlers import RotatingFileHandler
import logging
import os
from datetime import datetime

def setup_logging():
    # Create a directory for logs if it doesn't already exist
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Log file name based on today's date
    log_file_name = f"calculate_risk_log_{datetime.now().strftime('%d_%m_%Y')}.log"
    log_file_path = os.path.join(logs_dir, log_file_name)

    # Define log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Log everything from DEBUG and above

    # Set up the rotating file handler with maxBytes = 100 MB
    rotating_handler = RotatingFileHandler(
        log_file_path, maxBytes=100*1024*1024, backupCount=5  # 100 MB per file, 5 backups
    )
    rotating_handler.setFormatter(formatter)

    # Add the rotating file handler to the root logger
    root_logger.addHandler(rotating_handler)
    # Set up stream handler (console output)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)