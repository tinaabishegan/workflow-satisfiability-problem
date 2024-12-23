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


def Solver(filename, max_solutions=1, progress_callback=None, **kwargs):
    """
    :param filename: Path to the input file.
    :param max_solutions: Number of solutions to retrieve (>=1). Default=1 => single solution.
    :param progress_callback: Optional callback for progress (unused here).
    :param kwargs: Additional arguments (unused).
    """
    model = cp_model.CpModel()
    steps_count, users_count, constraints, user_capacity_constraints = parse_file(filename)
    
    # Create variables: one for each step
    assignments = [model.NewIntVar(1, users_count, f'step_{i + 1}') for i in range(steps_count)]
    
    user_authorisations = {}
    one_team_constraints = []

    # ---------- Parse constraints ----------
    for constraint in constraints:
        parts = constraint.split()
        
        if parts[0] == "Authorisations":
            user = int(parts[1][1:])
            allowed_steps = [int(step[1:]) for step in parts[2:]]
            if user in user_authorisations:
                print(f"Warning: User u{user} has multiple authorisations; ignoring duplicates.")
                continue
            user_authorisations[user] = allowed_steps
            for st_index in range(steps_count):
                if (st_index + 1) not in allowed_steps:
                    model.Add(assignments[st_index] != user)
            print(f"Applied Authorisation constraint for user u{user} on steps {allowed_steps}")

        elif parts[0] == "Separation-of-duty":
            s1, s2 = int(parts[1][1:]), int(parts[2][1:])
            model.Add(assignments[s1 - 1] != assignments[s2 - 1])
            print(f"Applied Separation-of-duty between s{s1} and s{s2}")

        elif parts[0] == "Binding-of-duty":
            s1, s2 = int(parts[1][1:]), int(parts[2][1:])
            model.Add(assignments[s1 - 1] == assignments[s2 - 1])
            print(f"Applied Binding-of-duty between s{s1} and s{s2}")

        elif parts[0] == "At-most-k":
            k = int(parts[1])
            step_indices = [int(s[1:]) - 1 for s in parts[2:]]
            if k < len(step_indices):
                # Combinatorial approach: for each combination of k+1 steps, force at least one pair same user
                import itertools
                for combo in itertools.combinations(step_indices, k + 1):
                    bools_same = []
                    for i, j in itertools.combinations(combo, 2):
                        b = model.NewBoolVar(f'pair_{i+1}_{j+1}_sameuser')
                        model.Add(assignments[i] == assignments[j]).OnlyEnforceIf(b)
                        model.Add(assignments[i] != assignments[j]).OnlyEnforceIf(b.Not())
                        bools_same.append(b)
                    model.AddBoolOr(bools_same)
                print(f"Applied At-most-k = {k} on steps {[s+1 for s in step_indices]}")
            else:
                print(f"Ignored At-most-k with k >= #steps_in_constraint => no effect")

        elif parts[0] == "One-team":
            # Parse steps and teams
            line = constraint
            st = re.findall(r's(\d+)', line)
            group_steps = [int(x) for x in st]
            teams_raw = re.findall(r'\(([^)]+)\)', line)
            team_groups = []
            for team_str in teams_raw:
                us = re.findall(r'u(\d+)', team_str)
                team_groups.append([int(u) for u in us])
            if not group_steps or not team_groups:
                print(f"Warning: Unable to parse One-team: {line}")
                continue
            one_team_constraints.append({
                'steps': group_steps,
                'teams': team_groups,
            })
            print(f"Parsed One-team for steps {group_steps} with teams {team_groups}")

    # ---------- Process One-Team constraints ----------
    for idx, otc in enumerate(one_team_constraints):
        stps = otc['steps']
        tms = otc['teams']
        step_vars = [assignments[s-1] for s in stps]
        allowed = []
        import itertools
        for tm in tms:
            for combo in itertools.product(tm, repeat=len(stps)):
                allowed.append(combo)
        model.AddAllowedAssignments(step_vars, allowed)
        print(f"Applied One-team for steps {stps}")

    # ---------- user_authorisations fallback ----------
    for u in range(1, users_count + 1):
        if u not in user_authorisations:
            print(f"User u{u} => no specific authorisations => can do any step")

    # ---------- user-capacity constraints ----------
    for (u, cap) in user_capacity_constraints:
        bool_list = []
        for st in range(steps_count):
            b = model.NewBoolVar(f'u{u}_s{st+1}')
            model.Add(assignments[st] == u).OnlyEnforceIf(b)
            model.Add(assignments[st] != u).OnlyEnforceIf(b.Not())
            bool_list.append(b)
        model.Add(sum(bool_list) <= cap)
        print(f"Applied user capacity: user u{u} <= {cap} steps")

    # ---------- Solve (single or multi) ----------
    solver = cp_model.CpSolver()
    start_ms = int(currenttime() * 1000)
    all_solutions = []

    class MultiSolCallback(cp_model.CpSolverSolutionCallback):
        def __init__(self, vars_, limit):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self._vars = vars_
            self._limit = limit
            self._count = 0

        def on_solution_callback(self):
            if self._count >= self._limit:
                self.StopSearch()
                return
            self._count += 1
            one_sol = []
            for i, var in enumerate(self._vars):
                one_sol.append(f"s{i+1}: u{self.Value(var)}")
            all_solutions.append(one_sol)

    collector = MultiSolCallback(assignments, max_solutions)
    status = solver.SearchForAllSolutions(model, collector)
    end_ms = int(currenttime() * 1000)

    d = {
        'sat': 'unsat',
        'sol': [],
        'mul_sol': '',
        'exe_time': f"{end_ms - start_ms}ms"
    }

    if len(all_solutions) > 0:
        d['sat'] = 'sat'
        # first solution
        d['sol'] = all_solutions[0]
        if len(all_solutions) == 1:
            # only one solution found
            d['mul_sol'] = "Unique solution found" if status == cp_model.OPTIMAL else "1 solution found"
        else:
            # multiple
            blocks = []
            for idx, sol_list in enumerate(all_solutions, start=1):
                blocks.append(f"Solution {idx}:\n" + "\n".join(sol_list))
            d['mul_sol'] = "\n\n".join(blocks)

    print("Solver status:", solver.StatusName(status))
    return d


if __name__ == '__main__':
    base_path = os.path.dirname(__file__)
    test_path = os.path.join(base_path, 'all/instances', 'example9.txt')
    # example usage
    d = Solver(test_path, max_solutions=1)  # attempt to find 2 solutions
    print("SAT?", d['sat'])
    print("First solution =>", d['sol'])
    print("All solutions =>\n", d['mul_sol'])
