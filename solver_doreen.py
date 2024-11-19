from z3 import*
from time import time as currenttime
from ortools.sat.python import cp_model
import os
import re
import numpy
# helper function provided in Moodle
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
        self.auth = [] # index: the user || element: steps authorised to the user
        self.SOD = [] # the list of pairs of steps that must be assigned to the different users
        self.BOD = [] # the list of pairs of steps that must be assigned to the same user
        self.at_most_k = [] # the list of pairs of k and steps
        self.one_team = [] # the list of pairs of steps and teams



def parse_file(filename):
    def read_attribute(name):
        line = f.readline()
        match = re.match(f'{name}:\\s*(\\d+)$', line)
        if match:
            return int(match.group(1))
        else:
            raise Exception(f"Could not parse line {line}; expected the {name} attribute")
    
    instance = Instance()
    with open(filename) as f:
        instance.number_of_steps = read_attribute("#Steps")
        instance.number_of_users = read_attribute("#Users")
        instance.number_of_constraints = read_attribute("#Constraints")
        # Initialise instance.auth with empty lists as elements
        instance.auth = [[] for _ in range(instance.number_of_users)]
        for _ in range(instance.number_of_constraints):
            l = f.readline()
            # 1st Constraint: Authorisations
            m = re.match(r"Authorisations u(\d+)(?: s\d+)*", l)
            if m:
                user_id = int(m.group(1))
                steps = [-1]  # For users that are not authorised to perform any steps, e.g., Authorisations u1
                for m in re.finditer(r's(\d+)', l):
                    if -1 in steps:
                        steps.remove(-1)  # If user has specified steps, then only store the steps authorised
                    steps.append(int(m.group(1)) - 1)  # -1 because list index starts from 0
                instance.auth[user_id - 1].extend(steps)
                continue
            # 2nd Constraint: Separation-of-duty
            m = re.match(r'Separation-of-duty s(\d+) s(\d+)', l)
            if m:
                steps = (int(m.group(1)) - 1, int(m.group(2)) - 1)
                instance.SOD.append(steps)
                continue
            # 3rd Constraint: Binding-of-duty
            m = re.match(r'Binding-of-duty s(\d+) s(\d+)', l)
            if m:
                steps = (int(m.group(1)) - 1, int(m.group(2)) - 1)
                instance.BOD.append(steps)
                continue
            # 4th Constraint: At-most-k
            m = re.match(r'At-most-k (\d+) (s\d+)(?: (s\d+))*', l)
            if m:
                k = int(m.group(1))
                steps = []
                for m in re.finditer(r's(\d+)', l):
                    steps.append(int(m.group(1)) - 1)
                instance.at_most_k.append((k, steps))
                continue
            # 5th Constraint: One-team constraint
            m = re.match(r'One-team\s+(s\d+)(?: s\d+)* (\((u\d+)*\))*', l)
            if m:
                steps = []
                for m in re.finditer(r's(\d+)', l):
                    steps.append(int(m.group(1)) - 1)
                teams = []
                for m in re.finditer(r'\((u\d+\s*)+\)', l):
                    team = []
                    for users in re.finditer(r'u(\d+)', m.group(0)):
                        team.append(int(users.group(1)) - 1)
                    teams.append(team)
                instance.one_team.append((steps, teams))
                continue
            else:
                raise Exception(f'Failed to parse this line: {l}')
    return instance


def Solver(filename, **kwargs):
    instance = parse_file(filename)
    '''
    :param filename:
    The constraint path
    :param kwargs:
    As you wish, you may supply extra arguments using the kwargs
    :return:
    A dict.
    '''
    # Printing (accessing or output) values from test instances
    print("=====================================================")
    print(f'\tFile: {filename}')
    print(f'\tNumber of Steps: {instance.number_of_steps}')
    print(f'\tNumber of Users: {instance.number_of_users}')
    print(f'\tNumber of Constraints: {instance.number_of_constraints}')
    print(f'\tAuthorisations: {instance.auth}')
    print(f'\tSeparation-of-duty: {instance.SOD}')
    print(f'\tBinding-of-duty: {instance.BOD}')
    print(f'\tAt-most-k: {instance.at_most_k}')
    print(f'\tOne-team: {instance.one_team}')
    print("=====================================================")

    ''' Start of Solver '''
    model = cp_model.CpModel()
    user_assignment = [[model.NewBoolVar(f's{s + 1}: u{u + 1}') for u in range(instance.number_of_users)]
                       for s in range(instance.number_of_steps)]
    # Each step is assigned to exactly one user
    for step in range(instance.number_of_steps):
        model.AddExactlyOne(user_assignment[step][user] for user in range(instance.number_of_users))

    # Authorisations constraint
    for user in range(instance.number_of_users):
        if instance.auth[user]:
            for step in range(instance.number_of_steps):
                if step not in instance.auth[user]:
                    model.Add(user_assignment[step][user] == 0)

    # Separation-of-duty constraint
    for (separated_step1, separated_step2) in instance.SOD:
        for user in range(instance.number_of_users):
            model.Add(user_assignment[separated_step2][user] == 0).OnlyEnforceIf(user_assignment[separated_step1][user])

    # Binding-of-duty constraint
    for (bound_step1, bound_step2) in instance.BOD:
        for user in range(instance.number_of_users):
            model.Add(user_assignment[bound_step2][user] == 1).OnlyEnforceIf(user_assignment[bound_step1][user])

    # At-most-k constraint
    for (k, steps) in instance.at_most_k:
        user_assignment_flag = [model.NewBoolVar(f'at-most-k_u{u}') for u in range(instance.number_of_users)]
        for user in range(instance.number_of_users):
            for step in steps:
                model.Add(user_assignment_flag[user] == 1).OnlyEnforceIf(user_assignment[step][user])
            model.Add(sum(user_assignment[step][user] for step in steps) >= user_assignment_flag[user])
        model.Add(sum(user_assignment_flag) <= k)

    # One-team constraint
    for (steps, teams) in instance.one_team:
        team_flag = [model.NewBoolVar(f'team{t}') for t in range(len(teams))]
        model.AddExactlyOne(team_flag)  # Only one team can be chosen
        for team_index in range(len(teams)):
            for step in steps:
                for user in teams[team_index]:
                    model.Add(user_assignment[step][user] == 0).OnlyEnforceIf(team_flag[team_index].Not())
        # Steps cannot be assigned to users not listed in teams
        users_in_teams = list(numpy.concatenate(teams).flat)
        for step in steps:
            for user in range(instance.number_of_users):
                if user not in users_in_teams:
                    model.Add(user_assignment[step][user] == 0)

    ''' End of Solver '''
    starttime = float(currenttime() * 1000)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    endtime = float(currenttime() * 1000)

    d = dict(
        sat='unsat',
        sol=[],
        mul_sol='',
        exe_time=f'{endtime - starttime:.2f}ms'
    )

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        d['sat'] = 'sat'
        for s in range(instance.number_of_steps):
            for u in range(instance.number_of_users):
                if solver.Value(user_assignment[s][u]):
                    d['sol'].append(f's{s + 1}: u{u + 1}')
        d['mul_sol'] = "Multiple solutions may exist" if status == cp_model.FEASIBLE else "Unique solution found"
    return d


if __name__ == '__main__':
    base_path = os.path.dirname(__file__)
    dpath = os.path.join(base_path, 'instances', 'example7.txt')  # Path to test file
    d = Solver(dpath)
    s = transform_output(d)
    print(s)
