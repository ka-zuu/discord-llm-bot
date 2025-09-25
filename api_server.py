
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
import discord
import logging
import asyncio
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

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Log request headers and raw body when Pydantic validation fails (HTTP 422).

        WARNING: This will log request bodies including potentially sensitive values
        such as API keys. In production consider masking or limiting this logging.
        """
        try:
            raw = await request.body()
            body_text = raw.decode("utf-8", errors="replace")
        except Exception as e:
            body_text = f"<could not read body: {e}>"

        # Collect headers and mask API key if present
        hdrs = dict(request.headers)
        api_key_header = None
        for k in list(hdrs.keys()):
            if k.lower() == "x-api-key":
                api_key_header = k
                break
        if api_key_header:
            hdrs[api_key_header] = "***MASKED***"

        logger.error(f"Request validation error: {exc.errors()}, headers={hdrs}, body={body_text}")
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

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
        persona_prompt = config.get("bot_persona", {}).get("system_prompt", "")
        task_instruction = "以下の情報のみを使用して、通知メッセージの本文だけを生成してください。他のテキスト（挨拶、追加の解説など）は一切含めないでください。"
        system_prompt = f"{persona_prompt}\n\n{task_instruction}"
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

            # discord.pyのAPI呼び出しは、FastAPIのイベントループから直接行うのではなく、
            # clientのイベントループで実行するようにスケジュールする必要があります。
            # これにより、スレッドセーフティとループ間の競合が保証されます。
            asyncio.run_coroutine_threadsafe(channel.send(notification_message), client.loop)
            logger.info(f"チャンネルID {channel_id} への通知をスケジュールしました。")
            return {"status": "ok", "message": "通知をスケジュールしました"}
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"/notifyエンドポイントでエラーが発生しました: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
            
    return app
