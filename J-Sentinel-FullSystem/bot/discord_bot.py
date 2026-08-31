import json
import os
import discord
from discord.ext import commands
import warning_parser
import weather_parser  # 追加

# スクリプトがある場所（bot/）を基準に、一つ上の階層（プロジェクトルート）に移動する
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
os.chdir(parent_dir)

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

    # --- 2. 天気予報の判定 ---
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
                
                if len(result_text) > 3900:
                    await message.channel.send(
                        f"⚠️ 「{target_region}」の情報はデータ量が多すぎるため送信できません。"
                    )
                else:
                    await message.channel.send(result_text)
                    
            elif info_type == "weather":
                json_path = os.path.join(parent_dir, "js_core", "database", "weather", "convert", "WeatherRT.json")
                result_data = weather_parser.get_weather_info(json_path, codemaster_dir, target_region)
                
                # Embed オブジェクトが返ってきた場合は embed パラメータで送信
                if isinstance(result_data, discord.Embed):
                    await message.channel.send(embed=result_data)
                else:
                    # エラーメッセージなどの文字列の場合
                    await message.channel.send(str(result_data))

        except discord.errors.HTTPException as e:
            if e.code == 50035:
                await message.channel.send("⚠️ メッセージの文字数が上限を超えたため送信できませんでした。")
            else:
                await message.channel.send(f"⚠️ メッセージの送信中にエラーが発生しました（コード: {e.code}）")
        except Exception as e:
            await message.channel.send(f"⚠️ エラーが発生しました: {e}")

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)