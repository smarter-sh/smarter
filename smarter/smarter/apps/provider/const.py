"""
Constants for the provider app.
"""

import os


namespace = "provider"
VERIFICATION_LIFETIME = 60 * 60 * 24 * 10  # 10 calendar days, expressed in seconds
VERIFICATION_LEAD_TIME = 60 * 60 * 36  # 36 hours in seconds

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.abspath(os.path.join(HERE, "data"))
