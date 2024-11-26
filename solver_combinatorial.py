import os
import re
from time import time as currenttime
from ortools.sat.python import cp_model
import itertools

def parse_file(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # Parse #Steps, #Users, #Constraints
    steps_count = int(lines[0].split(': ')[1])
    users_count = int(lines[1].split(': ')[1])
    constraints_count = int(lines[2].split(': ')[1])
    
    constraints = []
    user_capacity_constraints = []
    for line in lines[3:]:
        line = line.strip()
        if line.startswith("User-capacity"):
            parts = line.split()
            user = int(parts[1][1:])
            capacity = int(parts[2])
            user_capacity_constraints.append((user, capacity))
        else:
            constraints.append(line)

    return steps_count, users_count, constraints, user_capacity_constraints


def Solver(filename, progress_callback=None, **kwargs):
    model = cp_model.CpModel()
    steps_count, users_count, constraints, user_capacity_constraints = parse_file(filename)
    
    # Create variables: one for each step indicating assigned user (1 to users_count)
    assignments = [model.NewIntVar(1, users_count, f'step_{i + 1}') for i in range(steps_count)]
    
    # Track authorised steps per user to ensure only one authorisation entry per user
    user_authorisations = {}

    # Store all One-Team constraints to process later
    one_team_constraints = []

    # Parse constraints and apply them to the model
    for constraint in constraints:
        parts = constraint.split()
        
        if parts[0] == "Authorisations":
            user = int(parts[1][1:])
            allowed_steps = [int(step[1:]) for step in parts[2:]]
            
            # Check for duplicate authorisation entries for the same user
            if user in user_authorisations:
                print(f"Warning: User u{user} has multiple authorisations defined; only the first will be used.")
                continue
            
            user_authorisations[user] = allowed_steps
            for step in range(steps_count):
                if step + 1 not in allowed_steps:
                    model.Add(assignments[step] != user)
            print(f"Applied Authorisation constraint for user u{user} on steps {allowed_steps}")

        elif parts[0] == "Separation-of-duty":
            step1, step2 = int(parts[1][1:]), int(parts[2][1:])
            model.Add(assignments[step1 - 1] != assignments[step2 - 1])
            print(f"Applied Separation-of-duty constraint between steps s{step1} and s{step2}")

        elif parts[0] == "Binding-of-duty":
            step1, step2 = int(parts[1][1:]), int(parts[2][1:])
            model.Add(assignments[step1 - 1] == assignments[step2 - 1])
            print(f"Applied Binding-of-duty constraint between steps s{step1} and s{step2}")

        elif parts[0] == "At-most-k":
            k = int(parts[1])
            step_indices = [int(s[1:]) - 1 for s in parts[2:]]
            steps_T = [assignments[i] for i in step_indices]

            # Optimized At-most-k using combinations
            if k < len(steps_T):
                for combo in itertools.combinations(step_indices, k + 1):
                    # For each combination of k+1 steps, at least one pair must be assigned the same user
                    same_user_pairs = []
                    for (i, j) in itertools.combinations(combo, 2):
                        same_user = model.NewBoolVar(f'steps_{i+1}_{j+1}_same_user')
                        model.Add(assignments[i] == assignments[j]).OnlyEnforceIf(same_user)
                        model.Add(assignments[i] != assignments[j]).OnlyEnforceIf(same_user.Not())
                        same_user_pairs.append(same_user)
                    # At least one pair must be assigned to the same user
                    model.AddBoolOr(same_user_pairs)
                print(f"Applied optimized At-most-k constraint on steps {[i + 1 for i in step_indices]} with max {k} unique users")
            else:
                print(f"At-most-k constraint ignored for steps {[i + 1 for i in step_indices]} with k >= number of steps")

        elif parts[0] == "One-team":            

            # Parse the steps and teams
            group_steps = []
            team_groups = []

            line = constraint  # Use the entire line for regex parsing

            # Extract steps
            steps = re.findall(r's(\d+)', line)
            group_steps = [int(s) for s in steps]

            # Extract teams
            teams_raw = re.findall(r'\(([^)]+)\)', line)
            team_groups = []
            for team_str in teams_raw:
                users = re.findall(r'u(\d+)', team_str)
                team_groups.append([int(u) for u in users])

            # Check if steps and teams were successfully parsed
            if not group_steps or not team_groups:
                print(f"Warning: Unable to parse One-team constraint: {line}")
                continue  # Skip to next constraint

            # Store the constraint data
            one_team_constraints.append({
                'steps': group_steps,
                'teams': team_groups,
            })
            print(f"Parsed One-team constraint for steps {group_steps} with team groups {team_groups}")

    # After parsing all constraints, process the One-Team constraints
    for idx, otc in enumerate(one_team_constraints):
        steps = otc['steps']
        teams = otc['teams']
        step_vars = [assignments[s - 1] for s in steps]
        allowed_combinations = []
        for team in teams:
            team_combinations = itertools.product(team, repeat=len(steps))
            for combo in team_combinations:
                allowed_combinations.append(combo)
        model.AddAllowedAssignments(step_vars, allowed_combinations)
        print(f"Applied One-team constraint for steps {steps} with teams {teams}")

    # Handle users with no specified authorisations: allow any step
    all_steps = set(range(1, steps_count + 1))
    for user in range(1, users_count + 1):
        if user not in user_authorisations:
            print(f"User u{user} has no specific authorisations; allowed on any step.")

    # Add User-Capacity constraints
    for user, capacity in user_capacity_constraints:
        assigned_steps = []
        for step in range(steps_count):
            is_assigned = model.NewBoolVar(f'user_{user}_assigned_to_step_{step+1}')
            model.Add(assignments[step] == user).OnlyEnforceIf(is_assigned)
            model.Add(assignments[step] != user).OnlyEnforceIf(is_assigned.Not())
            assigned_steps.append(is_assigned)
        model.Add(sum(assigned_steps) <= capacity)
        print(f"Applied User-Capacity constraint: user u{user} can perform at most {capacity} steps")

    # Solve the model with additional settings for detailed logging
    solver = cp_model.CpSolver()
    # solver.parameters.log_search_progress = True  # Enables logging for troubleshooting

    starttime = int(currenttime() * 1000)

    # If a progress callback is provided, use it
    if progress_callback:
        class VarArraySolutionPrinterWithProgress(cp_model.CpSolverSolutionCallback):
            """Print intermediate solutions and report progress."""

            def __init__(self, variables, total_steps, callback):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self._variables = variables
                self._total_steps = total_steps
                self._callback = callback
                self._solution_count = 0

            def on_solution_callback(self):
                self._solution_count += 1
                progress = int((self._solution_count / self._total_steps) * 100)
                self._callback(progress)

        # Estimate total steps (this is just a placeholder)
        total_steps = 100
        solution_printer = VarArraySolutionPrinterWithProgress(assignments, total_steps, progress_callback)
        status = solver.Solve(model, solution_printer)
    else:
        status = solver.Solve(model)

    endtime = int(currenttime() * 1000)
    
    d = {
        'sat': 'unsat',
        'sol': [],
        'mul_sol': '',
        'exe_time': f"{endtime - starttime}ms"
    }
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        d['sat'] = 'sat'
        solution = [f"s{i+1}: u{solver.Value(assignments[i])}" for i in range(steps_count)]
        d['sol'] = solution

    print("Solver status:", solver.StatusName(status))
    return d


if __name__ == '__main__':
    from helper import transform_output
    # Use a relative path based on the current script location
    base_path = os.path.dirname(__file__)
    dpath = os.path.join(base_path, 'instances', 'example7.txt')  # Path to test file
    print(f"Resolved dpath: {dpath}")
    d = Solver(dpath, silent=False)
    s = transform_output(d)
    print(s)
