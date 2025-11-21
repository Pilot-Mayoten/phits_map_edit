import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import textwrap
import re
import math
import os
import heapq

# --- 定義 ---

# マップのサイズ（マス目）
MAP_ROWS = 15  # Y方向
MAP_COLS = 20  # X方向

# 1マスの物理的なサイズ (cm)
CELL_SIZE_X = 10.0
CELL_SIZE_Y = 10.0

# 建屋の高さ (cm)
CELL_HEIGHT_Z = 100.0 

# シミュレーション空間全体を囲むマージン (cm)
WORLD_MARGIN = 100.0

# タイルの種類と、内部データ、GUIでの色
CELL_TYPES = {
    "床 (通行可)": [0, "white"],
    "壁 (障害物)": [1, "black"],
    "放射線源": [9, "red"],
    "スタート": [2, "lime green"],
    "ゴール": [3, "blue"],
    "中継地点": [4, "orange"]  # A*アルゴリズム用に追加
}

print("🗺️ PHITS環境定義 & 線量可視化 & 経路探索 GUI 起動")

class MapEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🗺️ PHITS環境定義 & 線量可視化 & 経路探索 GUI")
        self.resizable(False, False)

        # 1. 内部データ初期化
        self.map_data = [[CELL_TYPES["床 (通行可)"][0] for _ in range(MAP_COLS)] 
                         for _ in range(MAP_ROWS)]
        
        # 線量マップデータの保持用
        self.dose_map = None

        # 2. ツール選択
        self.current_tool = tk.StringVar(value="床 (通行可)")

        # ステータスバー（座標表示用）
        self.status_var = tk.StringVar()
        self.status_var.set("準備完了")
        self.status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 3. GUI作成
        self.create_toolbox()
        self.create_map_grid()

    def create_toolbox(self):
        """左側のツールボックスを作成"""
        toolbox_frame = tk.Frame(self, relief=tk.RAISED, bd=2)
        toolbox_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(toolbox_frame, text="ツール選択", font=("", 12, "bold")).pack(pady=10)

        for name, (cell_id, color) in CELL_TYPES.items():
            rb = tk.Radiobutton(
                toolbox_frame,
                text=name,
                variable=self.current_tool,
                value=name,
                indicatoron=False,
                width=12,
                background=color,
                selectcolor=color,
                fg="white" if color in ["black", "red", "blue"] else "black"
            )
            rb.pack(pady=3, padx=10)
        
        tk.Frame(toolbox_frame, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=10)

        # --- アクションボタン群 ---
        
        # 1. PHITS入力生成
        generate_button = tk.Button(
            toolbox_frame, 
            text="環境入力ファイル\n(env_input.inp) を生成", 
            command=self.generate_environment_input
        )
        generate_button.pack(pady=10, padx=10)

        # 2. 線量マップ読込
        load_map_button = tk.Button(
            toolbox_frame,
            text="線量マップ読込\n(deposit.out)",
            command=self.load_dose_map
        )
        load_map_button.pack(pady=10, padx=10)

        # 3. 経路探索
        calc_route_button = tk.Button(
            toolbox_frame,
            text="最適経路探索\n(A* Start->Mid->Goal)",
            command=self.calculate_route,
            bg="orange"
        )
        calc_route_button.pack(pady=20, padx=10)


    def create_map_grid(self):
        """右側にマップのグリッド（マス目）と座標ラベルを作成"""
        grid_container = tk.Frame(self)
        grid_container.pack(side=tk.RIGHT, padx=10, pady=10)

        # --- X軸ラベル (上部) ---
        for c in range(0, MAP_COLS, 5):
            x_val = c * CELL_SIZE_X
            lbl = tk.Label(grid_container, text=f"{x_val:.0f}")
            lbl.grid(row=0, column=c+1, sticky="w") 

        # --- Y軸ラベル (左側) ---
        # GUIの行番号 r=0 が Y座標の最大値に対応
        for r in range(0, MAP_ROWS, 5):
            y_val = (MAP_ROWS - r) * CELL_SIZE_Y
            lbl = tk.Label(grid_container, text=f"{y_val:.0f}", width=4, anchor="e")
            lbl.grid(row=r+1, column=0, sticky="n")

        # --- グリッドボタン本体 ---
        self.grid_buttons = []
        for r in range(MAP_ROWS):
            row_buttons = []
            for c in range(MAP_COLS):
                btn = tk.Button(
                    grid_container,
                    text="",
                    width=2,
                    height=1,
                    bg=CELL_TYPES["床 (通行可)"][1],
                    command=lambda r=r, c=c: self.on_cell_click(r, c)
                )
                btn.grid(row=r+1, column=c+1, sticky="nsew")
                
                # マウスホバーイベント
                btn.bind("<Enter>", lambda event, r=r, c=c: self.on_hover(r, c))
                
                row_buttons.append(btn)
            self.grid_buttons.append(row_buttons)

    def on_hover(self, r, c):
        """マウスが乗ったセルの座標を表示"""
        x_min, x_max, y_min, y_max, _, _ = self.get_coords(r, c)
        dose_info = ""
        if self.dose_map:
             dose_info = f" Dose: {self.dose_map[r][c]:.2e}"
        
        info = f"Grid[{r},{c}] : X={x_min:.1f}~{x_max:.1f}, Y={y_min:.1f}~{y_max:.1f} (cm){dose_info}"
        self.status_var.set(info)

    def get_coords(self, r, c):
        """GUIグリッド座標 -> 物理座標変換 (r=0 が Y最大)"""
        x_min = c * CELL_SIZE_X
        x_max = (c + 1) * CELL_SIZE_X
        
        y_max = (MAP_ROWS - r) * CELL_SIZE_Y
        y_min = (MAP_ROWS - r - 1) * CELL_SIZE_Y
        
        z_min = 0.0
        z_max = CELL_HEIGHT_Z
        return x_min, x_max, y_min, y_max, z_min, z_max

    def on_cell_click(self, r, c):
        tool_name = self.current_tool.get()
        new_id, new_color = CELL_TYPES[tool_name]
        
        # スタート(2)、ゴール(3)、中継(4) はマップ上に1つだけ
        if new_id in [2, 3, 4]:
             self.clear_existing_special_cell(new_id)

        self.map_data[r][c] = new_id
        self.grid_buttons[r][c].config(bg=new_color)

    def clear_existing_special_cell(self, target_id):
        """指定されたIDのセルをマップ上から消去する"""
        for r_idx, row in enumerate(self.map_data):
            for c_idx, cell_id in enumerate(row):
                if cell_id == target_id:
                    self.map_data[r_idx][c_idx] = 0
                    self.grid_buttons[r_idx][c_idx].config(bg=CELL_TYPES["床 (通行可)"][1])
                    return

    # ==========================================================================
    #  PHITS 入力ファイル生成 (複数線源対応)
    # ==========================================================================

    def generate_environment_input(self):
        phits_input_lines = [
            "[ T i t l e ]",
            "Environment Definition for Dose Map Calculation",
            "\n",
            "[ P a r a m e t e r s ]",
            "   maxcas   = 10000",
            "   maxbch   = 10",
            "\n",
            "[ M a t e r i a l ]",
            "  mat[1]   N 8 O 2         $ Air",
            "  mat[2]   Fe 1.0          $ Iron",
            "\n"
        ]

        surface_lines = ["[ S u r f a c e ]"]
        cell_lines = ["[ C e l l ]"]
        
        wall_surface_numbers = []
        source_coords = []
        surface_id_counter = 101 

        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                cell_id = self.map_data[r][c]
                x_min, x_max, y_min, y_max, z_min, z_max = self.get_coords(r, c)

                if cell_id == 1: # 壁
                    s_num = surface_id_counter
                    surface_lines.append(
                        f"  {s_num}  rpp  {x_min:.1f} {x_max:.1f}  {y_min:.1f} {y_max:.1f}  {z_min:.1f} {z_max:.1f}"
                    )
                    cell_lines.append(
                        f"  {s_num}    2  -7.874   -{s_num}    $ Wall at GUI(r={r}, c={c})"
                    )
                    wall_surface_numbers.append(s_num)
                    surface_id_counter += 1
                
                elif cell_id == 9: # 線源
                    src_x = (x_min + x_max) / 2.0
                    src_y = (y_min + y_max) / 2.0
                    src_z = (z_min + z_max) / 2.0 
                    source_coords.append((src_x, src_y, src_z))

        # --- 全体空間 ---
        map_width = MAP_COLS * CELL_SIZE_X
        map_height = MAP_ROWS * CELL_SIZE_Y
        
        s_world = 998
        s_void = 999
        
        world_x_min = -WORLD_MARGIN
        world_x_max = map_width + WORLD_MARGIN
        world_y_min = -WORLD_MARGIN
        world_y_max = map_height + WORLD_MARGIN
        world_z_min = -WORLD_MARGIN
        world_z_max = CELL_HEIGHT_Z + WORLD_MARGIN

        surface_lines.append(
            f"  {s_world}  rpp  {world_x_min:.1f} {world_x_max:.1f}  {world_y_min:.1f} {world_y_max:.1f}  {world_z_min:.1f} {world_z_max:.1f}"
        )
        surface_lines.append(
            f"  {s_void} so   {max(map_width, map_height, CELL_HEIGHT_Z) * 10.0}"
        )
        
        wall_exclusion_str = " ".join([f"#{num}" for num in wall_surface_numbers])
        wall_exclusion_wrapped = textwrap.fill(wall_exclusion_str, width=60, subsequent_indent="      ")

        cell_lines.append(
            f"  1000   1  -1.20E-3  -{s_world} {wall_exclusion_wrapped}   $ Air region"
        )
        cell_lines.append(
            f"  9000  -1            {s_world}    $ Outside world (void)"
        )
        
        phits_input_lines.extend(surface_lines)
        phits_input_lines.append("\n")
        phits_input_lines.extend(cell_lines)
        phits_input_lines.append("\n")

        # --- 線源定義 (複数対応) ---
        if not source_coords:
            phits_input_lines.append("[ S o u r c e ]")
            phits_input_lines.append("$ --- 警告: 線源がマップ上に配置されていません ---")
            phits_input_lines.append("\n")
        else:
            for src_x, src_y, src_z in source_coords:
                phits_input_lines.append("[ S o u r c e ]")
                phits_input_lines.extend([
                    f"   s-type = 1             $ Point source",
                    f"     proj = photon",
                    f"       x0 = {src_x:.3f}",
                    f"       y0 = {src_y:.3f}",
                    f"       z0 = {src_z:.3f}",
                    f"       z1 = {src_z:.3f}",
                    f"      dir = all          $ Isotropic",
                    "   e-type = 28             $ RI source",
                    "       ni = 1",
                    "     Cs-137 1.0E+12      $ 1.0E12 Bq",
                    "    dtime = -10.0",
                    "     norm = 0              $ Output in [/sec]"
                ])
                phits_input_lines.append("\n")

        # --- 線量マップ定義 [T-Deposit] (e-type削除済み) ---
        phits_input_lines.extend([
            "[ T - D e p o s i t ]",
            "    title = Dose Map for A* Algorithm",
            "     mesh = xyz            $ xyzメッシュを指定",
            "   x-type = 2",
            f"       nx = {MAP_COLS}",
            f"     xmin = 0.0",
            f"     xmax = {map_width:.1f}",
            "   y-type = 2",
            f"       ny = {MAP_ROWS}",
            f"     ymin = 0.0",
            f"     ymax = {map_height:.1f}",
            "   z-type = 2",
            "       nz = 1",
            f"     zmin = 0.0",
            f"     zmax = {CELL_HEIGHT_Z:.1f}", 
            "     unit = 0              $ [Gy/source] で出力",
            "   output = dose",
            "     axis = xy",
            "     file = deposit_xy.out",
            "     part = all",
            "   epsout = 1",
            "\n"
        ])

        phits_input_lines.append("[ E n d ]\n")

        final_input_string = "\n".join(phits_input_lines)
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".inp",
            filetypes=[("PHITS Input", "*.inp"), ("All Files", "*.*")],
            initialfile="env_input.inp",
            title="環境定義ファイル (env_input.inp) として保存"
        )
        
        if not filepath: return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(final_input_string)
            messagebox.showinfo("生成成功", f"保存しました:\n{filepath}")
        except Exception as e:
            messagebox.showerror("保存エラー", f"{e}")

    # ==========================================================================
    #  線量マップ読込 & 可視化
    # ==========================================================================

    def load_dose_map(self):
        filepath = filedialog.askopenfilename(
            title="PHITS出力ファイル (deposit.out) を選択",
            filetypes=[("PHITS Output", "*.out"), ("All Files", "*.*")]
        )
        if not filepath: return

        dose_map = self.parse_phits_output(filepath, MAP_ROWS, MAP_COLS)
        
        if dose_map:
            self.dose_map = dose_map  # クラス変数に保存
            self.apply_heatmap(dose_map)

    def parse_phits_output(self, filepath, rows, cols):
        """PHITS出力ファイルを解析 (ヘッダースキップ、データ切り出し強化版)"""
        dose_map = [[0.0 for _ in range(cols)] for _ in range(rows)]
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            all_found_values = []
            
            for line in lines:
                line = line.strip()
                if not line: continue
                if ":" in line or line.startswith("#"): continue # コマンド行スキップ
                if "=" in line: continue # パラメータ設定行スキップ
                if not any(c.isdigit() for c in line): continue # 数字なし行スキップ

                parts = re.split(r'\s+', line)
                for x in parts:
                    try:
                        val = float(x)
                        all_found_values.append(val)
                    except ValueError:
                        continue

            expected_count = rows * cols
            
            # デバッグ出力
            input_dir = os.path.dirname(filepath)
            raw_path = os.path.join(input_dir, "debug_raw_values.txt")
            with open(raw_path, "w") as f_debug:
                f_debug.write(f"Total found: {len(all_found_values)}\nNeeded: {expected_count}\n")
                for idx, val in enumerate(all_found_values):
                    f_debug.write(f"[{idx}] {val}\n")

            if len(all_found_values) < expected_count:
                messagebox.showwarning("データ不足", f"データ不足です。詳細は {raw_path} を確認してください。")
                return None

            # 先頭から必要な数だけ取得
            relevant_data = all_found_values[:expected_count]
            
            idx = 0
            for r in range(rows): 
                for c in range(cols):
                    dose_map[r][c] = relevant_data[idx]
                    idx += 1

            # デバッグ用CSV出力
            matrix_path = os.path.join(input_dir, "debug_matrix.csv")
            with open(matrix_path, "w") as f_csv:
                f_csv.write("Row,Col,Value\n")
                for r in range(rows):
                    for c in range(cols):
                        f_csv.write(f"{r},{c},{dose_map[r][c]}\n")
            
            print(f"デバッグファイル保存: {matrix_path}")
            return dose_map

        except Exception as e:
            messagebox.showerror("読み込みエラー", f"{e}")
            return None

    def apply_heatmap(self, dose_map):
        """対数スケールヒートマップ (白 -> 黄 -> 赤)"""
        if not dose_map: return

        flat_list = [val for row in dose_map for val in row if val > 0]
        if not flat_list: return
        
        max_dose = max(flat_list)
        min_dose = min(flat_list)
        
        if max_dose <= min_dose: return

        log_min = math.log10(min_dose)
        log_max = math.log10(max_dose)

        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                # オブジェクトがある場所は色を変えない
                if self.map_data[r][c] != 0: continue
                
                dose = dose_map[r][c]
                
                if dose <= 0:
                    ratio = 0.0
                else:
                    ratio = (math.log10(dose) - log_min) / (log_max - log_min)
                
                ratio = max(0.0, min(1.0, ratio))
                
                # 白 -> 黄 -> 赤
                if ratio < 0.5:
                    # 白(1,1,1) -> 黄(1,1,0)
                    # R:255, G:255, B:255->0
                    r_val = 255
                    g_val = 255
                    b_val = int(255 * (1 - ratio * 2))
                else:
                    # 黄(1,1,0) -> 赤(1,0,0)
                    # R:255, G:255->0, B:0
                    r_val = 255
                    g_val = int(255 * (2 - ratio * 2))
                    b_val = 0

                color_code = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
                self.grid_buttons[r][c].config(bg=color_code)
        
        messagebox.showinfo("完了", f"可視化完了\n最大: {max_dose:.2e}\n最小: {min_dose:.2e}")

    # ==========================================================================
    #  A* 経路探索
    # ==========================================================================

    def calculate_route(self):
        # 1. マップ上の重要地点を探す
        start_pos = None
        goal_pos = None
        middle_pos = None

        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                if self.map_data[r][c] == 2:
                    start_pos = (r, c)
                elif self.map_data[r][c] == 3:
                    goal_pos = (r, c)
                elif self.map_data[r][c] == 4:
                    middle_pos = (r, c)

        if not start_pos or not goal_pos:
            messagebox.showwarning("エラー", "スタート地点とゴール地点を配置してください。")
            return

        # 2. 線量マップ (未読込なら0)
        current_dose_map = self.dose_map if self.dose_map else [[0]*MAP_COLS for _ in range(MAP_ROWS)]
        
        # 3. 重み入力
        weight_str = simpledialog.askstring("設定", "被ばく回避の重み係数 (0:距離優先, 1000~:被ばく回避):", initialvalue="10000")
        if weight_str is None: return
        try:
            weight = float(weight_str)
        except ValueError:
            weight = 0.0

        # 4. 探索
        full_path = []
        if middle_pos:
            path1 = self.run_astar(start_pos, middle_pos, current_dose_map, weight)
            path2 = self.run_astar(middle_pos, goal_pos, current_dose_map, weight)
            if path1 and path2:
                full_path = path1 + path2[1:]
        else:
            full_path = self.run_astar(start_pos, goal_pos, current_dose_map, weight)

        if full_path:
            self.visualize_path(full_path)
            messagebox.showinfo("成功", f"経路を作成しました (ステップ数: {len(full_path)})")
        else:
            messagebox.showerror("失敗", "経路が見つかりませんでした。")

    def run_astar(self, start, goal, dose_map, weight):
        rows, cols = MAP_ROWS, MAP_COLS
        queue = []
        heapq.heappush(queue, (0, 0, start, [start]))
        
        visited = set()
        min_costs = {start: 0}
        
        while queue:
            _, cost, current, path = heapq.heappop(queue)
            
            if current == goal:
                return path
            
            if current in visited: continue
            visited.add(current)
            
            r, c = current
            
            # 4近傍探索
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                
                if not (0 <= nr < rows and 0 <= nc < cols): continue
                if self.map_data[nr][nc] == 1: continue # 壁
                
                next_pos = (nr, nc)
                
                # コスト = 移動(1) + 線量 * 重み
                dose_val = dose_map[nr][nc] if dose_map else 0
                new_cost = cost + 1 + (dose_val * weight)
                
                if next_pos not in min_costs or new_cost < min_costs[next_pos]:
                    min_costs[next_pos] = new_cost
                    heuristic = abs(goal[0] - nr) + abs(goal[1] - nc)
                    heapq.heappush(queue, (new_cost + heuristic, new_cost, next_pos, path + [next_pos]))
                    
        return None

    def visualize_path(self, path):
        for r, c in path:
            cell_id = self.map_data[r][c]
            # スタート・ゴール・中継・線源は塗りつぶさない
            if cell_id in [2, 3, 4, 9]: 
                continue
            self.grid_buttons[r][c].config(bg="magenta")

# --- アプリケーションの実行 ---
if __name__ == "__main__":
    app = MapEditorApp()
    app.mainloop()