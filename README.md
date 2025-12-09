# PHITS Map Editor & Route Planner

PHITSを用いた放射線環境下でのロボット等の移動シミュレーションを支援するための、統合GUIアプリケーションです。

マップの視覚的な作成から、環境全体の線量マップ生成、被ばくを考慮した最適経路の探索、経路上の詳細な被ばく評価用ファイル生成、結果の可視化まで、一連のワークフローをシームレスに実行できます。

## 主な機能

-   **GUIによるマップ作成:** 壁や線源などの環境オブジェクトをグリッド上に直感的に配置。
-   **環境シミュレーションの自動実行:** 作成したマップに基づいて、PHITSによる空間全体の線量分布計算をGUIから直接実行。
-   **A\*アルゴリズムによる最適経路探索:** 環境線量マップを考慮し、移動距離と被ばく線量のバランスを取った最適経路を自動で探索。
-   **複数経路の管理:** スタート・ゴールは共通で、評価ステップ幅などが異なる複数の移動経路シナリオを定義・管理。
-   **詳細評価用ファイルの一括生成:** 定義した経路に沿って、ロボット（検出器）を模擬した多数のPHITS入力ファイルを一括で生成。
-   **PHITSの一括実行と結果プロット:** 生成された詳細評価用ファイルを一括で実行し、経路ごとの積算線量を自動でグラフ化。
-   **経路の2D可視化:** 定義した経路と線源の位置関係を2Dグラフで視覚的に確認。

## ファイル構成

コードは機能ごとにモジュール化されており、メンテナンス性と拡張性を高めています。

```
phits_map_edit/
├── main.py                     # アプリケーションの起動、各モジュールの統合
├── app_config.py               # マップサイズなどの共通設定値
├── map_editor_view.py          # マップエディタ部分のGUI
├── simulation_controls_view.py # シミュレーション制御部分のGUI
├── phits_handler.py            # PHITSの入出力ファイル関連の処理
├── route_calculator.py         # A*アルゴリズムや経路計算ロジック
├── visualizer.py               # Matplotlibによるグラフ描画処理
├── utils.py                    # 座標変換などの共通関数
├── template.inp                # 詳細評価用PHITS入力のテンプレート
└── README.md                   # このファイル
```

## 必要なもの

-   Windows OS
-   Python 3.8 以上
-   PHITS（別途インストールと、`phits.bat`への環境変数PATH設定が必要）
-   Pythonライブラリ:
    -   `tkinter` (Python標準ライブラリ)
    -   `matplotlib`

`matplotlib`は以下のコマンドでインストールできます。

```powershell
pip install matplotlib
```

## ワークフロー（使い方）

### ステップ1: マップの作成と環境シミュレーション

1.  アプリケーションを起動します (`python main.py`)。
2.  左側の**マップエディタ**を使い、壁、線源、スタート、ゴールなどを配置します。
3.  右側の**実行ステップ**パネルにある「**1. 環境入力を生成**」ボタンを押します。
    -   核種と放射能を入力するダイアログが表示されます。
    -   続いて、環境定義用のPHITS入力ファイル (`env_input.inp`など) の保存ダイアログが表示されます。
4.  ファイル保存後、「続けてPHITSシミュレーションを実行しますか？」という確認ダイアログが表示されます。
    -   「はい」を選択すると、**PHITSが自動で実行**され、空間の線量マップが計算されます。
    -   進捗は下部のログエリアで確認できます。
5.  シミュレーション完了後、「**2. 線量マップ読込**」ボタンを押し、先ほどPHITSで生成された`deposit_xy.out`を読み込みます。マップ上にヒートマップとして線量分布が表示されます。

### ステップ2: 評価したい経路の定義と最適経路探索

1.  右側の**経路の管理**パネルにある「**経路を追加**」ボタンを押し、評価したい経路をリストに追加します。
    -   この作業を繰り返すことで、複数の評価シナリオ（経路）をリストに登録できます。
2.  **経路リストから最適経路探索を適用したい経路を1つ選択**します。
3.  「**3. 最適経路を探索**」ボタンを押します。
    -   被ばく回避の重み係数と、評価点のステップ幅を入力すると、A*アルゴリズムが実行されます。
    -   成功すると、回避経路がマップ上に描画され、選択した経路にその情報が紐付けられます。

### ステップ3: 詳細評価の実行と結果確認

1.  「**4. 経路上の詳細線量評価**」ボタンを押します。
    -   `maxcas` と `maxbch` の値を入力するダイアログが表示されます。
    -   続いて、シミュレーションファイル一式を保存するための**親フォルダ**を選択するよう求められます。
2.  指定したフォルダ内に、経路リストの各項目に対応するサブフォルダ (`route_1`, `route_2`...) が作成され、その中に多数の詳細評価ファイル (`detailed_point_...inp`) が生成されます。
3.  「**5. PHITS実行と結果プロット**」ボタンを押します。
    -   先ほどファイルを保存した親フォルダ（または個別の`route_*`フォルダ）を選択します。
    -   PHITSが一括で実行され、完了すると自動でmatplotlibのウィンドウが起動し、各経路の積算線量プロファイルが表示されます。
4.  「**経路を2D表示**」ボタンを押すと、登録されている全経路の評価点と線源の位置関係を2Dで確認できます。

## `template.inp` について

このアプリケーションは、詳細評価用の入力ファイルを生成する際に `template.inp` というテンプレートファイルを利用します。このファイルには、移動するロボット（立方体）の形状や材質、`[Transform]`による移動定義、線量検出器の設定などが記述されています。

プログラムは、このテンプレートを読み込み、以下のプレースホルダを各評価点の具体的な値に置換して、多数の入力ファイルを生成します。

-   `{det_x}`, `{det_y}`, `{det_z}`: ロボット（検出器）の中心座標。
-   `{detector_cell_id}`: ロボットのセルID。
-   `{maxcas_value}`, `{maxbch_value}`: 計算回数など。

ロボットの形状（サイズや材質など）を変更したい場合は、この`template.inp`の`[Surface]`や`[Cell]`、`[Material]`セクションを直接編集してください。

## 開発者向け情報

このプロジェクトへの貢献や、複数PCでの開発を行う方向けの情報です。

### Gitによるバージョン管理

ソースコードはGitで管理されています。リモートリポジトリはGitHubにあります。

-   **リポジトリのクローン (SSH):**
    ```powershell
    git clone git@github.com:Pilot-Mayoten/phits_map_edit.git
    cd phits_map_edit
    ```

### SSHキーの設定

GitHubへの安全なアクセスのため、SSHキーの設定を推奨します。

1.  **SSHキーの生成:**
    ```powershell
    ssh-keygen -t ed25519 -C "your_email@example.com"
    ```
    -   途中でパスフレーズの入力を求められますが、空のままEnterでも構いません。
2.  **ssh-agentへの登録:**
    ```powershell
    Get-Service -Name ssh-agent | Set-Service -StartupType Manual
    Start-Service ssh-agent
    ssh-add ~/.ssh/id_ed25519
    ```
3.  **公開鍵のコピー:**
    ```powershell
    Get-Content ~/.ssh/id_ed25519.pub | Set-Clipboard
    ```
4.  **GitHubへの登録:**
    -   [GitHubのSSH Keys設定ページ](https://github.com/settings/keys)にアクセスします。
    -   `New SSH key` ボタンを押し、Titleを適当に設定し、Keyフィールドにクリップボードの内容を貼り付けます。
5.  **接続テスト:**
    ```powershell
    ssh -T git@github.com
    ```
    -   `Hi (username)! You've successfully authenticated...` と表示されれば成功です。
    # HTTPSを利用する場合
    git clone https://github.com/Pilot-Mayoten/phits_map_edit.git

    # SSHを利用する場合 (推奨、後述の設定が必要)
    git clone git@github.com:Pilot-Mayoten/phits_map_edit.git
    ```

-   **変更内容のプッシュ (リモートへ保存):**
    ```powershell
    git add .
    git commit -m "変更内容の要約"
    git push
    ```

-   **最新内容のプル (リモートから取得):**
    ```powershell
    git pull
    ```

### SSHキーの設定 (推奨)

複数PCで開発を行う場合や、毎回パスワードを入力する手間を省くために、SSHキーによる認証を推奨します。

1.  **SSHキーの生成:**
    PowerShellを開き、以下のコマンドを実行します。`your_email@example.com`はご自身のメールアドレスに置き換えてください。
    ```powershell
    ssh-keygen -t ed25519 -C "your_email@example.com"
    ```
    -   保存先やパスフレーズを聞かれますが、基本的にEnterキーを押していけば完了します。

2.  **公開鍵のコピー:**
    生成した公開鍵 (`id_ed25519.pub`) の内容をクリップボードにコピーします。
    ```powershell
    Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard
    ```

3.  **GitHubへの登録:**
    -   [GitHubのSSHキー設定ページ](https://github.com/settings/keys)にアクセスします。
    -   `New SSH key` ボタンを押し、`Title`にPCの名前など分かりやすい名前を、`Key`にコピーした公開鍵を貼り付けて保存します。

4.  **リモートURLの切り替え:**
    既存のリポジトリでHTTPSからSSHに切り替える場合は、以下のコマンドを実行します。
    ```powershell
    git remote set-url origin git@github.com:Pilot-Mayoten/phits_map_edit.git
    ```

5.  **接続テスト:**
    ```powershell
    ssh -T git@github.com
    ```
    -   `Hi Pilot-Mayoten! You've successfully authenticated...` というメッセージが表示されれば成功です。
