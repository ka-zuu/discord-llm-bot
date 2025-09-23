import pytest
import yaml
from unittest.mock import patch

# グローバルなパッチを管理するための変数
config_patcher = None

def pytest_configure(config):
    """
    pytestのテストセッション開始時に呼び出されるフック。
    テスト収集が始まる前に、import時にファイルI/Oを行うモジュールのための
    グローバルなパッチを設定します。
    """
    global config_patcher

    # conftest.pyからの相対パスで設定ファイルを読み込む
    from pathlib import Path
    config_path = Path(__file__).parent / "test_config.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        test_config_data = yaml.safe_load(f)

    # config.load_config をモックするパッチを開始
    config_patcher = patch('config.load_config', return_value=test_config_data)
    config_patcher.start()

    # llm_handler モジュールは import 時に genai.configure を呼び出すため、
    # それもモックしておく必要がある
    patch('google.generativeai.configure').start()


def pytest_unconfigure(config):
    """
    pytestのテストセッション終了時に呼び出されるフック。
    設定したグローバルなパッチを停止します。
    """
    global config_patcher
    if config_patcher:
        config_patcher.stop()
        config_patcher = None

    # configureのパッチも停止
    patch.stopall()
