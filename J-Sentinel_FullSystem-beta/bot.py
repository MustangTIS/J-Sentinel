import json
import re
import os
import discord
from discord.ext import commands
import warning_parser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 1. config.json の読み込み
CONFIG_PATH = "config.json"
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"{CONFIG_PATH} が見つかりません。")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

# bot_settings からトークンを取得
bot_config = config.get("bot_settings", {})
BOT_TOKEN = bot_config.get("token")

if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("config.json の bot_settings.token に有効なBotトークンを設定してください。")

# 2. warning_parser のインポート
try:
    import warning_parser
except ImportError:
    warning_parser = None

# 3. Discord Bot の初期化（Intents設定）
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    # ボット自身のメッセージには反応しないようにする
    if message.author == bot.user:
        return

    # メッセージ内容を取得（全角スラッシュ「／」を半角の「/」に統一する）
    content = message.content.replace("／", "/")

    target_region = None

    # パターン1: 「〜の気象情報は」が含まれている場合（IRCの [名前] プレフィックスにも対応）
    if "の気象情報は" in content:
        # 「の気象情報は」の前の部分をゲット
        base_text = content.split("の気象情報は")[0]
        # もし先頭に [ユーザー名] がついていたら、最後の `]` より後ろの部分だけを地域名にする
        if "]" in base_text:
            base_text = base_text.split("]")[-1]
        target_region = base_text.strip()

    # パターン2: 「気象/」が含まれている場合（「[Mustang_TIS] 気象/宮崎市」のような形に対応）
    elif "気象/" in content:
        # 「気象/」の「気象/」以降をスパッと切り出す
        parts = content.split("気象/", 1)
        if len(parts) >= 2 and parts[1].strip():
            # スペースや余計な文字が入っていればきれいにする
            target_region = parts[1].strip().split()[0]  # 後ろに余分な文字がなければこれでもOK

    # どちらかの条件にヒットした場合の処理
    if target_region:
        # 起動場所に関係なく、bot.py がある場所を基準にして確実にパスを組み立てる
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(BASE_DIR, "js_core", "database", "keiho", "convert", "WarningRT.json")
        
        print(f"[Debug] 探索先パス: {json_path}")
        print(f"[Debug] ファイルが存在するか: {os.path.exists(json_path)}")
        print(f"[Debug] 抽出した地域: {target_region}")
        
        # 安全に warning_parser を呼び出す
        try:
            if warning_parser is not None:
                result_text = warning_parser.get_warning_info(json_path, target_region)
            else:
                result_text = "warning_parser モジュールが読み込まれていません。"
        except Exception as e:
            result_text = f"エラーが発生しました: {e}"
        
        # Discordのチャンネルに結果を送信
        await message.channel.send(result_text)

    # 他のコマンド機能を生かすためのおまじない
    await bot.process_commands(message)


# Botの起動
if __name__ == "__main__":
    bot.run(BOT_TOKEN)