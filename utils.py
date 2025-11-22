# utils.py

"""
複数のモジュールで共有される可能性のある、汎用的な便利関数を格納するモジュール。
"""

from app_config import MAP_ROWS, CELL_SIZE_X, CELL_SIZE_Y, CELL_HEIGHT_Z

def get_physical_coords(r, c):
    """
    GUIのグリッド座標 (row, col) から物理座標 (x_min, x_max, y_min, y_max, z_min, z_max) を計算する。
    
    Args:
        r (int): グリッドの行インデックス (0-indexed)
        c (int): グリッドの列インデックス (0-indexed)

    Returns:
        tuple: (x_min, x_max, y_min, y_max, z_min, z_max)
    """
    x_min = c * CELL_SIZE_X
    x_max = (c + 1) * CELL_SIZE_X
    
    # GUIの行番号 r=0 が物理座標のY最大値に対応するため、変換する
    y_max = (MAP_ROWS - r) * CELL_SIZE_Y
    y_min = (MAP_ROWS - r - 1) * CELL_SIZE_Y
    
    z_min = 0.0
    z_max = CELL_HEIGHT_Z
    
    return x_min, x_max, y_min, y_max, z_min, z_max
