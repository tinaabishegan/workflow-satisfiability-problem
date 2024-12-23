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
import pandas as pd  # For Excel file creation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class SolverBenchmarkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Solver Benchmarking Tool")
        self.geometry("900x700")
        self.create_widgets()
        self.solvers = ['solver_combinatorial']
        self.instance_folders = []
        self.results = {}  # To store the results for plotting
        self.timeout = 240  # Timeout in seconds (4 minutes)
        self.runs_per_instance = 1  # Number of times each instance is solved

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True)

        # Frame for folder selection
        folder_frame = ttk.LabelFrame(main_frame, text="Instance Folders")
        folder_frame.pack(fill='x', padx=10, pady=10)

        self.folder_listbox = tk.Listbox(folder_frame, selectmode='extended', height=5)
        self.folder_listbox.pack(fill='x', expand=True, padx=5, pady=5)

        add_folder_button = ttk.Button(folder_frame, text="Add Folders", command=self.add_folders)
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

    def add_folders(self):
        folders_selected = filedialog.askdirectory(title="Select Instance Folders", mustexist=True, parent=self)
        if folders_selected:
            folders = self.get_all_subfolders(folders_selected)
            for folder_selected in folders:
                if folder_selected not in self.instance_folders:
                    self.instance_folders.append(folder_selected)
                    self.folder_listbox.insert(tk.END, folder_selected)

    def get_all_subfolders(self, parent_folder):
        subfolders = [os.path.join(parent_folder, f.name) for f in os.scandir(parent_folder) if f.is_dir()]
        if not subfolders:
            return [parent_folder]
        else:
            return subfolders

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

    def solver_with_timeout(self, solver_function, timeout, *args, **kwargs):
        """Run the solver with a timeout using threading."""
        result = [None]  # Mutable container to store the result
        exception = [None]  # Mutable container to store any exception

        def target():
            try:
                result[0] = solver_function(*args, **kwargs)
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            return "Timeout"
        if exception[0]:
            raise exception[0]
        return result[0]

    def run_benchmark(self):
        total_instance_files = sum(len([f for f in os.listdir(folder) if f.endswith('.txt') and not f.endswith('-solution.txt')]) for folder in self.instance_folders)
        total_tasks = total_instance_files * len(self.solvers)
        completed_tasks = 0

        self.results = {}  # Reset results

        for folder in self.instance_folders:
            folder_name = os.path.basename(folder)
            self.results[folder_name] = {'instances': {}}
            instance_files = sorted(
                [f for f in os.listdir(folder) if f.endswith('.txt') and not f.endswith('-solution.txt')],
                key=lambda x: int(re.search(r'\d+', os.path.splitext(x)[0]).group())
            )

            for instance_file in instance_files:
                instance_path = os.path.join(folder, instance_file)
                instance_name = os.path.splitext(instance_file)[0]

                # Parse constraints from the instance file
                num_constraints, constraint_counts = self.parse_instance_constraints(instance_path)
                self.results[folder_name]['instances'][instance_name] = {
                    'constraints': constraint_counts,
                    'times': {solver: [] for solver in self.solvers},
                    'is_sat': None  # Will be updated later
                }

                # Skip solvers based on folder name
                solvers_to_run = self.solvers.copy()
                if '4-constraint-hard' in folder_name:
                    solvers_to_run = ['solver_symmetry.py']  # Only run this solver
                if 'instances' in folder_name:
                    if instance_name == 'example19.txt':
                        solvers_to_run = []  # Only run this solver
                    if instance_name == 'example16.txt' or instance_name == 'example17.txt' or instance_name == 'example18.txt':
                        solvers_to_run = ['solver_combinatorial', 'solver_symmetry.py']
                for solver_name in solvers_to_run:
                    for _ in range(self.runs_per_instance):
                        start_time = time.time()
                        try:
                            solver_module = importlib.import_module(solver_name)
                            result = solver_module.Solver(instance_path)

                            is_sat = result['sat'] == 'sat'
                            elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds

                            self.results[folder_name]['instances'][instance_name]['times'][solver_name].append(elapsed_time)
                            if self.results[folder_name]['instances'][instance_name]['is_sat'] is None:
                                self.results[folder_name]['instances'][instance_name]['is_sat'] = is_sat
                            elif self.results[folder_name]['instances'][instance_name]['is_sat'] != is_sat:
                                print(f"Inconsistent SAT/UNSAT results for solver {solver_name} on instance {instance_name}")
                        except Exception as e:
                            print(f"Error running solver {solver_name} on instance {instance_name}: {e}")
                            self.results[folder_name]['instances'][instance_name]['times'][solver_name].append(float('inf'))
                            self.results[folder_name]['instances'][instance_name]['is_sat'] = False

                    completed_tasks += 1
                    progress = (completed_tasks / (total_tasks)) * 100
                    self.progress_var.set(progress)
                    self.update_idletasks()

        self.save_results_to_excel()
        messagebox.showinfo("Benchmarking Complete", "Benchmarking has completed successfully.")
        self.folder_listbox.config(state='normal')

    def parse_instance_constraints(self, instance_path):
        constraint_types = ['Authorisations', 'Separation-of-duty', 'Binding-of-duty', 'At-most-k', 'One-team', 'User-capacity']
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

    def save_results_to_excel(self):
        """Save results to an Excel file."""
        output_data = []
        for folder_name, folder_data in self.results.items():
            for instance_name, instance_data in folder_data['instances'].items():
                for solver_name, times in instance_data['times'].items():
                    for run_idx, time_value in enumerate(times, start=1):
                        output_data.append({
                            'Folder': folder_name,
                            'Instance': instance_name,
                            'Solver': solver_name,
                            'Run': run_idx,
                            'Time (ms)': time_value,
                            'SAT/UNSAT': instance_data['is_sat']
                        })

        df = pd.DataFrame(output_data)
        excel_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if excel_path:
            df.to_excel(excel_path, index=False)
            print(f"Results saved to {excel_path}")

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
                # Exclude solver_doreen times for 4-constraint-hard
                if '4-constraint-hard' in folder_name:
                    data_copy = data.copy()
                    data_copy['times'] = {k: v for k, v in data['times'].items() if k != 'solver_doreen'}
                    overall_data['instances'][instance_name] = data_copy
                else:
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
        instances = sorted(instances_data.keys(), key=lambda x: int(x))
        num_instances = len(instances)
        x = np.arange(num_instances)
        width = 0.25

        fig, ax = plt.subplots(figsize=(10, 6))

        # Exclude solver_doreen times for 4-constraint-hard
        solvers_to_plot = self.solvers.copy()
        if '4-constraint-hard' in folder_name and 'solver_doreen' in solvers_to_plot:
            solvers_to_plot.remove('solver_doreen')

        for idx, solver_name in enumerate(solvers_to_plot):
            solver_times = []
            for instance_name in instances:
                instance_times = instances_data[instance_name]['times']
                is_sat = instances_data[instance_name]['is_sat']
                if solver_name in instance_times:
                    time_value = instance_times[solver_name]
                    if is_sat is False:
                        solver_times.append(0)  # Represent unsat with zero height
                    else:
                        solver_times.append(time_value)
                else:
                    solver_times.append(0)
            bar_positions = x + idx * width
            bar_container = ax.bar(bar_positions, solver_times, width, label=solver_name)

            # Annotate bars with actual time values
            for rect, time_value in zip(bar_container, solver_times):
                ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f'{time_value:.2f}', ha='center', va='bottom', rotation=90)

        ax.set_xlabel('Instances')
        ax.set_ylabel('Mean Execution Time (ms)')
        ax.set_title(f'Mean Execution Time per Solver for {folder_name}')
        ax.set_xticks(x + width * (len(solvers_to_plot) - 1) / 2)
        ax.set_xticklabels(instances, rotation=90)
        ax.legend()

        fig.tight_layout()

        # Embed plot in tkinter
        graph_tab = ttk.Frame(sub_notebook)
        sub_notebook.add(graph_tab, text='Solver Times')

        canvas = FigureCanvasTkAgg(fig, master=graph_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def plot_constraints_vs_time(self, folder_name, sub_notebook):
        instances_data = self.results[folder_name]['instances']

        constraint_types = ['Authorisations', 'Separation-of-duty', 'Binding-of-duty', 'At-most-k', 'One-team', 'User-capacity']

        for ctype in constraint_types:
            # For each solver, map number of constraints to list of times
            constraint_counts_set = set()
            solver_times_by_constraint_count = {solver_name: {} for solver_name in self.solvers}

            for instance_name, data in instances_data.items():
                num_constraints = data['constraints'][ctype]
                constraint_counts_set.add(num_constraints)
                for solver_name in self.solvers:
                    # Skip solver_doreen for 4-constraint-hard
                    if '4-constraint-hard' in folder_name and solver_name == 'solver_doreen':
                        continue
                    instance_times = data['times']
                    is_sat = data['is_sat']
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

            for solver_name in solver_times_by_constraint_count:
                # Skip solver_doreen for 4-constraint-hard
                if '4-constraint-hard' in folder_name and solver_name == 'solver_doreen':
                    continue
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
                    # Annotate each point with actual time value
                    for x_point, y_point in zip(counts_for_plot, mean_times):
                        ax.text(x_point, y_point, f'{y_point:.2f}', ha='right', va='bottom')

            ax.set_xlabel(f'Number of {ctype} Constraints')
            ax.set_ylabel('Mean Execution Time (ms)')
            ax.set_title(f'{ctype} Constraints vs Execution Time for {folder_name}')
            ax.legend()

            fig.tight_layout()

            # Embed plot in tkinter
            graph_tab = ttk.Frame(sub_notebook)
            sub_notebook.add(graph_tab, text=f'{ctype} Constraints')

            canvas = FigureCanvasTkAgg(fig, master=graph_tab)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)

    def plot_overall_solver_times(self, overall_data, sub_notebook):
        instances_data = overall_data['instances']
        instances = sorted(instances_data.keys(), key=lambda x: int(x))
        num_instances = len(instances)
        x = np.arange(num_instances)
        width = 0.25

        fig, ax = plt.subplots(figsize=(10, 6))

        for idx, solver_name in enumerate(self.solvers):
            solver_times = []
            for instance_name in instances:
                data = instances_data[instance_name]
                # Skip solver_doreen times for 4-constraint-hard
                if '4-constraint-hard' in data.get('folder_name', '') and solver_name == 'solver_doreen':
                    solver_times.append(0)
                    continue
                instance_times = data['times']
                is_sat = data['is_sat']
                if solver_name in instance_times:
                    time_value = instance_times[solver_name]
                    if is_sat is False:
                        solver_times.append(0)  # Represent unsat with zero height
                    else:
                        solver_times.append(time_value)
                else:
                    solver_times.append(0)
            bar_positions = x + idx * width
            bar_container = ax.bar(bar_positions, solver_times, width, label=solver_name)

            # Annotate bars with actual time values
            for rect, time_value in zip(bar_container, solver_times):
                ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f'{time_value:.2f}', ha='center', va='bottom', rotation=90)

        ax.set_xlabel('Instances')
        ax.set_ylabel('Mean Execution Time (ms)')
        ax.set_title('Overall Mean Execution Time per Solver')
        ax.set_xticks(x + width * (len(self.solvers) - 1) / 2)
        ax.set_xticklabels(instances, rotation=90)
        ax.legend()

        fig.tight_layout()

        # Embed plot in tkinter
        graph_tab = ttk.Frame(sub_notebook)
        sub_notebook.add(graph_tab, text='Overall Solver Times')

        canvas = FigureCanvasTkAgg(fig, master=graph_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def plot_overall_constraints_vs_time(self, overall_data, sub_notebook):
        instances_data = overall_data['instances']

        constraint_types = ['Authorisations', 'Separation-of-duty', 'Binding-of-duty', 'At-most-k', 'One-team', 'User-capacity']

        for ctype in constraint_types:
            # For each solver, map number of constraints to list of times
            constraint_counts_set = set()
            solver_times_by_constraint_count = {solver_name: {} for solver_name in self.solvers}

            for instance_name, data in instances_data.items():
                num_constraints = data['constraints'][ctype]
                constraint_counts_set.add(num_constraints)
                for solver_name in self.solvers:
                    # Skip solver_doreen times for 4-constraint-hard
                    if '4-constraint-hard' in data.get('folder_name', '') and solver_name == 'solver_doreen':
                        continue
                    instance_times = data['times']
                    is_sat = data['is_sat']
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

            for solver_name in solver_times_by_constraint_count:
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
                    # Annotate each point with actual time value
                    for x_point, y_point in zip(counts_for_plot, mean_times):
                        ax.text(x_point, y_point, f'{y_point:.2f}', ha='right', va='bottom')

            ax.set_xlabel(f'Number of {ctype} Constraints')
            ax.set_ylabel('Mean Execution Time (ms)')
            ax.set_title(f'Overall {ctype} Constraints vs Execution Time')
            ax.legend()

            fig.tight_layout()

            # Embed plot in tkinter
            graph_tab = ttk.Frame(sub_notebook)
            sub_notebook.add(graph_tab, text=f'{ctype} Constraints')

            canvas = FigureCanvasTkAgg(fig, master=graph_tab)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)

if __name__ == '__main__':
    app = SolverBenchmarkApp()
    app.mainloop()
