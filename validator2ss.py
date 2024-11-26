import re
import os
from typing import Dict, List, Set, Tuple

class WSPValidator:
    def __init__(self):
        self.steps_count: int = 0
        self.users_count: int = 0
        self.constraints_count: int = 0
        self.authorisations: Dict[int, List[int]] = {}  # user -> allowed steps
        self.separation_duties: List[Tuple[int, int]] = []
        self.binding_duties: List[Tuple[int, int]] = []
        self.at_most_k: List[Tuple[int, List[int]]] = []  # (k, steps)
        self.one_team: List[Tuple[List[int], List[List[int]]]] = []  # (steps, teams)

    def parse_problem(self, problem_file: str) -> None:
        """Parse the problem instance file."""
        with open(problem_file, 'r') as f:
            lines = f.readlines()

        # Parse header
        self.steps_count = int(lines[0].split(': ')[1])
        self.users_count = int(lines[1].split(': ')[1])
        self.constraints_count = int(lines[2].split(': ')[1])

        # Parse constraints
        for line in lines[3:]:
            line = line.strip()
            if not line:
                continue

            if line.startswith("Authorisations"):
                parts = line.split()
                user = int(parts[1][1:])
                steps = [int(step[1:]) for step in parts[2:]]
                self.authorisations[user] = steps
            elif line.startswith("Separation-of-duty"):
                parts = line.split()
                s1, s2 = int(parts[1][1:]), int(parts[2][1:])
                self.separation_duties.append((s1, s2))
            elif line.startswith("Binding-of-duty"):
                parts = line.split()
                s1, s2 = int(parts[1][1:]), int(parts[2][1:])
                self.binding_duties.append((s1, s2))
            elif line.startswith("At-most-k"):
                parts = line.split()
                k = int(parts[1])
                steps = [int(step[1:]) for step in parts[2:]]
                self.at_most_k.append((k, steps))
            elif line.startswith("One-team"):
                # Parse steps and teams
                steps = [int(s) for s in re.findall(r's(\d+)', line)]
                teams_raw = re.findall(r'\(([^)]+)\)', line)
                teams = [[int(u[1:]) for u in team.split()] for team in teams_raw]
                self.one_team.append((steps, teams))

    def parse_solution(self, solution_file: str) -> Dict[int, int]:
        """Parse the solution file and return step -> user assignments."""
        assignments = {}
        with open(solution_file, 'r') as f:
            for line in f:
                step, user = line.strip().split(': ')
                step_num = int(step[1:])  # Extract step number (e.g., s1 -> 1)
                user_num = int(user[1:])  # Extract user number (e.g., u372 -> 372)
                assignments[step_num] = user_num
        return assignments

    def validate_solution(self, assignments: Dict[int, int]) -> Tuple[bool, List[str]]:
        """Validate if the solution satisfies all constraints."""
        errors = []

        # Check if all steps are assigned
        if len(assignments) != self.steps_count:
            errors.append(f"Not all steps are assigned. Expected {self.steps_count}, got {len(assignments)}.")
            return False, errors

        # Authorisation validation
        for step, user in assignments.items():
            if user in self.authorisations:
                if step not in self.authorisations[user]:
                    errors.append(f"Authorisation violated: User u{user} is not authorised for step s{step}.")

        # Separation-of-duty validation
        for s1, s2 in self.separation_duties:
            if assignments.get(s1) == assignments.get(s2):
                errors.append(f"Separation-of-duty violated: Steps s{s1} and s{s2} assigned to the same user u{assignments[s1]}.")

        # Binding-of-duty validation
        for s1, s2 in self.binding_duties:
            if assignments.get(s1) != assignments.get(s2):
                errors.append(f"Binding-of-duty violated: Steps s{s1} and s{s2} assigned to different users.")

        # At-most-k validation
        for k, steps in self.at_most_k:
            assigned_users = {assignments[s] for s in steps if s in assignments}
            if len(assigned_users) > k:
                errors.append(f"At-most-{k} violated: More than {k} users assigned to steps {steps}.")

        # One-team validation
        for steps, teams in self.one_team:
            assigned_users = [assignments[s] for s in steps if s in assignments]

            # Check if all assigned users form a valid team
            if not any(all(user in team for user in assigned_users) for team in teams):
                errors.append(f"One-team violated: Steps {steps} assigned users {assigned_users} do not match any valid team {teams}.")

        return len(errors) == 0, errors


def main():
    validator = WSPValidator()

    # Parse problem and solution
    base_path = os.path.dirname(__file__)
    problem_file = os.path.join(base_path, 'all/5-constraint/2.txt')  # Path to test file
    solution_file = os.path.join(base_path, '0-solution.txt')  # Path to test file

    validator.parse_problem(problem_file)
    assignments = validator.parse_solution(solution_file)

    # Validate solution
    is_valid, errors = validator.validate_solution(assignments)

    if is_valid:
        print("Solution is valid!")
    else:
        print("Solution is invalid. Errors found:")
        for error in errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()
# python validator2ss.py C:\Users\Tinaabishegan\Documents\symbolicai\cw2\all/5-constraint/2.txt 0-solution.txt