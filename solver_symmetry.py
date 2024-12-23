import os
import re
from time import time as currenttime
from ortools.sat.python import cp_model

def parse_file(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
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


def Solver(filename, max_solutions=1, **kwargs):
    """
    :param filename: Path to the input file
    :param max_solutions: # of solutions requested; default 1 => single solution
    """
    model = cp_model.CpModel()
    steps_count, users_count, constraints, user_capacity_constraints = parse_file(filename)

    assignments = [model.NewIntVar(1, users_count, f'step_{i+1}') for i in range(steps_count)]
    user_authorisations = {}
    one_team_constraints = []

    # ---------- parse constraints ----------
    for c in constraints:
        parts = c.split()
        if parts[0] == "Authorisations":
            u = int(parts[1][1:])
            allowed = [int(x[1:]) for x in parts[2:]]
            if u in user_authorisations:
                print("Duplicate authorisations, ignoring extras.")
                continue
            user_authorisations[u] = allowed
            for step in range(steps_count):
                if (step + 1) not in allowed:
                    model.Add(assignments[step] != u)

        elif parts[0] == "Separation-of-duty":
            s1, s2 = int(parts[1][1:]), int(parts[2][1:])
            model.Add(assignments[s1 - 1] != assignments[s2 - 1])

        elif parts[0] == "Binding-of-duty":
            s1, s2 = int(parts[1][1:]), int(parts[2][1:])
            model.Add(assignments[s1 - 1] == assignments[s2 - 1])

        elif parts[0] == "At-most-k":
            k = int(parts[1])
            step_indices = [int(s[1:]) - 1 for s in parts[2:]]
            user_vars = [model.NewIntVar(1, users_count, f'user_{x}') for x in range(k)]
            for i in range(k - 1):
                model.Add(user_vars[i] < user_vars[i+1])
            for st in step_indices:
                bools_ = []
                for i in range(k):
                    b = model.NewBoolVar(f'step_{st}_assigned_{i}')
                    model.Add(assignments[st] == user_vars[i]).OnlyEnforceIf(b)
                    bools_.append(b)
                model.AddExactlyOne(bools_)

        elif parts[0] == "One-team":
            line = c
            st = re.findall(r's(\d+)', line)
            group_steps = [int(x) for x in st]
            teams_raw = re.findall(r'\(([^)]+)\)', line)
            teams = []
            for tstr in teams_raw:
                us = re.findall(r'u(\d+)', tstr)
                teams.append([int(uu) for uu in us])
            if not group_steps or not teams:
                print(f"Warning parse One-team: {line}")
                continue
            one_team_constraints.append({'steps': group_steps, 'teams': teams})

    # ---------- process One-team constraints ----------
    for idx, otc in enumerate(one_team_constraints):
        stp = otc['steps']
        tms = otc['teams']
        step_vars = [assignments[s - 1] for s in stp]
        allowed = []
        import itertools
        for team in tms:
            for combo in itertools.product(team, repeat=len(stp)):
                allowed.append(combo)
        model.AddAllowedAssignments(step_vars, allowed)

    # ---------- user capacity ----------
    for (u, cap) in user_capacity_constraints:
        bools = []
        for s in range(steps_count):
            b = model.NewBoolVar(f'u{u}_s{s+1}')
            model.Add(assignments[s] == u).OnlyEnforceIf(b)
            model.Add(assignments[s] != u).OnlyEnforceIf(b.Not())
            bools.append(b)
        model.Add(sum(bools) <= cap)

    # ---------- handle unknown user authorisations (all steps are allowed) ----------
    for uu in range(1, users_count+1):
        if uu not in user_authorisations:
            print(f"User u{uu} => no explicit authorisations => can do any step")

    solver = cp_model.CpSolver()
    t0 = currenttime() * 1000

    if max_solutions <= 1:
        status = solver.Solve(model)
        t1 = currenttime() * 1000
        d = {
            'sat': 'unsat',
            'sol': [],
            'mul_sol': '',
            'exe_time': f"{int(t1 - t0)}ms"
        }
        if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            d['sat'] = 'sat'
            arr = []
            for i in range(steps_count):
                arr.append(f"s{i+1}: u{solver.Value(assignments[i])}")
            d['sol'] = arr
        print("Solver status:", solver.StatusName(status))
        return d
    else:
        # MULTIPLE solutions
        all_solutions = []
        class MultipleSolCollector(cp_model.CpSolverSolutionCallback):
            def __init__(self, varlist, limit):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self._vars = varlist
                self._limit = limit
                self._found = 0

            def on_solution_callback(self):
                if self._found >= self._limit:
                    self.StopSearch()
                    return
                self._found += 1
                sol = []
                for i, var in enumerate(self._vars):
                    val = self.Value(var)
                    sol.append(f"s{i+1}: u{val}")
                all_solutions.append(sol)

        collector = MultipleSolCollector(assignments, max_solutions)
        status = solver.SearchForAllSolutions(model, collector)
        t1 = currenttime() * 1000
        d = {
            'sat': 'unsat',
            'sol': [],
            'mul_sol': '',
            'exe_time': f"{int(t1 - t0)}ms"
        }
        if len(all_solutions) > 0:
            d['sat'] = 'sat'
            d['sol'] = all_solutions[0]
            # store all in mul_sol
            blocks = []
            for idx, sol in enumerate(all_solutions, start=1):
                block = f"Solution {idx}:\n" + "\n".join(sol)
                blocks.append(block)
            d['mul_sol'] = "\n\n".join(blocks)

        print("Solver status:", solver.StatusName(status))
        return d

if __name__ == '__main__':
    base = os.path.dirname(__file__)
    testf = os.path.join(base, 'all/instances', 'example9.txt')
    d = Solver(testf, max_solutions=1)
    print("SAT?", d['sat'])
    print("Sols:\n", d['mul_sol'])
