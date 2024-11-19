import re
import itertools

def parse_file(filename):
    """
    Parse the input file to extract steps, users, constraints, and precedence constraints.
    """
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # Parse #Steps, #Users, #Constraints
    steps_count = int(lines[0].split(': ')[1])
    users_count = int(lines[1].split(': ')[1])
    constraints_count = int(lines[2].split(': ')[1])

    constraints = []
    precedence_constraints = []

    # Separate general constraints and precedence constraints
    for line in lines[3:]:
        line = line.strip()
        if line.startswith("Precedence"):
            parts = line.split()
            s1, s2 = parts[1], parts[2]
            precedence_constraints.append((s1, s2))
        else:
            constraints.append(line)

    return steps_count, users_count, constraints, precedence_constraints


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
    steps_count, users_count, constraints, precedence_constraints = parse_file(filename)
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
                if step_to_user[step1] == step_to_user[step2]:
                    print(f"Separation-of-duty violated: Steps s{step1} and s{step2} assigned to the same user u{step_to_user[step1]}.")
                    return False
        return True

    def validate_binding_of_duty():
        for constraint in constraints:
            parts = constraint.split()
            if parts[0] == "Binding-of-duty":
                step1, step2 = int(parts[1][1:]), int(parts[2][1:])
                if step_to_user[step1] != step_to_user[step2]:
                    print(f"Binding-of-duty violated: Steps s{step1} and s{step2} assigned to different users u{step_to_user[step1]} and u{step_to_user[step2]}.")
                    return False
        return True

    def validate_at_most_k():
        for constraint in constraints:
            parts = constraint.split()
            if parts[0] == "At-most-k":
                k = int(parts[1])
                step_indices = [int(s[1:]) for s in parts[2:]]
                users_assigned = {step_to_user[step] for step in step_indices}
                if len(users_assigned) > k:
                    print(f"At-most-k violated: More than {k} unique users assigned to steps {step_indices} (users: {users_assigned}).")
                    return False
        return True

    def validate_one_team():
        for constraint in constraints:
            if constraint.startswith("One-team"):
                # Parse steps and teams
                steps = [int(s) for s in re.findall(r's(\d+)', constraint)]  # Use the matched digits directly
                teams_raw = re.findall(r'\(([^)]+)\)', constraint)
                teams = [[int(u[1:]) for u in team.split()] for team in teams_raw]

                # Verify that the user assignments for the steps form a valid team
                assigned_users = [step_to_user[step] for step in steps]
                if not any(all(assigned_users[i] in team for i in range(len(steps))) for team in teams):
                    print(f"One-team violated: Steps {steps} assigned users {assigned_users}, not matching any valid team {teams}.")
                    return False
        return True


    def validate_precedence_constraints():
        for s1, s2 in precedence_constraints:
            s1_index = int(s1[1:])
            s2_index = int(s2[1:])
            if step_to_user[s1_index] >= step_to_user[s2_index]:
                print(f"Precedence constraint violated: Step {s1} (u{step_to_user[s1_index]}) must precede step {s2} (u{step_to_user[s2_index]}).")
                return False
        return True

    # Apply all validations
    validators = [
        validate_authorisations,
        validate_separation_of_duty,
        validate_binding_of_duty,
        validate_at_most_k,
        validate_one_team,
        validate_precedence_constraints,
    ]

    for validator in validators:
        if not validator():
            print("Solution validation failed.")
            return False

    print("Solution is valid.")
    return True



# Example Usage
if __name__ == "__main__":
    input_file = 'instances/example7.txt'  # Path to test file
    solution_file = "0-solution.txt"  # File containing the solution
    validate_solution_from_solver(input_file, solution_file)
