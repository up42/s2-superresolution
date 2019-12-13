"""
This module is used in test_s2_tiles_supres script.
"""
import sys
import os

# Import the required classes and functions
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/predict"))
)
# pylint: disable=unused-import,wrong-import-position
from s2_tiles_supres import Superresolution

# pylint: disable=unused-import,wrong-import-position,line-too-long
from helper import (
    LOG_FORMAT,
    get_logger,
    load_params,
    load_metadata,
    ensure_data_directories_exist,
    SENTINEL2_L1C,
)

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/utils"))
)
# pylint: disable=unused-import,wrong-import-position
from synthetic_image import SyntheticImage
