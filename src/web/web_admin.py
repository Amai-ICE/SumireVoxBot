import os
from pathlib import Path
from loguru import logger
import jaconv
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn
import secrets

app = FastAPI()
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))
security = HTTPBasic()
vv_client = None

# 認証用のIDとパスワード
load_dotenv()
ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")

if not ADMIN_USER or not ADMIN_PASS:
    error_msg = "環境変数 ADMIN_USER または ADMIN_PASSWORD が設定されていません"
    logger.error(error_msg)
    raise RuntimeError(error_msg)


def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USER)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="IDまたはパスワードが違います",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user_dict = await vv_client.get_user_dict()
    return templates.TemplateResponse("index.html", {"request": request, "user_dict": user_dict})


@app.post("/add")
async def add_word(word: str = Form(...), reading: str = Form(...), username: str = Depends(authenticate)):
    if not word.strip() or not reading.strip():
        logger.warning("空の単語または読みが送信されました")
        return RedirectResponse(url="/?error=empty_input", status_code=303)

    # 1. 入力データの正規化 (比較用)
    # 単語(表記)を「全角・小文字」に統一
    input_word = jaconv.h2z(word.strip(), kana=True, digit=True, ascii=True).lower()

    # 読みを「全角カタカナ」に統一
    input_reading = jaconv.hira2kata(jaconv.h2z(reading.strip(), kana=True, digit=False, ascii=False))

    # 2. エンジン側の辞書を取得
    try:
        user_dict = await vv_client.get_user_dict()
    except Exception as e:
        logger.error(f"ユーザー辞書の取得に失敗しました: {e}")
        return RedirectResponse(url="/?error=fetch_failed", status_code=303)

    # 3. 重複チェック
    # エンジン側の既存データも「全角・小文字」に変換して比較する
    existing_uuids = []
    for uuid, data in user_dict.items():
        # エンジンから返ってくる surface を正規化
        normalized_surface = jaconv.h2z(data['surface'], kana=True, digit=True, ascii=True).lower()

        if normalized_surface == input_word:
            existing_uuids.append(uuid)

    # 4. 重複がある場合は削除
    if existing_uuids:
        logger.warning(f"重複エントリを検出しました: {len(existing_uuids)}件 (単語: {input_word})")

    for old_uuid in existing_uuids:
        try:
            await vv_client.delete_user_dict(old_uuid)
        except Exception as e:
            logger.error(f"既存の辞書エントリ(UUID: {old_uuid})の削除に失敗しました: {e}")

    # 5. 登録
    try:
        await vv_client.add_user_dict(input_word, input_reading)
        logger.info(f"単語を登録しました: {input_word} ({input_reading}) by {username}")
    except Exception as e:
        logger.error(f"単語の登録に失敗しました: {e}")
        return RedirectResponse(url="/?error=add_failed", status_code=303)

    return RedirectResponse(url="/", status_code=303)


@app.post("/delete/{uuid}")
async def delete_word(uuid: str, username: str = Depends(authenticate)):
    try:
        await vv_client.delete_user_dict(uuid)
        logger.info(f"単語を削除しました: UUID={uuid} by {username}")
    except Exception as e:
        logger.error(f"単語の削除に失敗しました (UUID: {uuid}): {e}")
        return RedirectResponse(url="/?error=delete_failed", status_code=303)

    return RedirectResponse(url="/", status_code=303)

class WebAdminServer:
    def __init__(self, client):
        global vv_client
        vv_client = client
        # 設定を保持
        self.config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="warning"  # ログをスッキリさせたい場合はwarningに
        )
        self.server = uvicorn.Server(self.config)

    async def run(self):
        """Webサーバーを起動する"""
        await self.server.serve()

    async def stop(self):
        """Webサーバーを安全に停止する"""
        self.server.should_exit = True
        await self.server.shutdown()
