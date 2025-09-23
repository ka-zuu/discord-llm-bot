import logging
import google.generativeai as genai
from config import load_config

logger = logging.getLogger(__name__)
config = load_config()

# 設定ファイルからAPIキーを設定
api_key = config.get("gemini_api_key")
if not api_key:
    logger.error("gemini_api_keyが設定ファイルに設定されていません。")
    raise ValueError("gemini_api_keyが設定ファイルに設定されていません。")

genai.configure(api_key=api_key)

# GenerativeModelのインスタンスをキャッシュするための辞書
_model_cache = {}

def get_model(model_name: str, system_prompt: str) -> genai.GenerativeModel:
    """
    モデル名とシステムプロンプトに基づいて、キャッシュされたGenerativeModelインスタンスを取得します。
    キャッシュにない場合は新しいインスタンスを作成してキャッシュに追加します。
    """
    cache_key = (model_name, system_prompt)
    if cache_key not in _model_cache:
        logger.info(f"新しいGenerativeModelインスタンスを作成します: model={model_name}")
        _model_cache[cache_key] = genai.GenerativeModel(
            model_name, system_instruction=system_prompt
        )
    return _model_cache[cache_key]

async def generate_response(history: list, system_prompt: str) -> str:
    """
    LLMモデルを使用して、会話履歴とシステムプロンプトに基づいた応答を生成します。

    Args:
        history: 会話履歴のリスト。形式: [{'role': 'user' or 'assistant', 'content': '...'}, ...]
        system_prompt: ボットのペルソナを定義するシステムプロンプト。

    Returns:
        LLMによって生成された応答テキスト。
    """
    model_name = config.get("bot_persona", {}).get("model", "gemini-1.5-flash-latest")
    model = get_model(model_name, system_prompt)

    # APIが期待する形式に会話履歴を変換
    api_history = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else msg["role"]
        api_history.append({"role": role, "parts": [{"text": msg["content"]}]})

    try:
        if not api_history:
            logger.warning("会話履歴が空の状態でgenerate_responseが呼ばれました。")
            return "エラー: 会話履歴が空です。"
        
        response = await model.generate_content_async(api_history)
        return response.text
    except Exception as e:
        logger.error(f"LLM APIエラー: {e}", exc_info=True)
        return "申し訳ありません、応答の生成中にエラーが発生しました。"