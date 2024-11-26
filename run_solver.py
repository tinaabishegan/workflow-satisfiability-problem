# run_solver.py
import sys
import importlib
import time

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python run_solver.py <solver_module_name> <instance_file>")
        sys.exit(1)

    solver_module_name = sys.argv[1]
    instance_file = sys.argv[2]

    try:
        solver_module = importlib.import_module(solver_module_name)
    except ImportError as e:
        print(f"Error: Failed to import solver module '{solver_module_name}': {e}")
        sys.exit(1)

    start_time = time.time()
    try:
        result = solver_module.Solver(instance_file)
        end_time = time.time()
        elapsed_time = (end_time - start_time) * 1000  # Convert to milliseconds
        sat_status = result.get('sat', 'unsat')
        # Output the result in a standardized format
        print(f"sat_status:{sat_status}")
        print(f"time_ms:{elapsed_time}")
    except Exception as e:
        print(f"Error: Solver execution failed: {e}")
        sys.exit(1)
