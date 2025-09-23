# 多機能Discordボット開発仕様書 (SPEC.md)

## 1. プロジェクト概要

Pythonで動作する多機能Discordボットを開発する。このボットはLLM (Gemini) と連携し、自然な対話機能、設定ファイルによるキャラクター付け、そして外部からの操作を可能にするシンプルなAPIを提供する。

### 主な機能

-   **LLM連携チャット**: Discord上でボットにメンションすると、LLMが文脈を考慮した返信を生成する。
-   **会話履歴の認識**: メッセージへの返信（リプライ）形式でのメンションには、過去のやり取りを遡って文脈を把握した上で応答する。
-   **動的なキャラクター設定**: YAML形式の設定ファイルで、ボットの口調や役割（ペルソナ）を自由に変更できる。
-   **外部連携API**: 自宅サーバー内の他のスクリプトやアプリケーションから、ボットを介してDiscordに通知を送信したり、LLMとの対話を行ったりできる。

---

## 2. 技術スタック

-   **言語**: Python 3.11+
-   **ライブラリ**:
    -   `discord.py`: Discord API連携
    -   `fastapi`: Web APIサーバー構築
    -   `uvicorn`: ASGIサーバー
    -   `google-generativeai`: Google Gemini API連携
    -   `PyYAML`: 設定ファイルの読み込み

---

## 3. プロジェクト構造

以下のディレクトリ・ファイル構成で開発を行う。

```text
.
├── main.py             # アプリケーションの起動スクリプト
├── discord_bot.py      # Discordボットのロジック
├── api_server.py       # FastAPIサーバーのロジック
├── llm_handler.py      # LLMとの連携ロジック
├── config.py           # 設定ファイルの読み込みロジック
├── config.yaml         # 各種設定ファイル
└── requirements.txt    # 依存ライブラリリスト
```

---

## 4. 各モジュールの詳細仕様

### 4.1. 設定ファイル (`config.yaml`)

アプリケーションの動作設定をこのファイルで一元管理する。

```yaml
# DiscordとLLMの認証情報
discord_token: "YOUR_DISCORD_BOT_TOKEN"
# Gemini APIキーは環境変数(GEMINI_API_KEY)で設定すること。

# APIサーバーの設定
api_server:
  host: "0.0.0.0"
  port: 8080
  api_key: "YOUR_SECRET_API_KEY" # 外部連携APIの認証用キー
  default_notify_channel_id: 123456789012345678 # デフォルトの通知先チャンネルID

# ボットのキャラクター設定
bot_persona:
  name: "AIアシスタント"
  model: "gemini-2.5-flash-latest"
  system_prompt: |
    あなたは親切で知識豊富なAIアシスタントです。
    ユーザーからの質問には、常に丁寧かつ分かりやすく回答してください。
    不明な点については、正直に「分かりません」と答えてください。
```

### 4.2. 設定ローダー (`config.py`)

`config.yaml`を読み込み、アプリケーション全体で利用可能な辞書オブジェクトとして提供する。

- `load_config()`関数を定義し、`config.yaml`をパースして返す。

### 4.3. LLMハンドラ (`llm_handler.py`)

LLMとのやり取りを抽象化する。

- **`async def generate_response(history: list, system_prompt: str) -> str`** 関数を実装する。
  - `history`: `[{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]` 形式の会話履歴リスト。
  - `system_prompt`: `config.yaml`から読み込んだキャラクター設定。
  - 処理内容: `google-generativeai`ライブラリを使い、`gemini-2.5-flash-latest`などのモデルに対して、システムプロンプトと会話履歴を渡して応答テキストを生成・返却する。

### 4.4. Discordボット (`discord_bot.py`)

Discord APIとの通信、イベントハンドリングを行う。

- `discord.Client`のインスタンスを生成する。この際、メッセージ内容を読み取るために`intents.message_content = True`を有効にすること。
- **`on_ready()`**: 起動時にコンソールに`「{ボット名}が起動しました」`と表示する。
- **`on_message(message)`**: メッセージ受信時のイベントハンドラ。以下のロジックを実装する。
  1.  メッセージの送信者がボット自身の場合は無視する。
  2.  メッセージにボットへのメンションが含まれていない場合は無視する。
  3.  **会話履歴の構築**:
      - メッセージが返信（リプライ）の場合 (`message.reference`が存在する場合）、返信元を最大5件まで再帰的に辿り、古い順に会話履歴リストを構築する。
      - 通常のメンションの場合は、そのメッセージのみを履歴とする。
  4.  `llm_handler.generate_response()`を呼び出し、応答テキストを取得する。
  5.  取得したテキストを`message.reply()`で返信する。

### 4.5. APIサーバー (`api_server.py`)

`FastAPI`を用いて、外部からのHTTPリクエストを処理する。

- **認証**:
  - `config.yaml` の `api_server.api_key` を用いたAPIキー認証を実装する。
  - HTTPリクエストヘッダー `X-API-Key` に含まれる値を検証する。
  - 認証に失敗した場合は `401 Unauthorized` を返す。
- **依存性の注入**: `main.py`で生成されたDiscordクライアントのインスタンスを受け取り、APIの処理内で利用できるようにする。
- **`POST /chat` (要認証)**:
  - リクエストボディ: `{"message": str}`
  - 処理: 受け取った`message`を基に`llm_handler`を呼び出し、LLMからの応答を生成する。
  - レスポンス: `{"response": str}`
- **`POST /notify` (要認証)**:
  - リクエストボディ: `{"prompt": str, "channel_id": int | None = None}`
  - 処理:
    1.  受け取った`prompt`を基に`llm_handler`で通知用のメッセージを生成する。
    2.  `channel_id`が指定されていればそのチャンネルへ、なければ`config.yaml`の`default_notify_channel_id`へ、注入されたDiscordクライアントを使ってメッセージを送信する。
  - レスポンス: `{"status": "ok", "message": "通知を送信しました"}`

### 4.6. メインスクリプト (`main.py`)

アプリケーション全体の起動と管理を行う。

- `config.py`を使って設定をロードする。
- `discord_bot.py`のクライアントインスタンスを生成する。
- `api_server.py`のFastAPIアプリケーションインスタンスを生成し、その際にDiscordクライアントインスタンスを渡す。
- `asyncio.gather`を使い、Discordボットの`client.start()`とUvicornサーバーを非同期で並行実行する。

---

## 5. 実装要件

- **エラーハンドリング**: LLM APIからのエラーレスポンス、Discord APIの接続断など、想定されるエラーに対して適切な例外処理とロギングを行うこと。
- **セキュリティ**: DiscordトークンやAPIキーは、コード内に直接書き込まず、設定ファイルや環境変数から読み込むこと。
- **非同期処理**: `discord.py`と`FastAPI`は共に非同期フレームワークであるため、ブロッキングする処理（同期的なAPI呼び出しなど）は避け、`async/await`を適切に使用すること。
