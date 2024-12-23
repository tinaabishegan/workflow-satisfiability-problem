from z3 import *
from time import time as currenttime
import os
import re
import numpy
# We see also from the code: from ortools.sat.python import cp_model (but not necessarily used fully).
from ortools.sat.python import cp_model

def transform_output(d):
    crlf = '\r\n'
    s = []
    s = ''.join(kk + crlf for kk in d['sol'])
    s = d['sat']+crlf+s+d['mul_sol']
    s = crlf + s + crlf+str(d['exe_time']) if 'exe_time' in d else s
    return s

class Instance:
    def __init__(self):
        self.number_of_steps = 0
        self.number_of_users = 0
        self.number_of_constraints = 0
        self.auth = []
        self.SOD = []
        self.BOD = []
        self.at_most_k = []
        self.one_team = []
        self.user_capacity = []

def parse_file(filename):
    def read_attribute(name):
        line = f.readline()
        match = re.match(f'{name}:\\s*(\\d+)$', line)
        if match:
            return int(match.group(1))
        else:
            raise Exception(f"Failed parse line {line}, expected {name}")

    instance = Instance()
    with open(filename) as f:
        instance.number_of_steps = read_attribute("#Steps")
        instance.number_of_users = read_attribute("#Users")
        instance.number_of_constraints = read_attribute("#Constraints")
        instance.auth = [[] for _ in range(instance.number_of_users)]
        for _ in range(instance.number_of_constraints):
            l = f.readline().strip()
            # parse each constraint
            m = re.match(r"Authorisations u(\d+)(?: s\d+)*", l)
            if m:
                u = int(m.group(1))
                steps_ = [-1]
                for mm in re.finditer(r's(\d+)', l):
                    if -1 in steps_:
                        steps_.remove(-1)
                    steps_.append(int(mm.group(1)) - 1)
                instance.auth[u-1].extend(steps_)
                continue
            m = re.match(r'Separation-of-duty s(\d+) s(\d+)', l)
            if m:
                s1 = int(m.group(1)) - 1
                s2 = int(m.group(2)) - 1
                instance.SOD.append((s1, s2))
                continue
            m = re.match(r'Binding-of-duty s(\d+) s(\d+)', l)
            if m:
                s1 = int(m.group(1)) - 1
                s2 = int(m.group(2)) - 1
                instance.BOD.append((s1, s2))
                continue
            m = re.match(r'At-most-k (\d+) (s\d+)(?: (s\d+))*', l)
            if m:
                k = int(m.group(1))
                stp = []
                for mm in re.finditer(r's(\d+)', l):
                    stp.append(int(mm.group(1)) - 1)
                instance.at_most_k.append((k, stp))
                continue
            m = re.match(r'One-team\s+(s\d+)(?: s\d+)* (\((u\d+)*\))*', l)
            if m:
                stp = []
                for mm in re.finditer(r's(\d+)', l):
                    stp.append(int(mm.group(1)) - 1)
                tms = []
                for mm in re.finditer(r'\((u\d+\s*)+\)', l):
                    t_ = []
                    for us in re.finditer(r'u(\d+)', mm.group(0)):
                        t_.append(int(us.group(1)) - 1)
                    tms.append(t_)
                instance.one_team.append((stp, tms))
                continue
            m = re.match(r'User-capacity u(\d+) (\d+)', l)
            if m:
                uid = int(m.group(1)) - 1
                cap = int(m.group(2))
                instance.user_capacity.append((uid, cap))
                continue
            else:
                raise Exception(f"Cannot parse line => {l}")
    return instance


def Solver(filename, max_solutions=1, **kwargs):
    """
    :param filename: path to constraint
    :param max_solutions: number of solutions to find (1 => single solution)
    """
    instance = parse_file(filename)
    print("=====================================================")
    print(f"File: {filename}")
    print(f"Steps: {instance.number_of_steps}, Users: {instance.number_of_users}, Constraints: {instance.number_of_constraints}")
    print(f"Auth: {instance.auth}")
    print(f"SOD: {instance.SOD}")
    print(f"BOD: {instance.BOD}")
    print(f"At-most-k: {instance.at_most_k}")
    print(f"One-team: {instance.one_team}")
    print(f"User-capacity: {instance.user_capacity}")
    print("=====================================================")

    start_time = currenttime() * 1000.0

    # We'll do a CP approach for enumerating solutions (like we did in the older partial code).
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()

    # user_assignment[s][u] = bool => step s is assigned to user u
    user_assignment = [[model.NewBoolVar(f's{s+1}_u{u+1}')
                        for u in range(instance.number_of_users)]
                       for s in range(instance.number_of_steps)]
    # each step exactly 1 user
    for s in range(instance.number_of_steps):
        model.AddExactlyOne(user_assignment[s][u] for u in range(instance.number_of_users))

    # Auth
    for u, stp_list in enumerate(instance.auth):
        if len(stp_list) == 1 and stp_list[0] == -1:
            # means no steps allowed
            # => user cannot be assigned to any step
            for s in range(instance.number_of_steps):
                model.Add(user_assignment[s][u] == 0)
        elif len(stp_list) > 0:
            # those steps are allowed, the rest are not
            allowed_set = set(stp_list)
            for s in range(instance.number_of_steps):
                if s not in allowed_set:
                    model.Add(user_assignment[s][u] == 0)

    # SOD
    for (s1, s2) in instance.SOD:
        for u in range(instance.number_of_users):
            model.Add(user_assignment[s2][u] == 0).OnlyEnforceIf(user_assignment[s1][u])

    # BOD
    for (s1, s2) in instance.BOD:
        for u in range(instance.number_of_users):
            model.Add(user_assignment[s2][u] == 1).OnlyEnforceIf(user_assignment[s1][u])

    # At-most-k
    for (k, stp) in instance.at_most_k:
        user_flag = [model.NewBoolVar(f'atmostk_u{u}') for u in range(instance.number_of_users)]
        for u in range(instance.number_of_users):
            # if user is assigned in any of stp => user_flag[u] = 1
            for ss in stp:
                model.Add(user_flag[u] == 1).OnlyEnforceIf(user_assignment[ss][u])
            # user assigned to stp >= user_flag[u]
            model.Add(sum(user_assignment[ss][u] for ss in stp) >= user_flag[u])
        model.Add(sum(user_flag) <= k)

    # One-team
    for (steps_, teams) in instance.one_team:
        team_flags = [model.NewBoolVar(f'team_{i}') for i in range(len(teams))]
        model.AddExactlyOne(team_flags)
        # if team i is selected => users outside that team for the steps => 0
        for i, tlist in enumerate(teams):
            # if not in tlist => can't assign
            for s_ in steps_:
                for u_ in range(instance.number_of_users):
                    if u_ not in tlist:
                        model.Add(user_assignment[s_][u_] == 0).OnlyEnforceIf(team_flags[i])

    # user-capacity
    for (u, cap) in instance.user_capacity:
        model.Add(sum(user_assignment[s][u] for s in range(instance.number_of_steps)) <= cap)

    solver = cp_model.CpSolver()

    if max_solutions <= 1:
        # single solution
        status = solver.Solve(model)
        end_time = currenttime() * 1000.0
        d = dict(sat='unsat', sol=[], mul_sol='', exe_time=f'{(end_time - start_time):.2f}ms')
        if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
            d['sat'] = 'sat'
            # build sol
            for s in range(instance.number_of_steps):
                for u in range(instance.number_of_users):
                    if solver.Value(user_assignment[s][u]):
                        d['sol'].append(f's{s+1}: u{u+1}')
            if status == cp_model.FEASIBLE:
                d['mul_sol'] = "Multiple solutions may exist"
            else:
                d['mul_sol'] = "Unique solution found"
        return d
    else:
        # multiple solutions
        solutions_found = []

        class MultiSolutionCallback(cp_model.CpSolverSolutionCallback):
            def __init__(self, assign_bools, step_count, user_count, limit):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self._assign = assign_bools
                self._steps = step_count
                self._users = user_count
                self._limit = limit
                self._count = 0

            def on_solution_callback(self):
                if self._count >= self._limit:
                    self.StopSearch()
                    return
                self._count += 1
                one_sol = []
                for s_ in range(self._steps):
                    for u_ in range(self._users):
                        if self.Value(self._assign[s_][u_]):
                            one_sol.append(f's{s_+1}: u{u_+1}')
                solutions_found.append(one_sol)

        cb = MultiSolutionCallback(user_assignment, instance.number_of_steps, instance.number_of_users, max_solutions)
        status = solver.SearchForAllSolutions(model, cb)
        end_time = currenttime() * 1000.0
        d = dict(sat='unsat', sol=[], mul_sol='', exe_time=f'{(end_time - start_time):.2f}ms')
        if len(solutions_found) > 0:
            d['sat'] = 'sat'
            # first solution in 'sol'
            d['sol'] = solutions_found[0]
            # store all solutions in mul_sol
            blocks = []
            for idx, sol in enumerate(solutions_found, start=1):
                blocks.append(f"Solution {idx}:\n" + "\n".join(sol))
            d['mul_sol'] = "\n\n".join(blocks)
        return d

if __name__=='__main__':
    base_path = os.path.dirname(__file__)
    dpath = os.path.join(base_path, 'all/instances', 'example9.txt')
    ret = Solver(dpath, max_solutions=1)
    print("sat:", ret['sat'])
    print("First solution =>", ret['sol'])
    print("All solutions =>\n", ret['mul_sol'])
