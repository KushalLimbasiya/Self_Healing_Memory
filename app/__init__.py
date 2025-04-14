# This file makes the app directory a Python package
# It can contain initialization code for the package

import os
import logging

# Ensure the log directory exists
if not os.path.exists('logs'):
    os.makedirs('logs')

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

__version__ = '0.1.0'
