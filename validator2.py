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
                steps = []
                teams = []
                # Extract steps
                for part in parts[1:]:
                    if part.startswith('s'):
                        steps.append(int(part[1:]))
                    elif part.startswith('('):
                        # Extract team
                        users = [int(u[1:]) for u in re.findall(r'u\d+', part)]
                        teams.append(users)
                self.one_team.append((steps, teams))
    
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
            if assignments[s1] == assignments[s2]:
                errors.append(f"Separation of duty violated for steps s{s1} and s{s2}")
        
        # Check binding of duty
        for s1, s2 in self.binding_duties:
            if assignments[s1] != assignments[s2]:
                errors.append(f"Binding of duty violated for steps s{s1} and s{s2}")
        
        # Check at-most-k
        for k, steps in self.at_most_k:
            users = set(assignments[s] for s in steps)
            if len(users) > k:
                errors.append(f"At-most-{k} constraint violated for steps {steps}")
        
        # Check one-team
        for steps, teams in self.one_team:
            assigned_users = set(assignments[s] for s in steps)
            valid_team = False
            for team in teams:
                if assigned_users.issubset(set(team)):
                    valid_team = True
                    break
            if not valid_team:
                errors.append(f"One-team constraint violated for steps {steps}")
        
        return len(errors) == 0, errors

def main():
    validator = WSPValidator()
    
    # Parse problem and solution
    base_path = os.path.dirname(__file__)
    problem_file = os.path.join(base_path, 'instances', 'example7.txt')  # Path to test file
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
