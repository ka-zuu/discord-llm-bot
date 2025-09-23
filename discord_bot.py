
import discord
import re
import logging
from config import load_config
from llm_handler import generate_response

logger = logging.getLogger(__name__)
config = load_config()
bot_persona = config.get("bot_persona", {})
system_prompt = bot_persona.get("system_prompt", "あなたはAIアシスタントです。")

def create_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.info(f"{client.user.name}が起動しました")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        if not client.user.mentioned_in(message):
            return

        history = []
        # メンションを削除する正規表現
        mention_pattern = re.compile(f'<@!?{client.user.id}>')

        # リプライを遡って履歴を作成
        current_message = message
        for _ in range(5): # 最大5件まで遡る
            if current_message.reference and current_message.reference.message_id:
                try:
                    referenced_message = await message.channel.fetch_message(current_message.reference.message_id)
                    
                    clean_content = mention_pattern.sub(' ', referenced_message.content).strip()

                    if referenced_message.author == client.user:
                        history.insert(0, {"role": "assistant", "content": clean_content})
                    else:
                        history.insert(0, {"role": "user", "content": clean_content})
                        
                    current_message = referenced_message
                except discord.NotFound:
                    logger.warning(f"参照先のメッセージが見つかりませんでした: {current_message.reference.message_id}")
                    break
            else:
                break
        
        # 現在のメッセージを履歴に追加
        clean_content = mention_pattern.sub(' ', message.content).strip()
        history.append({"role": "user", "content": clean_content})

        try:
            logger.info(f"受信メッセージ: {message.author.name}: {clean_content}")
            logger.debug(f"送信履歴: {history}")
            async with message.channel.typing():
                response_text = await generate_response(history, system_prompt)
                logger.info(f"応答メッセージ: {response_text}")
                await message.reply(response_text)
        except Exception as e:
            logger.error(f"メッセージ処理中にエラーが発生しました: {e}", exc_info=True)
            await message.reply("申し訳ありません、処理中にエラーが発生しました。")

    return client
