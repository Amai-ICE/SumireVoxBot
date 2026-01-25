import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# ロガー関連のインポート
from src.utils.logger import setup_logger, console
from rich.table import Table

from src.core.voicevox_client import VoicevoxClient
from src.core.database import Database
from src.web.web_admin import run_web_admin

# ロガーのセットアップ
logger = setup_logger()

# インテントの設定
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

cogs = [
    "src.cogs.voice"
]


class SumireVox(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.vv_client = VoicevoxClient()
        self.db = Database()

    async def setup_hook(self) -> None:
        logger.info("初期化シーケンスを開始します...")

        await self.db.init_db()
        # Web管理画面のタスク開始
        asyncio.create_task(run_web_admin(self.vv_client))

        logger.info("Cogs の読み込みを開始します")
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.success(f"Loaded: {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}: {e}")

        # スラッシュコマンドの同期も自動で行う場合はここに追加できます
        await self.tree.sync()
        logger.info("スラッシュコマンドの同期が完了しました")

    async def close(self) -> None:
        logger.warning("シャットダウンシーケンスを開始します...")
        await self.vv_client.close()
        logger.success("VOICEVOX セッションを終了しました")
        await self.db.close()
        logger.success("データベース接続を終了しました")
        await super().close()
        logger.success("Discord セッションを終了しました")

    async def on_ready(self) -> None:
        # 起動時のステータスを Rich のテーブルで表示
        table = Table(title="🌸 SumireVox システム稼働状況", show_header=True, header_style="bold magenta")
        table.add_column("項目", style="cyan")
        table.add_column("ステータス", style="green")

        table.add_row("ログインユーザー", f"{self.user} ({self.user.id})")
        table.add_row("discord.py バージョン", discord.__version__)
        table.add_row("接続サーバー数", str(len(self.guilds)))
        table.add_row("Web管理画面", "http://localhost:8080 (Basic Auth 有効)")
        table.add_row("VOICEVOX Engine", os.getenv("VOICEVOX_URL", "http://localhost:50021"))

        console.print(table)
        logger.success("SumireVox は正常に起動し、待機中です。")


bot = SumireVox()


@bot.command()
@commands.is_owner()
async def sync(ctx):
    logger.info("手動同期リクエストを受信しました")
    synced = await bot.tree.sync()
    await ctx.send(f"Successfully synced {len(synced)} commands.")
    logger.success(f"{len(synced)} 個のコマンドを同期しました")


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")

    if token:
        try:
            bot.run(token, log_handler=None)  # 標準のロガーを無効化して loguru に一本化
        except Exception as e:
            logger.critical(f"Botの実行中に致命的なエラーが発生しました: {e}")
    else:
        logger.error(".env ファイルに DISCORD_TOKEN が見つかりません。")
