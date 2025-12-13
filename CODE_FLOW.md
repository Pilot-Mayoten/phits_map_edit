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

---

## A*アルゴリズムの解説と本プロジェクトでの適用

以下は一般的なA*アルゴリズムの概要と、本プロジェクト（グリッド上の被ばくを考慮した経路探索）への具体的な適用方法についての解説です。実装やチューニングの指針、どのファイルを編集すれば振る舞いを変えられるかも併せて記載します。

- **A* の基本（一般論）**
  - 目的: 始点から終点までの最短（最小コスト）経路を効率的に求める。Dijkstra の最適性を保ちつつ、探索を絞るためにヒューリスティック関数を使う。
  - 評価関数 f(n) = g(n) + h(n)
    - g(n): 始点からノード n までにかかった実コスト（既知）
    - h(n): ノード n からゴールまでの推定コスト（ヒューリスティック、例えばユークリッド距離やマンハッタン距離）
  - ヒューリスティックは一貫性（consistent, monotone）かつ過小評価（admissible）であれば最短経路が保証される。

- **典型的な疑似コード（要点）**
  - openSet（優先度付きキュー、f値でソート）と closedSet を用意
  - openSet に start を入れる（g(start)=0）
  - openSet が空でない間:
    - 現在ノード = openSet.pop()（最小 f）
    - もし現在ノードが goal なら経路復元して終了
    - 隣接ノードに対して tentative_g = g(current) + cost(current, neighbor) を計算
    - tentative_g が neighbor の既存 g より小さければ更新して openSet に追加/優先度更新

- **本プロジェクトでの具体的適用（ポイント）**
  - 探索空間: マップは格子（グリッド）として扱われます。各セルには壁/通行可/線源/被ばく値などの情報がある想定です。
  - ノード: グリッドのセル中央（もしくはステップ幅に応じたサンプリング点）がノードになります。`step`（ステップ幅）を大きくするとノード数が減り計算が速く、細かい経路は失われます。
  - 隣接性: 4方向（上下左右）または8方向（斜め含む）移動を採用できます。斜め移動を採用する場合はコストに sqrt(2) を乗じる等の補正を行ってください。
  - コスト関数の設計:
    - 「距離コスト（移動距離）」と「被ばくコスト（そのセルで被ばくする値）」を組み合わせます。
    - 例: cost(current, neighbor) = distance(current, neighbor) + w * exposure(neighbor)
      - `w` は被ばくの重み（ユーザが設定する係数）。`w=0` とすれば純粋な最短経路探索に、`w>0` で被ばく回避を考慮した経路になる。
    - exposure(neighbor) は環境線量マップ上の値（`deposit_xy.out` を読み込んで得たグリッド値）を使います。必要に応じて正規化（例: max で割る）してから加算することで、距離と被ばくのスケールを揃えるとチューニングしやすいです。
  - ヒューリスティック (h): ゴールまでの最短直線距離（ユークリッド距離）を用いるのが一般的です。これが過小評価になるため、最適性が保たれます。

- **実装上の注意 / 実用的チューニング**
  - 被ばく値のスケーリング: exposure のスケールが距離コストに比べて大きすぎると経路が過剰に回避的になります。`w` と exposure の正規化の組合せで調整してください。
  - ステップ幅 (`step`) の選択: 小さいほど精密だが計算費用が高い。詳細評価用の PHITS 入力点はこのステップ幅に従って配置されるため、PHITS の実行数にも影響します。
  - 障害物（壁）の扱い: 壁セルは移動不可能（ノード除外）にします。斜め移動を許可する場合、隣接2セルが壁である対角移動を禁止する等の処理を入れると破綻を防げます。
  - 経路のスムージング: A* は格子の特性でギザギザした経路を生成することがあるため、必要ならポスト処理でスムージング（経路上の冗長点削除や線分近似）を行ってください。

- **このプロジェクトで変更すべきファイルとパラメータ**
  - `route_calculator.py`
    - A* の本体実装があります。`find_path(start, goal, map, step, weight, heuristic)` のような関数を探し、`cost` と `h` の実装を編集してください。
    - exposure（線量）を取得する箇所は、`map` 引数が線量グリッドを含む構造になっている想定です。必要なら `map` の仕様（キー名や正規化の有無）を合わせてください。
  - `simulation_controls_view.py` / `main.py`
    - ユーザが被ばくの重み（`w`）やステップ幅（`step`）を変更できる UI を提供しています。UI側で取得した値を `route_calculator` に渡す部分を確認・変更してください。
  - `map_editor_view.py` / `phits_handler.py`
    - `deposit_xy.out` を読み込むパーサ（`phits_handler.extract_dose_from_deposit`）の出力形式に応じて、`route_calculator` が参照するグリッド配列の向きやインデックスが一致するよう注意してください（行列の行列転置や座標系差に注意）。

- **簡単な調整例（擬似コード）**
  - cost の例:

```text
function cost(current, neighbor):
    d = distance(current, neighbor)          # 例: 1 (隣接) または sqrt(2) (斜め)
    e = exposure_grid[neighbor.y][neighbor.x] # 事前に読み込んだ線量値
    e_norm = e / exposure_max                # 正規化
    return d + weight * e_norm
```

  - ヒューリスティック:

```text
h(n) = euclidean_distance(n, goal)
```

- **デバッグのヒント（A*関連）**
  - 小さなマップや簡単な障害物配置で `w=0`（純粋最短） と `w>0` を比較して、被ばく回避の効果を視覚的に確認してください。
  - ノード数や openSet のサイズをログ出力すると、計算負荷の傾向が掴みやすいです。
  - 経路が異常に長くなる場合、exposure のスケールか weight の値が大きすぎる可能性があります。正規化や重みを見直してください。

---

上記を `CODE_FLOW.md` に追記しました。さらに、具体的な `route_calculator.py` の関数定義やパラメータ名を私が直接読んで、該当箇所に合わせた微修正／サンプルコードを入れてほしい場合は、その旨を指示してください。次にこの変更をコミットして push します。