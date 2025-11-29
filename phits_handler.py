# phits_handler.py

"""
PHITSの入力ファイル生成、実行、出力解析など、PHITS関連の処理を担うモジュール。
"""

import textwrap
import re
import os
import shutil
import subprocess
from tkinter import filedialog, messagebox

from app_config import (MAP_ROWS, MAP_COLS, CELL_SIZE_X, CELL_SIZE_Y, 
                        CELL_HEIGHT_Z, WORLD_MARGIN)
from utils import get_physical_coords

def generate_environment_input_file(map_data):
    """
    現在のマップデータから、環境定義用のPHITS入力ファイル文字列を生成し、
    ファイル保存ダイアログを表示して保存する。
    """
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
            cell_id = map_data[r][c]
            x_min, x_max, y_min, y_max, z_min, z_max = get_physical_coords(r, c)

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

    # --- 線量マップ定義 [T-Deposit] ---
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


class AdvancedPhitsMerger:
    def __init__(self, base_content, merge_content):
        self.append_only_keys = ['source', 'tend']
        self.overwrite_keys = ['title', 'parameters', 'tdeposit']
        self.merge_keys = ['material', 'surface', 'cell', 'volume', 'transform']

        self.base_sections = self._parse(base_content)
        self.merge_sections = self._parse(merge_content)
        
        self.id_maps = {'mat': {}, 'cell': {}, 'surf': {}, 'trans': {}}

    def _parse(self, text):
        sections = {}
        header_pattern = re.compile(r'^\s*\[\s*([^\]]+?)\s*\]', re.IGNORECASE)
        current_key, current_header = None, None
        
        for i, line in enumerate(text.splitlines()):
            match = header_pattern.match(line)
            if match:
                header_text = match.group(0).strip()
                key = re.sub(r'[^a-zA-Z0-9]', '', match.group(1)).lower()
                if key in self.append_only_keys:
                    key = f"{key}_{i}"
                if key not in sections:
                    sections[key] = (header_text, [])
                current_key = key
            elif current_key:
                sections[current_key][1].append(line)
        return sections

    def merge(self):
        self._renumber_and_map_ids()
        self._update_references()
        return self._render_output()

    def _renumber_and_map_ids(self):
        id_patterns = {
            'mat': re.compile(r'^\s*mat\s*\[\s*(\d+)\s*\]', re.IGNORECASE),
            'cell': re.compile(r'^\s*(\d+)\s+'),
            'surf': re.compile(r'^\s*(\d+)\s+'),
            'trans': re.compile(r'^\s*\*?Tr(\d+)', re.IGNORECASE)
        }
        section_keys = {'mat': 'material', 'cell': 'cell', 'surf': 'surface', 'trans': 'transform'}

        for id_type, pattern in id_patterns.items():
            key = section_keys[id_type]
            base_ids = {int(m.group(1)) for sec_key, (_, lines) in self.base_sections.items() if sec_key.startswith(key) for line in lines for m in [pattern.match(line)] if m}
            
            max_base_id = max(base_ids) if base_ids else 0
            next_id = max_base_id + 1

            if key in self.merge_sections:
                new_lines = []
                for line in self.merge_sections[key][1]:
                    match = pattern.match(line)
                    if not match:
                        new_lines.append(line)
                        continue
                    
                    old_id = int(match.group(1))
                    new_id = old_id
                    if old_id in base_ids:
                        new_id = next_id
                        next_id += 1
                    
                    self.id_maps[id_type][old_id] = new_id
                    
                    if id_type == 'mat':
                        line = pattern.sub(f"mat[{new_id}]", line, 1)
                    elif id_type == 'trans':
                        line = pattern.sub(f"*Tr{new_id}", line, 1)
                    else:
                        line = pattern.sub(f"{new_id} ", line, 1)
                    new_lines.append(line)
                self.merge_sections[key] = (self.merge_sections[key][0], new_lines)

    def _update_references(self):
        if 'cell' not in self.merge_sections: return

        new_cell_lines = []
        cell_line_pattern = re.compile(r'^\s*(\d+)\s+(-?\d+)\s+([^ ]+)\s+(.*)', re.IGNORECASE)

        for line in self.merge_sections['cell'][1]:
            match = cell_line_pattern.match(line)
            if not match:
                new_cell_lines.append(line)
                continue

            cell_id_str, mat_id_str, density, rest_of_line = match.groups()
            mat_id = int(mat_id_str)
            
            # Material IDの参照更新
            if abs(mat_id) in self.id_maps['mat']:
                new_mat_id = self.id_maps['mat'][abs(mat_id)]
                mat_id_str = f'{"-" if mat_id < 0 else ""}{new_mat_id}'

            # Surface IDの参照更新
            def replace_surf(m):
                prefix, old_id_str = m.group(1), m.group(2)
                old_id = int(old_id_str)
                new_id = self.id_maps['surf'].get(old_id, old_id)
                return f"{prefix}{new_id}"
            rest_of_line = re.sub(r'([+\-#])(\d+)', replace_surf, rest_of_line)

            # Transform IDの参照更新
            def replace_trans(m):
                prefix, old_id_str, suffix = m.groups()
                old_id = int(old_id_str)
                new_id = self.id_maps['trans'].get(old_id, old_id)
                return f"{prefix}{new_id}{suffix}"
            rest_of_line = re.sub(r'(trcl\s*=\s*\(?\s*)(\d+)(\s*\)?)', replace_trans, rest_of_line, flags=re.IGNORECASE)

            new_cell_lines.append(f"  {cell_id_str} {mat_id_str} {density} {rest_of_line}")
        
        self.merge_sections['cell'] = (self.merge_sections['cell'][0], new_cell_lines)

    def _render_output(self):
        final_sections = self.base_sections.copy()

        for key, (header, lines) in self.merge_sections.items():
            if any(key.startswith(k) for k in self.append_only_keys):
                final_sections[key] = (header, lines)
            elif key in self.overwrite_keys:
                final_sections[key] = (header, lines)
            elif key in self.merge_keys:
                if key == 'cell':
                    # セルの場合は、マージ(テンプレート)側を先に書き込むことで優先させる
                    if key in final_sections:
                        final_sections[key][1][:] = lines + final_sections[key][1]
                    else:
                        final_sections[key] = (header, lines)
                elif key in final_sections:
                    final_sections[key][1].extend(lines)
                else:
                    final_sections[key] = (header, lines)
            elif key not in final_sections:
                final_sections[key] = (header, lines)

        order = ['title', 'parameters', 'material', 'surface', 'cell', 'volume', 'transform', 'source', 'tdeposit', 'tend']
        output_lines = []
        written_keys = set()

        for key_prefix in order:
            keys_to_write = sorted([k for k in final_sections if k.startswith(key_prefix)])
            for key in keys_to_write:
                if key not in written_keys:
                    header, lines = final_sections[key]
                    output_lines.append(header)
                    output_lines.extend(l for l in lines if l.strip())
                    output_lines.append('')
                    written_keys.add(key)
        
        return "\n".join(output_lines)


def generate_detailed_simulation_files(routes, output_dir):
    """
    AdvancedPhitsMergerを使用して、経路上の各評価点に対するPHITS入力ファイルを生成する。
    """
    try:
        with open(os.path.join(os.path.dirname(__file__), 'template.inp'), 'r', encoding='utf-8') as f:
            template_text = f.read()
    except Exception as e:
        messagebox.showerror("テンプレート読み込み失敗", f"template.inpの読み込みに失敗: {e}")
        return False, 0

    env_path = filedialog.askopenfilename(
        title='環境定義ファイル(env_input.inp)を選択',
        filetypes=[('PHITS Input', '*.inp'), ('All', '*.*')]
    )
    if not env_path:
        return False, 0 # キャンセルされた
        
    try:
        with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
            env_text = f.read()
    except Exception as e:
        messagebox.showerror('読込失敗', f'環境定義ファイルの読み込みに失敗: {e}')
        return False, 0

    # --- 検出器のセルIDを動的に決定 ---
    # 環境ファイル内の最大のセルIDを探す
    cell_id_pattern = re.compile(r'^\s*(\d+)\s+\d+')
    max_env_cell_id = 0
    for line in env_text.splitlines():
        # コメント行は除外
        if line.strip().startswith('$'):
            continue
        match = cell_id_pattern.match(line)
        if match:
            max_env_cell_id = max(max_env_cell_id, int(match.group(1)))
    
    # 衝突しないように、十分大きなIDを開始点とするのも良い
    # ここでは単純に最大値+1とする
    detector_cell_id_start = max_env_cell_id + 1
    # --- ID決定ここまで ---

    file_count = 0
    try:
        for ri, route in enumerate(routes, start=1):
            route_dir = os.path.join(output_dir, f"route_{ri}")
            os.makedirs(route_dir, exist_ok=True)

            # この経路で使用する検出器IDを決定（基本は同じだが、将来的な拡張のため）
            detector_cell_id = detector_cell_id_start 

            for idx, pt in enumerate(route.get('detailed_path', []), start=1):
                det_x, det_y, det_z = pt
                
                filled_template = template_text
                replacements = {
                    '{det_x}': f"{det_x:.3f}",
                    '{det_y}': f"{det_y:.3f}",
                    '{det_z}': f"{det_z:.3f}",
                    '{nuclide_name}': route.get('nuclide', 'Cs-137'),
                    '{activity_value}': route.get('activity', '1.0E+12'),
                    '{maxcas_value}': str(route.get('maxcas', 10000)),
                    '{maxbch_value}': str(route.get('maxbch', 10)),
                    '{detector_cell_id}': str(detector_cell_id), # 動的に決定したIDを適用
                }
                for key, val in replacements.items():
                    filled_template = filled_template.replace(key, val)

                merger = AdvancedPhitsMerger(base_content=env_text, merge_content=filled_template)
                final_content = merger.merge()

                out_name = os.path.join(route_dir, f"detailed_point_{idx:03d}.inp")
                with open(out_name, 'w', encoding='utf-8') as f:
                    f.write(final_content)

                file_count += 1

        if file_count > 0:
            messagebox.showinfo('生成完了', f'{file_count}件の詳細入力ファイルを作成しました。')
        return True, file_count

    except Exception as e:
        messagebox.showerror('生成失敗', f'詳細入力ファイルの生成中に予期せぬエラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
        return False, 0

def load_and_parse_dose_map():
    """
    ファイル選択ダイアログを開き、PHITSの出力ファイル(deposit.out)を読み込んで、
    線量マップデータを返す。
    """
    filepath = filedialog.askopenfilename(
        title="PHITS出力ファイル (deposit.out) を選択",
        filetypes=[("PHITS Output", "*.out"), ("All Files", "*.*")]
    )
    if not filepath: return None

    dose_map = [[0.0 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        expected_count = MAP_ROWS * MAP_COLS

        # 1) ヘッダを避け、連続した「数値行ブロック」を探す
        groups = []
        current = []
        for line in lines:
            s = line.strip()
            if not s or ":" in s or s.startswith("#") or "=" in s:
                if current:
                    groups.append(current)
                    current = []
                continue
            if not any(c.isdigit() for c in s):
                if current:
                    groups.append(current)
                    current = []
                continue
            # この行は数値を含む可能性あり -> グループに追加
            current.append(s)
        if current:
            groups.append(current)

        # 2) 各グループから数値を抽出し、期待数を満たすブロックを選択
        best_nums = []
        best_diff = None
        for grp in groups:
            nums = []
            for ln in grp:
                parts = re.split(r"\s+", ln)
                for tok in parts:
                    try:
                        nums.append(float(tok))
                    except ValueError:
                        continue
            if not nums:
                continue
            if len(nums) >= expected_count:
                diff = len(nums) - expected_count
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_nums = nums
        # 3) 期待数を満たすグループが無ければ、最も多くの数を持つグループを選ぶ
        if not best_nums and groups:
            # find group with max numeric tokens
            max_cnt = 0
            for grp in groups:
                nums = []
                for ln in grp:
                    parts = re.split(r"\s+", ln)
                    for tok in parts:
                        try:
                            nums.append(float(tok))
                        except ValueError:
                            continue
                if len(nums) > max_cnt:
                    max_cnt = len(nums)
                    best_nums = nums

        # fallback: 全体から抽出 (最終手段)
        if not best_nums:
            all_text = "".join(lines)
            num_pattern = r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+(?:[eE][-+]?\d+)?"
            raw_numbers = re.findall(num_pattern, all_text)
            best_nums = []
            for tok in raw_numbers:
                try:
                    best_nums.append(float(tok))
                except ValueError:
                    continue

        # デバッグ出力: 選択した数値列を保存
        input_dir = os.path.dirname(filepath)
        raw_path = os.path.join(input_dir, "debug_raw_values.txt")
        try:
            with open(raw_path, "w", encoding='utf-8') as f_debug:
                f_debug.write(f"Total found: {len(best_nums)}\nNeeded: {expected_count}\n")
                for idx, val in enumerate(best_nums):
                    f_debug.write(f"[{idx}] {val}\n")
        except Exception:
            pass

        if len(best_nums) < expected_count:
            messagebox.showwarning("データ不足", f"出力ファイルから十分な数のデータを読み込めませんでした。詳細は {raw_path} を確認してください。")
            return None

        relevant_data = best_nums[:expected_count]
        idx = 0
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                dose_map[r][c] = relevant_data[idx]
                idx += 1
        
        messagebox.showinfo("読込成功", "線量マップを正常に読み込みました。")
        return dose_map

    except Exception as e:
        messagebox.showerror("読み込みエラー", f"{e}")
        return None

def execute_phits_simulation(inp_path, phits_command="phits.bat"):
    """
    指定された.inpファイルでPHITSシミュレーションを実行する。
    1021.pyを参考に、より堅牢な実行方法を採用。
    """
    base_name = os.path.splitext(os.path.basename(inp_path))[0]
    run_dir = os.path.join(os.path.dirname(inp_path), f"run_{base_name}")
    
    try:
        os.makedirs(run_dir, exist_ok=True)
        shutil.copy(inp_path, os.path.join(run_dir, "input.inp"))

        # コマンドをリスト形式で準備（より安全）
        # shell=Falseで実行するため、cdは使えない。cwdでディレクトリを指定する。
        command_parts = [phits_command, "input.inp"]

        process = subprocess.Popen(
            command_parts,
            cwd=run_dir,  # 実行ディレクトリを指定
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        stdout, stderr = process.communicate(timeout=600)

        # ログにすべての出力を記録
        log_message = (
            f"--- PHITS Log for {base_name} ---\n"
            f"Return Code: {process.returncode}\n"
            f"[STDOUT]:\n{stdout}\n"
            f"[STDERR]:\n{stderr}\n"
            f"--- End Log ---\n"
        )
        
        # 結果ファイルの存在確認
        deposit_path = os.path.join(run_dir, "deposit.out")
        if not os.path.exists(deposit_path):
            error_message = f"PHITSは終了しましたが、deposit.outが生成されませんでした。\n{log_message}"
            return False, error_message

        # returncodeが0でなくても、deposit.outがあれば成功とみなす場合もあるが、
        # ここでは厳密にチェックする。
        if process.returncode != 0:
            error_message = f"PHITS実行エラー (code: {process.returncode})。\n{log_message}"
            return False, error_message
        
        # 成功時もログは返す（呼び出し元で表示するため）
        return True, (run_dir, log_message)

    except FileNotFoundError:
        return False, f"コマンド '{phits_command}' が見つかりません。フルパスで指定するか、環境変数PATHを確認してください。"
    except subprocess.TimeoutExpired:
        return False, f"PHITS実行がタイムアウトしました ({base_name})"
    except Exception as e:
        return False, f"PHITS実行中に予期せぬエラーが発生しました ({base_name}): {e}"

def extract_dose_from_deposit(run_dir):
    """
    実行ディレクトリ内の deposit.out から線量を取得する。
    """
    deposit_path = os.path.join(run_dir, "deposit.out")
    if not os.path.exists(deposit_path):
        return None, f"deposit.outが見つかりません: {run_dir}"

    try:
        with open(deposit_path, "r", encoding='utf-8', errors='ignore') as f:
            for line in f:
                # regメッシュの場合、"sum over"を含む行から値を取得
                if "sum over" in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return float(parts[-2]), None # 線量値を返す
        return None, "deposit.out内に線量情報が見つかりません。"
    except (ValueError, IndexError) as e:
        return None, f"線量のパースに失敗: {e}"
    except Exception as e:
        return None, f"deposit.outの読み込みエラー: {e}"
