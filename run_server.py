"""
One-click server launcher for RVSAT-1 Flight Operations Web Application.
"""
import sys
import os
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=======================================================================")
    print("         LAUNCHING RVSAT-1 MISSION CONTROL FLIGHT SERVER               ")
    print("=======================================================================")
    print("  URL: http://localhost:8000")
    print("  Scoreboard Projector: http://localhost:8000/scoreboard")
    print("  Admin Console: http://localhost:8000/admin")
    print("=======================================================================\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
