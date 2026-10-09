"""
SmartStock — Master Pipeline Runner
===================================
Executes the full end-to-end supply chain analytics pipeline in sequential order:
1. Data Ingestion & Operational Layer Generation (data_pipeline.py)
2. Exploratory Profiling & ABC-XYZ Segmentation (eda_analytics.py)
3. Out-of-Sample Demand Forecasting Benchmark (forecasting.py)
4. Stochastic Inventory Optimization Engine (inventory_engine.py)
5. Daily Discrete-Event Simulation Audit (simulation.py)
6. Parametric Scenario Stress-Testing (scenario_analysis.py)
7. Power BI Star-Schema Export (export_powerbi.py)
"""

import time
import subprocess
import sys


def run_step(step_num: int, total_steps: int, description: str, script_name: str):
    print("\n" + "=" * 80)
    print(f"STEP [{step_num}/{total_steps}]: {description.upper()}")
    print(f"Executing: python src/{script_name}")
    print("=" * 80)
    
    start_time = time.time()
    result = subprocess.run([sys.executable, f"src/{script_name}"], capture_output=False)
    elapsed = time.time() - start_time
    
    if result.returncode != 0:
        print(f"\n[ERROR] Step {step_num} ({script_name}) failed with exit code {result.returncode}!")
        sys.exit(result.returncode)
    else:
        print(f"\n-> Step {step_num} completed successfully in {elapsed:.1f} seconds.")


def main():
    print("*" * 80)
    print("       SMARTSTOCK: END-TO-END SUPPLY CHAIN OPTIMIZATION PIPELINE")
    print("*" * 80)
    total_start = time.time()

    steps = [
        ("Data Ingestion & Operational Modeling", "data_pipeline.py"),
        ("Data Hygiene & ABC-XYZ Profiling", "eda_analytics.py"),
        ("Out-of-Sample Demand Forecasting Benchmark", "forecasting.py"),
        ("Stochastic Inventory Optimization (SS, ROP, EOQ)", "inventory_engine.py"),
        ("28-Day Daily Discrete-Event Inventory Simulation", "simulation.py"),
        ("Parametric Scenario Sensitivity Engine", "scenario_analysis.py"),
        ("Power BI Star-Schema Dataset Preparation", "export_powerbi.py"),
    ]

    for idx, (desc, script) in enumerate(steps, 1):
        run_step(idx, len(steps), desc, script)

    total_time = time.time() - total_start
    print("\n" + "*" * 80)
    print(f"SUCCESS: ALL 7 PIPELINE MODULES EXECUTED IN {total_time:.1f} SECONDS!")
    print("All processed data, charts, and Power BI tables are up-to-date.")
    print("To launch the interactive simulator, run: streamlit run app/streamlit_app.py")
    print("*" * 80)


if __name__ == "__main__":
    main()
