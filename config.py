import yaml
import os

def load_config():
    """config.yamlを読み込み、辞書として返します。"""
    # スクリプト自身のディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # config.yamlへの絶対パスを構築
    config_path = os.path.join(script_dir, "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
