import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
import numpy as np
import importlib
import re
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class SolverBenchmarkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Solver Benchmarking Tool")
        self.geometry("900x700")
        self.create_widgets()
        self.solvers = ['solver_combinatorial', 'solver_symmetry', 'solver_doreen']
        self.instance_folders = []
        self.results = {}  # To store the results for plotting

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True)

        # Frame for folder selection
        folder_frame = ttk.LabelFrame(main_frame, text="Instance Folders")
        folder_frame.pack(fill='x', padx=10, pady=10)

        self.folder_listbox = tk.Listbox(folder_frame, selectmode='extended', height=5)
        self.folder_listbox.pack(fill='x', expand=True, padx=5, pady=5)

        add_folder_button = ttk.Button(folder_frame, text="Add Folder", command=self.add_folder)
        add_folder_button.pack(side='left', padx=5, pady=5)

        remove_folder_button = ttk.Button(folder_frame, text="Remove Selected", command=self.remove_folder)
        remove_folder_button.pack(side='left', padx=5, pady=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', padx=10, pady=10)

        # Start button
        start_button = ttk.Button(main_frame, text="Start Benchmarking", command=self.start_benchmarking)
        start_button.pack(pady=5)

        # Generate graphs button
        graph_button = ttk.Button(main_frame, text="Generate Graphs", command=self.generate_graphs)
        graph_button.pack(pady=5)

        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

    def add_folder(self):
        folder_selected = filedialog.askdirectory(title="Select Instance Folder")
        if folder_selected:
            self.instance_folders.append(folder_selected)
            self.folder_listbox.insert(tk.END, folder_selected)

    def remove_folder(self):
        selected_indices = list(self.folder_listbox.curselection())
        selected_indices.reverse()  # Remove from the end to avoid index shifting
        for index in selected_indices:
            self.instance_folders.pop(index)
            self.folder_listbox.delete(index)

    def start_benchmarking(self):
        if not self.instance_folders:
            messagebox.showerror("Error", "Please add at least one instance folder.")
            return

        # Disable buttons during execution
        self.folder_listbox.config(state='disabled')
        self.progress_var.set(0)
        threading.Thread(target=self.run_benchmark).start()

    def run_benchmark(self):
        total_instance_files = sum(len([f for f in os.listdir(folder) if f.endswith('.txt') and not f.endswith('-solution.txt')]) for folder in self.instance_folders)
        total_tasks = total_instance_files * len(self.solvers)
        completed_tasks = 0

        self.results = {}  # Reset results

        for folder in self.instance_folders:
            folder_name = os.path.basename(folder)
            self.results[folder_name] = {'instances': {}}
            instance_files = sorted([f for f in os.listdir(folder) if f.endswith('.txt') and not f.endswith('-solution.txt')])

            for instance_file in instance_files:
                instance_path = os.path.join(folder, instance_file)
                instance_name = os.path.splitext(instance_file)[0]

                # Parse constraints from the instance file
                num_constraints, constraint_counts = self.parse_instance_constraints(instance_path)
                self.results[folder_name]['instances'][instance_name] = {
                    'constraints': constraint_counts,
                    'times': {},
                    'is_sat': False  # Default to False, will update later
                }

                # Determine number of runs
                if '4-constraint-hard' in folder_name:
                    num_runs = 5
                else:
                    num_runs = 15

                for solver_name in self.solvers:
                    times = []
                    is_sat = None
                    for _ in range(num_runs):
                        start_time = time.time()
                        solver_module = importlib.import_module(solver_name)
                        try:
                            result = solver_module.Solver(instance_path)
                            if is_sat is None:
                                is_sat = (result['sat'] == 'sat')
                            elif is_sat != (result['sat'] == 'sat'):
                                print(f"Inconsistent sat/unsat results for solver {solver_name} on instance {instance_name}")
                            if result['sat'] != 'sat':
                                is_sat = False
                                break  # No need to time unsat instances
                        except Exception as e:
                            print(f"Error running solver {solver_name} on instance {instance_name}: {e}")
                            times.append(float('inf'))
                            continue
                        end_time = time.time()
                        elapsed_time = (end_time - start_time) * 1000  # Convert to milliseconds
                        times.append(elapsed_time)

                    if is_sat:
                        mean_time = np.mean(times)
                        self.results[folder_name]['instances'][instance_name]['times'][solver_name] = mean_time
                        self.results[folder_name]['instances'][instance_name]['is_sat'] = True
                    else:
                        print(f"Instance {instance_name} is unsatisfiable for solver {solver_name}, skipping.")

                    completed_tasks += 1
                    progress = (completed_tasks / (total_tasks)) * 100
                    self.progress_var.set(progress)
                    self.update_idletasks()

        messagebox.showinfo("Benchmarking Complete", "Benchmarking has completed successfully.")
        self.folder_listbox.config(state='normal')

    def parse_instance_constraints(self, instance_path):
        constraint_types = ['Authorisations', 'Separation-of-duty', 'Binding-of-duty', 'At-most-k', 'One-team', 'Precedence']
        constraint_counts = {ctype: 0 for ctype in constraint_types}
        total_constraints = 0

        with open(instance_path, 'r') as file:
            lines = file.readlines()

        for line in lines:
            line = line.strip()
            for ctype in constraint_types:
                if line.startswith(ctype):
                    constraint_counts[ctype] += 1
                    total_constraints += 1
                    break

        return total_constraints, constraint_counts

    def generate_graphs(self):
        if not self.results:
            messagebox.showerror("Error", "No results to display. Please run the benchmarking first.")
            return

        # Clear existing tabs
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)

        overall_data = {'instances': {}, 'constraints': {}, 'times': {}}

        for folder_name in self.results:
            self.create_folder_tab(folder_name)
            # Collect data for overall graph
            folder_data = self.results[folder_name]['instances']
            for instance_name, data in folder_data.items():
                if data['is_sat']:
                    overall_data['instances'][instance_name] = data
                    # Sum constraints
                    constraints = data['constraints']
                    for ctype, count in constraints.items():
                        overall_data['constraints'][ctype] = overall_data['constraints'].get(ctype, 0) + count
                    # Times
                    for solver_name, time_value in data['times'].items():
                        if solver_name not in overall_data['times']:
                            overall_data['times'][solver_name] = []
                        overall_data['times'][solver_name].append(time_value)

        # Create overall tab
        self.create_overall_tab(overall_data)

    def create_folder_tab(self, folder_name):
        folder_tab = ttk.Frame(self.notebook)
        self.notebook.add(folder_tab, text=folder_name)

        # Create sub-notebook for graphs
        sub_notebook = ttk.Notebook(folder_tab)
        sub_notebook.pack(fill='both', expand=True)

        # Plotting the mean times for each solver
        self.plot_solver_times(folder_name, sub_notebook)

        # Plotting constraint counts vs mean time
        self.plot_constraints_vs_time(folder_name, sub_notebook)

    def create_overall_tab(self, overall_data):
        overall_tab = ttk.Frame(self.notebook)
        self.notebook.add(overall_tab, text='Overall')

        # Create sub-notebook for graphs
        sub_notebook = ttk.Notebook(overall_tab)
        sub_notebook.pack(fill='both', expand=True)

        # Plot overall mean times
        self.plot_overall_solver_times(overall_data, sub_notebook)

        # Plot overall constraints vs time
        self.plot_overall_constraints_vs_time(overall_data, sub_notebook)

    def plot_solver_times(self, folder_name, sub_notebook):
        instances_data = self.results[folder_name]['instances']
        instances = [name for name in instances_data.keys() if instances_data[name]['is_sat']]
        num_instances = len(instances)
        x = np.arange(num_instances)
        width = 0.25

        fig, ax = plt.subplots(figsize=(8, 6))

        for idx, solver_name in enumerate(self.solvers):
            solver_times = []
            for instance_name in instances:
                instance_times = instances_data[instance_name]['times']
                if solver_name in instance_times:
                    solver_times.append(instance_times[solver_name])
                else:
                    solver_times.append(0)  # Or np.nan
            ax.bar(x + idx * width, solver_times, width, label=solver_name)

        ax.set_xlabel('Instances')
        ax.set_ylabel('Mean Execution Time (ms)')
        ax.set_title(f'Mean Execution Time per Solver for {folder_name}')
        ax.set_xticks(x + width)
        ax.set_xticklabels(instances, rotation=90)
        ax.legend()

        # Embed plot in tkinter
        graph_tab = ttk.Frame(sub_notebook)
        sub_notebook.add(graph_tab, text='Solver Times')

        canvas = FigureCanvasTkAgg(fig, master=graph_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def plot_constraints_vs_time(self, folder_name, sub_notebook):
        instances_data = self.results[folder_name]['instances']

        constraint_types = ['Authorisations', 'Separation-of-duty', 'Binding-of-duty', 'At-most-k', 'One-team', 'Precedence']

        for ctype in constraint_types:
            # For each solver, map number of constraints to list of times
            constraint_counts_set = set()
            solver_times_by_constraint_count = {solver_name: {} for solver_name in self.solvers}

            for instance_name, data in instances_data.items():
                if not data.get('is_sat', False):
                    continue
                num_constraints = data['constraints'][ctype]
                if num_constraints == 0:
                    continue
                constraint_counts_set.add(num_constraints)
                for solver_name in self.solvers:
                    instance_times = data['times']
                    if solver_name in instance_times:
                        time_value = instance_times[solver_name]
                        if not np.isfinite(time_value):
                            continue
                        if num_constraints not in solver_times_by_constraint_count[solver_name]:
                            solver_times_by_constraint_count[solver_name][num_constraints] = []
                        solver_times_by_constraint_count[solver_name][num_constraints].append(time_value)

            if not constraint_counts_set:
                # No constraints of this type
                continue

            constraint_counts = sorted(constraint_counts_set)
            fig, ax = plt.subplots(figsize=(8, 6))

            for solver_name in self.solvers:
                mean_times = []
                counts_for_plot = []
                for count in constraint_counts:
                    times_list = solver_times_by_constraint_count[solver_name].get(count, [])
                    if times_list:
                        mean_time = np.mean(times_list)
                        counts_for_plot.append(count)
                        mean_times.append(mean_time)
                if counts_for_plot:
                    ax.plot(counts_for_plot, mean_times, marker='o', label=solver_name)

            ax.set_xlabel(f'Number of {ctype} Constraints')
            ax.set_ylabel('Mean Execution Time (ms)')
            ax.set_title(f'{ctype} Constraints vs Execution Time for {folder_name}')
            ax.legend()

            # Embed plot in tkinter
            graph_tab = ttk.Frame(sub_notebook)
            sub_notebook.add(graph_tab, text=f'{ctype} Constraints')

            canvas = FigureCanvasTkAgg(fig, master=graph_tab)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)

    def plot_overall_solver_times(self, overall_data, sub_notebook):
        instances_data = overall_data['instances']
        instances = list(instances_data.keys())
        num_instances = len(instances)
        x = np.arange(num_instances)
        width = 0.25

        fig, ax = plt.subplots(figsize=(8, 6))

        for idx, solver_name in enumerate(self.solvers):
            solver_times = []
            for instance_name in instances:
                instance_times = instances_data[instance_name]['times']
                if solver_name in instance_times:
                    solver_times.append(instance_times[solver_name])
                else:
                    solver_times.append(0)  # Or np.nan
            ax.bar(x + idx * width, solver_times, width, label=solver_name)

        ax.set_xlabel('Instances')
        ax.set_ylabel('Mean Execution Time (ms)')
        ax.set_title('Overall Mean Execution Time per Solver')
        ax.set_xticks(x + width)
        ax.set_xticklabels(instances, rotation=90)
        ax.legend()

        # Embed plot in tkinter
        graph_tab = ttk.Frame(sub_notebook)
        sub_notebook.add(graph_tab, text='Overall Solver Times')

        canvas = FigureCanvasTkAgg(fig, master=graph_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def plot_overall_constraints_vs_time(self, overall_data, sub_notebook):
        instances_data = overall_data['instances']

        constraint_types = ['Authorisations', 'Separation-of-duty', 'Binding-of-duty', 'At-most-k', 'One-team', 'Precedence']

        for ctype in constraint_types:
            # For each solver, map number of constraints to list of times
            constraint_counts_set = set()
            solver_times_by_constraint_count = {solver_name: {} for solver_name in self.solvers}

            for instance_name, data in instances_data.items():
                num_constraints = data['constraints'][ctype]
                if num_constraints == 0:
                    continue
                constraint_counts_set.add(num_constraints)
                for solver_name in self.solvers:
                    instance_times = data['times']
                    if solver_name in instance_times:
                        time_value = instance_times[solver_name]
                        if not np.isfinite(time_value):
                            continue
                        if num_constraints not in solver_times_by_constraint_count[solver_name]:
                            solver_times_by_constraint_count[solver_name][num_constraints] = []
                        solver_times_by_constraint_count[solver_name][num_constraints].append(time_value)

            if not constraint_counts_set:
                # No constraints of this type
                continue

            constraint_counts = sorted(constraint_counts_set)
            fig, ax = plt.subplots(figsize=(8, 6))

            for solver_name in self.solvers:
                mean_times = []
                counts_for_plot = []
                for count in constraint_counts:
                    times_list = solver_times_by_constraint_count[solver_name].get(count, [])
                    if times_list:
                        mean_time = np.mean(times_list)
                        counts_for_plot.append(count)
                        mean_times.append(mean_time)
                if counts_for_plot:
                    ax.plot(counts_for_plot, mean_times, marker='o', label=solver_name)

            ax.set_xlabel(f'Number of {ctype} Constraints')
            ax.set_ylabel('Mean Execution Time (ms)')
            ax.set_title(f'Overall {ctype} Constraints vs Execution Time')
            ax.legend()

            # Embed plot in tkinter
            graph_tab = ttk.Frame(sub_notebook)
            sub_notebook.add(graph_tab, text=f'{ctype} Constraints')

            canvas = FigureCanvasTkAgg(fig, master=graph_tab)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)

if __name__ == '__main__':
    app = SolverBenchmarkApp()
    app.mainloop()
