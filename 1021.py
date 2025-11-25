import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import shutil
import subprocess
import matplotlib.pyplot as plt
import math
import time
import json
import threading
from queue import Queue

class MultiRoutePHITSGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Improved PHITS Multi-Route GUI")
        self.root.geometry("1200x750")

        self.routes = []
        self.dose_results = {}
        self.output_dir = tk.StringVar()
        self.phits_command = tk.StringVar(value='phits.bat') # Default command
        
        # PHITSパラメータ用のStringVar
        self.maxcas = tk.StringVar(value='1000')
        self.maxbch = tk.StringVar(value='5')

        # --- UI Setup ---
        self._setup_styles()
        self._setup_menu()
        
        # Main layout container
        main_paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Frame for controls
        controls_frame = ttk.Frame(main_paned_window, padding="10")
        main_paned_window.add(controls_frame, weight=1)

        # Right Frame for route list and logs
        right_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(right_frame, weight=2)
        
        self._setup_controls(controls_frame)
        self._setup_route_display(right_frame)
        self._setup_logging(right_frame)
        
        # Status Bar
        self.status_bar = ttk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Queue for thread communication
        self.log_queue = Queue()
        self.root.after(100, self.process_log_queue)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", padding=2)
        style.configure("TEntry", padding=4)
        style.configure("TLabelframe.Label", font=('Helvetica', 12, 'bold'))

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save Routes", command=self.save_routes)
        file_menu.add_command(label="Load Routes", command=self.load_routes)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

    def _setup_controls(self, parent_frame):
        # Input Frame
        input_frame = ttk.LabelFrame(parent_frame, text="Route and Source Settings", padding=10)
        input_frame.pack(fill=tk.X, expand=True, pady=(0, 10))

        labels = ["Start (x1, y1, z1)", "Midpoint (x2, y2, z2)", "End (x3, y3, z3)", "Source (sx, sy, sz)"]
        self.entries = []
        for i, label_text in enumerate(labels):
            ttk.Label(input_frame, text=label_text).grid(row=i, column=0, sticky="e", padx=5, pady=2)
            row_entries = [ttk.Entry(input_frame, width=8) for _ in range(3)]
            for j, entry in enumerate(row_entries):
                entry.grid(row=i, column=j + 1, padx=2, pady=2)
            self.entries.append(row_entries)

        # [NUCLIDE AND ACTIVITY INPUTS]
        ttk.Label(input_frame, text="Nuclide").grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self.nuclide_entry = ttk.Entry(input_frame, width=12)
        self.nuclide_entry.grid(row=4, column=1, columnspan=2, sticky="w", padx=2)
        self.nuclide_entry.insert(0, "Cs-137") # Default value

        ttk.Label(input_frame, text="Activity (Bq)").grid(row=5, column=0, sticky="e", padx=5, pady=2)
        self.activity_entry = ttk.Entry(input_frame, width=12)
        self.activity_entry.grid(row=5, column=1, columnspan=2, sticky="w", padx=2)
        self.activity_entry.insert(0, "1.0E+12") # Default value

        # [REST OF THE CONTROLS - Adjusted row numbers]
        ttk.Label(input_frame, text="Step (Start -> Mid) [cm]").grid(row=6, column=0, sticky="e", padx=5, pady=5)
        self.step_length1 = ttk.Entry(input_frame, width=10)
        self.step_length1.grid(row=6, column=1, columnspan=2, sticky="w", padx=2)

        ttk.Label(input_frame, text="Step (Mid -> End) [cm]").grid(row=7, column=0, sticky="e", padx=5, pady=5)
        self.step_length2 = ttk.Entry(input_frame, width=10)
        self.step_length2.grid(row=7, column=1, columnspan=2, sticky="w", padx=2)

        folder_frame = ttk.Frame(input_frame)
        folder_frame.grid(row=8, column=0, columnspan=4, sticky="ew", pady=5)
        ttk.Button(folder_frame, text="Select Output Folder", command=self.select_folder).pack(side=tk.LEFT)
        ttk.Label(folder_frame, textvariable=self.output_dir, relief=tk.SUNKEN, anchor="w", width=30).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Action Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=9, column=0, columnspan=4, pady=10)
        ttk.Button(button_frame, text="Add Route", command=self.add_route).pack(side=tk.LEFT, padx=5)
        

        # Simulation Frame
        action_frame = ttk.LabelFrame(parent_frame, text="Simulation & Analysis", padding=10)
        action_frame.pack(fill=tk.X, expand=True)

        # PHITS パラメータ入力
        ttk.Label(action_frame, text="Max CAS:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        param_entry_cas = ttk.Entry(action_frame, textvariable=self.maxcas, width=12)
        param_entry_cas.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(action_frame, text="Max BCH:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        param_entry_bch = ttk.Entry(action_frame, textvariable=self.maxbch, width=12)
        param_entry_bch.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        # ボタンの行をずらす (row=0 -> row=2, row=1 -> row=3, etc.)
        ttk.Button(action_frame, text="Generate PHITS Files", command=self.generate_all_files).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(action_frame, text="Run PHITS Simulation", command=self.run_all_phits_threaded).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(action_frame, text="Calculate Dose", command=self.calculate_dose).grid(row=3, column=0, padx=5, pady=5)
        ttk.Button(action_frame, text="Visualize All Routes", command=self.visualize_routes).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(action_frame, text="Compare Route Doses", command=self.visualize_dose_comparison).grid(row=4, column=0, columnspan=1, padx=5, pady=5)
        ttk.Button(action_frame, text="Show Dose Profile", command=self.visualize_dose_profile).grid(row=4, column=1, columnspan=1, padx=5, pady=5)

    def _setup_route_display(self, parent_frame):
        display_frame = ttk.LabelFrame(parent_frame, text="Registered Routes", padding=10)
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        cols = ("#", "Nuclide", "Activity", "Source", "Step1", "Step2", "Start", "Mid", "End")
        self.tree = ttk.Treeview(display_frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)

        # [Adjusted Column Widths]
        self.tree.column("#", width=30, anchor=tk.CENTER)
        self.tree.column("Nuclide", width=70, anchor=tk.CENTER)
        self.tree.column("Activity", width=90, anchor=tk.E) # Right align activity
        self.tree.column("Source", width=120, anchor=tk.CENTER)
        self.tree.column("Step1", width=50, anchor=tk.CENTER)
        self.tree.column("Step2", width=50, anchor=tk.CENTER)
        self.tree.column("Start", width=120, anchor=tk.CENTER)
        self.tree.column("Mid", width=120, anchor=tk.CENTER)
        self.tree.column("End", width=120, anchor=tk.CENTER)
        
        vsb = ttk.Scrollbar(display_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(display_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(display_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_route).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_route).pack(side=tk.LEFT, padx=5)

    def _setup_logging(self, parent_frame):
        log_frame = ttk.LabelFrame(parent_frame, text="Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=10, state='disabled', wrap='word', bg='#f0f0f0')
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def log(self, message):
        """Adds a message to the log queue to be displayed in the GUI."""
        self.log_queue.put(message)

    def process_log_queue(self):
        """Processes messages from the log queue and updates the log widget."""
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, message + '\n')
            self.log_text.config(state='disabled')
            self.log_text.see(tk.END)
        self.root.after(100, self.process_log_queue)

    def update_status(self, message):
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def update_route_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.routes):
            # [Display Nuclide and Activity]
            self.tree.insert("", "end", values=(
                i + 1,
                r.get('nuclide', 'N/A'),
                r.get('activity', 'N/A'),
                str(r['source']),
                r['step_length1'],
                r['step_length2'],
                str(r['start']),
                str(r['mid']),
                str(r['end'])
            ))

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir.set(folder)
            self.log(f"Output folder set to: {folder}")

    def add_route(self):
        try:
            start = tuple(float(e.get()) for e in self.entries[0])
            mid = tuple(float(e.get()) for e in self.entries[1])
            end = tuple(float(e.get()) for e in self.entries[2])
            source_coords = tuple(float(e.get()) for e in self.entries[3]) # Changed variable name for clarity
            step1 = float(self.step_length1.get())
            step2 = float(self.step_length2.get())

            # [GET NUCLIDE AND ACTIVITY]
            nuclide = self.nuclide_entry.get()
            activity_str = self.activity_entry.get() # Get as string first
            if not nuclide or not activity_str:
                raise ValueError("Nuclide and Activity cannot be empty")
            # Try to convert activity to float to validate, but store as string
            try:
                float(activity_str)
            except ValueError:
                raise ValueError("Activity must be a valid number (e.g., 1.0E+12)")

            self.routes.append({
                "start": start, "mid": mid, "end": end,
                "source": source_coords, # Store source coordinates tuple
                "step_length1": step1, "step_length2": step2,
                "nuclide": nuclide,      # Store nuclide name string
                "activity": activity_str # Store activity as string (PHITS format)
            })
            self.update_route_tree()
            self.log(f"Added new route ({nuclide}, {activity_str} Bq). Total routes: {len(self.routes)}")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


    def edit_route(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a route to edit.")
            return
        
        item_values = self.tree.item(selected_item, "values")
        index = int(item_values[0]) - 1
        route = self.routes[index]
        
        for i, key in enumerate(["start", "mid", "end", "source"]):
            for j in range(3):
                self.entries[i][j].delete(0, tk.END)
                self.entries[i][j].insert(0, route[key][j])

        self.step_length1.delete(0, tk.END)
        self.step_length1.insert(0, route["step_length1"])
        self.step_length2.delete(0, tk.END)
        self.step_length2.insert(0, route["step_length2"])
        
        # Remove from list and tree, user will re-add
        del self.routes[index]
        self.update_route_tree()
        self.log(f"Loaded Route {index+1} for editing. Press 'Add Route' to save changes.")

        # [LOAD NUCLIDE AND ACTIVITY]
        self.nuclide_entry.delete(0, tk.END)
        self.nuclide_entry.insert(0, route.get("nuclide", "Cs-137")) # Use default if missing
        self.activity_entry.delete(0, tk.END)
        self.activity_entry.insert(0, route.get("activity", "1.0E+12")) # Use default if missing

        self.routes.pop(index) # Remove from list (user must re-add)
        self.update_route_tree()
        self.log(f"Loaded Route {index + 1} for editing. Press 'Add Route' to save changes.")

    def delete_route(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Error", "Please select route(s) to delete.")
            return

        # Sort indices in reverse to avoid index shifting issues
        indices_to_delete = sorted([int(self.tree.item(item, "values")[0]) - 1 for item in selected_items], reverse=True)
        
        for index in indices_to_delete:
            del self.routes[index]

        self.update_route_tree()
        self.log(f"Deleted {len(indices_to_delete)} route(s).")
        
    def save_routes(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not filepath:
            return
        try:
            with open(filepath, 'w') as f:
                json.dump(self.routes, f, indent=4)
            self.log(f"Routes successfully saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save routes: {e}")

    def load_routes(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not filepath:
            return
        try:
            with open(filepath, 'r') as f:
                self.routes = json.load(f)
            self.update_route_tree()
            self.log(f"Routes successfully loaded from {filepath}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load routes: {e}")

    def generate_all_files(self):
        try:
            outdir = self.output_dir.get()
            if not outdir:
                messagebox.showerror("Error", "Please select an output folder.")
                return
            if not self.routes:
                messagebox.showwarning("Warning", "No routes to generate.")
                return

            template_content = self.get_template_content()

            total_files = 0
            for idx, route in enumerate(self.routes):
                route_dir = os.path.join(outdir, f"route_{idx+1:03}")
                os.makedirs(route_dir, exist_ok=True)

                path = self.compute_full_path(route["start"], route["mid"], route["end"], route["step_length1"], route["step_length2"])

                # [GET NUCLIDE AND ACTIVITY FOR THIS ROUTE]
                nuclide = route.get("nuclide", "Cs-137") # Default if missing
                activity = route.get("activity", "1.0E+12") # Default if missing

                for i, (x, y, z) in enumerate(path):
                    # [PASS NUCLIDE/ACTIVITY TO generate_input_text]
                    input_text = self.generate_input_text(
                        template_content, x, y, z,
                        route["source"], # Pass source coordinates tuple
                        nuclide, activity # Pass nuclide and activity strings
                    )
                    input_filename = os.path.join(route_dir, f"input_{i:03}.inp")
                    with open(input_filename, "w", encoding="utf-8") as f:
                        f.write(input_text)
                    total_files += 1

            self.log(f"Generated {total_files} PHITS input files for {len(self.routes)} routes.")
            messagebox.showinfo("Success", f"PHITS input files generated successfully!")

        except FileNotFoundError:
             messagebox.showerror("Template Error", "Could not find 'template.inp'. Please ensure it's in the same directory.")
        except Exception as e:
            messagebox.showerror("File Generation Error", f"An error occurred: {e}")
        
        # [UPDATED generate_input_text signature and body]
    def generate_input_text(self, template, x, y, z, source_pos, nuclide, activity):
        maxcas_val = self.maxcas.get()
        maxbch_val = self.maxbch.get()

        return template.format(
            det_x=x, det_y=y, det_z=z,
            src_x=source_pos[0], src_y=source_pos[1], src_z=source_pos[2],
            maxcas_value=maxcas_val,
            maxbch_value=maxbch_val,
            nuclide_name=nuclide,     # Insert nuclide name
            activity_value=activity   # Insert activity value
        )

    def get_template_content(self):
            # スクリプト自身の絶対パスを取得
            script_path = os.path.abspath(__file__)
            # スクリプトが存在するディレクトリのパスを取得
            script_dir = os.path.dirname(script_path)
            # template.inpへの完全なパスを構築
            template_path = os.path.join(script_dir, "template.inp")
        
            self.log(f"Loading template from: {template_path}")
            # [修正点] 文字コードをUTF-8に指定してファイルを開く
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()

    def run_all_phits_threaded(self):
        if not self.output_dir.get():
            messagebox.showerror("Error", "Output folder not selected.")
            return
        if not self.routes:
            messagebox.showwarning("Warning", "No routes to simulate.")
            return

        self.log("--- Starting PHITS Simulation ---")
        self.update_status("Running PHITS...")
        # Disable run button to prevent multiple runs
        # Note: This requires getting a reference to the button. For simplicity, we skip this.
        
        thread = threading.Thread(target=self.run_all_phits_worker, daemon=True)
        thread.start()

    def run_all_phits_worker(self):
        try:
            outdir = self.output_dir.get()
            for idx, route in enumerate(self.routes):
                route_dir = os.path.join(outdir, f"route_{idx+1:03}")
                if not os.path.isdir(route_dir):
                    continue

                inp_files = sorted([f for f in os.listdir(route_dir) if f.endswith(".inp")])
                self.log(f"Processing Route {idx+1} with {len(inp_files)} steps...")

                for i, inp_file in enumerate(inp_files):
                    run_dir = os.path.join(route_dir, f"run_{i:03}")
                    os.makedirs(run_dir, exist_ok=True)
                    
                    shutil.copy(os.path.join(route_dir, inp_file), os.path.join(run_dir, "input.inp"))

                    command = f'cd /d "{run_dir}" && {self.phits_command.get()} input.inp'
                    self.log(f"Executing: {command}")
                    
                    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        self.log(f"ERROR in {run_dir}:")
                        self.log(f"  STDOUT: {stdout.strip()}")
                        self.log(f"  STDERR: {stderr.strip()}")
                    else:
                        self.log(f"Successfully ran step {i+1}/{len(inp_files)} for Route {idx+1}")
            
            self.log("--- PHITS Simulation Complete ---")
            messagebox.showinfo("Success", "PHITS simulation for all routes has completed.")
        except Exception as e:
            self.log(f"FATAL ERROR during PHITS execution: {e}")
            messagebox.showerror("Execution Error", f"An error occurred: {e}")
        finally:
            self.update_status("Ready")

    def calculate_dose(self):
        try:
            outdir = self.output_dir.get()
            if not outdir:
                messagebox.showerror("Error", "Output folder not selected.")
                return

            self.dose_results = {}
            self.log("--- Calculating Doses ---")

            for idx, route in enumerate(self.routes):
                route_name = f"Route {idx+1}"
                route_dir = os.path.join(outdir, f"route_{idx+1:03}")
                dose_list = []

                run_folders = sorted([d for d in os.listdir(route_dir) if d.startswith("run_") and os.path.isdir(os.path.join(route_dir, d))])
                
                for run_folder in run_folders:
                    deposit_path = os.path.join(route_dir, run_folder, "deposit.out")
                    if not os.path.exists(deposit_path):
                        self.log(f"Warning: 'deposit.out' not found in {run_folder}")
                        continue

                    with open(deposit_path, "r") as f:
                        for line in f:
                            if "sum over" in line:
                                parts = line.strip().split()
                                try:
                                    dose = float(parts[-2])
                                    dose_list.append(dose)
                                except (ValueError, IndexError):
                                    self.log(f"Warning: Could not parse dose from line: {line.strip()}")
                                break
                
                if dose_list:
                    total = sum(dose_list)
                    maximum = max(dose_list)
                    average = total / len(dose_list) if dose_list else 0
                    self.dose_results[route_name] = {
                        "doses": dose_list,
                        "total": total,
                        "max": maximum,
                        "avg": average
                    }
                    self.log(f"{route_name}: Total={total:.4E}, Max={maximum:.4E}, Avg={average:.4E}")
            
            if self.dose_results:
                messagebox.showinfo("Calculation Complete", "Dose calculation finished. See log for details.")
            else:
                messagebox.showwarning("No Data", "No dose data could be calculated.")

        except Exception as e:
            messagebox.showerror("Calculation Error", f"An error occurred during dose calculation: {e}")

    def visualize_dose_comparison(self):
        if not self.dose_results:
            messagebox.showinfo("No Data", "Please calculate doses first.")
            return

        labels = list(self.dose_results.keys())
        total = [v["total"] for v in self.dose_results.values()]
        maximum = [v["max"] for v in self.dose_results.values()]
        average = [v["avg"] for v in self.dose_results.values()]

        x = range(len(labels))
        width = 0.25

        plt.figure(figsize=(12, 7))
        plt.bar([i - width for i in x], total, width=width, label="Total Dose")
        plt.bar(x, average, width=width, label="Average Dose")
        plt.bar([i + width for i in x], maximum, width=width, label="Maximum Dose")
        
        plt.xticks(x, labels, rotation=45, ha="right")
        plt.ylabel("Dose [Gy/source]")
        plt.title("Comparison of Doses for Each Route")
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    def visualize_dose_profile(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a route to visualize its dose profile.")
            return
        
        item_values = self.tree.item(selected_item[0], "values")
        route_name = f"Route {item_values[0]}"

        if route_name not in self.dose_results:
            messagebox.showinfo("No Data", f"No dose data for {route_name}. Please run calculation.")
            return

        route_data = self.dose_results[route_name]
        doses = route_data["doses"]
        steps = range(1, len(doses) + 1)
        
        plt.figure(figsize=(10, 6))
        plt.plot(steps, doses, marker='o', linestyle='-', color='teal')
        plt.xlabel("Step Number Along Path")
        plt.ylabel("Dose [Gy/source]")
        plt.title(f"Dose Profile for {route_name}")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def visualize_routes(self):
        if not self.routes:
            messagebox.showinfo("No Data", "No routes registered to visualize.")
            return

        fig, ax = plt.subplots(figsize=(10, 8))
        colors = plt.cm.viridis( [i/len(self.routes) for i in range(len(self.routes))] )

        for idx, route in enumerate(self.routes):
            color = colors[idx]
            path = self.compute_full_path(route["start"], route["mid"], route["end"], route["step_length1"], route["step_length2"])
            xs = [p[0] for p in path]
            zs = [p[2] for p in path]

            ax.plot(zs, xs, marker='.', linestyle='-', color=color, label=f"Route {idx+1}")
            sx, _, sz = route["source"]
            ax.scatter(sz, sx, color=color, marker='*', s=150, edgecolors='black', label=f"Source {idx+1}")

        ax.set_xlabel("Z-axis [cm]")
        ax.set_ylabel("X-axis [cm]")
        ax.set_title("Visualization of Routes and Source Locations (Z-X Plane)")
        ax.axis('equal')
        ax.grid(True)
        ax.legend()
        plt.tight_layout()
        plt.show()

    # --- Utility and Calculation Functions (largely unchanged) ---
    def distance(self, p1, p2):
        return math.sqrt(sum((b - a) ** 2 for a, b in zip(p1, p2)))

    def interpolate_point(self, p1, p2, ratio):
        return tuple(p1[i] + ratio * (p2[i] - p1[i]) for i in range(3))

    def compute_full_path(self, start, mid, end, step_length1, step_length2):
        path = [start]
        
        seg1_len = self.distance(start, mid)
        if step_length1 > 0 and seg1_len > 0:
            n_steps1 = int(seg1_len // step_length1)
            for step in range(1, n_steps1 + 1):
                ratio = (step * step_length1) / seg1_len
                path.append(self.interpolate_point(start, mid, ratio))
        path.append(mid)

        seg2_len = self.distance(mid, end)
        if step_length2 > 0 and seg2_len > 0:
            n_steps2 = int(seg2_len // step_length2)
            for step in range(1, n_steps2 + 1):
                ratio = (step * step_length2) / seg2_len
                path.append(self.interpolate_point(mid, end, ratio))
        
        if path[-1] != end:
            path.append(end)
        return path


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiRoutePHITSGUI(root)
    root.mainloop()