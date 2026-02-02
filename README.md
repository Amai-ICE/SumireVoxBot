# SumireVox 🌸

SumireVoxは、DiscordのテキストメッセージをVOICEVOXを使用して読み上げる、高性能なDiscord読み上げBotです。
PostgreSQLを使用した柔軟な設定保存や、Dockerによる簡単なデプロイが可能です。

## ✨ 主な機能

- **メッセージ読み上げ**: 指定したチャンネルのメッセージをVCで読み上げます。
- **VOICEVOX連携**: 多様なキャラクターボイスで読み上げが可能です。
- **高度なカスタマイズ**:
  - キャラクター（話者）、速度、ピッチの個別設定。
  - ユーザーごとの音声設定。
- **辞書機能**: 
  - サーバーごとの単語登録。
  - グローバル辞書（特定IDのサーバー）との同期機能。
- **自動機能**: 
  - VCへのユーザー入室に合わせた自動参加・自動退出。
  - VC通知機能。
- **直感的なUI**: Discordのスラッシュコマンドとインタラクティブなボタン/メニューによる操作。

## 🛠 技術スタック

- **言語**: Python 3.12+
- **ライブラリ**: discord.py, loguru, aiohttp, SQLAlchemy
- **音声合成**: VOICEVOX Engine
- **データベース**: PostgreSQL 15
- **インフラ**: Docker / Docker Compose

## 🚀 セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/SumireVox.git
cd SumireVox
```

### 2. 環境設定

`.env.template` を `.env` にコピーし、必要な情報を記入してください。

```bash
cp .env.template .env
```

**主な設定項目:**
- `DISCORD_TOKEN`: Discord Botのトークン
- `VOICEVOX_HOST`: VOICEVOX Engineのホスト名（Docker使用時は `voicevox_engine`）
- `GLOBAL_DICT_ID`: グローバル辞書として使用するギルドID

### 3. 起動（Docker Composeを使用する場合）

```bash
docker-compose up -d
```

これにより、Bot、PostgreSQL、VOICEVOX Engineのすべてが自動的に起動します。

## 🎮 コマンド一覧

| コマンド | 説明 |
| :--- | :--- |
| `/join` | Botをボイスチャンネルに参加させます。 |
| `/leave` | Botをボイスチャンネルから退出させます。 |
| `/set_voice` | 音声（話者、速度、ピッチ）を設定します。 |
| `/add_word` | 辞書に単語を登録します。 |
| `/remove_word` | 辞書から単語を削除します。 |
| `/dictionary` | 辞書一覧を表示・管理します。 |
| `/config` | 現在の設定を確認します。 |
| `/ping` | Botの応答速度を確認します。 |

## 📁 プロジェクト構造

- `src/cogs`: Botの機能モジュール（読み上げ、コマンド等）
- `src/core`: データベース接続、VOICEVOXクライアント等のコアロジック
- `src/queries`: データベース操作用クエリ
- `src/utils`: ロガーやユーティリティツール
- `assets`: 画像やアセットファイル

## ⚖️ ライセンス

[LICENSE](LICENSE) ファイルを参照してください。
