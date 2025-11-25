# visualizer.py

"""
matplotlibを使用したグラフ描画機能を担当するモジュール。
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def visualize_routes_3d(routes, sources):
    """
    登録されたすべての経路と線源を3Dで可視化する。

    Args:
        routes (list[dict]): 経路情報のリスト。
                             各辞書には "detailed_path" キーが含まれている必要がある。
        sources (list[tuple]): 線源の(x, y, z)座標のリスト。
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
        
    # 線源をプロット (引数から受け取る)
    if sources:
        sx = [s[0] for s in sources]
        sy = [s[1] for s in sources]
        sz = [s[2] for s in sources]
        ax.scatter(sx, sy, sz, color='red', marker='*', s=200, edgecolors='black', label="Sources")

    ax.set_xlabel("X-axis [cm]")
    ax.set_ylabel("Y-axis [cm]")
    ax.set_zlabel("Z-axis [cm]")
    ax.set_title("3D Visualization of Routes and Source Locations")
    
    # 凡例を表示
    ax.legend()
    
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
        if range_x <= 0:
            range_x = eps
        if range_y <= 0:
            range_y = eps
        if range_z <= 0:
            range_z = eps
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

    Args:
        routes (list[dict]): 経路情報のリスト。各辞書には "detailed_path" キーが含まれている必要がある。
        sources (list[tuple]): 線源の(x, y, z)座標のリスト。Zは無視してXY平面に投影する。
    """
    if not routes:
        print("可視化対象の経路がありません。")
        return

    fig, ax = plt.subplots(figsize=(10, 8))

    # カラーマップを設定
    colors = plt.cm.viridis([i/len(routes) for i in range(len(routes))])

    all_x = []
    all_y = []

    for idx, route in enumerate(routes):
        path = route.get("detailed_path")
        if not path:
            continue

        color = colors[idx]
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        ax.plot(xs, ys, marker='.', linestyle='-', color=color, label=f"Route {idx+1}")
        all_x.extend(xs)
        all_y.extend(ys)

    # 線源をプロット (Zは無視してXY投影)
    if sources:
        sx = [s[0] for s in sources]
        sy = [s[1] for s in sources]
        ax.scatter(sx, sy, color='red', marker='*', s=150, edgecolors='black', label='Sources')
        all_x.extend(sx)
        all_y.extend(sy)

    ax.set_xlabel("X-axis [cm]")
    ax.set_ylabel("Y-axis [cm]")
    ax.set_title("2D Visualization (Top-Down) of Routes and Source Locations")
    ax.legend()
    ax.grid(True)

    # 軸範囲とアスペクト調整
    if all_x and all_y:
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        # パディング
        pad_x = (max_x - min_x) * 0.05 if max_x > min_x else 0.5
        pad_y = (max_y - min_y) * 0.05 if max_y > min_y else 0.5
        ax.set_xlim(min_x - pad_x, max_x + pad_x)
        ax.set_ylim(min_y - pad_y, max_y + pad_y)
        try:
            ax.set_aspect('equal', adjustable='box')
        except Exception:
            pass

    plt.tight_layout()
    plt.show()

