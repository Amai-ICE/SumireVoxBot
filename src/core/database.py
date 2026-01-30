import json

import asyncpg
import os
from loguru import logger
from src.core.models import GuildSettings
from src.queries import UserSettingsQueries, GuildDictQueries, GuildSettingsQueries


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                database=os.getenv("POSTGRES_DB"),
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT")
            )

    async def init_db(self):
        if self.pool is None:
            await self.connect()

        async with self.pool.acquire() as conn:
            # ユーザー設定
            await conn.execute(UserSettingsQueries.CREATE_TABLE)
            # サーバーごとの辞書
            await conn.execute(GuildDictQueries.CREATE_TABLE)
            # サーバーごとの設定
            await conn.execute(GuildSettingsQueries.CREATE_TABLE)

    async def get_guild_settings(self, guild_id: int) -> GuildSettings:
        """サーバー設定を取得する。型が文字列でも辞書でも対応できるようにする"""
        row = await self.pool.fetchrow(GuildSettingsQueries.GET_SETTINGS, guild_id)

        if row:
            raw_data = row['settings']

            # もしデータが文字列(str)で返ってきたら辞書に変換
            if isinstance(raw_data, str):
                try:
                    raw_data = json.loads(raw_data)
                except json.JSONDecodeError:
                    logger.error(f"JSONのパースに失敗しました: {raw_data}")
                    return GuildSettings()

            # 辞書(dict)としてPydanticでバリデーション
            return GuildSettings.model_validate(raw_data)

        # データがない場合はデフォルト設定
        return GuildSettings()

    async def set_guild_settings(self, guild_id: int, settings: GuildSettings):
        """サーバー設定を保存する"""
        # Pydanticモデルを辞書に変換
        settings_dict = settings.model_dump()
        settings_json = json.dumps(settings_dict)

        # INSERT ... ON CONFLICT (UPSERT) で保存
        await self.pool.execute(GuildSettingsQueries.SET_SETTINGS, guild_id, settings_json)

        logger.debug(f"[{guild_id}] サーバー設定を更新しました。")

    # ユーザー設定の取得
    async def get_user_setting(self, user_id: int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                UserSettingsQueries.GET_SETTINGS,
                user_id
            )
            if row:
                return {"speaker": row['speaker'], "speed": row['speed'], "pitch": row['pitch']}
            return {"speaker": 1, "speed": 1.0, "pitch": 0.0}

    # ユーザー設定の保存
    async def set_user_setting(self, user_id: int, speaker: int, speed: float, pitch: float):
        async with self.pool.acquire() as conn:
            await conn.execute(UserSettingsQueries.SET_SETTINGS, user_id, speaker, speed, pitch)

    # ギルド辞書の取得（グローバル統合が不要になったためシンプルに）
    async def get_guild_dict(self, guild_id: int):
        """特定のギルドの辞書を辞書形式で取得"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(GuildDictQueries.GET_DICT, guild_id)
            return {row['word']: row['reading'] for row in rows}

    # ギルド辞書の登録
    async def set_guild_word(self, guild_id: int, word: str, reading: str):
        async with self.pool.acquire() as conn:
            await conn.execute(GuildDictQueries.INSERT_WORD, guild_id, word, reading)

    # ギルド辞書の削除
    async def remove_guild_word(self, guild_id: int, word: str):
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                GuildDictQueries.REMOVE_WORD,
                guild_id, word
            )
            return result == "DELETE 1"

    # ギルド辞書の一覧取得
    async def get_guild_words(self, guild_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                GuildDictQueries.GET_DICT_WORDS,
                guild_id
            )

    async def close(self):
        if self.pool:
            await self.pool.close()