# config_loader.py

"""
設定ファイル (config.ini) を読み込み、アプリケーション全体で使用する設定値を管理するモジュール。
"""

import configparser
import os
from pathlib import Path

# デフォルト設定ファイルのパス
CONFIG_FILE_PATH = Path(__file__).parent / "config.ini"

class ConfigManager:
    """設定ファイルを管理するクラス。"""
    
    def __init__(self, config_file=CONFIG_FILE_PATH):
        """
        設定ファイルを読み込む。
        
        Args:
            config_file (Path): 設定ファイルのパス。
        """
        self.config = configparser.ConfigParser()
        
        # 設定ファイルが存在するか確認
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_file}")
        
        # 設定ファイルを読み込む
        self.config.read(config_file, encoding='utf-8')
    
    # --- PHITS関連の設定 ---
    
    def get_phits_command(self):
        """PHITSの実行コマンドを取得する。"""
        return self.config.get('PHITS', 'command', fallback='phits.bat')
    
    def get_default_maxcas(self):
        """デフォルトの maxcas 値を取得する。"""
        return self.config.getint('PHITS', 'default_maxcas', fallback=10000)
    
    def get_default_maxbch(self):
        """デフォルトの maxbch 値を取得する。"""
        return self.config.getint('PHITS', 'default_maxbch', fallback=10)
    
    # --- 環境設定 ---
    
    def get_default_nuclide(self):
        """デフォルトの核種を取得する。"""
        return self.config.get('Environment', 'default_nuclide', fallback='Cs-137')
    
    def get_default_activity(self):
        """デフォルトの放射能 (Bq) を取得する。"""
        return self.config.get('Environment', 'default_activity', fallback='1.0E+12')
    
    # --- 可視化設定 ---
    
    def get_font_directory(self):
        """フォントディレクトリを取得する。"""
        return self.config.get('Visualization', 'font_directory', fallback='C:/Windows/Fonts')
    
    def get_font_files(self):
        """優先フォントファイルのリストを取得する。"""
        font_files_str = self.config.get('Visualization', 'font_files', fallback='meiryo.ttc,msgothic.ttc,yugothb.ttc')
        return [f.strip() for f in font_files_str.split(',')]
    
    # --- ロギング設定 ---
    
    def get_log_directory(self):
        """ログファイルの出力先を取得する。"""
        return self.config.get('Logging', 'log_directory', fallback='logs')
    
    def get_log_prefix(self):
        """ログファイルの接頭辞を取得する。"""
        return self.config.get('Logging', 'log_prefix', fallback='phits_map_edit')
    
    # --- UI設定 ---
    
    def get_window_width(self):
        """ウィンドウ幅を取得する。"""
        return self.config.getint('UI', 'window_width', fallback=1600)
    
    def get_window_height(self):
        """ウィンドウ高さを取得する。"""
        return self.config.getint('UI', 'window_height', fallback=1080)
    
    def get_grid_width(self):
        """グリッドの幅を取得する。"""
        return self.config.getint('UI', 'grid_width', fallback=1050)
    
    def get_control_panel_width(self):
        """制御パネルの幅を取得する。"""
        return self.config.getint('UI', 'control_panel_width', fallback=300)
    
    # --- アプリケーション設定 ---
    
    def get_app_title(self):
        """アプリケーションタイトルを取得する。"""
        return self.config.get('Application', 'title', fallback='PHITS Map Editor & Route Planner')
    
    def get_app_version(self):
        """アプリケーションバージョンを取得する。"""
        return self.config.get('Application', 'version', fallback='1.0.0')


# グローバル設定マネージャーインスタンス
_config_manager = None

def get_config():
    """グローバル設定マネージャーを取得する（シングルトンパターン）。"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
