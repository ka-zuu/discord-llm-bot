import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, AsyncMock, patch

# api_server.pyをインポートするために、プロジェクトのルートをパスに追加する必要がある場合があります。
# pytestは通常これを自動的に処理します。
from api_server import create_api_server


@pytest.fixture
def app():
    """
    テスト用のFastAPIアプリケーションインスタンスを作成するpytestフィクスチャ。
    APIキーやデフォルトチャンネルIDなどの設定値をパッチして、テストの独立性を保ちます。
    """
    with patch('api_server.API_KEY', 'test-secret-key'):
        with patch('api_server.DEFAULT_CHANNEL_ID', 12345):
            # /notifyエンドポイントが使用するdiscord.Clientのメソッドをモックします
            mock_client = MagicMock()
            mock_client.loop = MagicMock()
            mock_client.get_channel.return_value = AsyncMock()
            _app = create_api_server(mock_client)
            yield _app


@pytest.mark.asyncio
async def test_chat_unauthorized(app):
    """不正なAPIキーでのリクエストが拒否されることをテストします。"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/chat", json={"message": "hello"}, headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid API Key"}


@pytest.mark.asyncio
async def test_chat_success(app, monkeypatch):
    """正常なチャットリクエストをテストします。"""
    # LLMへの外部呼び出しをモックします
    mock_llm = AsyncMock(return_value="This is a test response.")
    monkeypatch.setattr("api_server.generate_response", mock_llm)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-API-Key": "test-secret-key"}
        )
        assert response.status_code == 200
        assert response.json() == {"response": "This is a test response."}
        mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_invalid_payload(app):
    """不正なペイロードでのリクエストがエラーになることをテストします。"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/chat",
            json={"wrong_field": "hello"},  # 'message' フィールドがありません
            headers={"X-API-Key": "test-secret-key"}
        )
        assert response.status_code == 422  # Unprocessable Entity
