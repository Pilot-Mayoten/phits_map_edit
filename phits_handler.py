# phits_handler.py

"""
PHITSの入力ファイル生成、実行、出力解析など、PHITS関連の処理を担うモジュール。
"""

import textwrap
import re
import os
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
        "\\n",
        "[ P a r a m e t e r s ]",
        "   maxcas   = 10000",
        "   maxbch   = 10",
        "\\n",
        "[ M a t e r i a l ]",
        "  mat[1]   N 8 O 2         $ Air",
        "  mat[2]   Fe 1.0          $ Iron",
        "\\n"
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
    phits_input_lines.append("\\n")
    phits_input_lines.extend(cell_lines)
    phits_input_lines.append("\\n")

    # --- 線源定義 (複数対応) ---
    if not source_coords:
        phits_input_lines.append("[ S o u r c e ]")
        phits_input_lines.append("$ --- 警告: 線源がマップ上に配置されていません ---")
        phits_input_lines.append("\\n")
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
            phits_input_lines.append("\\n")

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
        "\\n"
    ])

    phits_input_lines.append("[ E n d ]\\n")
    final_input_string = "\\n".join(phits_input_lines)
    
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
        messagebox.showinfo("生成成功", f"保存しました:\\n{filepath}")
    except Exception as e:
        messagebox.showerror("保存エラー", f"{e}")

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
        
        all_found_values = []
        
        for line in lines:
            line = line.strip()
            if not line or ":" in line or line.startswith("#") or "=" in line:
                continue
            if not any(c.isdigit() for c in line):
                continue

            parts = re.split(r'\\s+', line)
            for x in parts:
                try:
                    all_found_values.append(float(x))
                except ValueError:
                    continue

        expected_count = MAP_ROWS * MAP_COLS
        
        if len(all_found_values) < expected_count:
            messagebox.showwarning("データ不足", f"出力ファイルから十分な数のデータを読み込めませんでした。")
            return None

        relevant_data = all_found_values[:expected_count]
        
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
