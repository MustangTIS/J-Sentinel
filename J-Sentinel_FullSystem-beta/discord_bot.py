import json
import os
import discord
from discord.ext import commands
import warning_parser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 設定読み込み
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config.get("bot_settings", {}).get("token")
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    exit(0) # 万が一直接叩かれてもトークンがなければ即終了

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[Discord] Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content.replace("／", "/")
    target_region = None

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
        
        # --- ここから送信処理（文字数制限・エラー対策） ---
        try:
            if len(result_text) > 3900:
                await message.channel.send(
                    f"⚠️ 「{target_region}」の気象情報はデータ量が多すぎるため、"
                    "Discordの送信文字数制限（4000文字）を超過しました。\n"
                    "（より細かい地域を指定して検索してください）"
                )
            else:
                await message.channel.send(result_text)
                
        except discord.errors.HTTPException as e:
            if e.code == 50035:
                await message.channel.send("⚠️ メッセージの文字数が上限を超えたため送信できませんでした。")
            else:
                await message.channel.send(f"⚠️ メッセージの送信中にエラーが発生しました（コード: {e.code}）")

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)