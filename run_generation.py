"""
One-click dataset and challenge generator for RVSAT-1 Satellite Telemetry Challenge.
"""
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generator.gen import generate_all_teams

if __name__ == "__main__":
    print("=======================================================================")
    print("      RVSAT-1 SATELLITE TELEMETRY DATASET & PACKAGE GENERATOR          ")
    print("=======================================================================")
    generate_all_teams()
    print("\n[SUCCESS] Datasets, encrypted packages, and answer keys generated successfully!")
