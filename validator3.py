import re
from collections import defaultdict
import os
import sys

# Parsing functions
def parse_problem_instance(filepath):
    """Parse problem instance from a text file."""
    authorizations = defaultdict(list)
    separation_of_duty = []
    binding_of_duty = []
    at_most_k = []
    one_team = []
    user_capacity = {}

    with open(filepath, 'r') as file:
        lines = file.readlines()

    for line in lines[3:]:  # Skip header lines
        line = line.strip()
        if not line or line.startswith('#'):
            continue  # Skip empty lines and comments
        if line.startswith('Authorisations'):
            parts = line.split()
            user = parts[1]
            steps = parts[2:]
            for step in steps:
                authorizations[user].append(step)
        elif line.startswith('Separation-of-duty'):
            parts = line.split()
            separation_of_duty.append((parts[1], parts[2]))
        elif line.startswith('Binding-of-duty'):
            parts = line.split()
            binding_of_duty.append((parts[1], parts[2]))
        elif line.startswith('At-most-k'):
            parts = line.split()
            k = int(parts[1])
            steps = parts[2:]
            at_most_k.append((k, steps))
        elif line.startswith('One-team'):
            steps = [int(s) for s in re.findall(r's(\d+)', line)]
            teams_raw = re.findall(r'\(([^)]+)\)', line)
            teams = [[int(u[1:]) for u in team.split()] for team in teams_raw]
            one_team.append((steps, teams))
        elif line.startswith('User-capacity'):
            parts = line.split()
            user = parts[1]
            capacity = int(parts[2])
            user_capacity[user] = capacity
    return authorizations, separation_of_duty, binding_of_duty, at_most_k, one_team, user_capacity

def parse_solution(filepath):
    """Parse solution from a text file."""
    solution = {}
    with open(filepath, 'r') as file:
        lines = file.readlines()
    for line in lines:
        if not line.strip():
            continue  # Skip empty lines
        try:
            step, user = line.strip().split(': ')
            solution[step] = user
        except ValueError:
            print(f"Invalid line in solution file: '{line.strip()}'")
    return solution

# Validation functions
def validate_authorizations(solution, authorizations):
    for step, user in solution.items():
        if user in authorizations:
            if step not in authorizations[user]:
                print(f"Authorization violation: User {user} is not authorized for step {step}.")
        else:
            # User not specified in authorizations; considered authorized for all steps
            pass  # No violation

def validate_separation_of_duty(solution, separation_of_duty):
    for step1, step2 in separation_of_duty:
        user1 = solution.get(step1)
        user2 = solution.get(step2)
        if user1 and user2 and user1 == user2:
            print(f"Separation-of-duty violation between steps {step1} and {step2} assigned to user {user1}.")

def validate_binding_of_duty(solution, binding_of_duty):
    for step1, step2 in binding_of_duty:
        user1 = solution.get(step1)
        user2 = solution.get(step2)
        if user1 and user2 and user1 != user2:
            print(f"Binding-of-duty violation: Steps {step1} and {step2} assigned to different users ({user1}, {user2}).")

def validate_at_most_k(solution, at_most_k):
    for k, steps in at_most_k:
        assigned_users = set()
        for step in steps:
            user = solution.get(step)
            if user:
                assigned_users.add(user)
        if len(assigned_users) > k:
            print(f"At-most-{k} violation: More than {k} users assigned to steps {steps}. Users assigned: {assigned_users}")

def validate_one_team(solution, one_team):
    """
    Validate that the steps are assigned to a valid team of users.
    """
    for steps, teams in one_team:
        assigned_users = [solution.get(step) for step in steps if solution.get(step)]
        valid_team = any(all(user in team for user in assigned_users) for team in teams)
        if not valid_team:
            print(f"One-team violation: Steps {steps} assigned users {assigned_users} do not match any valid team {teams}.")


def validate_user_capacity(solution, user_capacity):
    user_step_counts = {}
    for step, user in solution.items():
        user_step_counts[user] = user_step_counts.get(user, 0) + 1
    for user, capacity in user_capacity.items():
        assigned_steps = user_step_counts.get(user, 0)
        if assigned_steps > capacity:
            print(f"User-capacity violation: User {user} assigned to {assigned_steps} steps, exceeds capacity {capacity}.")

# Main execution
def main():
    if len(sys.argv) != 3:
        print("Usage: python validator3.py <problem_instance_file> <solution_file>")
        return

    problem_instance_file = sys.argv[1]
    solution_file = sys.argv[2]

    # Parse input files
    authorizations, separation_of_duty, binding_of_duty, at_most_k, one_team, user_capacity = parse_problem_instance(problem_instance_file)
    solution = parse_solution(solution_file)

    # Run validations
    validate_authorizations(solution, authorizations)
    validate_separation_of_duty(solution, separation_of_duty)
    validate_binding_of_duty(solution, binding_of_duty)
    validate_at_most_k(solution, at_most_k)
    validate_one_team(solution, one_team)
    validate_user_capacity(solution, user_capacity)

if __name__ == "__main__":
    main()
# python validator3.py C:\Users\Tinaabishegan\Documents\symbolicai\cw2\all/5-constraint/2.txt 0-solution.txt