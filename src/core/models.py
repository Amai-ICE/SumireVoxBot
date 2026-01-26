from pydantic import BaseModel, Field


class GuildSettings(BaseModel):
    """
    サーバー（ギルド）ごとの設定を管理するモデル
    JSONBから変換したり、デフォルト値を一括管理したりします。
    """
    # 自動接続
    auto_join: bool = Field(default=False, description="ボイスチャンネルへの自動接続")

    # 文字数制限
    max_chars: int = Field(default=50, ge=10, le=500, description="読み上げ文字数の上限")

    # 入退出の読み上げ
    read_vc_status: bool = Field(default=False, description="ユーザーの入退出を通知")

    # メンション読み上げ
    read_mention: bool = Field(default=True, description="メンションを名前で読み上げるか")

    # さん付け
    add_suffix: bool = Field(default=False, description="ユーザー名の後に『さん』を付ける")
