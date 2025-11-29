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
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", padding=2)
        style.configure("TEntry", padding=4)
        style.configure("TLabelframe.Label", font=('Helvetica', 12, 'bold'))
        
        self.create_widgets()

    def create_widgets(self):
        # --- 全体を上下左右に分割するPanedWindow ---
        main_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # --- 上部：経路定義とリスト ---
        top_frame = ttk.Frame(main_paned)
        main_paned.add(top_frame, weight=2)

        top_paned = ttk.PanedWindow(top_frame, orient=tk.HORIZONTAL)
        top_paned.pack(fill=tk.BOTH, expand=True)
        
        route_definition_frame = self._create_route_definition_panel(top_paned)
        top_paned.add(route_definition_frame, weight=1)

        route_list_frame = self._create_route_list_panel(top_paned)
        top_paned.add(route_list_frame, weight=2)

        # --- 中間部：シミュレーション実行 ---
        action_frame = self._create_simulation_actions_panel(main_paned)
        main_paned.add(action_frame, weight=1)
        
        # --- 下部：ログ表示 ---
        log_frame = self._create_log_display_panel(main_paned)
        main_paned.add(log_frame, weight=2) # weightを増やして高さを確保

    def _create_route_definition_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="経路定義", padding=10)

        # --- 入力フィールド ---
        self.entries = {}
        # 注目点 (Start/Goal) はマップから取得するため、ここでは定義しない
        labels = {
            "nuclide": "核種",
            "activity": "放射能 (Bq)",
        }

        for i, (key, text) in enumerate(labels.items()):
            ttk.Label(frame, text=text).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            entry = ttk.Entry(frame, width=15)
            entry.grid(row=i, column=1, columnspan=3, sticky="we", padx=5, pady=2)
            self.entries[key] = entry

        # PHITS実行コマンドの入力欄を追加
        phits_cmd_frame = ttk.Frame(frame)
        phits_cmd_frame.grid(row=i + 1, column=0, columnspan=4, sticky="we", pady=2)
        ttk.Label(phits_cmd_frame, text="PHITS実行ファイル").pack(side=tk.LEFT, padx=5)
        self.phits_command_entry = ttk.Entry(phits_cmd_frame)
        self.phits_command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.phits_command_entry.insert(0, "phits.bat") # デフォルト値
        ttk.Button(phits_cmd_frame, text="参照...", 
                   command=lambda: self.callbacks.get("select_phits_command", lambda: None)()).pack(side=tk.LEFT, padx=5)

        # デフォルト値
        self.entries["nuclide"].insert(0, "Cs-137")
        self.entries["activity"].insert(0, "1.0E+12")

        # --- アクションボタン ---
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=i + 2, column=0, columnspan=4, pady=10)
        ttk.Button(button_frame, text="経路を追加", command=self.callbacks["add_route"]).pack(side=tk.LEFT, padx=5)

        return frame

    def _create_route_list_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="経路リスト", padding=10)
        
        cols = ("#", "核種", "放射能", "ステップ幅(cm)")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)

        self.tree.column("#", width=30, anchor=tk.CENTER)
        self.tree.column("核種", width=120)
        self.tree.column("放射能", width=120)
        self.tree.column("ステップ幅(cm)", width=100, anchor=tk.E)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky="w")
        ttk.Button(button_frame, text="選択を削除", command=self.callbacks["delete_route"]).pack(side=tk.LEFT, padx=5)
        
        return frame

    def _create_simulation_actions_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="実行と可視化", padding=10)

        # --- 実行フレーム ---
        run_frame = ttk.Frame(frame)
        run_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(run_frame, text="1. 環境入力を生成", command=self.callbacks["generate_env_map"]).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(run_frame, text="2. 線量マップ読込", command=self.callbacks.get("load_dose_map", lambda: None)).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(run_frame, text="3. 最適経路を探索", command=self.callbacks["find_optimal_route"]).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(run_frame, text="4. 経路上の詳細線量評価", 
                   command=self.callbacks["run_detailed_simulation"]).pack(fill=tk.X, pady=3)
        ttk.Button(run_frame, text="5. PHITS実行と結果プロット", 
                   command=self.callbacks["run_phits_and_plot"]).pack(fill=tk.X, pady=3)
        
        # --- デバッグ用フレーム ---
        debug_frame = ttk.Frame(frame)
        debug_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(debug_frame, text="デバッグ用バッチファイル生成", 
                   command=self.callbacks.get("generate_debug_batch")).pack(side=tk.LEFT, padx=5)
        
        # --- 可視化フレーム ---
        vis_frame = ttk.Frame(frame)
        vis_frame.pack(fill=tk.X)
        ttk.Button(vis_frame, text="経路を2D表示", command=self.callbacks["visualize_routes"]).pack(side=tk.LEFT, padx=5, pady=5)

        return frame

    def _create_log_display_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="ログ", padding=10)
        # tk.Textからscrolledtext.ScrolledTextに変更
        self.log_text = scrolledtext.ScrolledText(frame, height=10, state='disabled', wrap='word', bg='#f0f0f0')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        return frame

    def get_route_definition_data(self):
        """経路定義フォームから入力値を取得して辞書として返す"""
        try:
            data = {
                "nuclide": self.entries["nuclide"].get(),
                "activity": self.entries["activity"].get(),
            }
            # 簡単なバリデーション
            if not data["nuclide"] or not data["activity"]:
                raise ValueError("核種と放射能は必須です。")
            float(data["activity"]) # 数値変換できるかテスト
            return data
        except ValueError as e:
            messagebox.showerror("入力エラー", f"無効な入力値があります: {e}")
            return None

    def get_phits_command(self):
        """PHITS実行コマンド入力欄から値を取得する"""
        return self.phits_command_entry.get()

    def set_phits_command(self, path):
        """PHITS実行コマンド入力欄に値を設定する"""
        self.phits_command_entry.delete(0, tk.END)
        self.phits_command_entry.insert(0, path)

    def update_route_tree(self, routes):
        """指定された経路リストでTreeviewを更新する"""
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(routes):
            # a_star_pathがあればステップ数を表示、なければステップ幅を表示
            step_info = f"{len(r['a_star_path'])} pts" if 'a_star_path' in r else r.get('step_width', 'N/A')

            values = (
                i + 1,
                r.get('nuclide', 'N/A'),
                r.get('activity', 'N/A'),
                step_info,
            )
            self.tree.insert("", "end", values=values)
    
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
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)
