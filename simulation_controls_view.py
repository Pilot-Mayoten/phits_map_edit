# simulation_controls_view.py

"""
シミュレーションの制御に関連するGUIコンポーネント
（経路設定、実行ボタン、ログ表示など）を管理するモジュール。
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

class SimulationControlsView(tk.Frame):
    def __init__(self, master, callbacks):
        super().__init__(master)
        self.callbacks = callbacks

        # スタイル設定
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=8, font=("Meiryo UI", 10))
        style.configure("TLabel", padding=4, font=("Meiryo UI", 10))
        style.configure("TEntry", padding=6, font=("Meiryo UI", 10))
        style.configure("TLabelframe", padding=10)
        style.configure("TLabelframe.Label", font=("Meiryo UI", 11, "bold"))
        style.configure("Treeview", font=("Meiryo UI", 10), rowheight=25)
        style.configure("Treeview.Heading", font=("Meiryo UI", 10, "bold"))
        
        self.create_widgets()

    def create_widgets(self):
        # --- パネル全体を縦スクロール可能にする ---
        # ウィンドウが低いと下のボタンが見切れるため、Canvas + Scrollbar で
        # スクロールできるようにし、内部フレームにコンテンツを積む。
        canvas = tk.Canvas(self, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        content = ttk.Frame(canvas)
        content_id = canvas.create_window((0, 0), window=content, anchor="nw")

        # 内部フレームのサイズ変更に合わせてスクロール領域を更新
        def _on_content_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        content.bind("<Configure>", _on_content_configure)

        # Canvas の幅に内部フレームを合わせる（横方向はいっぱいに広げる）
        def _on_canvas_configure(event):
            canvas.itemconfigure(content_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        # マウスホイールでスクロール（パネル上にポインタがあるときのみ）
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")
        def _bind_wheel(_):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def _unbind_wheel(_):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        # --- ファイルと保存状態（保存系ボタンを一箇所に集約）---
        file_frame = self._create_file_panel(content)
        file_frame.pack(fill=tk.X, expand=False, padx=2, pady=(2, 6))

        # --- 経路の管理 ---
        route_management_frame = self._create_route_management_panel(content)
        route_management_frame.pack(fill=tk.X, expand=False, padx=2, pady=(0, 6))

        # --- シミュレーション実行 ---
        action_frame = self._create_simulation_actions_panel(content)
        action_frame.pack(fill=tk.X, expand=False, padx=2, pady=2)

    def _create_file_panel(self, parent):
        """マップ／結果の保存・読込ボタンと、保存状態の表示をまとめたパネル。"""
        frame = ttk.LabelFrame(parent, text="ファイルと保存状態", padding=10)

        # --- 保存状態の表示 ---
        self.map_status_var = tk.StringVar(value="マップ: (無題)")
        self.results_status_var = tk.StringVar(value="結果: なし")

        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=(0, 8))
        self.map_status_label = ttk.Label(status_frame, textvariable=self.map_status_var)
        self.map_status_label.pack(anchor=tk.W)
        self.results_status_label = ttk.Label(status_frame, textvariable=self.results_status_var)
        self.results_status_label.pack(anchor=tk.W)

        # --- マップの保存／読込 ---
        map_row = ttk.Frame(frame)
        map_row.pack(fill=tk.X, pady=2)
        ttk.Button(map_row, text="マップを保存",
                   command=self.callbacks.get("save_map", lambda: None)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(map_row, text="マップを読込",
                   command=self.callbacks.get("load_map", lambda: None)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        # --- 結果の保存／表示 ---
        result_row = ttk.Frame(frame)
        result_row.pack(fill=tk.X, pady=2)
        self.save_csv_button = ttk.Button(result_row, text="結果をCSV保存",
                                          command=self.callbacks["save_results_csv"], state="disabled")
        self.save_csv_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(result_row, text="結果をExcelで開く",
                   command=self.callbacks.get("open_csv", lambda: None)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        return frame

    def set_save_status(self, map_label, map_state, results_label, results_state):
        """保存状態の表示を更新する（main.py から呼ばれる）。"""
        # 未保存=赤 / 保存済=緑 / 新規=グレー
        state_color = {"dirty": "#c0392b", "saved": "#27ae60",
                       "new": "#888888", "unsaved": "#c0392b", "none": "#888888"}
        self.map_status_var.set(map_label)
        self.results_status_var.set(results_label)
        self.map_status_label.configure(foreground=state_color.get(map_state, "#888888"))
        self.results_status_label.configure(foreground=state_color.get(results_state, "#888888"))

    def _create_route_management_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="経路の管理", padding=10)
        
        # --- 経路リスト ---
        cols = ("#", "色", "係数ω", "ステップ幅(cm)", "総線量(Gy/source)")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=5) # 表示行数を5行に制限
        for col in cols:
            self.tree.heading(col, text=col)

        self.tree.column("#", width=40, anchor=tk.CENTER)
        self.tree.column("色", width=100, anchor=tk.CENTER)
        self.tree.column("係数ω", width=100, anchor=tk.E)
        self.tree.column("ステップ幅(cm)", width=130, anchor=tk.E)
        self.tree.column("総線量(Gy/source)", width=150, anchor=tk.E)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # --- ボタン ---
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        
        ttk.Button(button_frame, text="経路を追加", command=self.callbacks["add_route"]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="選択を削除", command=self.callbacks["delete_route"]).pack(side=tk.LEFT, padx=5)

        # --- 結果アクセスボタン ---
        result_button_frame = ttk.Frame(frame)
        result_button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        ttk.Button(result_button_frame, text="選択経路の線量プロファイルを表示",
                  command=self.callbacks.get("show_dose_profile", lambda: None)).pack(fill=tk.X, padx=5)

        return frame

    def _create_simulation_actions_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="実行と可視化", padding=10)

        # --- 実行フレーム ---
        run_frame = ttk.LabelFrame(frame, text="実行ステップ")
        run_frame.pack(fill=tk.X, padx=5, pady=5, anchor=tk.E)
        
        # ボタンフレーム（右寄せ）
        run_button_frame = ttk.Frame(run_frame)
        run_button_frame.pack(fill=tk.X, padx=5, pady=4)
        
        ttk.Button(run_button_frame, text="1. 環境入力を生成", command=self.callbacks["generate_env_map"], width=28).pack(fill=tk.X, pady=2)
        ttk.Button(run_button_frame, text="2. 線量マップ読込", command=self.callbacks.get("load_dose_map", lambda: None), width=28).pack(fill=tk.X, pady=2)
        ttk.Button(run_button_frame, text="3. 最適経路を探索", command=self.callbacks["find_optimal_route"], width=28).pack(fill=tk.X, pady=2)
        ttk.Button(run_button_frame, text="4. 経路上の詳細線量評価", 
                   command=self.callbacks["run_detailed_simulation"], width=28).pack(fill=tk.X, pady=2)
        ttk.Button(run_button_frame, text="5. PHITS実行と結果プロット", 
                   command=self.callbacks["run_phits_and_plot"], width=28).pack(fill=tk.X, pady=2)
        
        # --- デバッグ用フレーム ---
        debug_frame = ttk.LabelFrame(frame, text="その他の機能")
        debug_frame.pack(fill=tk.X, padx=5, pady=(10, 5), anchor=tk.E) # 右寄せアンカーを指定
        
        # デバッグボタンフレーム（右寄せ）
        debug_button_frame = ttk.Frame(debug_frame)
        debug_button_frame.pack(fill=tk.X, padx=5, pady=4)
        
        ttk.Button(debug_button_frame, text="経路を2D表示", command=self.callbacks["visualize_routes"], width=28).pack(fill=tk.X, pady=2)
        ttk.Button(debug_button_frame, text="A*評価関数を可視化", command=self.callbacks["visualize_astar_eval"], width=28).pack(fill=tk.X, pady=2)

        return frame

    def get_route_definition_data(self):
        """経路定義フォームから入力値を取得して辞書として返す"""
        # 核種と放射能は「環境入力を生成」で設定されるため、ここでは空の辞書を返す
        data = {}
        return data

    def get_phits_command(self):
        """PHITS実行コマンドとして 'phits.bat' を返す"""
        return "phits.bat"

    def update_route_tree(self, routes):
        """指定された経路リストでTreeviewを更新する"""
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(routes):
            step_info = f"{len(r['detailed_path'])} pts" if 'detailed_path' in r else r.get('step_width', 'N/A')
            color = r.get('color', 'black')
            weight = r.get('weight', None)
            if weight is not None:
                weight_str = f"{weight:.0f}"
            else:
                weight_str = "-"
            total_dose = r.get('total_dose', None)
            if total_dose is not None:
                dose_str = f"{total_dose:.4e}"
            else:
                dose_str = "-"

            values = (
                i + 1,
                color,
                weight_str,
                step_info,
                dose_str,
            )
            # 色のタグを設定
            tag_name = f"color_{color}"
            self.tree.tag_configure(tag_name, background=color, foreground="white" if color in ["black", "red", "blue", "green", "purple", "navy"] else "black")
            self.tree.insert("", "end", values=values, tags=(tag_name,))
    def get_selected_route_indices(self):
        """Treeviewで選択されているアイテムのインデックス(0-based)のリストを返す"""
        selected_items = self.tree.selection()
        if not selected_items:
            return []
        indices = [int(self.tree.item(item, "values")[0]) - 1 for item in selected_items]
        return sorted(indices, reverse=True) # 逆順ソートで削除時のインデックスエラーを防ぐ

    def log(self, message):
        """ログウィジェットにメッセージを追記する"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n') # 改行コードを '\\n' から '\n' に修正
