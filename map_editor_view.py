# map_editor_view.py

"""
マップエディタのGUIコンポーネント（ツールボックス、グリッド表示など）を管理するモジュール。

グリッドは 1 枚の Canvas に矩形を描画して表現する。
- 300 個のボタンウィジェットを廃止したため動作が軽い。
- ウィンドウ（ペイン）のサイズに合わせてマス目ごと拡大縮小する。
"""

import tkinter as tk
from tkinter import messagebox
import math
from app_config import MAP_ROWS, MAP_COLS, CELL_TYPES, CELL_SIZE_X, CELL_SIZE_Y
from utils import get_physical_coords

# Canvas 内の余白（軸ラベル用）
MARGIN_LEFT = 44   # Y軸ラベル
MARGIN_TOP = 22    # X軸ラベル
MARGIN_RIGHT = 8
MARGIN_BOTTOM = 8

FLOOR_COLOR = CELL_TYPES["床 (通行可)"][1]
GRID_LINE_COLOR = "#c8c8c8"


class MapEditorView(tk.Frame):
    def __init__(self, master, on_cell_click_callback, on_hover_callback):
        super().__init__(master)

        self.on_cell_click_callback = on_cell_click_callback
        self.on_hover_callback = on_hover_callback
        self.main_app = None  # ★main.py からセットされる（save/load用）

        self.current_tool = tk.StringVar(value="床 (通行可)")

        # 各セルの色を保持（再描画・リサイズで使用）
        self.cell_colors = [[FLOOR_COLOR for _ in range(MAP_COLS)]
                            for _ in range(MAP_ROWS)]

        # Canvas 上のアイテムID
        self._rect_ids = [[None for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
        self._x_labels = []  # (item_id, col)
        self._y_labels = []  # (item_id, row)

        # グリッドのジオメトリ（リサイズ時に更新）
        self._cell = 0.0
        self._ox = MARGIN_LEFT
        self._oy = MARGIN_TOP
        self._last_hover = None
        self._items_built = False

        self.create_widgets()

    # ------------------------------------------------------------------ #
    #  ウィジェット生成
    # ------------------------------------------------------------------ #
    def create_widgets(self):
        # --- 1. 左側のツールボックス ---
        toolbox_frame = tk.Frame(self, relief=tk.RAISED, bd=2)
        toolbox_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.create_toolbox(toolbox_frame)

        # --- 2. 右側のマップグリッド（Canvas / ウィンドウに合わせて伸縮）---
        grid_container = tk.Frame(self)
        grid_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True,
                            padx=10, pady=10)
        self.create_map_grid(grid_container)

    def create_toolbox(self, parent):
        tk.Label(parent, text="ツール選択", font=("Meiryo UI", 13, "bold")).pack(pady=10)

        for name, (_, color) in CELL_TYPES.items():
            rb = tk.Radiobutton(
                parent,
                text=name,
                variable=self.current_tool,
                value=name,
                indicatoron=False,
                width=14,
                height=2,
                background=color,
                selectcolor=color,
                activebackground=color,
                font=("Meiryo UI", 11),
                fg="white" if color in ["black", "red", "blue"] else "black",
                relief=tk.RAISED,
                bd=2
            )
            rb.pack(pady=5, padx=10, fill=tk.X)

    def create_map_grid(self, parent):
        self.canvas = tk.Canvas(parent, bg="#e0e0e0", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_click)   # ドラッグで連続描画
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", lambda e: setattr(self, "_last_hover", None))

    # ------------------------------------------------------------------ #
    #  描画・レイアウト
    # ------------------------------------------------------------------ #
    def _build_items(self):
        """Canvas アイテムを最初に一度だけ生成する。"""
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                self._rect_ids[r][c] = self.canvas.create_rectangle(
                    0, 0, 0, 0,
                    fill=self.cell_colors[r][c],
                    outline=GRID_LINE_COLOR,
                    width=1,
                )
        # X軸ラベル（上部・5マスごと）
        for c in range(0, MAP_COLS, 5):
            item = self.canvas.create_text(0, 0, text=f"{c * CELL_SIZE_X:.0f}",
                                           font=("Meiryo UI", 8, "bold"), fill="#333")
            self._x_labels.append((item, c))
        # Y軸ラベル（左側・5マスごと）
        for r in range(0, MAP_ROWS, 5):
            item = self.canvas.create_text(0, 0, text=f"{(MAP_ROWS - r) * CELL_SIZE_Y:.0f}",
                                           font=("Meiryo UI", 8, "bold"), fill="#333", anchor="e")
            self._y_labels.append((item, r))
        self._items_built = True

    def _on_resize(self, event):
        # 利用可能領域からマス目サイズを算出（縦横比 1:1 を維持）
        avail_w = event.width - MARGIN_LEFT - MARGIN_RIGHT
        avail_h = event.height - MARGIN_TOP - MARGIN_BOTTOM
        if avail_w <= 0 or avail_h <= 0:
            return

        cell = min(avail_w / MAP_COLS, avail_h / MAP_ROWS)
        if cell <= 0:
            return

        if not self._items_built:
            self._build_items()

        self._cell = cell
        grid_w = cell * MAP_COLS
        grid_h = cell * MAP_ROWS
        # グリッド領域を中央寄せ
        self._ox = MARGIN_LEFT + (avail_w - grid_w) / 2
        self._oy = MARGIN_TOP + (avail_h - grid_h) / 2

        self._layout()

    def _layout(self):
        """現在のジオメトリに合わせて全アイテムの座標を更新する。"""
        cell = self._cell
        ox, oy = self._ox, self._oy

        for r in range(MAP_ROWS):
            y0 = oy + r * cell
            y1 = y0 + cell
            for c in range(MAP_COLS):
                x0 = ox + c * cell
                self.canvas.coords(self._rect_ids[r][c], x0, y0, x0 + cell, y1)

        # ラベルのフォントサイズをマス目に合わせて調整
        font_size = max(7, min(11, int(cell * 0.45)))
        label_font = ("Meiryo UI", font_size, "bold")

        for item, c in self._x_labels:
            self.canvas.coords(item, ox + c * cell + cell / 2, oy - MARGIN_TOP / 2)
            self.canvas.itemconfigure(item, font=label_font)
        for item, r in self._y_labels:
            self.canvas.coords(item, ox - 4, oy + r * cell + cell / 2)
            self.canvas.itemconfigure(item, font=label_font)

    # ------------------------------------------------------------------ #
    #  マウスイベント
    # ------------------------------------------------------------------ #
    def _xy_to_cell(self, x, y):
        if self._cell <= 0:
            return None
        c = int((x - self._ox) // self._cell)
        r = int((y - self._oy) // self._cell)
        if 0 <= r < MAP_ROWS and 0 <= c < MAP_COLS:
            return r, c
        return None

    def _on_click(self, event):
        cell = self._xy_to_cell(event.x, event.y)
        if cell:
            self.on_cell_click_callback(cell[0], cell[1])

    def _on_motion(self, event):
        cell = self._xy_to_cell(event.x, event.y)
        if cell and cell != self._last_hover:
            self._last_hover = cell
            self.on_hover_callback(cell[0], cell[1])

    # ------------------------------------------------------------------ #
    #  外部から呼ばれる公開メソッド（インターフェースは従来通り）
    # ------------------------------------------------------------------ #
    def update_cell_color(self, r, c, color):
        """指定されたセルの色を更新する"""
        self.cell_colors[r][c] = color
        item = self._rect_ids[r][c]
        if item is not None:
            self.canvas.itemconfigure(item, fill=color)

    def apply_heatmap(self, dose_map, map_data):
        """線量マップデータに基づいてヒートマップを適用する"""
        if not dose_map:
            return

        # 0より大きい値のみを対象に最大・最小を計算
        flat_list = [val for row in dose_map for val in row if val > 0]
        if not flat_list:
            messagebox.showinfo("可視化情報", "線量データが全て0以下のため、ヒートマップは適用されません。")
            return

        max_dose = max(flat_list)
        min_dose = min(flat_list)

        if max_dose <= min_dose:
            return

        log_min = math.log10(min_dose)
        log_max = math.log10(max_dose)

        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                # 既にオブジェクトが配置されているマスは色を変えない
                if map_data[r][c] != 0:
                    continue

                dose = dose_map[r][c]

                if dose <= 0:
                    ratio = 0.0
                else:
                    # 対数スケールで色の比率を計算
                    ratio = (math.log10(dose) - log_min) / (log_max - log_min)

                ratio = max(0.0, min(1.0, ratio))  # 0.0-1.0の範囲に収める

                color_code = self.get_heatmap_color(ratio)
                self.update_cell_color(r, c, color_code)

        messagebox.showinfo("完了", f"線量マップを可視化しました。\\n最大: {max_dose:.2e}\\n最小: {min_dose:.2e}")

    def get_heatmap_color(self, ratio):
        """0.0(白) -> 0.5(黄) -> 1.0(赤)のカラースケールで色コードを返す"""
        if ratio < 0.5:
            # 白(1,1,1) -> 黄(1,1,0)
            r_val = 255
            g_val = 255
            b_val = int(255 * (1 - ratio * 2))
        else:
            # 黄(1,1,0) -> 赤(1,0,0)
            r_val = 255
            g_val = int(255 * (2 - ratio * 2))
            b_val = 0
        return f"#{r_val:02x}{g_val:02x}{b_val:02x}"

    def refresh_grid(self, map_data):
        """マップデータに基づいてグリッド表示を全て更新する"""
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                cell_id = map_data[r][c]
                # セルIDから対応する色を取得
                color = None
                for name, (cid, col) in CELL_TYPES.items():
                    if cid == cell_id:
                        color = col
                        break
                if color:
                    self.update_cell_color(r, c, color)

    def visualize_path(self, path, map_data):
        """指定された経路をマップ上に描画する"""
        for r, c in path:
            cell_id = map_data[r][c]
            # スタート、ゴール、中継、線源のマスは上書きしない
            if cell_id not in [0, 1]:
                continue
            self.update_cell_color(r, c, "magenta")
