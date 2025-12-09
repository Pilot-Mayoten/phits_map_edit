# map_editor_view.py

"""
マップエディタのGUIコンポーネント（ツールボックス、グリッド表示など）を管理するモジュール。
"""

import tkinter as tk
from tkinter import messagebox
import math
from app_config import MAP_ROWS, MAP_COLS, CELL_TYPES, CELL_SIZE_X, CELL_SIZE_Y
from utils import get_physical_coords

class MapEditorView(tk.Frame):
    def __init__(self, master, on_cell_click_callback, on_hover_callback):
        super().__init__(master)
        
        self.on_cell_click_callback = on_cell_click_callback
        self.on_hover_callback = on_hover_callback

        self.current_tool = tk.StringVar(value="床 (通行可)")
        
        self.grid_buttons = [] # グリッドのボタンウィジェットを保持

        self.create_widgets()

    def create_widgets(self):
        # --- 1. 左側のツールボックス ---
        toolbox_frame = tk.Frame(self, relief=tk.RAISED, bd=2)
        toolbox_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.create_toolbox(toolbox_frame)

        # --- 2. 右側のマップグリッド ---
        grid_container = tk.Frame(self)
        grid_container.pack(side=tk.RIGHT, padx=10, pady=10)
        self.create_map_grid(grid_container)

    def create_toolbox(self, parent):
        tk.Label(parent, text="ツール選択", font=("Meiryo UI", 13, "bold")).pack(pady=10)

        for name, (_, color) in CELL_TYPES.items():
            rb = tk.Radiobutton(
                parent,
                text=name,
                variable=self.current_tool,
                value=name,
                indicatoron=False,
                width=14,
                height=2,
                background=color,
                selectcolor=color,
                activebackground=color,
                font=("Meiryo UI", 11),
                fg="white" if color in ["black", "red", "blue"] else "black",
                relief=tk.RAISED,
                bd=2
            )
            rb.pack(pady=5, padx=10, fill=tk.X)

    def create_map_grid(self, parent):
        # --- X軸ラベル (上部) ---
        for c in range(0, MAP_COLS, 5):
            x_val = c * CELL_SIZE_X
            lbl = tk.Label(parent, text=f"{x_val:.0f}", font=("Meiryo UI", 9, "bold"), bg="#e0e0e0")
            lbl.grid(row=0, column=c+1, sticky="ew", padx=1, pady=1) 

        # --- Y軸ラベル (左側) ---
        for r in range(0, MAP_ROWS, 5):
            y_val = (MAP_ROWS - r) * CELL_SIZE_Y
            lbl = tk.Label(parent, text=f"{y_val:.0f}", width=5, anchor="e", font=("Meiryo UI", 9, "bold"), bg="#e0e0e0")
            lbl.grid(row=r+1, column=0, sticky="ns", padx=1, pady=1)

        # --- グリッドボタン本体 ---
        for r in range(MAP_ROWS):
            row_buttons = []
            for c in range(MAP_COLS):
                btn = tk.Button(
                    parent,
                    text="",
                    width=4,
                    height=2,
                    bg=CELL_TYPES["床 (通行可)"][1],
                    activebackground="#ffffff",
                    relief=tk.SOLID,
                    bd=1,
                    command=lambda r_val=r, c_val=c: self.on_cell_click_callback(r_val, c_val)
                )
                btn.grid(row=r+1, column=c+1, sticky="nsew", padx=1, pady=1)
                
                btn.bind("<Enter>", lambda event, r_val=r, c_val=c: self.on_hover_callback(r_val, c_val))
                
                row_buttons.append(btn)
            self.grid_buttons.append(row_buttons)

    def update_cell_color(self, r, c, color):
        """指定されたセルの色を更新する"""
        self.grid_buttons[r][c].config(bg=color)

    def apply_heatmap(self, dose_map, map_data):
        """線量マップデータに基づいてヒートマップを適用する"""
        if not dose_map: return

        # 0より大きい値のみを対象に最大・最小を計算
        flat_list = [val for row in dose_map for val in row if val > 0]
        if not flat_list: 
            messagebox.showinfo("可視化情報", "線量データが全て0以下のため、ヒートマップは適用されません。")
            return
        
        max_dose = max(flat_list)
        min_dose = min(flat_list)
        
        if max_dose <= min_dose: return

        log_min = math.log10(min_dose)
        log_max = math.log10(max_dose)

        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                # 既にオブジェクトが配置されているマスは色を変えない
                if map_data[r][c] != 0: continue
                
                dose = dose_map[r][c]
                
                if dose <= 0:
                    ratio = 0.0
                else:
                    # 対数スケールで色の比率を計算
                    ratio = (math.log10(dose) - log_min) / (log_max - log_min)
                
                ratio = max(0.0, min(1.0, ratio)) # 0.0-1.0の範囲に収める
                
                color_code = self.get_heatmap_color(ratio)
                self.grid_buttons[r][c].config(bg=color_code)
        
        messagebox.showinfo("完了", f"線量マップを可視化しました。\\n最大: {max_dose:.2e}\\n最小: {min_dose:.2e}")

    def get_heatmap_color(self, ratio):
        """0.0(白) -> 0.5(黄) -> 1.0(赤)のカラースケールで色コードを返す"""
        if ratio < 0.5:
            # 白(1,1,1) -> 黄(1,1,0)
            r_val = 255
            g_val = 255
            b_val = int(255 * (1 - ratio * 2))
        else:
            # 黄(1,1,0) -> 赤(1,0,0)
            r_val = 255
            g_val = int(255 * (2 - ratio * 2))
            b_val = 0
        return f"#{r_val:02x}{g_val:02x}{b_val:02x}"

    def visualize_path(self, path, map_data):
        """指定された経路をマップ上に描画する"""
        for r, c in path:
            cell_id = map_data[r][c]
            # スタート、ゴール、中継、線源のマスは上書きしない
            if cell_id not in [0, 1]:
                continue
            self.update_cell_color(r, c, "magenta")
