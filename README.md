# PHITS Map Editor & Route Planner

PHITSを用いた放射線環境下でのロボット等の移動シミュレーションを支援する統合GUIアプリケーションです。

## 主な特徴

- 直感的なGUIでマップ（壁・線源・スタート・ゴール等）を作成
- マップの保存・読み込み（JSON形式）
- PHITSによる線量マップ自動生成・読込
- A\*アルゴリズムによる最適経路探索（被ばく回避重み付け可）
- 複数経路の管理・比較（各経路ごとに重み・ステップ幅・合計線量を表示）
- 経路ごとの詳細線量評価ファイル一括生成
- PHITS一括実行・経路ごとの積算線量プロファイル自動グラフ化
- 2D経路・障害物・線源の可視化（マップ縮尺に忠実なグリッド表示）
- 結果のCSV出力・Excel連携

## 必要環境

- Windows OS
- Python 3.10 以上（推奨: 3.13）
- PHITS（別途インストールし、`phits.bat`をPATHに追加）
- Pythonライブラリ: `tkinter`（標準）、`matplotlib`、`numpy`

## セットアップ

1. プロジェクト直下で仮想環境を作成し、必要なライブラリをインストール

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install matplotlib numpy
    ```

2. PHITSの`phits.bat`がPATHに通っていることを確認

## 起動方法

- PowerShell: `./run.ps1`
- コマンドプロンプト: `run.bat`

> これらのスクリプトはTcl/Tkのパスを自動設定し、仮想環境のPythonで`main.py`を実行します。

## 使い方ワークフロー

1. **マップ作成**: GUIで壁・線源・スタート・ゴール等を配置。必要に応じて「マップを保存」「マップを読込」
2. **環境入力生成・線量マップ作成**: 「1. 環境入力を生成」→「続けてPHITSシミュレーション」→「2. 線量マップ読込」
3. **経路追加・最適化**: 「経路を追加」→リストから選択→「3. 最適経路を探索」
4. **詳細評価・結果確認**: 「4. 経路上の詳細線量評価」→「5. PHITS実行と結果プロット」
5. **プロファイル・2D表示・CSV出力**: 経路選択→「線量プロファイルを表示」「経路を2D表示」「結果をExcelで開く」

## 設定ファイル（config.ini）

アプリ全体のUIサイズやPHITSコマンド、フォント設定などを`config.ini`で管理できます。

```ini
[UI]
window_width = 1600
window_height = 1080
grid_width = 1050
control_panel_width = 300

[PHITS]
command = phits.bat
default_maxcas = 10000
default_maxbch = 10

[Visualization]
font_directory = C:/Windows/Fonts
font_files = meiryo.ttc,msgothic.ttc,yugothb.ttc
```

## テンプレートファイル（template.inp）

詳細評価用PHITS入力ファイルのテンプレート。ロボット形状や検出器設定を編集可能。

---

ご質問・不具合報告はGitHubのIssueまたはリポジトリ管理者まで。
