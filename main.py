import asyncio
import logging
import threading
import uvicorn
from config import load_config
from discord_bot import create_bot
from api_server import create_api_server

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_api_server(app, host, port):
    uvicorn.run(app, host=host, port=port)

async def main():
    # 設定の読み込み
    config = load_config()
    discord_token = config.get("discord_token")
    api_config = config.get("api_server", {})
    api_host = api_config.get("host", "0.0.0.0")
    api_port = api_config.get("port", 8080)

    if not discord_token or discord_token == "YOUR_DISCORD_BOT_TOKEN":
        logger.error("Discordボットのトークンが設定されていません。config.yamlを確認してください。")
        return

    # Discordボットのクライアントを作成
    discord_client = create_bot()

    # FastAPIアプリケーションを作成
    api_app = create_api_server(discord_client)
    
    # Uvicornサーバーを別スレッドで実行
    api_thread = threading.Thread(
        target=run_api_server, 
        args=(api_app, api_host, api_port),
        daemon=True
    )
    api_thread.start()
    logger.info(f"APIサーバーを {api_host}:{api_port} で起動します。")

    # Discordボットを実行
    try:
        await discord_client.start(discord_token)
    except KeyboardInterrupt:
        logger.info("アプリケーションを終了します。")
        await discord_client.close()

if __name__ == "__main__":
    asyncio.run(main())
