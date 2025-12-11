# Code Flow / 関数呼び出しフロー

このドキュメントは、アプリケーションの主要な操作と、それに対応するGUIボタンからコア関数までの呼び出し関係（コールグラフ）を短くまとめたものです。開発者がどの関数を編集すれば特定の振る舞いを変えられるかを素早く把握できるように作成しています。

※ ファイルパスはリポジトリのルート（`main.py` と同じ階層）を基準としています。

---

## 高レベルワークフロー（ユーザー操作 → コード）

- GUI起動
  - `python main.py` を実行すると `main.py` が GUI を初期化し、各ビュー（`map_editor_view.py`、`simulation_controls_view.py`）を作成して相互にイベントを接続します。

- 1. 環境入力を生成（ボタン）
  - GUI: `simulation_controls_view.py` のボタン "1. 環境入力を生成" が押される。
  - main: `main.py` の `generate_env_map()` が呼ばれる。
  - 振る舞い:
    - マップデータを `map_editor_view` から取得
    - 核種／放射能の入力ダイアログを表示
    - `phits_handler.generate_environment_input_file(map_data, nuclide, activity)` を呼び出して `env_input.inp`（等）を生成。戻り値として保存パスを返す。
    - 保存後に「PHITSを自動実行しますか？」を確認し、許可されれば `run_env_simulation_threaded(inp_path)` を呼ぶ（バックグラウンド実行）。
  - 生成物:
    - 例: `env_input.inp`（保存先はユーザが選択）
    - 期待されるPHITS出力: `deposit_xy.out`（`phits_handler` 側のテンプレートに基づく）

- 2. 線量マップ読込（ボタン）
  - GUI: ユーザが `deposit_xy.out` を選択して読み込む。
  - main: 結果を読み込む処理で `phits_handler.extract_dose_from_deposit(run_dir)`（または同等のパーサ）を用いて、グリッド形式の線量データを取り出し `visualizer` に渡して表示する。

- 3. 最適経路を探索（ボタン）
  - GUI: `simulation_controls_view.py` の "3. 最適経路を探索" ボタン。
  - main: `main.py` の `run_route_planning()`（あるいは類似のメソッド）を経由して `route_calculator.py` の A* 実装を呼び出す。
  - 振る舞い:
    - 選択した経路設定（ステップ幅、重みなど）をもとに A* を実行し、結果を `map_editor_view` に描画する。

- 4. 経路上の詳細線量評価（ボタン）
  - GUI: "4. 経路上の詳細線量評価" ボタンが押される。
  - main: `main.py` の `run_detailed_simulation()` が呼ばれる。
  - 振る舞い:
    - `maxcas` / `maxbch` をダイアログで入力（デフォルトあり）
    - 保存先の親フォルダを選択
    - `phits_handler.generate_detailed_simulation_files(routes, output_dir, default_maxcas, default_maxbch)` を呼び、各評価点に対する `detailed_point_...inp` を `route_X/` サブフォルダに生成する。
    - 生成時、内部で `AdvancedPhitsMerger` を利用して `env_input.inp` と `template.inp` をマージし、重複IDのリナンバリングや参照書き換えを行う。
    - ここで、Airセルに検出器（ロボット）セルを重複させないために、検出器セルIDを Air セルの除外リスト（例 `#1001`）として追記する処理が行われる。

- 5. PHITS実行と結果プロット（ボタン）
  - GUI: "5. PHITS実行と結果プロット" ボタン。
  - main: `main.py` の `run_phits_and_plot_threaded()`（バックグラウンド）を走らせ、内部で `run_phits_and_plot_worker()` が各 `route_*` フォルダを巡回する。
  - 振る舞い:
    - 各詳細入力 (`*.inp`) に対して `phits_handler.execute_phits_simulation(inp_path, phits_command, expected_output)` を呼ぶ。
    - 実行完了後、`phits_handler.extract_dose_from_deposit(run_dir)` で各点の被ばくデータを抽出し、経路ごとの積算線量を算出する。
    - 結果は `result_queue` 経由でメインスレッドに渡され、`main.process_result_queue()` により受け取り、`visualizer.plot_dose_profile(results, routes)` を呼んでグラフ表示する。
    - また、`results_exporter.generate_results_csv(results, outpath)`（存在する場合）を呼んでCSV出力できる。

---

## 主要モジュールと関数（開発者向けショートリファレンス）

- `main.py`
  - `generate_env_map()`
    - マップ情報を集め、核種/活動量ダイアログを表示し、`phits_handler.generate_environment_input_file()` を呼ぶ。
  - `run_env_simulation_threaded(inp_path)` / `run_env_simulation_worker(inp_path)`
    - 環境入力ファイルをPHITSで実行し、出力ファイル（例: `deposit_xy.out`）の有無をチェック。
  - `run_detailed_simulation()`
    - `maxcas`/`maxbch` ダイアログを表示し、親フォルダ選択 → `phits_handler.generate_detailed_simulation_files()` を呼ぶ。
  - `run_phits_and_plot_threaded()` / `run_phits_and_plot_worker()`
    - 複数経路の詳細入力を順次実行、結果を集約して `visualizer` に渡す。
  - `process_result_queue()`
    - ワーカースレッドからの結果を受信してGUIへ反映する。

- `phits_handler.py`
  - `generate_environment_input_file(map_data, nuclide, activity)`
    - 環境用PHITS入力を生成し、保存パスを返す（例: `env_input.inp`）。テンプレート内の出力ファイル名（`file =` 指定）と `execute_phits_simulation()` の `expected_output` を整合させること。
  - `AdvancedPhitsMerger` クラス
    - `merge(base_env_path, template_path, out_path, ...)`
    - IDのリナンバリング、参照の書換え、さらにAirセルから検出器セルIDを除外するための追記ロジックがある（衝突防止の重要箇所）。
  - `generate_detailed_simulation_files(routes, output_dir, default_maxcas, default_maxbch)`
    - 各評価点について `template.inp` のプレースホルダを置換して `detailed_point_*.inp` を生成する。
  - `execute_phits_simulation(inp_path, phits_command='phits.bat', expected_output='deposit.out')`
    - 指定のコマンドでPHITSを実行し、実行終了後に `expected_output` の存在をチェックする。テンプレートに合わせて `expected_output` を `deposit_xy.out` 等に設定すること。
  - `extract_dose_from_deposit(run_dir)`
    - `deposit_xy.out` や `deposit.out` を解析して、格子ごとの線量値や積算値を取り出す。

- `simulation_controls_view.py`
  - GUI のボタン・Treeview を定義。ユーザー操作を main.py のコールバックへ繋ぐ。
  - `get_phits_command()` を使って実行するPHITSコマンドを取得する（デフォルト `phits.bat`）。

- `visualizer.py`
  - `plot_map(...)` / `plot_routes(...)` / `plot_dose_profile(results, routes)`
  - 受け取ったデータを matplotlib で可視化する。経路ごとの色は GUI が割り当てた色を使用する。

- `route_calculator.py`
  - A* 実装。`find_path(start, goal, map, step)` のような関数があり、線量マップと重み係数を使って経路を返す。

- `results_exporter.py`（参照されているが未確認の場合あり）
  - `generate_results_csv(results, outpath)` などの関数を提供し、プロット結果をCSVに保存する。

---

## 重要なファイル名とテンプレートプレースホルダ

- 環境入力ファイル: `env_input.inp`（ユーザが保存するファイル名）
- 環境出力（PHITS）: `deposit_xy.out`（`template.inp` の `[T-Deposit]` セクションに応じる）
- 詳細評価テンプレート: `template.inp`
  - プレースホルダ例: `{det_x}`, `{det_y}`, `{det_z}`, `{detector_cell_id}`, `{maxcas_value}`, `{maxbch_value}`
- 生成される詳細入力: `route_1/detailed_point_0001.inp` など

---

## どこを編集すれば良いか（代表例）

- PHITS 実行コマンドを変えたい: `simulation_controls_view.py::get_phits_command()` と `main.py` のワーカー呼び出し部で渡すコマンドを変更する。
- 出力ファイル名を変更したい: `phits_handler.generate_environment_input_file()` でテンプレート中の `file = ...` 行を変更し、`phits_handler.execute_phits_simulation()` の `expected_output` 引数と一致させる。
- Airセルから検出器を明示的に除外する処理を変更したい: `phits_handler.py` の `AdvancedPhitsMerger.merge()` を編集する（コメントで理由が付与されているはず）。
- 詳細テンプレートの値置換ロジックを変えたい: `phits_handler.generate_detailed_simulation_files()` を編集する。

---

## デバッグのヒント

- PHITS 実行後に "出力ファイルが見つからない" エラーが出る場合は、まずテンプレート内の `file =` の値と `execute_phits_simulation()` に渡している `expected_output` が一致しているか確認してください。
- マージ後のPHITS入力が正しく動作しない場合は、`AdvancedPhitsMerger` の生成したファイルを手動でPHITSに与えて、PHITSの標準出力/エラーログを確認してください。

---

このファイルは将来的に自動生成（静的解析で関数を辿る）することもできますが、現時点では手作業で主要フローとポイントをまとめています。追加で「関数ごとの詳細な引数一覧」「シーケンス図」等が必要でしたら作成します。