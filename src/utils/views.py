import discord
from src.utils.logger import logger


# 数値入力用のモーダル（既存のものをシンプルに修正）
class ConfigEditModal(discord.ui.Modal):
    def __init__(self, item_name: str, item_key: str, current_value: int, db):
        super().__init__(title=f"{item_name} の設定")
        self.item_key = item_key
        self.db = db

        self.value_input = discord.ui.TextInput(
            label="数値を入力してください",
            default=str(current_value),
            placeholder="例: 100",
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.value_input.value
        if not value.isdigit():
            return await interaction.response.send_message("❌ 数値を入力してください。", ephemeral=True)

        new_value = int(value)
        settings = await self.db.get_guild_settings(interaction.guild.id)
        old_value = getattr(settings, self.item_key)

        try:
            setattr(settings, self.item_key, new_value)
            await self.db.set_guild_settings(interaction.guild.id, settings)
            await interaction.response.send_message(f"✅ 設定を更新しました：`{old_value}` ➡ **`{new_value}`**",
                                                    ephemeral=True)
        except Exception as e:
            logger.error(f"Config update failed: {e}")
            await interaction.response.send_message(f"❌ 更新に失敗しました: {e}", ephemeral=True)


# ON/OFF 選択用の View
class ConfigToggleView(discord.ui.View):
    def __init__(self, item_name: str, item_key: str, db):
        super().__init__(timeout=60)
        self.item_name = item_name
        self.item_key = item_key
        self.db = db

    @discord.ui.select(
        placeholder="状態を選択してください",
        options=[
            discord.SelectOption(label="有効 (ON)", value="True", emoji="✅"),
            discord.SelectOption(label="無効 (OFF)", value="False", emoji="❌"),
        ]
    )
    async def select_toggle(self, interaction: discord.Interaction, select: discord.ui.Select):
        new_value = select.values[0] == "True"
        settings = await self.db.get_guild_settings(interaction.guild.id)
        old_value = getattr(settings, self.item_key)

        setattr(settings, self.item_key, new_value)
        await self.db.set_guild_settings(interaction.guild.id, settings)

        status_text = "有効" if new_value else "無効"
        await interaction.response.send_message(
            f"✅ **{self.item_name}** を **{status_text}** に設定しました。",
            ephemeral=True
        )


class ConfigAutoJoinView(discord.ui.View):
    def __init__(self, db, bot):
        super().__init__(timeout=180)
        self.db = db
        self.bot = bot
        self.selected_vc = None
        self.selected_tc = None

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.voice],
        placeholder="1. 監視するボイスチャンネルを選択",
    )
    async def select_vc(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.selected_vc = select.values[0]
        await interaction.response.send_message(f"✅ 監視対象を {self.selected_vc.mention} に指定しました。",
                                                ephemeral=True)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="2. 読み上げるテキストチャンネルを選択",
    )
    async def select_tc(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.selected_tc = select.values[0]
        await interaction.response.send_message(f"✅ 読み上げ先を {self.selected_tc.mention} に指定しました。",
                                                ephemeral=True)

    @discord.ui.button(label="このBotの設定として保存", style=discord.ButtonStyle.success, emoji="🤖")
    async def save_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_vc or not self.selected_tc:
            return await interaction.response.send_message("❌ VCとTCの両方を選択してください。", ephemeral=True)

        settings = await self.db.get_guild_settings(interaction.guild.id)

        # 辞書の初期化（既存データがあれば維持）
        if settings.auto_join_config is None:
            settings.auto_join_config = {}

        # Bot IDをキーにして設定を書き込み（既存の別Bot設定は壊さない）
        bot_key = str(self.bot.user.id)
        settings.auto_join_config[bot_key] = {
            "voice": self.selected_vc.id,
            "text": self.selected_tc.id
        }
        # 全体フラグも念のためON
        settings.auto_join = True

        await self.db.set_guild_settings(interaction.guild.id, settings)
        await interaction.response.send_message(
            f"✅ **{self.bot.user.name}** の自動接続設定を保存しました！\n"
            f"次回から {self.selected_vc.name} への入室を検知して {self.selected_tc.name} で読み上げを開始します。",
            ephemeral=True
        )


# メインの項目選択 View
class ConfigSearchView(discord.ui.View):
    def __init__(self, db, bot):
        super().__init__(timeout=180)
        self.db = db
        self.bot = bot

    @discord.ui.select(
        placeholder="設定する項目を選んでください",
        options=[
            discord.SelectOption(label="自動接続（Bot個別設定）", value="auto_join",
                                 description="どのVCを監視し、どのTCで読み上げるか", emoji="🤖"),
            discord.SelectOption(label="文字数制限", value="max_chars", description="読み上げる最大文字数 (10-500)",
                                 emoji="📝"),
            discord.SelectOption(label="入退出の読み上げ", value="read_vc_status", description="ユーザーの入退室を通知",
                                 emoji="🚪"),
            discord.SelectOption(label="メンション読み上げ", value="read_mention",
                                 description="メンションを読み上げるか", emoji="🆔"),
            discord.SelectOption(label="さん付け", value="add_suffix", description="名前に「さん」を付けるか", emoji="🎀"),
            discord.SelectOption(label="ローマ字読み", value="read_romaji", description="ローマ字をそのまま読むか",
                                 emoji="🔤"),
            discord.SelectOption(label="添付ファイルの読み上げ", value="read_attachments",
                                 description="ファイル名を読み上げるか", emoji="📎"),
            discord.SelectOption(label="コードブロックの省略", value="skip_code_blocks",
                                 description="コードをスキップするか", emoji="💻"),
            discord.SelectOption(label="URLの省略", value="skip_urls", description="URLを省略して読むか", emoji="🔗"),
        ]
    )
    async def select_item(self, interaction: discord.Interaction, select: discord.ui.Select):
        item_key = select.values[0]

        if item_key == "auto_join":
            return await interaction.response.send_message(
                "### 🤖 自動接続の個別設定\n"
                "このBotが自動で参加するチャンネルを選択してください。\n"
                "※設定はBot（インスタンス）ごとに保存されます。",
                view=ConfigAutoJoinView(self.db, self.bot),
                ephemeral=True
            )

        settings = await self.db.get_guild_settings(interaction.guild.id)
        current_value = getattr(settings, item_key)
        item_label = [opt.label for opt in select.options if opt.value == item_key][0]

        if isinstance(current_value, bool):
            await interaction.response.send_message(
                f"**{item_label}** の切り替え：",
                view=ConfigToggleView(item_label, item_key, self.db),
                ephemeral=True
            )
        else:
            await interaction.response.send_modal(
                ConfigEditModal(item_label, item_key, current_value, self.db)
            )
