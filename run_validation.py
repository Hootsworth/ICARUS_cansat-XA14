"""
One-click validation and test harness for the RVSAT-1 Satellite Telemetry Challenge.
Executes the reference solver across all 11 team datasets and verifies 100% correctness.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solver.solve import test_all_teams

if __name__ == "__main__":
    print("=======================================================================")
    print("          RVSAT-1 REFERENCE SOLVER & QUALITY TEST HARNESS             ")
    print("=======================================================================")
    success = test_all_teams()
    if success:
        print("\n[VERIFIED] ALL 11 TEAMS PASSED 100% OF CHALLENGE CRITERIA!")
        sys.exit(0)
    else:
        print("\n[ERROR] ONE OR MORE TEAM DATASETS FAILED VERIFICATION!")
        sys.exit(1)
