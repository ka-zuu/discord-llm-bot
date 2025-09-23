
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
import discord
import logging
from pydantic import BaseModel
from config import load_config
from llm_handler import generate_response

logger = logging.getLogger(__name__)
config = load_config()
api_config = config.get("api_server", {})
API_KEY = api_config.get("api_key", "YOUR_SECRET_API_KEY")
DEFAULT_CHANNEL_ID = api_config.get("default_notify_channel_id")

api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        logger.warning(f"不正なAPIキーが使用されました: {api_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

class ChatRequest(BaseModel):
    message: str

class NotifyRequest(BaseModel):
    prompt: str
    channel_id: int | None = None

def create_api_server(client: discord.Client):
    app = FastAPI()

    @app.post("/chat", dependencies=[Depends(get_api_key)])
    async def chat(request: ChatRequest):
        logger.info(f"/chatエンドポイントへのリクエスト: {request.message}")
        system_prompt = config.get("bot_persona", {}).get("system_prompt", "")
        history = [{"role": "user", "content": request.message}]
        try:
            response = await generate_response(history, system_prompt)
            logger.info(f"/chatエンドポイントからのレスポンス: {response}")
            return {"response": response}
        except Exception as e:
            logger.error(f"/chatエンドポイントでエラーが発生しました: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/notify", dependencies=[Depends(get_api_key)])
    async def notify(request: NotifyRequest):
        logger.info(f"/notifyエンドポイントへのリクエスト: {request.prompt}")
        system_prompt = "あなたは通知アシスタントです。以下の情報を基に、簡潔で分かりやすい通知メッセージを作成してください。"
        history = [{"role": "user", "content": request.prompt}]
        
        try:
            notification_message = await generate_response(history, system_prompt)
            
            channel_id = request.channel_id if request.channel_id else DEFAULT_CHANNEL_ID
            if not channel_id:
                logger.error("通知チャンネルIDが設定されていません。")
                raise HTTPException(status_code=400, detail="Channel ID is not configured")

            channel = client.get_channel(channel_id)
            if not channel:
                logger.error(f"チャンネルが見つかりません: {channel_id}")
                raise HTTPException(status_code=404, detail=f"Channel with ID {channel_id} not found")

            await channel.send(notification_message)
            logger.info(f"チャンネルID {channel_id} に通知を送信しました。")
            return {"status": "ok", "message": "通知を送信しました"}
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"/notifyエンドポイントでエラーが発生しました: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
            
    return app
