import os
import re
from time import time as currenttime
from ortools.sat.python import cp_model

def parse_file(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # Parse #Steps, #Users, #Constraints
    steps_count = int(lines[0].split(': ')[1])
    users_count = int(lines[1].split(': ')[1])
    constraints_count = int(lines[2].split(': ')[1])
    
    constraints = []
    precedence_constraints = []
    for line in lines[3:]:
        line = line.strip()
        if line.startswith("Precedence"):
            parts = line.split()
            s1 = parts[1]
            s2 = parts[2]
            precedence_constraints.append((s1, s2))
        else:
            constraints.append(line)

    print(f"Total constraints parsed: {len(constraints) + len(precedence_constraints)}")
    return steps_count, users_count, constraints, precedence_constraints


def Solver(filename, **kwargs):
    model = cp_model.CpModel()
    steps_count, users_count, constraints, precedence_constraints = parse_file(filename)
    
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
            
            # Create k variables to represent the possible users that can be assigned
            user_vars = [model.NewIntVar(1, users_count, f'user_{i}') for i in range(k)]
            
            # Break symmetry by ordering the user variables
            for i in range(k-1):
                model.Add(user_vars[i] < user_vars[i+1])
            
            # For each step, create variables to indicate which user_var it's assigned to
            for step in step_indices:
                # Create binary variables for each possible assignment
                assignment_vars = []
                for i in range(k):
                    is_assigned = model.NewBoolVar(f'step_{step}_assigned_to_{i}')
                    assignment_vars.append(is_assigned)
                    # If is_assigned is true, then assignments[step] must equal user_vars[i]
                    model.Add(assignments[step] == user_vars[i]).OnlyEnforceIf(is_assigned)
                
                # Each step must be assigned to exactly one user variable
                model.Add(sum(assignment_vars) == 1)
            
            print(f"Applied At-most-k constraint on steps {[s + 1 for s in step_indices]} with max {k} unique users")



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
                'team_vars': [],  # To store team selection variables
            })
            # print(f"Applied One-team constraint for steps {group_steps} with team groups {team_groups}")

        # After parsing all constraints, process the One-Team constraints
        # Mapping from step to list of constraints it belongs to
        step_constraints = {}

        # For each One-Team constraint, create team selection variables
        for idx, otc in enumerate(one_team_constraints):
            teams = otc['teams']
            steps = otc['steps']
            team_vars = []
            for team_idx, team in enumerate(teams):
                team_var = model.NewBoolVar(f'one_team_{idx}_team_{team_idx}_selected')
                team_vars.append(team_var)
            otc['team_vars'] = team_vars

            # Ensure exactly one team is selected for this constraint
            model.Add(sum(team_vars) == 1)

            # For each step, add to step_constraints
            for step in steps:
                if step not in step_constraints:
                    step_constraints[step] = []
                step_constraints[step].append({
                    'constraint_idx': idx,
                    'team_vars': team_vars,
                    'teams': teams,
                })

            # For each step in the constraint, ensure the assigned user is in the selected team
            for team_idx, team in enumerate(teams):
                team_var = team_vars[team_idx]
                for step in steps:
                    # Ensure that if this team is selected, the assigned user is in this team
                    allowed_users_bools = []
                    for user in team:
                        user_assigned = model.NewBoolVar(f'step_{step}_user_{user}_team_{idx}_{team_idx}')
                        model.Add(assignments[step - 1] == user).OnlyEnforceIf(user_assigned)
                        model.Add(assignments[step - 1] != user).OnlyEnforceIf(user_assigned.Not())
                        allowed_users_bools.append(user_assigned)
                    # If the team is selected, then one of its users must be assigned to the step
                    model.AddBoolOr(allowed_users_bools).OnlyEnforceIf(team_var)

        # Handle overlapping steps between One-Team constraints
        for step, constraints_list in step_constraints.items():
            if len(constraints_list) > 1:
                # Step appears in multiple One-Team constraints
                # Process pairs of constraints
                for i in range(len(constraints_list)):
                    for j in range(i + 1, len(constraints_list)):
                        c1 = constraints_list[i]
                        c2 = constraints_list[j]
                        c1_team_vars = c1['team_vars']
                        c2_team_vars = c2['team_vars']
                        c1_teams = c1['teams']
                        c2_teams = c2['teams']
                        # For all combinations of selected teams, enforce compatibility
                        for ti1, team1 in enumerate(c1_teams):
                            for ti2, team2 in enumerate(c2_teams):
                                selected_i = c1_team_vars[ti1]
                                selected_j = c2_team_vars[ti2]
                                overlap = set(team1).intersection(set(team2))
                                if not overlap:
                                    # If intersection is empty, cannot select both teams
                                    model.Add(selected_i + selected_j <= 1)

            print(f"Applied One-team constraint for steps {group_steps} with team groups {team_groups}")



    # Handle users with no specified authorisations: allow any step
    all_steps = set(range(1, steps_count + 1))
    for user in range(1, users_count + 1):
        if user not in user_authorisations:
            print(f"User u{user} has no specific authorisations; allowed on any step.")
    
    # Solve the model with additional settings for detailed logging
    solver = cp_model.CpSolver()
    # solver.parameters.log_search_progress = True  # Enables logging for troubleshooting

    starttime = int(currenttime() * 1000)
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
        
        # # Check for multiple solutions
        # if status == cp_model.OPTIMAL:
        #     d['mul_sol'] = "this is the only solution"
        # else:
        #     d['mul_sol'] = "other solutions exist"
    
    print("Solver status:", solver.StatusName(status))
    return d

if __name__ == '__main__':
    from helper import transform_output
    # Use a relative path based on the current script location
    base_path = os.path.dirname(__file__)
    dpath = os.path.join(base_path, 'instances/4-constraint-hard', '0.txt')  # Path to test file
    # dpath = os.path.join(base_path, 'instances', '4-constraint-hard', '0.txt')  # Path to test file
    print(f"Resolved dpath: {dpath}")
    d = Solver(dpath, silent=False)
    s = transform_output(d)
    print(s)