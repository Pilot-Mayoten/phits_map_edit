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


def generate_detailed_simulation_files(routes, output_dir):
    """
    routes: list of route dicts with 'detailed_path' containing [(x,y,z), ...]
    output_dir: destination folder

    振る舞い:
    - ユーザに既存の環境入力ファイル(env_input.inp)を選択してもらい、その内容を各詳細入力ファイルの先頭に挿入します。
    - `template.inp` を読み、[ S o u r c e ] セクションを削除して検出器位置だけ差し替えます。
    - 各評価点ごとに個別の inp ファイルを生成する。
    """
    # テンプレート読み込み
    try:
        with open(os.path.join(os.path.dirname(__file__), 'template.inp'), 'r', encoding='utf-8') as tf:
            template_text = tf.read()
    except Exception as e:
        messagebox.showerror("テンプレート読み込み失敗", f"template.inp の読み込みに失敗しました: {e}")
        return False, 0

    # ユーザに env_input.inp（環境定義）を選択してもらう
    env_path = filedialog.askopenfilename(title='環境定義ファイル(env_input.inp)を選択（各詳細入力に挿入する）', filetypes=[('PHITS Input','*.inp'),('All','*.*')])
    env_text = ''
    if env_path:
        try:
            with open(env_path, 'r', encoding='utf-8', errors='ignore') as ef:
                env_text = ef.read()
        except Exception as e:
            messagebox.showwarning('警告', f'env_input ファイルの読み込みに失敗しました: {e}。env を挿入せずに生成します。')

    # ソース定義をテンプレートから削除する (簡易的に [ S o u r c e ] ～ 次の [ の先頭まで)
    template_no_source = re.sub(r"\[\s*S\s*o\s*u\s*r\s*c\s*e\s*\].*?(?=\n\[|\Z)", "", template_text, flags=re.S|re.I)

    file_count = 0
    try:
        for ri, route in enumerate(routes, start=1):
            route_dir = os.path.join(output_dir, f"route_{ri}")
            os.makedirs(route_dir, exist_ok=True)

            detailed = route.get('detailed_path', [])
            for idx, pt in enumerate(detailed, start=1):
                # pt は (x, y, z) の中心座標を想定
                det_x, det_y, det_z = pt

                # 既存 env をファイルにコピー into route_dir for traceability
                if env_text:
                    try:
                        with open(os.path.join(route_dir, 'env_input.inp'), 'w', encoding='utf-8') as ef:
                            ef.write(env_text)
                    except Exception:
                        pass

                # テンプレートに値を埋める
                # route に含まれる核種・放射能を使用（存在しなければテンプレート内の既定を残す）
                nuclide = route.get('nuclide', 'Cs-137')
                activity = route.get('activity', '1.0E+12')
                maxcas = route.get('maxcas', 10000)
                maxbch = route.get('maxbch', 10)

                filled = template_no_source
                filled = filled.replace('{det_x}', f"{det_x:.3f}")
                filled = filled.replace('{det_y}', f"{det_y:.3f}")
                filled = filled.replace('{det_z}', f"{det_z:.3f}")
                filled = filled.replace('{nuclide_name}', str(nuclide))
                filled = filled.replace('{activity_value}', str(activity))
                filled = filled.replace('{maxcas_value}', str(maxcas))
                filled = filled.replace('{maxbch_value}', str(maxbch))

                # ソースは env_input.inp に含まれているものを参照する前提なので削除済み
                out_name = os.path.join(route_dir, f"detailed_point_{idx:03d}.inp")
                with open(out_name, 'w', encoding='utf-8') as out_f:
                    # 先頭に env を挿入してからテンプレートを置く
                    if env_text:
                        out_f.write(env_text)
                        out_f.write("\n")
                    out_f.write(filled)

                file_count += 1

        messagebox.showinfo('生成完了', f'{file_count} 件の詳細PHITS入力ファイルを作成しました。')
        return True, file_count
    except Exception as e:
        messagebox.showerror('生成失敗', f'詳細入力ファイルの生成中にエラーが発生しました: {e}')
        return False, file_count

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
