import json
import os
import asyncio
from nio import AsyncClient, RoomMessageText
import warning_parser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# destinations から style が matrix のものを取得
destinations = config.get("destinations", [])
matrix_dest = next((d for d in destinations if d.get("style") == "matrix"), None)

if not matrix_dest or not matrix_dest.get("token"):
    exit(0)  # 設定がなければ即終了

HOMESERVER = matrix_dest.get("url")        # 例: "https://matrix.juggler.jp"
ACCESS_TOKEN = matrix_dest.get("token")    # 例: "syt_..."
TARGET_ROOM = matrix_dest.get("room")      # 例: "!SQJesCVnsLxvmqzdcd:matrix.juggler.jp"

# matrix-nio用のクライアント初期化（アクセストークン認証）
# ※ user_id はトークンから自動で解決できないため、configの構造によっては user_id も必要ですが、
#   一般的なアクセストークン運用では user_id, homeserver, token を渡します。
#   もし user_id が必要なら config に追加するか、適宜書き換えてください。
#   ここでは簡易的に homeserver と token を使った基本形にします。

async def message_callback(room, event):
    # 自分自身の発言は無視する
    if event.sender == client.user_id:
        return

    # テキストメッセージ以外は無視
    if not isinstance(event, RoomMessageText):
        return

    # 対象ルーム以外からの発言は無視（TARGET_ROOMが指定されている場合）
    if TARGET_ROOM and room.room_id != TARGET_ROOM:
        return

    content = event.body.replace("／", "/")
    target_region = None

    # Discord版と全く同じ解析ロジック
    if "の気象情報は" in content:
        base_text = content.split("の気象情報は")[0]
        if "]" in base_text:
            base_text = base_text.split("]")[-1]
        target_region = base_text.strip()
    elif "気象/" in content:
        parts = content.split("気象/", 1)
        if len(parts) >= 2 and parts[1].strip():
            target_region = parts[1].strip().split()[0]

    if target_region:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(BASE_DIR, "js_core", "database", "keiho", "convert", "WarningRT.json")
        
        try:
            result_text = warning_parser.get_warning_info(json_path, target_region)
        except Exception as e:
            result_text = f"エラーが発生しました: {e}"
        
        # Matrixルームへ返信を送信
        await client.room_send(
            room_id=room.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": result_text
            }
        )

async def main():
    # ユーザーIDをアクセストークンから推測するか、あるいは matrix_dest に user_id があればそれを使う
    # （※多くのマトリックス環境では user_id が必須なため、もしエラーになる場合は config に "user_id": "@xxx:matrix.juggler.jp" を追加してください）
    user_id = matrix_dest.get("user_id", "")
    
    global client
    client = AsyncClient(HOMESERVER, user_id)
    
    # アクセストークンとデバイスIDのセット
    client.access_token = ACCESS_TOKEN
    client.user_id = user_id

    # メッセージ受信時のコールバック登録
    client.add_event_callback(message_callback, RoomMessageText)

    print(f"[Matrix] Logged in / Connecting to {HOMESERVER}...")

    # 同期ループの開始
    await client.sync_forever(timeout=30000)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass