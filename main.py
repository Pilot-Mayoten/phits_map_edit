"""
PHITS Map Editor and Simulation Runner
======================================
This application serves as the main entry point and controller for the GUI.
It integrates various modules to provide a comprehensive workflow:
1.  **Map Creation**: Visually design a simulation environment using a grid.
2.  **Dose Map Generation**: Create a general dose map of the environment.
3.  **Optimal Route Finding**: Use the A* algorithm to find a low-dose path.
4.  **Detailed Simulation**: (Future Implementation) Run detailed simulations along the path.
"""

import tkinter as tk
from tkinter import messagebox

# --- アプリケーションのコアモジュール ---
from app_config import MAP_ROWS, MAP_COLS, CELL_TYPES
from map_editor_view import MapEditorView
from simulation_controls_view import SimulationControlsView
from phits_handler import generate_environment_input_file, load_and_parse_dose_map
from route_calculator import find_optimal_route
from utils import get_physical_coords

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🗺️ PHITS Map Editor & Route Planner")
        self.geometry("1400x800")

        # --- 1. 内部データの初期化 ---
        self.map_data = [[CELL_TYPES["床 (通行可)"][0] for _ in range(MAP_COLS)] 
                         for _ in range(MAP_ROWS)]
        self.dose_map = None # 線量マップデータ

        # --- 2. メインレイアウトの作成 ---
        main_paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- 3. GUIモジュールのインスタンス化 ---
        
        # 左側: マップエディタ
        self.map_editor_view = MapEditorView(main_paned_window, 
                                             on_cell_click_callback=self.on_cell_click,
                                             on_hover_callback=self.on_cell_hover)
        main_paned_window.add(self.map_editor_view, width=800)
        
        # 右側: シミュレーションコントロール
        sim_callbacks = {
            "generate_env": self.generate_phits_input,
            "load_dose_map": self.load_dose_map,
            "calculate_route": self.calculate_route,
        }
        self.sim_controls_view = SimulationControlsView(main_paned_window, sim_callbacks)
        main_paned_window.add(self.sim_controls_view, width=600)

        # --- 4. ステータスバー ---
        self.status_var = tk.StringVar(value="準備完了")
        status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ==========================================================================
    #  コールバック関数群 (各Viewからのイベントを処理)
    # ==========================================================================

    def on_cell_click(self, r, c):
        """マップエディタのセルがクリックされたときの処理"""
        tool_name = self.map_editor_view.current_tool.get()
        new_id, new_color = CELL_TYPES[tool_name]
        
        # スタート、ゴール、中継地点はマップ上に1つだけ存在できるようにする
        if new_id in [2, 3, 4]:
             self.clear_existing_special_cell(new_id)

        self.map_data[r][c] = new_id
        self.map_editor_view.update_cell_color(r, c, new_color)
        self.log(f"セル [{r},{c}] を「{tool_name}」に変更しました。")

    def on_cell_hover(self, r, c):
        """マップエディタのセルにマウスがホバーしたときの処理"""
        x_min, x_max, y_min, y_max, _, _ = get_physical_coords(r, c)
        dose_info = ""
        if self.dose_map and self.dose_map[r][c] > 0:
             dose_info = f" | Dose: {self.dose_map[r][c]:.2e}"
        
        info = f"Grid[{r},{c}] | X: {x_min:.1f}~{x_max:.1f}, Y: {y_min:.1f}~{y_max:.1f} (cm){dose_info}"
        self.status_var.set(info)

    def generate_phits_input(self):
        """環境入力ファイルの生成をphits_handlerに依頼"""
        self.log("PHITS環境入力ファイルの生成を開始します...")
        generate_environment_input_file(self.map_data)
        self.log("PHITS環境入力ファイルの生成処理が完了しました。")

    def load_dose_map(self):
        """線量マップの読み込みをphits_handlerに依頼し、結果をUIに反映"""
        self.log("線量マップファイルを選択してください...")
        dose_data = load_and_parse_dose_map()
        if dose_data:
            self.dose_map = dose_data
            self.map_editor_view.apply_heatmap(self.dose_map, self.map_data)
            self.log("線量マップを読み込み、ヒートマップを適用しました。")
        else:
            self.log("線量マップの読み込みはキャンセルされたか、失敗しました。")

    def calculate_route(self):
        """最適経路の計算をroute_calculatorに依頼し、結果をUIに反映"""
        self.log("最適経路の探索を開始します...")
        start_pos, goal_pos, middle_pos = self.find_special_points()

        if not start_pos or not goal_pos:
            messagebox.showwarning("設定エラー", "マップ上に「スタート」と「ゴール」を配置してください。")
            self.log("エラー: スタートまたはゴールが未配置のため、経路探索を中止しました。")
            return

        weight = self.sim_controls_view.get_weight_factor()
        self.log(f"探索条件: スタート{start_pos}, ゴール{goal_pos}, 中継{middle_pos}, 重み={weight}")

        path = find_optimal_route(start_pos, goal_pos, middle_pos, 
                                  self.map_data, self.dose_map, weight)
        
        if path:
            self.map_editor_view.visualize_path(path, self.map_data)
            self.log(f"経路が見つかりました (総ステップ数: {len(path)})。マップ上に表示します。")
            messagebox.showinfo("探索成功", f"経路が見つかりました。 (ステップ数: {len(path)})")
        else:
            self.log("エラー: 指定された条件下でゴールまでの経路が見つかりませんでした。")
            messagebox.showerror("探索失敗", "経路が見つかりませんでした。壁の配置などを確認してください。")

    # ==========================================================================
    #  ヘルパー関数
    # ==========================================================================

    def clear_existing_special_cell(self, target_id):
        """指定されたIDの特殊セル（スタート等）が既に存在する場合、それを床に戻す"""
        for r_idx, row in enumerate(self.map_data):
            for c_idx, cell_id in enumerate(row):
                if cell_id == target_id:
                    self.map_data[r_idx][c_idx] = 0 # 床に戻す
                    floor_color = CELL_TYPES["床 (通行可)"][1]
                    self.map_editor_view.update_cell_color(r_idx, c_idx, floor_color)
                    return

    def find_special_points(self):
        """マップデータからスタート、ゴール、中継地点の座標を探す"""
        start, goal, middle = None, None, None
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                cell_id = self.map_data[r][c]
                if cell_id == 2:
                    start = (r, c)
                elif cell_id == 3:
                    goal = (r, c)
                elif cell_id == 4:
                    middle = (r, c)
        return start, goal, middle

    def log(self, message):
        """ロギングを一元管理する"""
        print(message) # コンソールにも出力
        self.sim_controls_view.log(message)


if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()