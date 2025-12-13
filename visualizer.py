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
        ax.plot(xs, ys, zs, marker='.', linestyle='-', color=color, label=f"Route {idx+1}")
        
    # 線源をプロット (引数から受け取る)
    if sources:
        sx = [s[0] for s in sources]
        sy = [s[1] for s in sources]
        sz = [s[2] for s in sources]
        ax.scatter(sx, sy, sz, color='red', marker='*', s=200, edgecolors='black', label="Sources")

    ax.set_xlabel("X-axis [cm]", fontproperties=_font_prop)
    ax.set_ylabel("Y-axis [cm]", fontproperties=_font_prop)
    ax.set_zlabel("Z-axis [cm]", fontproperties=_font_prop)
    ax.set_title("3D Visualization of Routes and Source Locations", fontproperties=_font_prop)
    
    # 凡例のフォントも設定
    legend = ax.legend()
    for text in legend.get_texts():
        text.set_font_properties(_font_prop)
    
    # グリッド表示
    ax.grid(True)
    
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


def visualize_routes_2d(routes, sources):
    """
    登録されたすべての経路と線源を2Dのトップダウン（X-Y平面）で可視化する。
    経路ごとに色分けして表示する。
    """
    set_japanese_font()
    if not any(r.get("detailed_path") for r in routes):
        print("可視化対象の詳細経路がありません。")
        return

    fig, ax = plt.subplots(figsize=(10, 8))

    all_x = []
    all_y = []

    for idx, route in enumerate(routes):
        path = route.get("detailed_path")
        if not path:
            continue

        color = route.get('color', 'gray')
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        ax.plot(xs, ys, marker='.', linestyle='-', color=color, label=f"Route {idx+1}")
        all_x.extend(xs)
        all_y.extend(ys)
        
        # 始点と終点を強調
        ax.scatter(xs[0], ys[0], color=color, marker='^', s=150, edgecolors='black') # Start
        ax.scatter(xs[-1], ys[-1], color=color, marker='s', s=150, edgecolors='black') # Goal

    # 線源をプロット (Zは無視してXY投影)
    if sources:
        sx = [s[0] for s in sources]
        sy = [s[1] for s in sources]
        ax.scatter(sx, sy, color='yellow', marker='*', s=300, edgecolors='black', label='Sources')
        all_x.extend(sx)
        all_y.extend(sy)

    ax.set_xlabel("X-axis [cm]", fontproperties=_font_prop)
    ax.set_ylabel("Y-axis [cm]", fontproperties=_font_prop)
    ax.set_title("2D Visualization (Top-Down) of Routes and Source Locations", fontproperties=_font_prop)
    
    legend = ax.legend()
    for text in legend.get_texts():
        text.set_font_properties(_font_prop)
        
    ax.grid(True)

    # 軸範囲とアスペクト調整
    if all_x and all_y:
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        pad_x = (max_x - min_x) * 0.1 if max_x > min_x else 1
        pad_y = (max_y - min_y) * 0.1 if max_y > min_y else 1
        ax.set_xlim(min_x - pad_x, max_x + pad_x)
        ax.set_ylim(min_y - pad_y, max_y + pad_y)
        try:
            ax.set_aspect('equal', adjustable='box')
        except Exception:
            pass

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

        ax.plot(distances, doses, marker='o', linestyle='-', label=f"{route_name}", color=color)

    if has_data_to_plot:
        ax.set_xlabel(xlabel, fontproperties=_font_prop)
        ax.set_ylabel("線量 [Gy/source]", fontproperties=_font_prop)
        ax.set_title("経路上の線量プロファイル", fontproperties=_font_prop)
        ax.set_yscale('log')
        ax.legend(prop=_font_prop)
        ax.grid(True, which="both", ls="--")
        plt.tight_layout()
        plt.show() # グラフが閉じられるまでここでブロック
    else:
        # プロットするデータがなかった場合、不要なウィンドウを閉じる
        plt.close(fig)

