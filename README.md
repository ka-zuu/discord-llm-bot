
# Discord LLM Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)

Gemini APIと連携して動作する、多機能なDiscordボットです。

自然な対話機能、設定ファイルによるキャラクター付け、そして外部アプリケーションとの連携を可能にするAPIサーバー機能を備えています。

## ✨ 主な機能

- **🤖 LLM連携による対話**: Discord上でボットにメンションすると、文脈を考慮した自然な返信を生成します。
- **📚 会話履歴の認識**: メッセージへの返信（リプライ）にメンションを付けると、過去のやり取りを最大5件まで遡って文脈を把握し、応答します。
- **🎭 動的なキャラクター設定**: `config.yaml` ファイルを編集するだけで、ボットの口調や役割（ペルソナ）を自由に変更できます。
- **🔌 外部連携API**: `FastAPI`で構築されたAPIサーバーを内蔵。他のスクリプトやアプリケーションから、Discordへの通知送信やLLMとの対話が可能です。

---

## 🛠️ 動作環境

- Python 3.11以上

## 📦 セットアップ

1.  **リポジトリをクローンします:**
    ```bash
    git clone https://github.com/your-username/discord-llm-bot.git
    cd discord-llm-bot
    ```

2.  **必要なライブラリをインストールします:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **設定ファイルを作成します:**
    `config.yaml.example` をコピーして `config.yaml` を作成します。
    ```bash
    cp config.yaml.example config.yaml
    ```

4.  **`config.yaml` を編集します:**
    - `discord_token`: あなたのDiscordボットのトークンを設定します。
    - `api_key`: APIサーバーの認証に使用する任意のシークレットキーを設定します。
    - `default_notify_channel_id`: `/notify` APIのデフォルト通知先チャンネルIDを設定します。
    - `bot_persona`: ボットのキャラクター設定をお好みに合わせて変更します。

5.  **環境変数を設定します:**
    Gemini APIのAPIキーを環境変数 `GEMINI_API_KEY` に設定します。
    ```bash
    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ```

## 🚀 実行方法

以下のコマンドでアプリケーションを起動します。

```bash
python main.py
```

コンソールに `AIアシスタントが起動しました` と表示されれば成功です。

---

## 📡 APIエンドポイント

APIサーバーはデフォルトで `http://0.0.0.0:8080` で起動します。
すべてのリクエストには、HTTPヘッダーに `X-API-Key: YOUR_SECRET_API_KEY` を含める必要があります。

### `POST /chat`

LLMと対話するためのエンドポイントです。

- **リクエストボディ:**
  ```json
  {
    "message": "自己紹介してください"
  }
  ```
- **レスポンス:**
  ```json
  {
    "response": "こんにちは。私はAIアシスタントです。..."
  }
  ```

### `POST /notify`

指定したチャンネルに通知メッセージを送信します。

- **リクエストボディ:**
  ```json
  {
    "prompt": "サーバーのCPU使用率が90%を超えました。至急確認してください。",
    "channel_id": 123456789012345678 // (オプション) 省略時はconfigのデフォルト値が使われる
  }
  ```
- **レスポンス:**
  ```json
  {
    "status": "ok",
    "message": "通知を送信しました"
  }
  ```

---

## 📁 プロジェクト構造

```
.
├── main.py             # アプリケーションの起動スクリプト
├── discord_bot.py      # Discordボットのロジック
├── api_server.py       # FastAPIサーバーのロジック
├── llm_handler.py      # LLM(Gemini)との連携ロジック
├── config.py           # 設定ファイルの読み込みロジック
├── config.yaml         # 各種設定ファイル
├── config.yaml.example # 設定ファイルの見本
├── requirements.txt    # 依存ライブラリリスト
└── README.md           # このファイル
```
