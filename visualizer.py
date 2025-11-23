# visualizer.py

"""
matplotlibを使用したグラフ描画機能を担当するモジュール。
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def visualize_routes_3d(routes):
    """
    登録されたすべての経路と線源を3Dで可視化する。

    Args:
        routes (list[dict]): 経路情報のリスト。
                             各辞書には "detailed_path" と "source" キーが含まれている必要がある。
    """
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
        
        # 線源をプロット
        sx, sy, sz = route["source"]
        ax.scatter(sx, sy, sz, color=color, marker='*', s=200, edgecolors='black', label=f"Source {idx+1}")

    ax.set_xlabel("X-axis [cm]")
    ax.set_ylabel("Y-axis [cm]")
    ax.set_zlabel("Z-axis [cm]")
    ax.set_title("3D Visualization of Routes and Source Locations")
    
    # 凡例を表示
    ax.legend()
    
    # グリッド表示
    ax.grid(True)
    
    # アスペクト比を調整（データ範囲に基づいて設定）
    all_x = [p[0] for r in routes for p in r.get("detailed_path", [])] + [r["source"][0] for r in routes]
    all_y = [p[1] for r in routes for p in r.get("detailed_path", [])] + [r["source"][1] for r in routes]
    all_z = [p[2] for r in routes for p in r.get("detailed_path", [])] + [r["source"][2] for r in routes]
    
    if all_x and all_y and all_z:
        range_x = max(all_x) - min(all_x)
        range_y = max(all_y) - min(all_y)
        range_z = max(all_z) - min(all_z)
        ax.set_box_aspect([range_x, range_y, range_z]) # For matplotlib 3.1+

    plt.tight_layout()
    plt.show()

