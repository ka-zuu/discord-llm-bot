import yaml

def load_config():
    """config.yamlを読み込み、辞書として返します。"""
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
