import os
import re
import itertools
from threading import Thread
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter import StringVar, IntVar, BooleanVar
from tkinter.ttk import Treeview, Progressbar
import time
import subprocess

def parse_file(filename):
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
            user_id = parts[1]
            capacity = int(parts[2])
            user_capacity_constraints[user_id] = capacity
        else:
            constraints.append(line)

    return steps_count, users_count, constraints, user_capacity_constraints

# GUI Application Class
class WorkflowSolverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Workflow Satisfiability Problem Solver")
        self.geometry("1000x700")
        self.create_widgets()
        self.steps = []
        self.users = []
        self.constraints = []
        self.user_capacity_constraints = {}
        self.user_authorisations = {}
        self.one_team_constraints = []
        self.at_most_k_constraints = []
        self.binding_of_duty_constraints = []
        self.separation_of_duty_constraints = []
        self.conflicts = []
        self.timeout = 240  # 4 minutes timeout

    def create_widgets(self):
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both')

        # Create frames for each tab
        self.input_frame = ttk.Frame(self.notebook)
        self.constraints_frame = ttk.Frame(self.notebook)
        self.results_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.input_frame, text='Input')
        self.notebook.add(self.constraints_frame, text='Constraints')
        self.notebook.add(self.results_frame, text='Results')

        # Build Input Tab
        self.build_input_tab()

        # Build Constraints Tab
        self.build_constraints_tab()

        # Build Results Tab
        self.build_results_tab()

    # ------------- Input Tab Enhancements -------------
    def build_input_tab(self):
        frame = self.input_frame

        # Solver Selection
        solver_frame = ttk.LabelFrame(frame, text="Select Solver")
        solver_frame.pack(fill='x', padx=5, pady=5)

        self.solver_var = StringVar(value="solver_combinatorial")  # Default solver
        solvers = ["solver_combinatorial", "solver_symmetry", "solver_doreen"]
        self.solver_dropdown = ttk.Combobox(solver_frame, textvariable=self.solver_var, values=solvers, state='readonly')
        self.solver_dropdown.pack(fill='x', padx=5, pady=5)

        # Steps and Users Label Frames
        steps_labelframe = ttk.LabelFrame(frame, text="Steps")
        steps_labelframe.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        users_labelframe = ttk.LabelFrame(frame, text="Users")
        users_labelframe.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        # Steps Listbox and Buttons
        self.steps_listbox = tk.Listbox(steps_labelframe)
        self.steps_listbox.pack(fill='both', expand=True, padx=5, pady=5)

        steps_button_frame = ttk.Frame(steps_labelframe)
        steps_button_frame.pack()

        add_step_button = ttk.Button(steps_button_frame, text="+", command=self.add_step)
        add_step_button.pack(side='left', padx=5, pady=5)

        remove_step_button = ttk.Button(steps_button_frame, text="−", command=self.remove_step)
        remove_step_button.pack(side='left', padx=5, pady=5)

        # Users Listbox and Buttons
        self.users_listbox = tk.Listbox(users_labelframe)
        self.users_listbox.pack(fill='both', expand=True, padx=5, pady=5)

        users_button_frame = ttk.Frame(users_labelframe)
        users_button_frame.pack()

        add_user_button = ttk.Button(users_button_frame, text="+", command=self.add_user)
        add_user_button.pack(side='left', padx=5, pady=5)

        remove_user_button = ttk.Button(users_button_frame, text="−", command=self.remove_user)
        remove_user_button.pack(side='left', padx=5, pady=5)

        # Import/Export buttons
        import_button = ttk.Button(frame, text="Import Problem", command=self.import_problem)
        import_button.pack(side='left', padx=5, pady=5)

        export_button = ttk.Button(frame, text="Export Problem", command=self.export_problem)
        export_button.pack(side='left', padx=5, pady=5)

    # Dialog Classes for Constraints
    class AuthorisationConstraintDialog(tk.Toplevel):
        def __init__(self, parent, users, steps):
            super().__init__(parent)
            self.title("Add Authorisation Constraint")
            self.users = users
            self.steps = steps
            self.result = None

            # Select User
            ttk.Label(self, text="Select User:").pack(pady=5)
            self.user_var = StringVar()
            self.user_combo = ttk.Combobox(self, textvariable=self.user_var, values=self.users, state='readonly')
            self.user_combo.pack(pady=5)

            # Select Steps
            ttk.Label(self, text="Select Allowed Steps:").pack(pady=5)
            self.steps_var = tk.Variable(value=self.steps)
            self.steps_listbox = tk.Listbox(self, listvariable=self.steps_var, selectmode='multiple')
            self.steps_listbox.pack(pady=5)

            # Add Constraint Button
            add_button = ttk.Button(self, text="Add Constraint", command=self.add_constraint)
            add_button.pack(pady=10)

        def add_constraint(self):
            selected_user = self.user_var.get()
            selected_indices = self.steps_listbox.curselection()
            selected_steps = [self.steps[i] for i in selected_indices]

            if selected_user and selected_steps:
                # Format result as "Authorisations uX sY sZ ..."
                self.result = (selected_user, selected_steps)
                self.destroy()
            else:
                messagebox.showerror("Error", "Please select a user and at least one step.")

    class SeparationConstraintDialog(tk.Toplevel):
        def __init__(self, parent, steps):
            super().__init__(parent)
            self.title("Add Separation-of-Duty Constraint")
            self.steps = steps
            self.result = None

            ttk.Label(self, text="Select Step 1:").pack(pady=5)
            self.step1_var = StringVar()
            self.step1_combo = ttk.Combobox(self, textvariable=self.step1_var, values=self.steps, state='readonly')
            self.step1_combo.pack(pady=5)

            ttk.Label(self, text="Select Step 2:").pack(pady=5)
            self.step2_var = StringVar()
            self.step2_combo = ttk.Combobox(self, textvariable=self.step2_var, values=self.steps, state='readonly')
            self.step2_combo.pack(pady=5)

            add_button = ttk.Button(self, text="Add Constraint", command=self.add_constraint)
            add_button.pack(pady=10)

        def add_constraint(self):
            step1 = self.step1_var.get()
            step2 = self.step2_var.get()
            if step1 and step2 and step1 != step2:
                self.result = (step1, step2)
                self.destroy()
            else:
                messagebox.showerror("Error", "Please select two different steps.")

    class BindingConstraintDialog(tk.Toplevel):
        def __init__(self, parent, steps):
            super().__init__(parent)
            self.title("Add Binding-of-Duty Constraint")
            self.steps = steps
            self.result = None

            ttk.Label(self, text="Select Step 1:").pack(pady=5)
            self.step1_var = StringVar()
            self.step1_combo = ttk.Combobox(self, textvariable=self.step1_var, values=self.steps, state='readonly')
            self.step1_combo.pack(pady=5)

            ttk.Label(self, text="Select Step 2:").pack(pady=5)
            self.step2_var = StringVar()
            self.step2_combo = ttk.Combobox(self, textvariable=self.step2_var, values=self.steps, state='readonly')
            self.step2_combo.pack(pady=5)

            add_button = ttk.Button(self, text="Add Constraint", command=self.add_constraint)
            add_button.pack(pady=10)

        def add_constraint(self):
            step1 = self.step1_var.get()
            step2 = self.step2_var.get()
            if step1 and step2 and step1 != step2:
                self.result = (step1, step2)
                self.destroy()
            else:
                messagebox.showerror("Error", "Please select two different steps.")

    class AtMostKConstraintDialog(tk.Toplevel):
        def __init__(self, parent, steps):
            super().__init__(parent)
            self.title("Add At-Most-k Constraint")
            self.steps = steps
            self.result = None

            ttk.Label(self, text="Select Steps:").pack(pady=5)
            self.steps_var = tk.Variable(value=self.steps)
            self.steps_listbox = tk.Listbox(self, listvariable=self.steps_var, selectmode='multiple')
            self.steps_listbox.pack(pady=5)

            ttk.Label(self, text="Enter value of k:").pack(pady=5)
            self.k_var = IntVar()
            self.k_entry = ttk.Entry(self, textvariable=self.k_var)
            self.k_entry.pack(pady=5)

            add_button = ttk.Button(self, text="Add Constraint", command=self.add_constraint)
            add_button.pack(pady=10)

        def add_constraint(self):
            selected_indices = self.steps_listbox.curselection()
            selected_steps = [self.steps[i] for i in selected_indices]
            k = self.k_var.get()
            if selected_steps and k > 0:
                # Steps should be in format s1, s2, etc.
                selected_steps_formatted = [f's{self.steps.index(step) + 1}' for step in selected_steps]
                self.result = (k, selected_steps_formatted)
                self.destroy()
            else:
                messagebox.showerror("Error", "Please select steps and enter a valid value for k.")

    class OneTeamConstraintDialog(tk.Toplevel):
        def __init__(self, parent, steps, users):
            super().__init__(parent)
            self.title("Add One-Team Constraint")
            self.steps = steps
            self.users = users
            self.result = None

            # Select Steps
            ttk.Label(self, text="Select Steps:").pack(pady=5)
            self.steps_var = tk.Variable(value=self.steps)
            self.steps_listbox = tk.Listbox(self, listvariable=self.steps_var, selectmode='multiple')
            self.steps_listbox.pack(pady=5)

            # Define Teams
            ttk.Label(self, text="Define Teams:").pack(pady=5)
            self.teams = []  # List of teams, each team is a string like (u1 u2)
            self.teams_frame = ttk.Frame(self)
            self.teams_frame.pack(pady=5)

            add_team_button = ttk.Button(self, text="Add Team", command=self.add_team)
            add_team_button.pack(pady=5)

            self.teams_listbox = tk.Listbox(self)
            self.teams_listbox.pack(pady=5)

            add_constraint_button = ttk.Button(self, text="Add Constraint", command=self.add_constraint)
            add_constraint_button.pack(pady=10)

        def add_team(self):
            dialog = WorkflowSolverApp.TeamDialog(self, self.users)
            self.wait_window(dialog)
            if dialog.result:
                team_users = dialog.result
                # Format team as (u1 u2 u3)
                team_str = '(' + ' '.join([f'u{self.users.index(u) + 1}' for u in team_users]) + ')'
                self.teams.append(team_str)
                self.teams_listbox.insert(tk.END, team_str)


        def add_constraint(self):
            selected_indices = self.steps_listbox.curselection()
            selected_steps = [self.steps[i] for i in selected_indices]
            if selected_steps and self.teams:
                # Steps should be in format s1, s2, etc.
                selected_steps_formatted = [f's{self.steps.index(step) + 1}' for step in selected_steps]
                self.result = (selected_steps_formatted, self.teams)
                self.destroy()
            else:
                messagebox.showerror("Error", "Please select steps and define at least one team.")

    class TeamDialog(tk.Toplevel):
        def __init__(self, parent, users):
            super().__init__(parent)
            self.title("Define Team")
            self.users = users
            self.result = None

            ttk.Label(self, text="Select Users for the Team:").pack(pady=5)
            self.users_var = tk.Variable(value=self.users)
            self.users_listbox = tk.Listbox(self, listvariable=self.users_var, selectmode='multiple')
            self.users_listbox.pack(pady=5)

            add_button = ttk.Button(self, text="Add Team", command=self.add_team)
            add_button.pack(pady=10)

        def add_team(self):
            selected_indices = self.users_listbox.curselection()
            selected_users = [self.users[i] for i in selected_indices]
            if selected_users:
                self.result = selected_users
                self.destroy()
            else:
                messagebox.showerror("Error", "Please select at least one user.")

    class UserCapacityConstraintDialog(tk.Toplevel):
        def __init__(self, parent, users):
            super().__init__(parent)
            self.title("Add User Capacity Constraint")
            self.users = users
            self.result = None

            # Select User
            ttk.Label(self, text="Select User:").pack(pady=5)
            self.user_var = StringVar()
            self.user_combo = ttk.Combobox(self, textvariable=self.user_var, values=self.users, state='readonly')
            self.user_combo.pack(pady=5)

            # Enter Capacity
            ttk.Label(self, text="Enter User Capacity (Max Steps):").pack(pady=5)
            self.capacity_var = IntVar()
            self.capacity_entry = ttk.Entry(self, textvariable=self.capacity_var)
            self.capacity_entry.pack(pady=5)

            # Add Constraint Button
            add_button = ttk.Button(self, text="Add Constraint", command=self.add_constraint)
            add_button.pack(pady=10)

        def add_constraint(self):
            selected_user = self.user_var.get()
            capacity = self.capacity_var.get()

            if selected_user and capacity > 0:
                self.result = (selected_user, capacity)
                self.destroy()
            else:
                messagebox.showerror("Error", "Please select a user and enter a valid capacity.")

    def add_step(self):
        step_label = f"s{len(self.steps) + 1}"
        if step_label not in self.steps:
            self.steps.append(step_label)
            self.steps_listbox.insert(tk.END, step_label)
        else:
            messagebox.showerror("Error", "Step already exists.")

    def remove_step(self):
        if self.steps:
            step_label = self.steps.pop()
            self.steps_listbox.delete(tk.END)
            # Remove associated constraints
            self.constraints = [c for c in self.constraints if step_label not in c]
            self.update_constraints_tree()
        else:
            messagebox.showerror("Error", "No steps to remove.")

    def add_user(self):
        user_label = f"u{len(self.users) + 1}"
        if user_label not in self.users:
            self.users.append(user_label)
            self.users_listbox.insert(tk.END, user_label)
        else:
            messagebox.showerror("Error", "User already exists.")

    def remove_user(self):
        if self.users:
            user_label = self.users.pop()
            self.users_listbox.delete(tk.END)
            # Remove associated constraints
            self.constraints = [c for c in self.constraints if user_label not in c]
            self.update_constraints_tree()
        else:
            messagebox.showerror("Error", "No users to remove.")

    # ------------- Constraints Tab Enhancements -------------
    def build_constraints_tab(self):
        frame = self.constraints_frame

        # Constraint Builders
        constraint_builder_frame = ttk.Frame(frame)
        constraint_builder_frame.pack(side='top', fill='x', padx=5, pady=5)

        # Authorisation Constraint Builder
        auth_button = ttk.Button(constraint_builder_frame, text="Add Authorisation Constraint", command=self.add_authorisation_constraint)
        auth_button.grid(row=0, column=0, padx=5, pady=5)

        # SoD Constraint Builder
        sod_button = ttk.Button(constraint_builder_frame, text="Add SoD Constraint", command=self.add_separation_constraint)
        sod_button.grid(row=0, column=1, padx=5, pady=5)

        # BoD Constraint Builder
        bod_button = ttk.Button(constraint_builder_frame, text="Add BoD Constraint", command=self.add_binding_constraint)
        bod_button.grid(row=0, column=2, padx=5, pady=5)

        # At-Most-k Constraint Builder
        atmostk_button = ttk.Button(constraint_builder_frame, text="Add At-Most-k Constraint", command=self.add_atmostk_constraint)
        atmostk_button.grid(row=0, column=3, padx=5, pady=5)

        # One-Team Constraint Builder
        oneteam_button = ttk.Button(constraint_builder_frame, text="Add One-Team Constraint", command=self.add_oneteam_constraint)
        oneteam_button.grid(row=0, column=4, padx=5, pady=5)

        # User-Capacity Constraint Builder (Changed from Precedence)
        user_capacity_button = ttk.Button(constraint_builder_frame, text="Add User Capacity Constraint", command=self.add_user_capacity_constraint)
        user_capacity_button.grid(row=0, column=5, padx=5, pady=5)

        # Add "Remove Constraint" button
        remove_constraint_button = ttk.Button(constraint_builder_frame, text="Remove Constraint", command=self.remove_constraint)
        remove_constraint_button.grid(row=0, column=6, padx=5, pady=5)

        # Constraints Treeview
        self.constraints_tree = Treeview(frame, columns=("Type", "Details"), show='headings')
        self.constraints_tree.heading("Type", text="Constraint Type")
        self.constraints_tree.heading("Details", text="Details")
        self.constraints_tree.pack(fill='both', expand=True, padx=5, pady=5)

    def remove_constraint(self):
        selected_item = self.constraints_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a constraint to remove.")
            return

        for item in selected_item:
            values = self.constraints_tree.item(item, 'values')
            self.constraints_tree.delete(item)
            constraint = values[1]
            if constraint.startswith("User-capacity"):
                self.user_capacity_constraints.remove(constraint)
            else:
                self.constraints.remove(constraint)

        self.update_constraints_tree()

    def add_authorisation_constraint(self):
        if not self.users or not self.steps:
            messagebox.showerror("Error", "At least one user and one step are required.")
            return

        dialog = WorkflowSolverApp.AuthorisationConstraintDialog(self, self.users, self.steps)
        self.wait_window(dialog)

        if dialog.result:
            user, allowed_steps = dialog.result
            allowed_steps_str = ' '.join(allowed_steps)
            constraint = f"Authorisations {user} {allowed_steps_str}"
            self.constraints.append(constraint)
            self.constraints_tree.insert('', tk.END, values=("Authorisation", constraint))

    def add_separation_constraint(self):
        if len(self.steps) < 2:
            messagebox.showerror("Error", "At least two steps are required.")
            return

        dialog = WorkflowSolverApp.SeparationConstraintDialog(self, self.steps)
        self.wait_window(dialog)
        if dialog.result:
            step1, step2 = dialog.result
            step1_index = self.steps.index(step1) + 1
            step2_index = self.steps.index(step2) + 1
            constraint = f"Separation-of-duty s{step1_index} s{step2_index}"
            self.constraints.append(constraint)
            self.constraints_tree.insert('', tk.END, values=("Separation-of-Duty", constraint))

    def add_binding_constraint(self):
        if len(self.steps) < 2:
            messagebox.showerror("Error", "At least two steps are required.")
            return

        dialog = WorkflowSolverApp.BindingConstraintDialog(self, self.steps)
        self.wait_window(dialog)
        if dialog.result:
            step1, step2 = dialog.result
            step1_index = self.steps.index(step1) + 1
            step2_index = self.steps.index(step2) + 1
            constraint = f"Binding-of-duty s{step1_index} s{step2_index}"
            self.constraints.append(constraint)
            self.constraints_tree.insert('', tk.END, values=("Binding-of-Duty", constraint))

    def add_atmostk_constraint(self):
        if len(self.steps) < 1:
            messagebox.showerror("Error", "At least one step is required.")
            return

        dialog = WorkflowSolverApp.AtMostKConstraintDialog(self, self.steps)
        self.wait_window(dialog)
        if dialog.result:
            k, selected_steps = dialog.result
            constraint = f"At-most-k {k} {' '.join(selected_steps)}"
            self.constraints.append(constraint)
            self.constraints_tree.insert('', tk.END, values=("At-Most-k", constraint))

    def add_oneteam_constraint(self):
        if len(self.steps) < 1 or len(self.users) < 1:
            messagebox.showerror("Error", "At least one step and one user are required.")
            return

        dialog = WorkflowSolverApp.OneTeamConstraintDialog(self, self.steps, self.users)
        self.wait_window(dialog)
        if dialog.result:
            selected_steps, teams = dialog.result
            constraint = f"One-team {' '.join(selected_steps)} {' '.join(teams)}"
            self.constraints.append(constraint)
            self.constraints_tree.insert('', tk.END, values=("One-Team", constraint))

    def add_user_capacity_constraint(self):
        if not self.users:
            messagebox.showerror("Error", "At least one user is required.")
            return

        dialog = WorkflowSolverApp.UserCapacityConstraintDialog(self, self.users)
        self.wait_window(dialog)
        if dialog.result:
            user, capacity = dialog.result
            constraint = f"User-capacity {user} {capacity}"
            self.constraints.append(constraint)
            self.constraints_tree.insert('', tk.END, values=("User-Capacity", constraint))

    def update_constraints_tree(self):
        # Clear the tree
        for item in self.constraints_tree.get_children():
            self.constraints_tree.delete(item)
        # Re-insert constraints
        for constraint in self.constraints:
            # Determine constraint type from the string
            if constraint.startswith("Authorisations"):
                constraint_type = "Authorisation"
            elif constraint.startswith("Separation-of-duty"):
                constraint_type = "Separation-of-Duty"
            elif constraint.startswith("Binding-of-duty"):
                constraint_type = "Binding-of-Duty"
            elif constraint.startswith("At-most-k"):
                constraint_type = "At-Most-k"
            elif constraint.startswith("One-team"):
                constraint_type = "One-Team"
            elif constraint.startswith("User-capacity"):
                constraint_type = "User-Capacity"
            else:
                constraint_type = "Unknown"
            self.constraints_tree.insert('', tk.END, values=(constraint_type, constraint))

     # ------------- Results Tab Enhancements -------------
    def build_results_tab(self):
        frame = self.results_frame

        # Solve button
        solve_button = ttk.Button(frame, text="Solve Problem", command=self.solve_problem)
        solve_button.pack(pady=10)

        # --- Added Validate Solution Checkbox ---
        self.validate_var = BooleanVar()
        validate_checkbox = ttk.Checkbutton(frame, text="Validate solution", variable=self.validate_var)
        validate_checkbox.pack(pady=5)

        # Progress bar
        self.progress_var = IntVar()
        self.progress_bar = Progressbar(frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', padx=5, pady=5)

        # Time and count information
        self.info_label = tk.Label(frame, text="")
        self.info_label.pack(pady=5)

        # Result Treeview
        self.result_tree = Treeview(frame, columns=("Step", "Assigned User"), show='headings')
        self.result_tree.heading("Step", text="Step")
        self.result_tree.heading("Assigned User", text="Assigned User")
        self.result_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # --- Create notebook for validation results ---
        self.validation_notebook = ttk.Notebook(frame)
        self.validation_notebook.pack(fill='both', expand=True, padx=5, pady=5)

    # ------------- Solver Execution in a Separate Thread -------------
    def solve_problem(self):
        # Run solver in a separate thread
        self.progress_var.set(0)
        self.update_idletasks()
        thread = Thread(target=self.run_solver)
        thread.start()
    
    def run_solver(self):
        selected_solver = self.solver_var.get()
        try:
            solver_module = __import__(selected_solver)
        except ImportError as e:
            messagebox.showerror("Error", f"Failed to load solver {selected_solver}: {e}")
            return

        temp_filename = 'temp_instance.txt'
        with open(temp_filename, 'w') as file:
            file.write(f"#Steps: {len(self.steps)}\n")
            file.write(f"#Users: {len(self.users)}\n")
            file.write(f"#Constraints: {len(self.constraints)}\n")
            for constraint in self.constraints:
                file.write(constraint + '\n')

        def solver_callback():
            start_time = time.time()
            d = solver_module.Solver(temp_filename)
            end_time = time.time()
            d['exe_time'] = end_time - start_time
            # Update results
            self.after(0, lambda: self.display_results(d, temp_filename))
            # os.remove(temp_filename)  # Remove after validation

        solver_thread = Thread(target=solver_callback)
        solver_thread.start()

    def display_results(self, d, temp_filename):
        self.result_tree.delete(*self.result_tree.get_children())
        if d['sat'] == 'sat':
            self.solutions = [d['sol']]
            self.show_solution(d['sol'])
            self.info_label['text'] = f"1 solution found. Solve time: {d['exe_time']:.2f} seconds."

            if self.validate_var.get():
                self.run_validators(temp_filename, 'temp_solution.txt')
            else:
                os.remove(temp_filename)
                os.remove('temp_solution.txt')

        else:
            self.info_label['text'] = "No solutions found."
            messagebox.showerror("No Solution", "No solution found.")
            os.remove(temp_filename)

    def show_solution(self, solution):
        self.result_tree.delete(*self.result_tree.get_children())
        with open('temp_solution.txt', 'w') as f:
            for line in solution:
                step, user = line.split(': ')
                self.result_tree.insert('', tk.END, values=(step, user))
                f.write(f"{step}: {user}\n")

    def run_validators(self, problem_file, solution_file):
        # Clear previous validation tabs
        for tab_id in self.validation_notebook.tabs():
            self.validation_notebook.forget(tab_id)

        # Run validator.py
        validation_result = self.run_validator_script('validator.py', problem_file, solution_file)
        self.add_validation_tab('Validator 1', validation_result)

        # Run validator2.py
        validation_result = self.run_validator_script('validator2.py', problem_file, solution_file)
        self.add_validation_tab('Validator 2', validation_result)

        # Run validator3.py
        validation_result = self.run_validator_script('validator3.py', problem_file, solution_file)
        self.add_validation_tab('Validator 3', validation_result)

        os.remove(problem_file)
        os.remove(solution_file)

    def run_validator_script(self, script_name, problem_file, solution_file):
        try:
            result = subprocess.run(['python', script_name, problem_file, solution_file],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout
            errors = result.stderr
            if result.returncode == 0:
                return output + errors
            else:
                return f"Validator encountered errors:\n{errors}"
        except Exception as e:
            return f"Failed to run {script_name}: {e}"

    def add_validation_tab(self, validator_name, validation_result):
        tab = ttk.Frame(self.validation_notebook)
        self.validation_notebook.add(tab, text=validator_name)
        text_widget = tk.Text(tab)
        text_widget.pack(fill='both', expand=True)
        text_widget.insert('1.0', validation_result)
        text_widget.config(state='disabled')

    def import_problem(self):
        """Import problem instance from a file."""
        filename = filedialog.askopenfilename(
            title="Import Problem", 
            filetypes=[("Text Files", "*.txt")]
        )
        if filename:
            try:
                # Parse the file
                steps_count, users_count, constraints, user_capacity_constraints = parse_file(filename)
                
                # Reset current data
                self.steps.clear()
                self.users.clear()
                self.constraints.clear()
                self.user_capacity_constraints.clear()

                # Populate steps and users
                self.steps = [f"s{i+1}" for i in range(steps_count)]
                self.users = [f"u{i+1}" for i in range(users_count)]

                # Populate constraints
                self.constraints = constraints
                for uc in user_capacity_constraints:
                    constraint = f"User-capacity {uc[0]} {uc[1]}"
                    self.constraints.append(constraint)

                # Update UI components
                self.steps_listbox.delete(0, tk.END)
                for step in self.steps:
                    self.steps_listbox.insert(tk.END, step)

                self.users_listbox.delete(0, tk.END)
                for user in self.users:
                    self.users_listbox.insert(tk.END, user)

                self.update_constraints_tree()

                messagebox.showinfo("Import Successful", f"Imported problem from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import problem: {e}")

    def export_problem(self):
        """Export problem instance to a file."""
        filename = filedialog.asksaveasfilename(
            title="Export Problem", 
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if filename:
            try:
                with open(filename, 'w') as file:
                    file.write(f"#Steps: {len(self.steps)}\n")
                    file.write(f"#Users: {len(self.users)}\n")
                    file.write(f"#Constraints: {len(self.constraints)}\n")
                    for constraint in self.constraints:
                        file.write(constraint + '\n')
                messagebox.showinfo("Export Successful", f"Problem exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export problem: {e}")


    # Run the application
if __name__ == '__main__':
    app = WorkflowSolverApp()
    app.mainloop()
