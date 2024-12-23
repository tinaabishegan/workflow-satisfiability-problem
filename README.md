# Workflow Satisfiability Problem (WSP) Solver Suite

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Installation](#installation)
- [Usage](#usage)
  - [Graphical User Interface (GUI)](#graphical-user-interface-gui)
  - [Solver Selection](#solver-selection)
  - [Defining Workflow Steps and Users](#defining-workflow-steps-and-users)
  - [Adding Constraints](#adding-constraints)
  - [Solving the Problem](#solving-the-problem)
  - [Importing and Exporting Problem Instances](#importing-and-exporting-problem-instances)
- [Validators](#validators)
  - [Validator.py](#validatorpy)
  - [Validator2.py](#validator2py)
  - [Validator3.py](#validator3py)
- [Benchmarking Tool](#benchmarking-tool)
- [Solver Modules](#solver-modules)
  - [Solver Combinatorial](#solver-combinatorial)
  - [Solver Symmetry](#solver-symmetry)
  - [Solver Doreen](#solver-doreen)
- [Helper Module](#helper-module)
- [References](#references)
- [Acknowledgments](#acknowledgments)

---

## Overview

The **Workflow Satisfiability Problem (WSP)** is a critical challenge in access control and workflow management systems. It involves determining whether there exists an assignment of users to workflow steps such that all specified constraints are satisfied. These constraints typically include authorizations, user capacities, separation of duties, binding of duties, and other organizational policies.

This project encompasses a comprehensive suite of tools designed to define, solve, validate, and benchmark WSP instances. It includes three distinct solver implementations, multiple validation scripts, a graphical user interface (GUI) for user interaction, and a benchmarking tool to evaluate solver performance across various problem instances.

---

## Directory Structure

```plaintext
WSP-Solver-Suite/
├── all/
│   ├── 1-constraint-small/
│   │   ├── 1.txt
│   │   ├── 1-solution.txt
│   │   └── ...
│   ├── 3-constraint/
│   │   ├── 1.txt
│   │   ├── 1-solution.txt
│   │   └── ...
│   ├── 3-constraint-small/
│   │   ├── 1.txt
│   │   ├── 1-solution.txt
│   │   └── ...
│   ├── 4-constraint/
│   │   ├── 1.txt
│   │   ├── 1-solution.txt
│   │   └── ...
│   ├── 4-constraint-hard/
│   │   ├── 1.txt
|   |   ├── 1-solution.txt
│   │   └── ...
│   ├── 4-constraint-small/
│   │   ├── 1.txt
│   │   ├── 1-solution.txt
│   │   └── ...
│   ├── 5-constraint/
│   │   ├── 1.txt
│   │   ├── 1-solution.txt
│   │   └── ...
│   ├── 5-constraint-small/
│   │   ├── 1.txt
│   │   ├── 1-solution.txt
│   │   └── ...
│   └── instances/
│       ├── example1.txt
│       └── ...
├── solver_combinatorial.py
├── solver_symmetry.py
├── solver_doreen.py
├── validator.py
├── validator2.py
├── validator3.py
├── helper.py
├── complete.py
├── evaluation.py
└── README.md
```

- **all/**: Contains all problem instance folders, each with multiple workflow satisfiability problem instances and their corresponding solutions.
- **solver_combinatorial.py**: Implements the combinatorial constraint programming approach to solving WSP.
- **solver_symmetry.py**: Enhances the combinatorial approach by incorporating symmetry-breaking techniques.
- **solver_doreen.py**: Employs a hybrid approach combining OR-Tools and Z3 for advanced constraint handling.
- **validator.py**, **validator2.py**, **validator3.py**: Scripts for validating solver-generated solutions against defined constraints.
- **helper.py**: Contains utility functions supporting the solvers and validators.
- **complete.py**: The main GUI application facilitating problem definition, solver execution, and solution visualization.
- **evaluation.py**: A benchmarking tool to assess and compare the performance of the three solvers across various problem instances.
- **README.md**: This documentation file.

---

## Installation

### Prerequisites

- **Python 3.7 or higher**: Ensure that Python is installed on your system. You can download it from [Python's official website](https://www.python.org/downloads/).
- **Google OR-Tools**: A powerful optimization engine used by the solvers.
- **Z3 Theorem Prover**: Required for the `solver_doreen` implementation.
- **Additional Python Libraries**: Such as `tkinter`, `matplotlib`, `numpy`, and `pandas`.

### Installation Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/tinaabishegan/workflow-satisfiability-problem.git
   ```

2. **Create a Virtual Environment (Optional but Recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Required Python Libraries**

   ```bash
   pip install ortools z3-solver matplotlib numpy pandas
   ```

   - **Note**: Ensure that `tkinter` is installed. It usually comes pre-installed with Python, but if not, refer to [Tkinter Installation Guide](https://tkdocs.com/tutorial/install.html).

4. **Verify Installation**

   Run a simple Python script to verify that all libraries are correctly installed.

   ```python
   import ortools
   import z3
   import matplotlib
   import numpy
   import pandas
   import tkinter
   print("All libraries are installed correctly.")
   ```

---

## Usage

The project offers a comprehensive GUI application for defining and solving WSP instances, along with validators and a benchmarking tool for performance analysis.

### Graphical User Interface (GUI)

The `complete.py` script launches the main GUI application, facilitating an interactive environment for defining workflow steps, users, constraints, and solving the WSP.

#### Launching the GUI

```bash
python complete.py
```

#### GUI Components

1. **Tabs Overview**
   
   - **Input Tab**: Define workflow steps, users, and import/export problem instances.
   - **Constraints Tab**: Add and manage various constraint types.
   - **Results Tab**: Execute solvers, view solutions, and validate results.

2. **Input Tab**

   - **Solver Selection**: Choose among the three solvers:
     - `solver_combinatorial`
     - `solver_symmetry`
     - `solver_doreen`
   
   - **Defining Steps and Users**:
     - **Steps Listbox**: Add or remove workflow steps.
     - **Users Listbox**: Add or remove users.
   
   - **Import/Export Functionality**:
     - **Import Problem**: Load a problem instance from a text file.
     - **Export Problem**: Save the current problem instance to a text file.

3. **Constraints Tab**

   - **Adding Constraints**: Add various constraint types using dedicated buttons:
     - **Add Authorisation Constraint**
     - **Add Separation-of-Duty Constraint**
     - **Add Binding-of-Duty Constraint**
     - **Add At-Most-k Constraint**
     - **Add One-Team Constraint**
     - **Add User Capacity Constraint**
   
   - **Constraints Treeview**: View and manage all added constraints. Remove selected constraints as needed.

4. **Results Tab**

   - **Solve Button**: Initiate the solving process using the selected solver.
   
   - **Validation Checkbox**: Option to enable solution validation after solving.
   
   - **Max Solutions Spinbox**: Specify the number of feasible solutions to retrieve.
   
   - **Progress Bar**: Monitor the progress of the solving process.
   
   - **Info Label**: Display information such as the number of solutions found and execution time.
   
   - **Solution Dropdown**: Select among multiple solutions if available.
   
   - **Results Treeview**: View the detailed assignment of users to steps for the selected solution.
   
   - **Validation Notebooks**: Access validation results from the three validator scripts, presented in separate tabs.

#### Defining Workflow Steps and Users

1. **Adding Steps**
   
   - Click the "+" button under the Steps Listbox.
   - Enter the step identifier (e.g., `s1`, `s2`, etc.).
   
2. **Adding Users**
   
   - Click the "+" button under the Users Listbox.
   - Enter the user identifier (e.g., `u1`, `u2`, etc.).

#### Adding Constraints

1. **Authorisation Constraint**
   
   - Click "Add Authorisation Constraint".
   - Select a user from the dropdown.
   - Select the steps that the user is authorised to perform.
   
2. **Separation-of-Duty Constraint**
   
   - Click "Add Separation-of-Duty Constraint".
   - Select two distinct steps that must be assigned to different users.
   
3. **Binding-of-Duty Constraint**
   
   - Click "Add Binding-of-Duty Constraint".
   - Select two distinct steps that must be assigned to the same user.
   
4. **At-Most-k Constraint**
   
   - Click "Add At-Most-k Constraint".
   - Select a set of steps.
   - Enter the maximum number of distinct users (`k`) allowed for these steps.
   
5. **One-Team Constraint**
   
   - Click "Add One-Team Constraint".
   - Select a set of steps.
   - Define teams by selecting users to form each team.
   
6. **User Capacity Constraint**
   
   - Click "Add User Capacity Constraint".
   - Select a user.
   - Enter the maximum number of steps the user can be assigned.

#### Solving the Problem

1. **Configure Solving Parameters**
   
   - Select the desired solver from the dropdown menu.
   - Specify the maximum number of solutions to retrieve using the spinbox.
   - Optionally, enable validation to verify solutions post-solving.
   
2. **Execute the Solver**
   
   - Click the "Solve Problem" button.
   - Monitor progress via the progress bar and info label.
   
3. **View Solutions**
   
   - Once solving is complete, use the solution dropdown to navigate between different solutions.
   - View detailed assignments in the Results Treeview.
   
4. **Validate Solutions**
   
   - If validation is enabled, view validation results in the Validation Notebooks.
   - Each validator script's output is displayed in its respective tab for comprehensive verification.

#### Importing and Exporting Problem Instances

1. **Importing a Problem Instance**
   
   - Click the "Import Problem" button.
   - Select the desired problem instance text file.
   - The GUI will populate steps, users, and constraints based on the imported file.
   
2. **Exporting a Problem Instance**
   
   - Click the "Export Problem" button.
   - Choose the destination and filename for the exported text file.
   - The current problem instance configuration will be saved for external use or sharing.

---

## Validators

Validating solver-generated solutions is crucial to ensure adherence to all defined constraints. This project includes three distinct validator scripts, each offering unique validation methodologies.

### Validator.py

**Purpose**:  
`validator.py` performs comprehensive validation of solutions by checking each constraint type against the user-step assignments.

**Key Features**:

- **Constraint Checks**:
  - **Authorisations**: Ensures steps are only assigned to authorized users.
  - **Separation-of-Duty**: Verifies that designated steps are assigned to different users.
  - **Binding-of-Duty**: Confirms that designated steps are assigned to the same user.
  - **At-Most-k**: Checks that no more than `k` distinct users are assigned to specified steps.
  - **One-Team**: Ensures that all steps in a set are assigned to users within a single team.
  - **User Capacity**: Validates that no user is assigned more steps than their capacity allows.

- **Usage**:

  ```bash
  python validator.py <problem_file> <solution_file>
  ```

- **Output**:  
  Reports whether the solution is valid and details any constraint violations.

### Validator2.py

**Purpose**:  
`validator2.py` offers an object-oriented approach to solution validation, encapsulating validation logic within a `WSPValidator` class for enhanced modularity and reusability.

**Key Features**:

- **Class Structure**:
  - **WSPValidator**: Handles parsing and validation processes.
  
- **Validation Process**:
  - **parse_problem**: Parses the problem instance, extracting constraints.
  - **parse_solution**: Reads and maps solution assignments.
  - **validate_solution**: Executes all constraint checks and aggregates results.

- **Usage**:

  ```bash
  python validator2.py <problem_file> <solution_file>
  ```

- **Output**:  
  Indicates overall solution validity and lists specific constraint violations if any.

### Validator3.py

**Purpose**:  
`validator3.py` provides a streamlined validation mechanism using regular expressions and direct mapping techniques for efficient constraint verification.

**Key Features**:

- **Efficient Parsing**: Utilizes regular expressions to parse problem and solution files swiftly.
  
- **Direct Mapping**: Maps constraints and assignments directly for rapid validation.
  
- **Comprehensive Checks**:
  - **Authorizations**
  - **Separation-of-Duty**
  - **Binding-of-Duty**
  - **At-Most-k**
  - **One-Team**
  - **User Capacity**

- **Usage**:

  ```bash
  python validator3.py <problem_instance_file> <solution_file>
  ```

- **Output**:  
  Reports solution validity and details any violations detected.

---

## Benchmarking Tool

The `evaluation.py` script serves as a benchmarking tool to evaluate and compare the performance of the three solvers across various WSP instances.

### Key Features

- **Instance Management**:
  - Select and manage multiple instance folders containing problem instances.
  
- **Benchmark Execution**:
  - Runs each solver on all selected problem instances.
  - Measures execution times and solution statuses (satisfiable or unsatisfiable).
  
- **Result Recording**:
  - Aggregates benchmarking results and exports them to an Excel file for detailed analysis.
  
- **Graphical Visualization**:
  - Generates performance graphs, including:
    - Mean execution times per solver.
    - Constraint counts versus execution times.
    - Overall solver performance across all instances.

### Usage

1. **Launch the Benchmarking Tool**

   ```bash
   python evaluation.py
   ```

2. **Add Instance Folders**
   
   - Click the "Add Folders" button to select directories containing problem instances.
   
3. **Start Benchmarking**
   
   - Click the "Start Benchmarking" button to begin the benchmarking process.
   - Monitor progress via the progress bar.

4. **Generate Graphs**
   
   - Once benchmarking is complete, click the "Generate Graphs" button to visualize performance metrics.
   - View graphs within the integrated notebook interface.

5. **Save Results**
   
   - Export benchmarking results to an Excel file for further analysis or record-keeping.

---

## Solver Modules

### Solver Combinatorial

**File**: `solver_combinatorial.py`

**Description**:  
Implements a combinatorial constraint programming approach using Google OR-Tools. It directly encodes constraints by enumerating possible combinations, particularly for complex constraints like "At-most-k."

**Key Functionalities**:

- **Constraint Encoding**:
  - Authorizations
  - Separation-of-Duty
  - Binding-of-Duty
  - At-Most-k
  - One-Team
  - User Capacity

- **Solution Enumeration**:
  - Supports single and multiple solution searches.

**Advantages**:

- Simple and direct encoding.
- Flexible for various constraint types.
- Easy to implement and understand.

**Disadvantages**:

- Scalability issues due to combinatorial explosion.
- Redundancy and symmetry not explicitly handled.

### Solver Symmetry

**File**: `solver_symmetry.py`

**Description**:  
Enhances the combinatorial approach by incorporating symmetry-breaking techniques to reduce redundant solution explorations. Utilizes auxiliary variables and ordering constraints to optimize performance.

**Key Functionalities**:

- **Constraint Encoding with Symmetry Breaking**:
  - Introduces auxiliary variables to enforce ordered assignments.
  - Reduces symmetrical redundancies in solution space.

- **Solution Enumeration**:
  - Similar to the combinatorial solver but with enhanced efficiency.

**Advantages**:

- Improved scalability for medium to large instances.
- Effective symmetry-breaking reduces redundant computations.

**Disadvantages**:

- Increased implementation complexity.
- Potential overhead from additional constraints.

### Solver Doreen

**File**: `solver_doreen.py`

**Description**:  
Employs a hybrid approach combining OR-Tools and the Z3 theorem prover for advanced constraint handling. Utilizes boolean variables for user assignments and leverages logical reasoning capabilities for complex constraints.

**Key Functionalities**:

- **Hybrid Constraint Encoding**:
  - Integrates OR-Tools for constraint programming.
  - Utilizes Z3 for logical reasoning and complex constraint handling.

- **Solution Enumeration**:
  - Supports single and multiple solution retrieval with enhanced efficiency.

**Advantages**:

- Advanced logical constraint handling.
- Efficient solution enumeration for logically dense constraints.
- Scalable for large and complex instances.

**Disadvantages**:

- High implementation complexity due to integration of two solver frameworks.
- Potential performance bottlenecks from hybrid execution.
- Requires careful synchronization between OR-Tools and Z3.

---

## Helper Module

**File**: `helper.py`

**Description**:  
Contains utility functions that support the core functionalities of the solvers and validators. Facilitates the transformation of solver outputs into user-friendly formats suitable for display within the GUI.

**Key Functionalities**:

- **Output Transformation**:
  - Converts solver result dictionaries into formatted strings.
  - Handles both single and multiple solution scenarios.



---
