#!/usr/bin/env python3
"""
Voice Commander Qt - A voice-controlled assistant with Qt UI
"""

import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from scripts
from scripts.main_qt import main

if __name__ == "__main__":
    main() 