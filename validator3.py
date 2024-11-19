import re
from collections import defaultdict
import os

# Parsing functions
def parse_problem_instance(filepath):
    """Parse problem instance from a text file."""
    authorizations = defaultdict(list)
    separation_of_duty = []
    binding_of_duty = []
    at_most_k = []
    one_team = []

    with open(filepath, 'r') as file:
        lines = file.readlines()

    for line in lines:
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
            # Handle One-team constraints (if present)
            # You can extend this parsing logic as needed
            pass
    return authorizations, separation_of_duty, binding_of_duty, at_most_k, one_team

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
    for steps, teams in one_team:
        assigned_users = [solution.get(step) for step in steps if solution.get(step)]
        for team in teams:
            if all(user in team for user in assigned_users):
                break
        else:
            print(f"One-team violation in steps {steps}. Users assigned: {assigned_users}")

# Main execution
def main():
    base_path = os.path.dirname(__file__)
    problem_instance_file = os.path.join(base_path, 'instances', 'example7.txt')  # Path to your problem instance file
    solution_file = os.path.join(base_path, '0-solution.txt')  # Path to your solution file

    # Parse input files
    authorizations, separation_of_duty, binding_of_duty, at_most_k, one_team = parse_problem_instance(problem_instance_file)
    solution = parse_solution(solution_file)

    # Run validations
    validate_authorizations(solution, authorizations)
    validate_separation_of_duty(solution, separation_of_duty)
    validate_binding_of_duty(solution, binding_of_duty)
    validate_at_most_k(solution, at_most_k)
    validate_one_team(solution, one_team)

if __name__ == "__main__":
    main()
