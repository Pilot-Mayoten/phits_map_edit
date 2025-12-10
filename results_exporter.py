# results_exporter.py

"""
シミュレーション結果をCSV形式でエクスポートする機能を提供するモジュール。
"""

import csv
import io

def generate_results_csv(results, routes):
    """
    シミュレーション結果と経路情報を受け取り、CSV形式の文字列を生成する。

    Args:
        results (dict): シミュレーション結果の辞書。
                        キーは 'route_1', 'route_2' など。
        routes (list): アプリケーションが管理する経路情報のリスト。

    Returns:
        str: CSV形式のデータ文字列。
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # --- ヘッダー行を書き込み ---
    writer.writerow([
        "Route Name",
        "Route Color",
        "Point Index",
        "Distance (cm)",
        "Dose (Gy/source)"
    ])

    # --- データ行を書き込み ---
    # 結果をルート名でソートして処理
    for route_name, result_data in sorted(results.items()):
        doses = result_data.get("doses", [])
        
        # 'route_1' のような名前からインデックス (0) を取得
        try:
            route_index = int(route_name.split('_')[-1]) - 1
            route_info = routes[route_index]
            route_color = route_info.get('color', 'N/A')
            step_width = route_info.get('step_width', 0)
        except (ValueError, IndexError):
            route_info = None
            route_color = 'N/A'
            step_width = 0

        if not doses:
            continue

        # 各評価点のデータを出力
        for i, dose in enumerate(doses):
            distance = i * step_width
            writer.writerow([
                route_name,
                route_color,
                i + 1,
                f"{distance:.2f}",
                f"{dose:.6e}"
            ])

    return output.getvalue()
