# SumireVoxBot

## 概要
discord.py と VOICEVOX エンジンを用いた読み上げBotです。辞書管理用のWeb管理画面と、サーバー別辞書をPostgreSQLで管理します。

## 必要環境
### ランタイム
- Python 3.14.2 (動作確認)
- FFmpeg (Discord の音声再生に必要)

### 外部サービス / ツール
- VOICEVOX エンジン (Docker イメージ: `voicevox/voicevox_engine:cpu-ubuntu20.04-latest`)
- PostgreSQL 15 (Docker イメージ: `postgres:15`)

## 環境変数
`.env.template` を参考に `.env` を用意してください。

- `DISCORD_TOKEN`: Discord Bot トークン
- `VOICEVOX_HOST` / `VOICEVOX_PORT`: VOICEVOX エンジン
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `POSTGRES_HOST` / `POSTGRES_PORT`: PostgreSQL
- `ADMIN_USER` / `ADMIN_PASSWORD`: Web管理画面のBasic認証

## セットアップ
1) `.env.template` を参考に `.env` を用意する
2) Docker を起動し、`docker-compose up -d` で VOICEVOX と PostgreSQL を起動する
3) 依存パッケージをインストールする
4) Bot を起動する

```bash
pip install -r requirements.txt
python main.py
```

## Web管理画面
- URL: `http://localhost:8080`
- Basic認証: `.env` の `ADMIN_USER` / `ADMIN_PASSWORD`
- VOICEVOX のユーザー辞書を追加・削除できます

## 機能
### 読み上げ
- /join で接続したVCで、同じテキストチャンネルのメッセージを読み上げ
- Botメッセージや `!` / `！` から始まるコマンドは読み上げ対象外
- URL・コードブロック・長文(50文字超)は省略して読み上げ
- 添付ファイルは件数を通知
- サーバー辞書の読み替えを適用して読み上げ

### 音声カスタマイズ
- `/set_voice` で話者・速度・ピッチをユーザーごとに保存

### 辞書機能
- サーバー辞書: `/add_word` `/remove_word` `/dictionary`
- グローバル辞書(VOICEVOXユーザー辞書): Web管理画面から追加・削除

### スラッシュコマンド
- `/join` 接続して読み上げ開始
- `/leave` 切断して読み上げ終了
- `/set_voice` 話者・速度・ピッチを設定
- `/add_word` サーバー辞書に登録
- `/remove_word` サーバー辞書から削除
- `/dictionary` サーバー辞書を一覧表示
