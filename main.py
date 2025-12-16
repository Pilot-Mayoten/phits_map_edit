"""
PHITS Map Editor and Simulation Runner
======================================
This application serves as the main entry point and controller for the GUI.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import tkinter.simpledialog as simpledialog
import os
import threading
from queue import Queue, Empty
from tkinter import scrolledtext

# --- アプリケーションのコアモジュール ---
from app_config import MAP_ROWS, MAP_COLS, CELL_TYPES
from map_editor_view import MapEditorView
from simulation_controls_view import SimulationControlsView
from phits_handler import (generate_environment_input_file, 
                           load_and_parse_dose_map, 
                           generate_detailed_simulation_files,
                           execute_phits_simulation,
                           extract_dose_from_deposit)
from route_calculator import find_optimal_route, compute_detailed_path_points, resample_path_by_width
from utils import get_physical_coords
import visualizer
from results_exporter import generate_results_csv

# ★デバッグ用のフラグ
_app_instance_count = 0

class MainApplication(tk.Tk):
    def __init__(self):
        global _app_instance_count
        _app_instance_count += 1
        print(f"--- MainApplication instance created. Count: {_app_instance_count} ---")
        if _app_instance_count > 1:
            messagebox.showwarning("多重起動警告", "MainApplicationのインスタンスが複数作成されました。予期せぬ動作の原因となります。")

        super().__init__()
        self.title("🗺️ PHITS Map Editor & Route Planner")
        self.geometry("1600x1080") # Windowの高さを拡大

        # --- 1. 内部データの初期化 ---
        self.map_data = [[CELL_TYPES["床 (通行可)"][0] for _ in range(MAP_COLS)] 
                         for _ in range(MAP_ROWS)]
        self.dose_map = None
        self.routes = [] # 複数の経路情報を管理するリスト
        self.route_colors = ['red', 'blue', 'green', 'purple', 'orange', 'cyan', 'magenta', 'brown', 'pink', 'gray']
        self.log_queue = Queue()
        self.result_queue = Queue() # ★結果受け渡し用のキューを追加
        self.latest_results = None # ★最新の結果を保持する変数

        # --- 2. メインレイアウトの作成 ---
        # 全体を上下に分割するPanedWindow
        root_pane = tk.PanedWindow(self, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        root_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 上半分（既存のメインコンテンツ）
        main_paned = tk.PanedWindow(root_pane, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        root_pane.add(main_paned, stretch="always")


        # --- 3. GUIモジュールのインスタンス化 ---
        self.map_editor_view = MapEditorView(main_paned, 
                                             self.on_cell_click,
                                             self.on_cell_hover)
        main_paned.add(self.map_editor_view, width=1050)
        main_paned.paneconfigure(self.map_editor_view, minsize=900)
        
        callbacks = {
            "generate_env_map": self.generate_env_map,
            "load_dose_map": self.load_dose_map,
            "find_optimal_route": self.calculate_optimal_route,
            "run_detailed_simulation": self.run_detailed_simulation,
            "add_route": self.add_route,
            "delete_route": self.delete_route,
            "visualize_routes": self.visualize_routes,
            "run_phits_and_plot": self.run_phits_and_plot_threaded,
            "save_results_csv": self.save_results_csv,
        }
        self.sim_controls_view = SimulationControlsView(main_paned, callbacks)
        main_paned.add(self.sim_controls_view, width=300)
        main_paned.paneconfigure(self.sim_controls_view, minsize=250)

        # 下半分（ログ表示エリア）
        log_frame = tk.LabelFrame(root_pane, text="実行ログ", padx=5, pady=5)
        root_pane.add(log_frame, stretch="never", height=200) # 初期高さを指定

        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, font=("Meiryo UI", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # --- 4. ステータスバー ---
        self.status_var = tk.StringVar(value="準備完了")
        status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.after(100, self.process_log_queue)
        self.after(200, self.process_result_queue) # ★結果処理ループを開始

    def process_result_queue(self):
        """結果キューを処理して、メインスレッドでGUI操作（プロットやダイアログ）を実行"""
        try:
            result = self.result_queue.get_nowait()
            
            # --- 結果のタイプを判定 ---
            # 1. 詳細線量評価の結果 (辞書型)
            if isinstance(result, dict):
                if not result:
                     self.log("プロットできる有効な結果がありませんでした。")
                     messagebox.showinfo("完了", "処理が完了しましたが、プロットできる有効なデータがありませんでした。")
                else:
                    self.log("全経路の処理が完了しました。結果をプロットします。")
                    self.latest_results = result # ★結果をインスタンス変数に保持
                    self.sim_controls_view.save_csv_button.config(state="normal") # ★ボタンを有効化
                    
                    # --- 経路データに total_dose を格納してツリーを更新 ---
                    for i, route in enumerate(self.routes):
                        route_name = f"route_{i + 1}"
                        if route_name in result:
                            route["total_dose"] = result[route_name].get("total_dose", None)
                    self.sim_controls_view.update_route_tree(self.routes)
                    
                    # --- 合計線量のサマリを作成 ---
                    summary_lines = ["\n--- 合計線量 結果サマリ ---"]
                    total_dose_summary = ""
                    # 合計線量が小さい順にソートして表示
                    sorted_results = sorted(result.items(), key=lambda item: item[1].get('total_dose', float('inf')))
                    
                    for route_name, res_data in sorted_results:
                        total_dose = res_data.get("total_dose", 0.0)
                        summary_line = f"  - {route_name}: {total_dose:.4e} Gy/source"
                        summary_lines.append(summary_line)

                    # ログに出力
                    self.log("\n".join(summary_lines))
                    
                    # 詳細プロットを表示
                    visualizer.plot_dose_profile(result, self.routes)
                    
                    # メッセージボックスにもサマリを表示
                    messagebox.showinfo("成功", "PHITSの一括実行と結果のプロットが完了しました。\n\n" + "\n".join(summary_lines))
            
            # 2. 環境シミュレーションの結果 (タプル型)
            elif isinstance(result, tuple) and result[0] == "env_sim_result":
                message = result[1]
                self.log(message)
                if "エラー" in message:
                    messagebox.showerror("環境シミュレーションエラー", message)
                else:
                    messagebox.showinfo("環境シミュレーション完了", message)

            # 3. その他のエラーメッセージ (文字列型)
            elif isinstance(result, str):
                self.log(f"処理中にエラーが発生しました: {result}")
                messagebox.showerror("処理エラー", result)

        except Empty:
            pass # キューが空なら何もしない
        finally:
            self.after(200, self.process_result_queue) # 次のチェックを予約

    def process_log_queue(self):
        """ログメッセージキューを処理して、表示を更新"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                # ScrolledTextにログを追記
                self.log_text.configure(state='normal')
                self.log_text.insert(tk.END, message + '\n')
                self.log_text.configure(state='disabled')
                self.log_text.see(tk.END) # 自動で最終行までスクロール

        except Empty:
            pass # キューが空なら何もしない
        finally:
            self.after(100, self.process_log_queue)

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
        # get_route_definition_dataは現在使われていないため、空の辞書を生成
        route_data = {}

        start, goal, middle = self.find_special_points()
        if not start or not goal:
            messagebox.showwarning("設定エラー", "マップ上に「スタート」と「ゴール」を配置してください。")
            self.log("エラー: 経路追加にはスタートとゴールが必須です。")
            return
        
        route_data["start"] = start
        route_data["goal"] = goal
        route_data["middle"] = middle
        # 経路に色を割り当てる
        route_data["color"] = self.route_colors[len(self.routes) % len(self.route_colors)]

        self.routes.append(route_data)
        self.log(f"新しい経路を追加しました (色: {route_data['color']})。総経路数: {len(self.routes)}")
        self.sim_controls_view.update_route_tree(self.routes)

    def delete_route(self):
        """選択された経路をリストから削除する"""
        indices = self.sim_controls_view.get_selected_route_indices()
        if not indices:
            messagebox.showinfo("情報", "削除する経路が選択されていません。")
            return

        if not messagebox.askyesno("確認", f"{len(indices)}件の経路を削除しますか？"):
            return

        for index in sorted(indices, reverse=True):
            if 0 <= index < len(self.routes):
                del self.routes[index]
        
        self.log(f"{len(indices)}件の経路を削除しました。")
        self.sim_controls_view.update_route_tree(self.routes)

    def generate_env_map(self):
        """環境入力ファイル(env_input.inp)を生成する際に、核種と放射能をユーザーに聞く。"""
        self.log("環境入力ファイルの生成を開始します...")
        
        # ダイアログで核種を聞く
        nuclide = simpledialog.askstring("環境設定", "核種を入力してください（例：Cs-137）:", initialvalue="Cs-137")
        if not nuclide:
            self.log("核種が入力されなかったため、処理を中断しました。")
            return
        
        # ダイアログで放射能を聞く
        activity_str = simpledialog.askstring("環境設定", "放射能（Bq）を入力してください（例：1.0E+12）:", initialvalue="1.0E+12")
        if not activity_str:
            self.log("放射能が入力されなかったため、処理を中断しました。")
            return
        
        try:
            activity = float(activity_str)
            self.log(f"設定内容: 核種={nuclide}, 放射能={activity:.2e} Bq")
            # ファイルを生成し、保存されたパスを受け取る
            saved_filepath = generate_environment_input_file(self.map_data, nuclide, activity)
            
            if saved_filepath:
                self.log(f"PHITS環境入力ファイルを生成しました: {saved_filepath}")
                # ユーザーに続けて実行するか確認
                if messagebox.askyesno("確認", "環境定義ファイルの生成が完了しました。\n続けてPHITSシミュレーションを実行しますか？"):
                    self.run_env_simulation_threaded(saved_filepath)

        except ValueError:
            self.log(f"エラー: 放射能の値が無効です（{activity_str}）。")
        except Exception as e:
            self.log(f"環境入力生成でエラー: {e}")

    def load_dose_map(self):
        """ユーザ操作で deposit.out を読み込み、ヒートマップを適用する（別ボタン）。"""
        self.log("線量マップ読み込みを開始します...")
        dose_data = load_and_parse_dose_map()
        if dose_data:
            self.dose_map = dose_data
            self.map_editor_view.apply_heatmap(self.dose_map, self.map_data)
            self.log("線量マップを読み込み、ヒートマップを適用しました。")
        else:
            self.log("線量マップの読み込みがキャンセルされたか、失敗しました。")

    def calculate_optimal_route(self):
        """A*で最適経路を探索し、ステップ幅でリサンプリングして経路に適用する"""
        self.log("最適経路の探索を開始します...")

        selected_indices = self.sim_controls_view.get_selected_route_indices()
        if not selected_indices:
            messagebox.showwarning("設定エラー", "「最適経路を探索」を適用する経路をリストから選択してください。")
            return
        if len(selected_indices) > 1:
            messagebox.showwarning("設定エラー", "経路は1つだけ選択してください。")
            return
        
        route_index = selected_indices[0]
        target_route = self.routes[route_index]

        start_grid = target_route.get("start")
        goal_grid = target_route.get("goal")
        middle_grid = target_route.get("middle")

        if not start_grid or not goal_grid:
            messagebox.showwarning("設定エラー", "選択された経路に「スタート」と「ゴール」が設定されていません。")
            return

        weight_str = simpledialog.askstring("設定", "被ばく回避の重み係数:", initialvalue="10000")
        try:
            weight = float(weight_str)
        except (ValueError, TypeError):
            return

        a_star_grid_path = find_optimal_route(start_grid, goal_grid, middle_grid, self.map_data, self.dose_map, weight)
        
        if a_star_grid_path:
            self.log(f"最適経路を発見 (グリッド数: {len(a_star_grid_path)})。")
            
            step_width_str = simpledialog.askstring("設定", "評価点のステップ幅 (cm):", initialvalue="10.0")
            try:
                step_width = float(step_width_str)
                if step_width <= 0: raise ValueError()
            except (ValueError, TypeError):
                self.log("無効なステップ幅が入力されたため、処理を中断します。")
                return

            physical_path = []
            for r, c in a_star_grid_path:
                coords = get_physical_coords(r, c)
                center = ((coords[0] + coords[1]) / 2, (coords[2] + coords[3]) / 2, (coords[4] + coords[5]) / 2)
                physical_path.append(center)
            
            detailed_path = resample_path_by_width(physical_path, step_width)
            
            target_route["step_width"] = step_width
            target_route["detailed_path"] = detailed_path
            
            self.map_editor_view.visualize_path(a_star_grid_path, self.map_data)
            self.log(f"ステップ幅 {step_width}cm で経路を再生成 ({len(detailed_path)}点)。経路 {route_index + 1} に適用しました。")
            self.sim_controls_view.update_route_tree(self.routes)
        else:
            messagebox.showerror("探索失敗", "経路が見つかりませんでした。")
            self.log("最適経路が見つかりませんでした。")

    def run_detailed_simulation(self):
        """経路上の詳細シミュレーションを実行"""
        self.log("詳細線量評価を開始します...")
        
        if not self.routes:
            messagebox.showinfo("情報", "評価対象の経路がありません。")
            return

        for i, route in enumerate(self.routes):
            if "detailed_path" not in route:
                messagebox.showwarning("経路未生成", f"経路 {i+1} の詳細経路が生成されていません。\n先に「3. 最適経路を探索」を実行してください。")
                return

        output_dir = filedialog.askdirectory(title="シミュレーション結果の保存先を選択")
        if not output_dir:
            return
        self.log(f"出力先フォルダ: {output_dir}")

        # ユーザに maxcas / maxbch の値を問い合わせ（キャンセルで中断）
        maxcas_str = simpledialog.askstring("詳細評価設定", "maxcas を入力してください:", initialvalue="10000")
        if maxcas_str is None:
            self.log("ユーザが maxcas の入力をキャンセルしました。")
            return
        maxbch_str = simpledialog.askstring("詳細評価設定", "maxbch を入力してください:", initialvalue="10")
        if maxbch_str is None:
            self.log("ユーザが maxbch の入力をキャンセルしました。")
            return

        try:
            maxcas_val = int(maxcas_str)
        except Exception:
            maxcas_val = None
        try:
            maxbch_val = int(maxbch_str)
        except Exception:
            maxbch_val = None

        success, file_count = generate_detailed_simulation_files(self.routes, output_dir, default_maxcas=maxcas_val, default_maxbch=maxbch_val)
        
        if success:
            self.log(f"合計{file_count}個のPHITS入力ファイルを生成しました。")
        else:
            self.log("PHITS入力ファイルの生成に失敗しました。")

    def visualize_routes(self):
        """登録された経路を2Dで可視化する"""
        self.log("経路の2D可視化を開始します...")
        if not self.routes:
            messagebox.showinfo("情報", "表示する経路がありません。")
            return
        
        if any("detailed_path" not in r for r in self.routes):
             messagebox.showinfo("情報", "詳細経路が未生成の経路は表示されません。\n「3. 最適経路を探索」を実行してください。")

        sources = self.find_source_points()
        visualizer.visualize_routes_2d(self.routes, sources)
        self.log("2D可視化ウィンドウを表示しました。")

    def save_results_csv(self):
        """シミュレーション結果をCSVファイルに保存する。"""
        self.log("CSVファイルへの結果保存処理を開始します...")
        if not self.latest_results:
            messagebox.showwarning("保存エラー", "保存対象のシミュレーション結果がありません。")
            self.log("エラー: 保存対象の結果がありませんでした。")
            return

        # ファイル保存ダイアログを表示
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV (Comma Separated Values)", "*.csv"), ("All Files", "*.*")],
            initialfile="phits_dose_results.csv",
            title="シミュレーション結果をCSV形式で保存"
        )

        if not filepath:
            self.log("CSV保存がユーザーによってキャンセルされました。")
            return

        try:
            # CSVデータを生成
            csv_data = generate_results_csv(self.latest_results, self.routes)
            
            # ファイルに書き込み
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                f.write(csv_data)
            
            self.log(f"結果をCSVファイルに正常に保存しました: {filepath}")
            messagebox.showinfo("保存成功", f"結果をCSVファイルに保存しました。\n{filepath}")

        except Exception as e:
            self.log(f"CSVファイルの保存中にエラーが発生しました: {e}")
            messagebox.showerror("保存エラー", f"CSVファイルの保存中にエラーが発生しました:\n{e}")

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

    def find_source_points(self):
        """マップデータから全ての線源の物理中心座標をリストで返す"""
        sources = []
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                if self.map_data[r][c] == 9: # 9は放射線源のID
                    x_min, x_max, y_min, y_max, z_min, z_max = get_physical_coords(r, c)
                    center_x = (x_min + x_max) / 2.0
                    center_y = (y_min + y_max) / 2.0
                    center_z = (z_min + z_max) / 2.0
                    sources.append((center_x, center_y, center_z))
        return sources

    def log(self, message):
        """ログメッセージをコンソールに出力し、GUI更新のためにキューに入れる"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log_queue.put(log_entry)

    def run_phits_and_plot_worker(self):
        """
        「4. 詳細線量評価」で生成済みの入力ファイル群を元に、PHITSを実行し、結果をプロットする。
        """
        self.log("PHITS一括実行と結果プロット処理を開始します...")

        phits_command = self.sim_controls_view.get_phits_command()
        if not phits_command:
            self.result_queue.put("PHITS実行コマンドが設定されていません。")
            return

        # 1. 複数の `route_*` フォルダが含まれる親フォルダ、あるいは単一の`route_*`フォルダを選択させる
        base_dir = filedialog.askdirectory(title="シミュレーションフォルダ(route_*が入っている親フォルダ、またはroute_*自体)を選択")
        if not base_dir:
            self.log("フォルダが選択されなかったため、処理を中断しました。")
            return
        
        self.log(f"選択されたフォルダ: {base_dir}")

        # 2. 処理対象となる `route_*` フォルダをリストアップ
        route_dirs = []
        # 選択されたフォルダ自身が `route_*` かどうかをチェック
        if os.path.basename(base_dir).startswith('route_'):
            route_dirs.append(base_dir)
            self.log(f"単一の経路フォルダ {os.path.basename(base_dir)} を処理対象とします。")
        else:
            # 親フォルダとして、中の `route_*` を探す
            try:
                found_dirs = sorted([
                    os.path.join(base_dir, d) for d in os.listdir(base_dir) 
                    if os.path.isdir(os.path.join(base_dir, d)) and d.startswith('route_')
                ])
                if not found_dirs:
                    self.result_queue.put(f"選択されたフォルダ内に 'route_*' という名前のサブフォルダが見つかりませんでした。")
                    return
                route_dirs.extend(found_dirs)
                self.log(f"発見された経路フォルダ: {[os.path.basename(d) for d in route_dirs]}")
            except Exception as e:
                self.result_queue.put(f"フォルダのスキャン中にエラーが発生しました: {e}")
                return
            
        # --- ここからが新しい処理フロー ---
        all_results = {}
        total_sims = sum(len([f for f in os.listdir(rd) if f.endswith(".inp")]) for rd in route_dirs)
        completed_sims = 0

        # 3. 各 `route_*` フォルダを順番に処理
        for route_dir in route_dirs:
            route_name = os.path.basename(route_dir)
            self.log(f"--- {route_name} の処理を開始 ---")
            
            inp_files = sorted([os.path.join(route_dir, f) for f in os.listdir(route_dir) if f.endswith(".inp")])
            if not inp_files:
                self.log(f"{route_name} 内に .inp ファイルが見つかりませんでした。スキップします。")
                continue

            doses_for_route = []
            
            # 4. 各 `.inp` ファイルに対してPHITSを実行
            for inp_path in inp_files:
                completed_sims += 1
                progress = f"({completed_sims}/{total_sims})"
                self.log(f"{progress} {os.path.basename(inp_path)} のPHITS実行中...")
                
                # phits_handler に inp_path を渡して実行を依頼
                # run_* フォルダの作成と input.inp へのコピーは execute_phits_simulation 内で行われる
                success, result = execute_phits_simulation(inp_path, phits_command)
                
                if not success:
                    error_msg = f"PHITS実行エラー ({os.path.basename(inp_path)}):\n{result}"
                    self.log(error_msg)
                    self.result_queue.put(error_msg) # エラーをメインスレッドに通知
                    return # 処理を中断
                
                run_dir, log_msg = result
                self.log(log_msg)

                # 線量抽出
                doses, error = extract_dose_from_deposit(run_dir)
                if error:
                    extract_error_msg = f"線量抽出エラー ({os.path.basename(run_dir)}):\n{error}"
                    self.log(extract_error_msg)
                    self.result_queue.put(extract_error_msg)
                    return # 処理を中断
                
                # 抽出した線量リストから最初の値（通常は1つしかない）を取得
                if doses:
                    dose = doses[0]
                    doses_for_route.append(dose)
                    self.log(f"  -> 抽出された線量: {dose:.4e} Gy/source")
                else:
                    self.log(f"  -> 警告: {os.path.basename(run_dir)} から線量を抽出できませんでした。")

            # 合計線量を計算
            total_dose = sum(doses_for_route)
            self.log(f"--- {route_name} の合計線量: {total_dose:.4e} Gy/source ---")

            # all_results には詳細な線量リストと合計線量を格納
            all_results[route_name] = {
                "doses": doses_for_route,
                "total_dose": total_dose
            }
            
            self.log(f"--- {route_name} の処理が正常に完了 ---")

        # 5. 全ての処理が完了したら、結果をプロットキューに入れる
        self.result_queue.put(all_results)
        self.log("全ての経路の処理が完了しました。")

    def run_phits_and_plot_threaded(self):
        """バックグラウンドでPHITSを実行し、結果をプロットする"""
        thread = threading.Thread(target=self.run_phits_and_plot_worker)
        thread.start()
        self.log("PHITS実行と結果プロット処理をバックグラウンドで開始しました。")
        messagebox.showinfo("処理中", "PHITS実行と結果プロット処理をバックグラウンドで開始しました。\n進捗はログを確認してください。")

    def run_env_simulation_threaded(self, filepath):
        """単一の環境入力ファイルでPHITSシミュレーションをバックグラウンド実行する"""
        thread = threading.Thread(target=self.run_env_simulation_worker, args=(filepath,))
        thread.start()
        self.log(f"環境シミュレーションをバックグラウンドで開始しました: {os.path.basename(filepath)}")
        messagebox.showinfo("処理中", "環境シミュレーションをバックグラウンドで開始しました。\n詳細はログを確認してください。")

    def run_env_simulation_worker(self, inp_path):
        """環境シミュレーションを実行するワーカースレッド"""
        self.log(f"環境シミュレーションワーカースレッドを開始: {os.path.basename(inp_path)}")
        
        phits_command = self.sim_controls_view.get_phits_command()
        if not phits_command:
            self.result_queue.put(("env_sim_result", "PHITS実行コマンドが設定されていません。"))
            return

        success, result = execute_phits_simulation(inp_path, phits_command, expected_output="deposit_xy.out")

        if success:
            run_dir, log_msg = result
            self.log(log_msg)
            # 成功メッセージをキューに入れる
            deposit_path = os.path.join(run_dir, 'deposit_xy.out')
            msg = f"環境シミュレーションが正常に完了しました。\n出力ファイル: {deposit_path}"
            self.result_queue.put(("env_sim_result", msg))
        else:
            self.log(f"環境シミュレーションでエラーが発生しました:\n{result}")
            self.result_queue.put(("env_sim_result", f"環境シミュレーションでエラーが発生しました:\n{result}"))


if __name__ == '__main__':
    try:
        app = MainApplication()
        app.mainloop()
    except Exception as e:
        import traceback
        with open("startup_error.log", "w") as f:
            f.write("アプリケーションの起動中にエラーが発生しました。\n")
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())
        messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました。詳細は startup_error.log を確認してください。\\n{e}")


