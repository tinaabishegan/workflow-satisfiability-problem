import re
import itertools
import sys

def parse_file(filename):
    """
    Parse the input file to extract steps, users, constraints, and user capacity constraints.
    """
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # Parse #Steps, #Users, #Constraints
    steps_count = int(lines[0].split(': ')[1])
    users_count = int(lines[1].split(': ')[1])
    constraints_count = int(lines[2].split(': ')[1])

    constraints = []
    user_capacity_constraints = {}

    for line in lines[3:]:
        line = line.strip()
        if line.startswith("User-capacity"):
            parts = line.split()
            user_id = int(parts[1][1:])  # e.g., u1
            capacity = int(parts[2])
            user_capacity_constraints[user_id] = capacity
        else:
            constraints.append(line)

    return steps_count, users_count, constraints, user_capacity_constraints


def parse_solution_file(solution_file):
    """
    Parse the solution file into a dictionary of step-user assignments.
    Example input format:
    s1: u372
    s2: u268
    """
    step_to_user = {}
    with open(solution_file, 'r') as file:
        lines = file.readlines()
        for line in lines:
            step, user = line.strip().split(': ')
            step_num = int(step[1:])  # Extract step number (e.g., s1 -> 1)
            user_num = int(user[1:])  # Extract user number (e.g., u372 -> 372)
            step_to_user[step_num] = user_num
    return step_to_user


def validate_solution_from_solver(filename, solution_file):
    """
    Validate the solution produced by the solver.
    """
    steps_count, users_count, constraints, user_capacity_constraints = parse_file(filename)
    step_to_user = parse_solution_file(solution_file)

    # Validator for each constraint type
    def validate_authorisations():
        for constraint in constraints:
            parts = constraint.split()
            if parts[0] == "Authorisations":
                user = int(parts[1][1:])
                allowed_steps = {int(step[1:]) for step in parts[2:]}
                for step, assigned_user in step_to_user.items():
                    if assigned_user == user and step not in allowed_steps:
                        print(f"Authorisation violated: User u{user} assigned to step s{step} not in allowed steps {allowed_steps}.")
                        return False
        return True

    def validate_separation_of_duty():
        for constraint in constraints:
            parts = constraint.split()
            if parts[0] == "Separation-of-duty":
                step1, step2 = int(parts[1][1:]), int(parts[2][1:])
                if step_to_user.get(step1) == step_to_user.get(step2):
                    print(f"Separation-of-duty violated: Steps s{step1} and s{step2} assigned to the same user u{step_to_user.get(step1)}.")
                    return False
        return True

    def validate_binding_of_duty():
        for constraint in constraints:
            parts = constraint.split()
            if parts[0] == "Binding-of-duty":
                step1, step2 = int(parts[1][1:]), int(parts[2][1:])
                if step_to_user.get(step1) != step_to_user.get(step2):
                    print(f"Binding-of-duty violated: Steps s{step1} and s{step2} assigned to different users u{step_to_user.get(step1)} and u{step_to_user.get(step2)}.")
                    return False
        return True

    def validate_at_most_k():
        for constraint in constraints:
            parts = constraint.split()
            if parts[0] == "At-most-k":
                k = int(parts[1])
                step_indices = [int(s[1:]) for s in parts[2:]]
                users_assigned = {step_to_user.get(step) for step in step_indices if step_to_user.get(step)}
                if len(users_assigned) > k:
                    print(f"At-most-k violated: More than {k} unique users assigned to steps {step_indices} (users: {users_assigned}).")
                    return False
        return True

    def validate_one_team():
        for constraint in constraints:
            if constraint.startswith("One-team"):
                parts = constraint.split()
                # Extract step indices from the constraint
                steps = [int(s) for s in re.findall(r's(\d+)', constraint)]
                # Extract team definitions from the constraint
                teams_raw = re.findall(r'\(([^)]+)\)', constraint)
                teams = [[int(u[1:]) for u in team.split()] for team in teams_raw]

                # Get the assigned users for the steps
                assigned_users = [step_to_user.get(step) for step in steps if step_to_user.get(step)]

                # Check if assigned users match any valid team
                if not any(all(user in team for user in assigned_users) for team in teams):
                    print(f"One-team violated: Steps {steps} assigned users {assigned_users} do not match any valid team {teams}.")
                    return False
        return True


    def validate_user_capacity():
        # Count the number of steps assigned to each user
        user_step_counts = {}
        for step, user in step_to_user.items():
            user_step_counts[user] = user_step_counts.get(user, 0) + 1

        for user, capacity in user_capacity_constraints.items():
            assigned_steps = user_step_counts.get(user, 0)
            if assigned_steps > capacity:
                print(f"User-capacity violated: User u{user} assigned to {assigned_steps} steps, exceeds capacity {capacity}.")
                return False
        return True

    # Apply all validations
    validators = [
        validate_authorisations,
        validate_separation_of_duty,
        validate_binding_of_duty,
        validate_at_most_k,
        validate_one_team,
        validate_user_capacity,
    ]

    all_valid = True
    for validator in validators:
        if not validator():
            all_valid = False

    if all_valid:
        print("Solution is valid.")
        return True
    else:
        print("Solution validation failed.")
        return False


# --- Adjusted main function to accept command-line arguments ---
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validator.py <problem_file> <solution_file>")
    else:
        input_file = sys.argv[1]
        solution_file = sys.argv[2]
        validate_solution_from_solver(input_file, solution_file)
# python validator.py C:\Users\Tinaabishegan\Documents\symbolicai\cw2\all/5-constraint/2.txt 0-solution.txt