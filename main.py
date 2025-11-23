"""
PHITS Map Editor and Simulation Runner
======================================
This application serves as the main entry point and controller for the GUI.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import tkinter.simpledialog as simpledialog

# --- アプリケーションのコアモジュール ---
from app_config import MAP_ROWS, MAP_COLS, CELL_TYPES
from map_editor_view import MapEditorView
from simulation_controls_view import SimulationControlsView
from phits_handler import (generate_environment_input_file, 
                           load_and_parse_dose_map, 
                           generate_detailed_simulation_files)
from route_calculator import find_optimal_route, compute_detailed_path_points
from utils import get_physical_coords
import visualizer

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🗺️ PHITS Map Editor & Route Planner")
        self.geometry("1600x900") # Windowサイズを少し拡大

        # --- 1. 内部データの初期化 ---
        self.map_data = [[CELL_TYPES["床 (通行可)"][0] for _ in range(MAP_COLS)] 
                         for _ in range(MAP_ROWS)]
        self.dose_map = None
        self.routes = [] # 複数の経路情報を管理するリスト

        # --- 2. メインレイアウトの作成 ---
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- 3. GUIモジュールのインスタンス化 ---
        self.map_editor_view = MapEditorView(main_paned, 
                                             self.on_cell_click,
                                             self.on_cell_hover)
        main_paned.add(self.map_editor_view, width=800)
        
        callbacks = {
            "generate_env_map": self.generate_and_load_dose_map,
            "find_optimal_route": self.calculate_optimal_route,
            "run_detailed_simulation": self.run_detailed_simulation,
            "add_route": self.add_route,
            "delete_route": self.delete_route,
            "visualize_routes": self.visualize_routes,
        }
        self.sim_controls_view = SimulationControlsView(main_paned, callbacks)
        main_paned.add(self.sim_controls_view, width=800)

        # --- 4. ステータスバー ---
        self.status_var = tk.StringVar(value="準備完了")
        status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ==========================================================================
    #  コールバック関数 (Viewからのイベントを処理)
    # ==========================================================================

    def on_cell_click(self, r, c):
        tool_name = self.map_editor_view.current_tool.get()
        new_id, new_color = CELL_TYPES[tool_name]
        
        if new_id in [2, 3, 4]:
             self.clear_existing_special_cell(new_id)

        self.map_data[r][c] = new_id
        self.map_editor_view.update_cell_color(r, c, new_color)
        self.log(f"セル [{r},{c}] を「{tool_name}」に変更しました。")

    def on_cell_hover(self, r, c):
        x_min, x_max, y_min, y_max, _, _ = get_physical_coords(r, c)
        dose_info = ""
        if self.dose_map and self.dose_map[r][c] > 0:
             dose_info = f" | Dose: {self.dose_map[r][c]:.2e}"
        info = f"Grid[{r},{c}] | X:{x_min:.1f}-{x_max:.1f}, Y:{y_min:.1f}-{y_max:.1f} (cm){dose_info}"
        self.status_var.set(info)

    def add_route(self):
        """新しい経路を定義リストに追加する"""
        self.log("新しい経路の追加処理を開始します。")
        route_data = self.sim_controls_view.get_route_definition_data()
        if not route_data:
            self.log("経路情報の取得に失敗しました。処理を中断します。")
            return

        # 経路に必要なスタート・ゴール・中継点をマップから取得
        start, goal, middle = self.find_special_points()
        if not start or not goal:
            messagebox.showwarning("設定エラー", "マップ上に「スタート」と「ゴール」を配置してください。")
            self.log("エラー: 経路追加にはスタートとゴールが必須です。")
            return
        
        # 取得した情報をすべて結合して一つの経路データにする
        route_data["start"] = start
        route_data["goal"] = goal
        route_data["middle"] = middle
        
        self.routes.append(route_data)
        self.log(f"新しい経路を追加しました。総経路数: {len(self.routes)}")
        self.sim_controls_view.update_route_tree(self.routes)

    def delete_route(self):
        """選択された経路をリストから削除する"""
        indices = self.sim_controls_view.get_selected_route_indices()
        if not indices:
            messagebox.showinfo("情報", "削除する経路が選択されていません。")
            return

        # 確認ダイアログ
        if not messagebox.askyesno("確認", f"{len(indices)}件の経路を削除しますか？"):
            return

        for index in indices: # indicesは逆順ソート済み
            if 0 <= index < len(self.routes):
                del self.routes[index]
        
        self.log(f"{len(indices)}件の経路を削除しました。")
        self.sim_controls_view.update_route_tree(self.routes)

    def generate_and_load_dose_map(self):
        """環境全体の線量マップを生成・読み込みする一連の処理"""
        self.log("環境線量マップの生成を開始します...")
        # (仮) PHITS実行とファイルI/Oはまだ実装しない
        # generate_environment_input_file(self.map_data)
        # self.log("PHITS入力ファイルを生成しました。")
        # self.log("PHITSを実行します... (この処理は数分かかることがあります)")
        
        # ダミーの線量マップを読み込む
        dose_data = load_and_parse_dose_map() # ファイル選択ダイアログが開く
        if dose_data:
            self.dose_map = dose_data
            self.map_editor_view.apply_heatmap(self.dose_map, self.map_data)
            self.log("線量マップを読み込み、ヒートマップを適用しました。")
        else:
            self.log("線量マップの読み込みがキャンセルされたか、失敗しました。")

    def calculate_optimal_route(self):
        """A*で最適経路を探索"""
        self.log("最適経路の探索を開始します...")
        start, goal, middle = self.find_special_points()
        if not start or not goal:
            messagebox.showwarning("設定エラー", "「スタート」と「ゴール」を配置してください。")
            return

        # (仮) 現状は重み係数をダイアログから取得
        weight_str = simpledialog.askstring("設定", "被ばく回避の重み係数:", initialvalue="10000")
        try:
            weight = float(weight_str)
        except (ValueError, TypeError):
            weight = 0.0

        path = find_optimal_route(start, goal, middle, self.map_data, self.dose_map, weight)
        
        if path:
            self.map_editor_view.visualize_path(path, self.map_data)
            self.log(f"最適経路を発見しました (ステップ数: {len(path)})。")
        else:
            messagebox.showerror("探索失敗", "経路が見つかりませんでした。")
            self.log("最適経路が見つかりませんでした。")

    def run_detailed_simulation(self):
        """経路上の詳細シミュレーションを実行"""
        self.log("詳細線量評価を開始します...")
        
        if not self.routes:
            messagebox.showinfo("情報", "評価対象の経路がありません。")
            self.log("経路が未定義のため、詳細評価を中止しました。")
            return

        output_dir = filedialog.askdirectory(title="シミュレーション結果の保存先を選択")
        if not output_dir:
            self.log("出力先フォルダが選択されなかったため、処理を中断しました。")
            return
            
        self.log(f"出力先フォルダ: {output_dir}")

        # 各経路について、詳細な評価点群を計算
        for route in self.routes:
            start_phys = get_physical_coords(*route["start"])
            goal_phys = get_physical_coords(*route["goal"])
            middle_phys = get_physical_coords(*route["middle"]) if route["middle"] else None
            
            # 物理座標系の中心点を計算
            start_center = ((start_phys[0]+start_phys[1])/2, (start_phys[2]+start_phys[3])/2, (start_phys[4]+start_phys[5])/2)
            goal_center = ((goal_phys[0]+goal_phys[1])/2, (goal_phys[2]+goal_phys[3])/2, (goal_phys[4]+goal_phys[5])/2)
            middle_center = ((middle_phys[0]+middle_phys[1])/2, (middle_phys[2]+middle_phys[3])/2, (middle_phys[4]+middle_phys[5])/2) if middle_phys else None

            route["detailed_path"] = compute_detailed_path_points(
                start_center, middle_center, goal_center, route["step"]
            )
            self.log(f"経路{self.routes.index(route)+1}の評価点({len(route['detailed_path'])}点)を計算しました。")

        # PHITSハンドラにファイル生成を依頼
        success, file_count = generate_detailed_simulation_files(self.routes, output_dir)
        
        if success:
            self.log(f"合計{file_count}個のPHITS入力ファイルを生成しました。")
            messagebox.showinfo("生成完了", f"PHITS入力ファイルの生成が完了しました。\\n場所: {output_dir}")
        else:
            self.log("PHITS入力ファイルの生成に失敗しました。")
            messagebox.showerror("生成失敗", "PHITS入力ファイルの生成に失敗しました。詳細はログを確認してください。")

    def visualize_routes(self):
        """登録された経路を3Dで可視化する"""
        self.log("経路の3D可視化を開始します...")
        if not self.routes:
            messagebox.showinfo("情報", "表示する経路がありません。")
            return
        
        # 評価点が未計算の経路があれば計算する
        for route in self.routes:
            if "detailed_path" not in route:
                self.log(f"経路{self.routes.index(route)+1}の評価点が未計算のため、計算します。")
                start_phys = get_physical_coords(*route["start"])
                goal_phys = get_physical_coords(*route["goal"])
                middle_phys = get_physical_coords(*route["middle"]) if route["middle"] else None
                
                start_center = ((start_phys[0]+start_phys[1])/2, (start_phys[2]+start_phys[3])/2, (start_phys[4]+start_phys[5])/2)
                goal_center = ((goal_phys[0]+goal_phys[1])/2, (goal_phys[2]+goal_phys[3])/2, (goal_phys[4]+goal_phys[5])/2)
                middle_center = ((middle_phys[0]+middle_phys[1])/2, (middle_phys[2]+middle_phys[3])/2, (middle_phys[4]+middle_phys[5])/2) if middle_phys else None

                route["detailed_path"] = compute_detailed_path_points(
                    start_center, middle_center, goal_center, route["step"]
                )

        visualizer.visualize_routes_3d(self.routes)
        self.log("3D可視化ウィンドウを表示しました。")

    # ==========================================================================
    #  ヘルパー関数
    # ==========================================================================

    def clear_existing_special_cell(self, target_id):
        for r, row in enumerate(self.map_data):
            for c, cell_id in enumerate(row):
                if cell_id == target_id:
                    self.map_data[r][c] = 0
                    self.map_editor_view.update_cell_color(r, c, CELL_TYPES["床 (通行可)"][1])
                    return

    def find_special_points(self):
        start, goal, middle = None, None, None
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                cell_id = self.map_data[r][c]
                if cell_id == 2: start = (r, c)
                elif cell_id == 3: goal = (r, c)
                elif cell_id == 4: middle = (r, c)
        return start, goal, middle

    def log(self, message):
        print(message)
        self.sim_controls_view.log(message)


if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()