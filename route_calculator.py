# route_calculator.py

"""
A*アルゴリズムを含む、経路計算関連のロジックを格納するモジュール。
"""

import heapq
import math
from app_config import MAP_ROWS, MAP_COLS

def find_optimal_route(start_pos, goal_pos, middle_pos, map_data, dose_map, weight):
    """
    スタート -> (中継点) -> ゴール までの最適経路を探索する。
    中継点がない場合は、スタート -> ゴール の経路を探索する。

    Args:
        start_pos (tuple): スタート地点の (row, col)
        goal_pos (tuple): ゴール地点の (row, col)
        middle_pos (tuple or None): 中継地点の (row, col)。なければ None。
        map_data (list[list[int]]): マップの内部データ (壁情報など)
        dose_map (list[list[float]]): 各マスの線量データ
        weight (float): 線量コストに対する重み係数

    Returns:
        list or None: 見つかった経路の座標リスト。見つからなければ None。
    """
    full_path = []
    
    #  dosis map がない場合は、線量ゼロのマップを作成
    if not dose_map:
        dose_map = [[0.0 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]

    if middle_pos:
        # 1. スタートから中継点まで
        path1 = run_astar(start_pos, middle_pos, map_data, dose_map, weight)
        if not path1:
            return None # 最初の区間で見つからなければ失敗

        # 2. 中継点からゴールまで
        path2 = run_astar(middle_pos, goal_pos, map_data, dose_map, weight)
        if not path2:
            return None # ２番目の区間で見つからなければ失敗
        
        # 経路を結合（中継点の重複を削除）
        full_path = path1 + path2[1:]
    else:
        # 中継点がない場合
        full_path = run_astar(start_pos, goal_pos, map_data, dose_map, weight)

    return full_path

def run_astar(start, goal, map_data, dose_map, weight):
    """
    A*アルゴリズムを実行して、2点間の最適経路を見つける。

    Returns:
        list or None: 経路のリスト。見つからなければNone。
    """
    rows, cols = MAP_ROWS, MAP_COLS
    
    # (評価値, 実コスト, 現在位置, 経路リスト)
    queue = [(0, 0, start, [start])]
    
    visited = set()
    min_costs = {start: 0}
    
    while queue:
        _, cost, current, path = heapq.heappop(queue)
        
        if current == goal:
            return path
        
        if current in visited:
            continue
        visited.add(current)
        
        r, c = current
        
        # 上下左右の4方向を探索
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            
            # マップ範囲外かチェック
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            # 壁かチェック
            if map_data[nr][nc] == 1:
                continue
            
            next_pos = (nr, nc)
            
            # コスト計算 = 移動コスト(1) + 線量コスト
            dose_val = dose_map[nr][nc]
            new_cost = cost + 1 + (dose_val * weight)
            
            if next_pos not in min_costs or new_cost < min_costs[next_pos]:
                min_costs[next_pos] = new_cost
                # ヒューリスティックコスト（マンハッタン距離）
                heuristic = abs(goal[0] - nr) + abs(goal[1] - nc)
                # 評価値 = 実コスト + ヒューリスティックコスト
                priority = new_cost + heuristic
                heapq.heappush(queue, (priority, new_cost, next_pos, path + [next_pos]))
                
    return None # ゴールに到達できなかった場合

# ==========================================================================
#  詳細評価用の経路点計算 (1021.pyより移植)
# ==========================================================================

def _distance(p1, p2):
    """3次元座標p1とp2のユークリッド距離を計算する"""
    return math.sqrt(sum((b - a) ** 2 for a, b in zip(p1, p2)))

def _interpolate_point(p1, p2, ratio):
    """p1とp2をratioで内分する点を計算する"""
    return tuple(p1[i] + ratio * (p2[i] - p1[i]) for i in range(3))

def compute_detailed_path_points(start_phys, mid_phys, end_phys, step_cm):
    """
    スタート、中継点、ゴールの物理座標から、指定されたステップ幅で
    評価点群の物理座標リストを生成する。
    """
    path_points = [start_phys]
    
    # --- スタート -> 中継点 ---
    if mid_phys:
        seg1_len = _distance(start_phys, mid_phys)
        if step_cm > 0 and seg1_len > 0:
            n_steps1 = int(seg1_len // step_cm)
            for step in range(1, n_steps1 + 1):
                ratio = (step * step_cm) / seg1_len
                path_points.append(_interpolate_point(start_phys, mid_phys, ratio))
        path_points.append(mid_phys)
        
        # --- 中継点 -> ゴール ---
        start_of_seg2 = mid_phys
    else:
        # --- スタート -> ゴール (中継点なし) ---
        start_of_seg2 = start_phys

    seg2_len = _distance(start_of_seg2, end_phys)
    if step_cm > 0 and seg2_len > 0:
        n_steps2 = int(seg2_len // step_cm)
        for step in range(1, n_steps2 + 1):
            ratio = (step * step_cm) / seg2_len
            path_points.append(_interpolate_point(start_of_seg2, end_phys, ratio))
    
    # 最後の点がゴールと完全一致でなければ、ゴールを追加
    if path_points[-1] != end_phys:
        path_points.append(end_phys)
        
    return path_points
