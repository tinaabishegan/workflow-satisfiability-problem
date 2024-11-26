import re
import os
import sys
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
        self.user_capacity_constraints: Dict[int, int] = {}  # user -> capacity
        
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
                
            parts = line.split()
            
            if parts[0] == "Authorisations":
                user = int(parts[1][1:])
                steps = [int(s[1:]) for s in parts[2:]]
                self.authorisations[user] = steps
                
            elif parts[0] == "Separation-of-duty":
                s1 = int(parts[1][1:])
                s2 = int(parts[2][1:])
                self.separation_duties.append((s1, s2))
                
            elif parts[0] == "Binding-of-duty":
                s1 = int(parts[1][1:])
                s2 = int(parts[2][1:])
                self.binding_duties.append((s1, s2))
                
            elif parts[0] == "At-most-k":
                k = int(parts[1])
                steps = [int(s[1:]) for s in parts[2:]]
                self.at_most_k.append((k, steps))
                
            elif parts[0] == "One-team":
                # Parse steps and teams
                steps = [int(s) for s in re.findall(r's(\d+)', line)]
                teams_raw = re.findall(r'\(([^)]+)\)', line)
                teams = [[int(u[1:]) for u in team.split()] for team in teams_raw]
                self.one_team.append((steps, teams))

            elif parts[0] == "User-capacity":
                user = int(parts[1][1:])
                capacity = int(parts[2])
                self.user_capacity_constraints[user] = capacity
    
    def parse_solution(self, solution_file: str) -> Dict[int, int]:
        """Parse the solution file and return step -> user assignments."""
        assignments = {}
        with open(solution_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                step, user = line.split(': ')
                step_num = int(step[1:])
                user_num = int(user[1:])
                assignments[step_num] = user_num
        return assignments
    
    def validate_solution(self, assignments: Dict[int, int]) -> Tuple[bool, List[str]]:
        """Validate if the solution satisfies all constraints."""
        errors = []
        
        # Check if all steps are assigned
        if len(assignments) != self.steps_count:
            errors.append(f"Not all steps are assigned. Expected {self.steps_count}, got {len(assignments)}")
            return False, errors
        
        # Check authorisations
        for step, user in assignments.items():
            if user in self.authorisations:
                if step not in self.authorisations[user]:
                    errors.append(f"User u{user} is not authorized for step s{step}")
        
        # Check separation of duty
        for s1, s2 in self.separation_duties:
            if assignments.get(s1) == assignments.get(s2):
                errors.append(f"Separation of duty violated for steps s{s1} and s{s2}")
        
        # Check binding of duty
        for s1, s2 in self.binding_duties:
            if assignments.get(s1) != assignments.get(s2):
                errors.append(f"Binding of duty violated for steps s{s1} and s{s2}")
        
        # Check at-most-k
        for k, steps in self.at_most_k:
            users = set(assignments.get(s) for s in steps if assignments.get(s) is not None)
            if len(users) > k:
                errors.append(f"At-most-{k} constraint violated for steps {steps}")
        
        # Validate One-Team
        # One-team validation
        for steps, teams in self.one_team:
            assigned_users = [assignments[s] for s in steps if s in assignments]

            # Check if all assigned users form a valid team
            if not any(all(user in team for user in assigned_users) for team in teams):
                errors.append(f"One-team violated: Steps {steps} assigned users {assigned_users} do not match any valid team {teams}.")


        # --- Added validation for user capacity ---
        # Check user capacity
        user_step_counts = {}
        for step, user in assignments.items():
            user_step_counts[user] = user_step_counts.get(user, 0) + 1

        for user, capacity in self.user_capacity_constraints.items():
            assigned_steps = user_step_counts.get(user, 0)
            if assigned_steps > capacity:
                errors.append(f"User capacity violated: User u{user} assigned to {assigned_steps} steps, exceeds capacity {capacity}.")
        
        return len(errors) == 0, errors

def main():
    validator = WSPValidator()
    
    # --- Adjusted to accept command-line arguments ---
    if len(sys.argv) != 3:
        print("Usage: python validator2.py <problem_file> <solution_file>")
        return
    problem_file = sys.argv[1]
    solution_file = sys.argv[2]
    
    # Parse problem and solution
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
# python validator2.py C:\Users\Tinaabishegan\Documents\symbolicai\cw2\all/5-constraint/2.txt 0-solution.txt