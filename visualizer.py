# visualizer.py

"""
matplotlibを使用したグラフ描画機能を担当するモジュール。
"""

import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

import matplotlib.font_manager as fm
from pathlib import Path
from config_loader import get_config

_japanese_font_found = False
_font_prop = None

def set_japanese_font():
    """
    日本語対応フォントをmatplotlibに設定する。
    設定ファイルから指定されたディレクトリ内の日本語フォントを探し、最初に見つかったものを利用する。
    """
    global _japanese_font_found, _font_prop
    if _japanese_font_found:
        if _font_prop:
            plt.rcParams['font.family'] = _font_prop.get_name()
        return

    config = get_config()
    font_dir = Path(config.get_font_directory())
    font_files = config.get_font_files()
    
    found_font_path = None
    for font_file in font_files:
        path = font_dir / font_file
        if path.exists():
            found_font_path = str(path)
            break
            
    if found_font_path:
        _font_prop = fm.FontProperties(fname=found_font_path)
        plt.rcParams['font.family'] = _font_prop.get_name()
        _japanese_font_found = True
        print(f"Japanese font '{_font_prop.get_name()}' ({found_font_path}) was set.")
    else:
        print("Warning: Japanese font not found. Text in graphs may be garbled.")

def visualize_routes_3d(routes, sources):
    """
    登録されたすべての経路と線源を3Dで可視化する。

    Args:
        routes (list[dict]): 経路情報のリスト。
                             各辞書には "detailed_path" キーが含まれている必要がある。
        sources (list[tuple]): 線源の(x, y, z)座標のリスト。
    """
    set_japanese_font() # ★フォント設定を呼び出し
    if not routes:
        print("可視化対象の経路がありません。")
        return

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # カラーマップを設定
    colors = plt.cm.viridis([i/len(routes) for i in range(len(routes))])

    for idx, route in enumerate(routes):
        path = route.get("detailed_path")
        if not path:
            continue
            
        color = colors[idx]
        
        # 経路（評価点）をプロット
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        zs = [p[2] for p in path]
        ax.plot(xs, ys, zs, marker='o', markersize=6, linestyle='-', linewidth=2.5, color=color, label=f"Route {idx+1}")
        
    # 線源をプロット (引数から受け取る)
    if sources:
        sx = [s[0] for s in sources]
        sy = [s[1] for s in sources]
        sz = [s[2] for s in sources]
        ax.scatter(sx, sy, sz, color='red', marker='*', s=600, edgecolors='black', linewidths=2, label="Sources")

    ax.set_xlabel("X-axis [cm]", fontproperties=_font_prop, fontsize=14)
    ax.set_ylabel("Y-axis [cm]", fontproperties=_font_prop, fontsize=14)
    ax.set_zlabel("Z-axis [cm]", fontproperties=_font_prop, fontsize=14)
    ax.set_title("3D Visualization of Routes and Source Locations", fontproperties=_font_prop, fontsize=16)
    
    # 軸の目盛りラベルのサイズを大きく
    ax.tick_params(axis='both', which='major', labelsize=12)
    
    # 凡例のフォントも設定
    legend = ax.legend(fontsize=13)
    for text in legend.get_texts():
        text.set_font_properties(_font_prop)
    
    # グリッド表示
    ax.grid(True, alpha=0.3)
    
    # アスペクト比を調整（データ範囲に基づいて設定）
    all_x = [p[0] for r in routes for p in r.get("detailed_path", [])] + [s[0] for s in sources]
    all_y = [p[1] for r in routes for p in r.get("detailed_path", [])] + [s[1] for s in sources]
    all_z = [p[2] for r in routes for p in r.get("detailed_path", [])] + [s[2] for s in sources]
    
    if all_x and all_y and all_z:
        range_x = max(all_x) - min(all_x)
        range_y = max(all_y) - min(all_y)
        range_z = max(all_z) - min(all_z)
        # mplot3d の内部変換行列が singular もしくは zero-range になると
        # inv_transform が None を返し、マウス移動時などに TypeError を投げることがある。
        # そのため 0 にならないよう小さな値でパディングする。
        eps = 1e-6
        if range_x <= 0: range_x = eps
        if range_y <= 0: range_y = eps
        if range_z <= 0: range_z = eps
        try:
            ax.set_box_aspect([range_x, range_y, range_z]) # For matplotlib 3.1+
        except Exception:
            # 万が一 matplotlib のバージョン差等で失敗しても可視化自体は続行する
            pass

    plt.tight_layout()
    plt.show()


def visualize_routes_2d(routes, sources, map_data=None):
    """
    登録されたすべての経路、線源、障害物を2Dのトップダウン（X-Y平面）で可視化する。
    経路ごとに色分けして表示する。
    """
    set_japanese_font()
    if not any(r.get("detailed_path") for r in routes):
        print("可視化対象の詳細経路がありません。")
        return

    # マップデータからマップサイズを取得して、適切な図サイズを計算
    if map_data is not None:
        from app_config import MAP_ROWS, MAP_COLS, CELL_SIZE_X, CELL_SIZE_Y
        map_width = MAP_COLS * CELL_SIZE_X
        map_height = MAP_ROWS * CELL_SIZE_Y
        aspect_ratio = map_width / map_height
        fig_width = max(10, 10 * aspect_ratio)  # 最小幅10、アスペクト比に応じて拡大
        fig, ax = plt.subplots(figsize=(fig_width, 10))
    else:
        fig, ax = plt.subplots(figsize=(10, 8))

    # 障害物（壁）を描画
    if map_data is not None:
        from app_config import MAP_ROWS, MAP_COLS, CELL_SIZE_X, CELL_SIZE_Y
        from utils import get_physical_coords
        
        # グリッドラインを描画（セル境界）
        for r in range(MAP_ROWS + 1):
            y_val = r * CELL_SIZE_Y
            ax.axhline(y=y_val, color='lightgray', linewidth=0.5, linestyle='--', alpha=0.5, zorder=0)
        
        for c in range(MAP_COLS + 1):
            x_val = c * CELL_SIZE_X
            ax.axvline(x=x_val, color='lightgray', linewidth=0.5, linestyle='--', alpha=0.5, zorder=0)
        
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                if map_data[r][c] == 1:  # 壁
                    x_min, x_max, y_min, y_max, _, _ = get_physical_coords(r, c)
                    rect = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                                        facecolor='gray', edgecolor='black', 
                                        alpha=0.6, linewidth=1, zorder=1)
                    ax.add_patch(rect)

    all_x = []
    all_y = []

    for idx, route in enumerate(routes):
        path = route.get("detailed_path")
        if not path:
            continue

        color = route.get('color', 'gray')
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        ax.plot(xs, ys, marker='o', markersize=12, linestyle='-', linewidth=4, color=color, label=f"Route {idx+1}")
        all_x.extend(xs)
        all_y.extend(ys)
        
        # 始点と終点を強調
        ax.scatter(xs[0], ys[0], color=color, marker='^', s=600, edgecolors='black', linewidths=2.4, zorder=5) # Start
        ax.scatter(xs[-1], ys[-1], color=color, marker='s', s=600, edgecolors='black', linewidths=2.4, zorder=5) # Goal

    # 線源をプロット (Zは無視してXY投影)
    if sources:
        sx = [s[0] for s in sources]
        sy = [s[1] for s in sources]
        ax.scatter(sx, sy, color='yellow', marker='*', s=1000, edgecolors='black', linewidths=3, label='Sources', zorder=5)
        all_x.extend(sx)
        all_y.extend(sy)

    ax.set_xlabel("X-axis [cm]", fontproperties=_font_prop, fontsize=20)
    ax.set_ylabel("Y-axis [cm]", fontproperties=_font_prop, fontsize=20)
    ax.set_title("2D Visualization (Top-Down) of Routes and Source Locations", fontproperties=_font_prop, fontsize=26)
    
    # 軸の目盛りラベルのサイズを大きく
    ax.tick_params(axis='both', which='major', labelsize=18, width=1.4)
    ax.minorticks_on()
    ax.tick_params(axis='both', which='minor', labelsize=16)
    
    legend = ax.legend(fontsize=18, loc='best')
    for text in legend.get_texts():
        text.set_font_properties(_font_prop)
        
    ax.grid(True, alpha=0.35, linewidth=1.6)

    # 軸範囲をマップ全体に設定
    if map_data is not None:
        from app_config import MAP_ROWS, MAP_COLS, CELL_SIZE_X, CELL_SIZE_Y
        map_width = MAP_COLS * CELL_SIZE_X
        map_height = MAP_ROWS * CELL_SIZE_Y
        ax.set_xlim(0, map_width)
        ax.set_ylim(0, map_height)
        # 縮尺が正確に 1:1 となるように設定
        ax.set_aspect('equal', adjustable='datalim')
    else:
        # map_dataがない場合は従来通りデータに基づいて範囲を設定
        if all_x and all_y:
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            pad_x = (max_x - min_x) * 0.1 if max_x > min_x else 1
            pad_y = (max_y - min_y) * 0.1 if max_y > min_y else 1
            ax.set_xlim(min_x - pad_x, max_x + pad_x)
            ax.set_ylim(min_y - pad_y, max_y + pad_y)
            ax.set_aspect('equal', adjustable='datalim')
    
    # 最後に tight_layout を適用
    plt.tight_layout()
    plt.show()


def plot_dose_profile(results, routes):
    """
    各経路の詳細な線量プロファイルを1つのグラフにまとめてプロットする。
    """
    set_japanese_font()
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    has_data_to_plot = False

    # 1. 詳細線量プロット
    for i, (route_name, result_data) in enumerate(results.items()):
        doses = result_data.get("doses", [])
        if not doses:
            continue
        
        has_data_to_plot = True
        
        # 対応する経路情報を見つける
        route_info = next((r for r in routes if f"route_{routes.index(r)+1}" == route_name), None)
        if not route_info or "step_width" not in route_info:
            distances = list(range(len(doses)))
            xlabel = "評価点インデックス"
        else:
            step_width = route_info["step_width"]
            distances = [j * step_width for j in range(len(doses))]
            xlabel = "経路に沿った距離 [cm]"

        color = route_info.get('color', 'gray') if route_info else plt.cm.viridis(i / len(results))

        ax.plot(distances, doses, marker='o', markersize=12, linestyle='-', linewidth=4, label=f"{route_name}", color=color)

    if has_data_to_plot:
        ax.set_xlabel(xlabel, fontproperties=_font_prop, fontsize=20)
        ax.set_ylabel("線量 [Gy/source]", fontproperties=_font_prop, fontsize=20)
        ax.set_title("経路上の線量プロファイル", fontproperties=_font_prop, fontsize=26)
        ax.set_yscale('log')
        ax.tick_params(axis='both', which='major', labelsize=18, width=1.4)
        ax.minorticks_on()
        ax.tick_params(axis='both', which='minor', labelsize=16)
        ax.legend(prop=_font_prop, fontsize=18, loc='best')
        ax.grid(True, which="major", ls="--", alpha=0.7, linewidth=1.7)
        ax.grid(True, which="minor", ls=":", alpha=0.5, linewidth=1.1)
        plt.tight_layout()
        plt.show() # グラフが閉じられるまでここでブロック
    else:
        # プロットするデータがなかった場合、不要なウィンドウを閉じる
        plt.close(fig)


def visualize_astar_evaluation(eval_data, path, map_data, eval_type='f'):
    """
    A*アルゴリズムの評価関数の値を2Dヒートマップで可視化する。
    
    Args:
        eval_data (dict): 各ノードの評価値データ {(row, col): {'f': f値, 'g': g値, 'h': h値}}
        path (list): 最終的に見つかった経路 [(row, col), ...]
        map_data (list[list[int]]): マップデータ (壁情報)
        eval_type (str): 表示する評価値のタイプ ('f', 'g', 'h')
    """
    set_japanese_font()
    
    from app_config import MAP_ROWS, MAP_COLS
    import numpy as np
    
    # 評価値マップを作成 (訪問していないノードはNaN)
    eval_map = np.full((MAP_ROWS, MAP_COLS), np.nan)
    
    for (r, c), values in eval_data.items():
        if eval_type in values:
            eval_map[r, c] = values[eval_type]
    
    # 壁の位置にもNaNを設定
    for r in range(MAP_ROWS):
        for c in range(MAP_COLS):
            if map_data[r][c] == 1:
                eval_map[r, c] = np.nan
    
    # 図を作成
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # ヒートマップを描画
    im = ax.imshow(eval_map, cmap='viridis', origin='upper', interpolation='nearest')
    
    # カラーバーを追加
    cbar = plt.colorbar(im, ax=ax)
    
    # タイトルとラベルを設定
    titles = {
        'f': 'f(n) = g(n) + h(n) の値 (評価関数)',
        'g': 'g(n) の値 (スタートからの実コスト)',
        'h': 'h(n) の値 (ゴールまでのヒューリスティック)'
    }
    cbar.set_label(titles.get(eval_type, eval_type), fontproperties=_font_prop, fontsize=14)
    ax.set_title(f'A* アルゴリズムの評価値マップ: {titles.get(eval_type, eval_type)}', 
                 fontproperties=_font_prop, fontsize=16)
    ax.set_xlabel('列 (Col)', fontproperties=_font_prop, fontsize=12)
    ax.set_ylabel('行 (Row)', fontproperties=_font_prop, fontsize=12)
    
    # 経路を重ねて描画
    if path:
        path_rows = [p[0] for p in path]
        path_cols = [p[1] for p in path]
        ax.plot(path_cols, path_rows, 'r-', linewidth=3, label='最適経路', alpha=0.8)
        ax.plot(path_cols[0], path_rows[0], 'go', markersize=15, label='スタート', markeredgecolor='black', markeredgewidth=2)
        ax.plot(path_cols[-1], path_rows[-1], 'r*', markersize=20, label='ゴール', markeredgecolor='black', markeredgewidth=2)
    
    # 凡例を追加
    legend = ax.legend(fontsize=12, loc='upper right')
    for text in legend.get_texts():
        text.set_font_properties(_font_prop)
    
    # グリッドを追加
    ax.set_xticks(range(0, MAP_COLS, max(1, MAP_COLS // 20)))
    ax.set_yticks(range(0, MAP_ROWS, max(1, MAP_ROWS // 20)))
    ax.grid(True, which='both', alpha=0.2, linestyle='--', linewidth=0.5)
    
    plt.tight_layout()
    plt.show()

