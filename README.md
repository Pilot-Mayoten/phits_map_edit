# PHITS Map Editor

ローカルで線量マップを可視化し、PHITS環境定義ファイル（`env_input.inp`）を生成できる小さなGUIツールです。

**目的**
- マップ（グリッド）上で壁・線源・スタート／ゴール等を配置
- PHITS用の環境入力ファイルを出力
- PHITS出力（`deposit.out`）を読み込んで対数ヒートマップで可視化
- A* による経路探索（被ばく回避を重み付け可能）

**ファイル**
- `main.py` - アプリ本体（Tkinter GUI）

**前提 / 必要環境**
- Windows（動作確認済み）
- Python 3.8 以上（この環境では Python 3.13）
- `tkinter`（標準ライブラリ、通常はPythonに同梱）

備考: `tkinter` が無い場合は、公式の Python インストーラーで "tcl/tk and IDLE" を有効にして再インストールしてください。

**使い方（簡単）**
1. ターミナル（PowerShell）でプロジェクトルートへ移動:

```powershell
cd C:\programs\phits_map_edit
```

2. Python 実行コマンド（環境により `python` が使える場合はそちらで可）:

```powershell
# フルパス（この環境で確認された例）
C:/Users/user/AppData/Local/Programs/Python/Python313/python.exe main.py

# あるいはPATHにpythonが通っている場合
python main.py
```

3. GUI が立ち上がります。左のツールでタイルを選択してマップを編集し、ボタンでPHITS入力や線量マップ読み込み、A*探索を実行します。

**PHITS 出力の読み込み**
- PHITSで作った `deposit.out`（または `deposit_xy.out` を想定）を読み込むと、対数スケールで可視化します。
- 解析に失敗した場合、同ディレクトリに `debug_raw_values.txt` と `debug_matrix.csv` が出力され、数値読み取りの状況を確認できます。

**Git / 開発ワークフロー（簡易）**
- グローバルユーザー名／メールの確認:

```powershell
git config --global --get user.name
git config --global --get user.email
```

- このリポジトリのみで上書きしたい場合（ローカル設定）:

```powershell
git -C . config user.name "Your Name"
git -C . config user.email "you@example.com"
```

- 変更のステージ／コミット／push の基本:

```powershell
git add -A
git commit -m "説明的なメッセージ"
# リモートが設定済みであれば
git push origin master
```

注意: 初めて `git push` する場合はリモート（GitHub等）を設定し、認証（PAT/tokenやSSHキー）を行ってください。

**カスタム設定 / トラブルシュート**
- `python` が見つからない場合は、Python のフルパスを使うか、インストーラーで "Add Python to PATH" を有効にして再インストールしてください。
- `tkinter` の ImportError が出る場合は、Python 再インストールで tcl/tk を有効化してください。

**ライセンス / 貢献**
- 小規模ツールのためライセンスは指定されていません。用途に応じて `MIT` などを追加してください。
- バグ報告や改善案があれば Issue や Pull Request をお願いします。

---

作成日: 2025-11-22
