"""
conftest.py — inserts lcc_system/src/ into sys.path so all test files can do
'from models import ...' without package gymnastics.
"""
import sys
import os

# Insert src/ directory onto sys.path
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
SRC_DIR = os.path.abspath(SRC_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
