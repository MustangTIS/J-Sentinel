import sys
import json
import os
import subprocess

os.chdir(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = "config.json"
if not os.path.exists(CONFIG_PATH):
    sys.exit(0)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

processes = []

# 1. Discord Bot の判定 (bot_settings)
discord_token = config.get("bot_settings", {}).get("token")
has_valid_discord = discord_token and discord_token != "YOUR_BOT_TOKEN_HERE"

if has_valid_discord:
    print("[Manager] Discord Bot を起動します...")
    p_disc = subprocess.Popen([sys.executable, "bot/discord_bot.py"])
    processes.append(p_disc)
else:
    print("[Manager] Discord Bot の設定がないためスキップします。")

# 2. Matrix Bot の判定 (destinations配列から "style": "matrix" を探す)
destinations = config.get("destinations", [])
matrix_dest = next((d for d in destinations if d.get("style") == "matrix"), None)

matrix_token = matrix_dest.get("token") if matrix_dest else None
has_valid_matrix = matrix_token and matrix_token != ""

if has_valid_matrix:
    print("[Manager] Matrix Bot を起動します...")
    p_matrix = subprocess.Popen([sys.executable, "bot/matrix_bot.py"])
    processes.append(p_matrix)
else:
    print("[Manager] Matrix Bot の設定がないためスキップします。")

# どの子プロセスも起動しなかった場合は無駄に常駐せず終了
if not processes:
    print("[Manager] 稼働させるボットがないため終了します。")
    sys.exit(0)

# 子プロセスを見守る
try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("[Manager] 終了シグナルを検知しました。子プロセスを停止します...")
    for p in processes:
        p.terminate()