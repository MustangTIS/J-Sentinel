import json
import os
import asyncio
from nio import AsyncClient, RoomMessageText
import warning_parser
from weather_parser_matrix import get_weather_text  # こちらをインポート

# スクリプトがある場所（bot/）を基準に、一つ上の階層（プロジェクトルート）に移動する
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
os.chdir(parent_dir)

# これでプロジェクトルートの config.json を正しく読めるようになる
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
    info_type = None  # "warning" または "weather"

    # --- 1. 警報・注意報の判定 ---
    if "の気象情報は" in content:
        base_text = content.split("の気象情報は")[0]
        if "]" in base_text:
            base_text = base_text.split("]")[-1]
        target_region = base_text.strip()
        info_type = "warning"
    elif "気象/" in content:
        parts = content.split("気象/", 1)
        if len(parts) >= 2 and parts[1].strip():
            target_region = parts[1].strip().split()[0]
            info_type = "warning"

    # --- 2. 天気予報の判定（追加） ---
    elif "の天気は" in content:
        base_text = content.split("の天気は")[0]
        if "]" in base_text:
            base_text = base_text.split("]")[-1]
        target_region = base_text.strip()
        info_type = "weather"
    elif "天気/" in content:
        parts = content.split("天気/", 1)
        if len(parts) >= 2 and parts[1].strip():
            target_region = parts[1].strip().split()[0]
            info_type = "weather"

    # --- 3. データの取得と送信 ---
    if target_region and info_type:
        codemaster_dir = os.path.join(parent_dir, "js_core", "codemaster")
        
        try:
            if info_type == "warning":
                json_path = os.path.join(parent_dir, "js_core", "database", "keiho", "convert", "WarningRT.json")
                result_text = warning_parser.get_warning_info(json_path, target_region)
            elif info_type == "weather":
                json_path = os.path.join(parent_dir, "js_core", "database", "weather", "convert", "WeatherRT.json")
                # ★ ここを discord.Embed ではなくテキストを返す get_weather_text に変更
                result_text = get_weather_text(json_path, codemaster_dir, target_region)
        except Exception as e:
            result_text = f"エラーが発生しました: {e}"
        
        # --- 文字数が多すぎる場合のガード処理 ---
        if len(result_text) > 2000:
            result_text = (
                f"⚠️ 「{target_region}」の情報はデータ量が膨大です（約{len(result_text)}文字）。\n"
                "チャットが埋まってしまうため、市町村名など（例: 「帯広市の気象情報は？」や「帯広の天気は？」など）でより細かく指定して検索してください。"
            )

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