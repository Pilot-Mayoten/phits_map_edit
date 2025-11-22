# simulation_controls_view.py

"""
シミュレーションの制御に関連するGUIコンポーネント
（経路設定、実行ボタン、ログ表示など）を管理するモジュール。
"""

import tkinter as tk
from tkinter import ttk

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
        # --- 全体を上下に分割するPanedWindow ---
        main_paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        # --- 上部：コントロールパネル ---
        controls_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(controls_frame, weight=1)

        # --- 下部：ログ表示 ---
        log_frame_container = ttk.Frame(main_paned_window)
        main_paned_window.add(log_frame_container, weight=1)

        self._create_simulation_actions(controls_frame)
        self._create_log_display(log_frame_container)


    def _create_simulation_actions(self, parent):
        action_frame = ttk.LabelFrame(parent, text="シミュレーション & 解析", padding=10)
        action_frame.pack(fill=tk.X, expand=True, padx=10, pady=10)

        # --- 1. 環境生成 & 線量マップ計算 ---
        env_frame = ttk.Frame(action_frame)
        env_frame.pack(fill=tk.X, pady=5)
        
        env_button = ttk.Button(
            env_frame, 
            text="1. 環境入力ファイル (env_input.inp) を生成", 
            command=self.callbacks["generate_env"]
        )
        env_button.pack(side=tk.LEFT, padx=5)
        
        load_map_button = ttk.Button(
            env_frame,
            text="2. 線量マップ読込 (deposit.out)",
            command=self.callbacks["load_dose_map"]
        )
        load_map_button.pack(side=tk.LEFT, padx=5)

        # --- セパレータ ---
        ttk.Separator(action_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- 2. 経路探索 ---
        route_frame = ttk.Frame(action_frame)
        route_frame.pack(fill=tk.X, pady=5)
        
        self.weight_var = tk.StringVar(value="10000")
        
        ttk.Label(route_frame, text="被ばく回避の重み係数:").pack(side=tk.LEFT, padx=(0, 5))
        weight_entry = ttk.Entry(route_frame, textvariable=self.weight_var, width=10)
        weight_entry.pack(side=tk.LEFT, padx=5)

        calc_route_button = ttk.Button(
            route_frame,
            text="3. 最適経路探索 (A*)",
            command=self.callbacks["calculate_route"],
        )
        calc_route_button.pack(side=tk.LEFT, padx=10)

    def _create_log_display(self, parent):
        log_frame = ttk.LabelFrame(parent, text="ログ", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.log_text = tk.Text(log_frame, height=10, state='disabled', wrap='word', bg='#f0f0f0')
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scroll.set)
        
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def get_weight_factor(self):
        """重み係数の入力値を取得してfloatで返す"""
        try:
            return float(self.weight_var.get())
        except (ValueError, TypeError):
            return 0.0 # 不正な値の場合は0を返す

    def log(self, message):
        """ログウィジェットにメッセージを追記する"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END) # 自動スクロール
