# APIサーバーのテストコード
import pytest
import yaml
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# テスト対象のコードをインポート
# モジュールレベルでのパッチが適用される前に、元のモジュールをインポートしておく
import llm_handler
from api_server import create_api_server

# --- Fixtures for Mocking Dependencies ---

@pytest.fixture(scope="function") # or just @pytest.fixture
def test_config():
    """
    テスト用の設定を読み込むFixture。
    関数スコープにすることで、各テストがクリーンな設定で開始され、
    テスト間での設定変更のリークを防ぐ。
    """
    with open("tests/test_config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@pytest.fixture(autouse=True)
def mock_other_dependencies():
    """
    テスト全体で使われる依存関係（設定以外）をモック化するFixture。
    設定のモックはconftest.pyで行われる。
    """
    # オブジェクトが使用される `api_server` モジュール内の `generate_response` をパッチする
    with patch('api_server.generate_response', new_callable=AsyncMock) as mock_generate_response, \
         patch('discord.Client') as mock_discord_client:

        mock_generate_response.return_value = "モックされたLLMの応答です。"

        mock_client_instance = MagicMock()
        mock_channel = AsyncMock()
        mock_channel.send = AsyncMock()
        mock_client_instance.get_channel.return_value = mock_channel
        mock_client_instance.loop = MagicMock()
        mock_client_instance.loop.create_task = MagicMock()

        # 依存関係を辞書としてyieldする
        yield {
            "mock_generate_response": mock_generate_response,
            "mock_discord_client": mock_client_instance,
            "mock_channel": mock_channel
        }


@pytest.fixture
def client(mock_other_dependencies):
    """
    モック化された依存関係を使ってFastAPIのTestClientをセットアップするFixture
    """
    # モック化されたDiscordクライアントインスタンスを取得
    mock_dc_client = mock_other_dependencies["mock_discord_client"]

    # FastAPIアプリケーションインスタンスを作成
    app = create_api_server(client=mock_dc_client)

    # TestClientを作成して返す
    with TestClient(app) as test_client:
        yield test_client

# --- Test Cases for /chat Endpoint ---

def test_chat_success(client, test_config):
    """/chatエンドポイントの正常系テスト"""
    # Arrange
    headers = {"X-API-Key": test_config["api_server"]["api_key"]}
    payload = {"message": "こんにちは"}

    # Act
    response = client.post("/chat", headers=headers, json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"response": "モックされたLLMの応答です。"}

def test_chat_invalid_api_key(client):
    """/chatエンドポイントのAPIキー不正テスト"""
    # Arrange
    headers = {"X-API-Key": "invalid-key"}
    payload = {"message": "こんにちは"}

    # Act
    response = client.post("/chat", headers=headers, json=payload)

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid API Key"}

def test_chat_llm_error(client, test_config, mock_other_dependencies):
    """/chatエンドポイントでLLMエラーが発生した場合のテスト"""
    # Arrange
    headers = {"X-API-Key": test_config["api_server"]["api_key"]}
    payload = {"message": "こんにちは"}

    # llm_handler.generate_responseが例外を発生するように設定
    mock_other_dependencies["mock_generate_response"].side_effect = Exception("LLM is down")

    # Act
    response = client.post("/chat", headers=headers, json=payload)

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "LLM is down"}

# --- Test Cases for /notify Endpoint ---

def test_notify_success(client, test_config, mock_other_dependencies):
    """/notifyエンドポイントの正常系テスト"""
    # Arrange
    headers = {"X-API-Key": test_config["api_server"]["api_key"]}
    payload = {"prompt": "サーバーメンテナンスのお知らせ", "channel_id": 987654321}
    mock_channel = mock_other_dependencies["mock_channel"]
    mock_discord_client = mock_other_dependencies["mock_discord_client"]

    # Act
    response = client.post("/notify", headers=headers, json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    mock_discord_client.get_channel.assert_called_once_with(987654321)
    mock_discord_client.loop.create_task.assert_called_once()
    mock_channel.send.assert_called_once_with("モックされたLLMの応答です。")

def test_notify_success_with_default_channel(client, test_config, mock_other_dependencies):
    """/notifyエンドポイントがデフォルトチャンネルIDを使用するかのテスト"""
    # Arrange
    headers = {"X-API-Key": test_config["api_server"]["api_key"]}
    payload = {"prompt": "デフォルトチャンネルへの通知"}
    default_channel_id = test_config["api_server"]["default_notify_channel_id"]
    mock_discord_client = mock_other_dependencies["mock_discord_client"]

    # Act
    response = client.post("/notify", headers=headers, json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    mock_discord_client.get_channel.assert_called_once_with(default_channel_id)

def test_notify_channel_not_found(client, test_config, mock_other_dependencies):
    """/notifyエンドポイントでチャンネルが見つからない場合のテスト"""
    # Arrange
    headers = {"X-API-Key": test_config["api_server"]["api_key"]}
    payload = {"prompt": "存在しないチャンネルへの通知", "channel_id": 111}
    mock_discord_client = mock_other_dependencies["mock_discord_client"]
    mock_discord_client.get_channel.return_value = None # チャンネルが見つからないように設定

    # Act
    response = client.post("/notify", headers=headers, json=payload)

    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_notify_channel_id_not_configured(client, test_config):
    """/notifyでチャンネルIDが未設定の場合のテスト"""
    # Arrange
    headers = {"X-API-Key": test_config["api_server"]["api_key"]}
    payload = {"prompt": "ID未設定通知"}

    # Act
    # api_serverモジュールでグローバル変数として読み込まれているDEFAULT_CHANNEL_IDを直接パッチする
    with patch("api_server.DEFAULT_CHANNEL_ID", None):
        response = client.post("/notify", headers=headers, json=payload)

    # Assert
    assert response.status_code == 400
    assert "Channel ID is not configured" in response.json()["detail"]
