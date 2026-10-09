"""
Standalone test runner using standard library unittest for VoicePilot.
"""

import sys
import os
import unittest

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.test_agent import *

if __name__ == '__main__':
    unittest.main()
