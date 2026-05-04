#!/usr/bin/env python3
"""Test if matplotlib is accessible."""
import sys
import os

print(f"Python: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"PATH: {os.environ.get('PATH', 'not set')}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'not set')}")

# Check matplotlib
try:
    import matplotlib
    print(f"matplotlib: {matplotlib.__version__}")
    print(f"matplotlib location: {matplotlib.__file__}")
except ImportError as e:
    print(f"matplotlib import FAILED: {e}")

# Check site-packages
import site
print(f"site-packages: {site.getsitepackages()}")
print(f"user site: {site.getusersitepackages()}")

# Check if matplotlib is in the local path
local_path = os.path.expanduser("~/.local/lib/python3.9/site-packages")
print(f"Local site-packages exists: {os.path.exists(local_path)}")
if os.path.exists(local_path):
    print(f"Contents: {os.listdir(local_path)[:10]}")

print("Test complete!")
