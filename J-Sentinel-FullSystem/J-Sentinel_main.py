# J_Sentinel_main.py
import os
import time
import sys
import webbrowser
import subprocess
import requests
import json
# 各種モジュールのインポート（system フォルダから取得）
from system import senders
from system import config_manager
from system.log_monitor import LogMonitor

# 各種パーサーのインポート（system フォルダから取得）
from system import quake_parser
from system import info_parser
from system import volcano_parser  # ← 火山用パーサを追加

os.chdir(os.path.dirname(os.path.abspath(__file__)))

CURRENT_VERSION = "1.2.9"
REPO_URL = "MustangTIS/J-Sentinel"

def check_for_updates():
    api_url = "https://api.github.com/repos/MustangTIS/J-Sentinel/releases/latest"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_tag = data.get("tag_name")
            current = f"v{CURRENT_VERSION}" if not CURRENT_VERSION.startswith("v") else CURRENT_VERSION
            if latest_tag and latest_tag != current:
                return "UPDATE_AVAILABLE", latest_tag, data.get("html_url")
            return "LATEST", current, None
    except Exception:
        return "ERROR", None, None
    return "ERROR", None, None

def launch_sentinel_core():
    """
    js_core/run_sentinel.py を別プロセスとして起動する
    """
    script_path = os.path.join("js_core", "run_sentinel.py")
    if os.path.exists(script_path):
        try:
            subprocess.Popen([sys.executable, script_path])
            return True
        except Exception as e:
            print(f"    └─ [Error] run_sentinel.py の起動に失敗しました: {e}")
            return False
    else:
        print(f"    └─ [Error] {script_path} が見つかりません。")
        return False

def process_and_dispatch(file_path, config):
    """
    検知されたファイルパスのフォルダ階層に応じて適切なパーサに一任し、
    取得した辞書データを各宛先へそのまま配信する
    """
    destinations = config.get("destinations", [])
    if not destinations or not os.path.exists(file_path):
        return

    # 1. JSONファイルの読み込み
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"    └─ [Error] JSONの読み込みに失敗しました ({file_path}): {e}")
        return

    # 2. パスに応じたパーサへの完全委任
    normalized_path = file_path.replace("\\", "/")
    parsed = None

    if "/volcano/" in normalized_path or normalized_path.endswith("/volcano"):
        parsed = volcano_parser.parse_volcano_json(data, mode="full")
    elif "/info/" in normalized_path or normalized_path.endswith("/info"):
        parsed = info_parser.parse_info_json(data)
    elif "/quake/" in normalized_path or normalized_path.endswith("/quake"):
        min_display = config.get("min_display_int", "1")
        parsed = quake_parser.parse_quake_json(data, min_display=min_display)
    else:
        print(f"    └─ [Skip] 対象外のフォルダパスです: {normalized_path}")
        return

    # 必須パラメータ（title / description）が取得できなければスキップ
    if not parsed or not parsed.get("title") or not parsed.get("description"):
        return

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 3. 各宛先（Discord/Matrix/Slack/Bluesky等）へのシンプルディスパッチ
    for dest in destinations:
        dest_mode = dest.get("mode", "full")
        try:
            res = senders.dispatch(
                style=dest.get("style", "disembed"),
                title=parsed.get("title"),
                description=parsed.get("description"),
                color=parsed.get("color", 0x3498DB),
                image_path=parsed.get("image_path"),
                url=dest.get("url", ""),
                bot_name="J-Sentinel Bot",
                current_version=CURRENT_VERSION,
                timestamp=timestamp,
                matrix_token=dest.get("token"),
                matrix_room=dest.get("room"),
                bsky_handle=dest.get("handle"),
                bsky_pass=dest.get("password"),
                web_url=parsed.get("web_url") or parsed.get("url"),
                mode=dest_mode
            )
            print(f"    └─ [Dispatch Success] Style: {dest.get('style')} -> Result: {res}")
        except Exception as e:
            print(f"    └─ [Dispatch Error] Style: {dest.get('style')} -> {e}")

def main():
    print("-" * 52)
    print(f">>> J-Sentinel Core: Initialization...")
    print(f">>> J-Sentinel Core: Boot Sequence Started...")
    print("-" * 52)

    config = config_manager.load_system_config()

    print(f"\n [Step 1/3] Booting J-Sentinel Core.......... [  OK  ]")
    print(f"    └─ [System Version: v{CURRENT_VERSION}]")

    print(f" [Step 2/3] Checking for updates...")
    status, ver, url = check_for_updates()
    if status == "UPDATE_AVAILABLE":
        print(f"    └─ [Notice] 新バージョン {ver} が公開されています。")
        webbrowser.open(url)
    elif status == "LATEST":
        print(f"    └─ [Notice] バージョン {ver} は最新です。  [  OK  ]")
    else:
        print(f"    └─ [Warning] アップデート確認をスキップしました。")

    print(f" [Step 3/3] Launching js_core/run_sentinel.py.. ", end="", flush=True)
    if launch_sentinel_core():
        print("[  OK  ]")
    else:
        print("[  !!  ]")
        input("\n    Enterキーを押すと終了します...")
        sys.exit(1)

    # 設定から監視ベースディレクトリを取得（デフォルトは js_core/database）
    monitor_dir = config.get("monitor_base_dir", os.path.join("js_core", "database"))
    monitor = LogMonitor(monitor_dir)

    print(f"\n" + "="*52)
    print(f"    SYSTEM STATUS: ALL GREEN / READY")
    print(f"    WELCOME TO J-SENTINEL V{CURRENT_VERSION}")
    print(f"="*52 + "\n")

    health_counter = 0

    while True:
        try:
            # ログファイルの新着ブロックをチェック
            detected_blocks = monitor.check_new_logs()
            if detected_blocks:
                for block in detected_blocks:
                    print(f"\n[Monitor] 新着イベントを検知しました。配信処理を開始します...")
                    process_and_dispatch(block, config)

            if health_counter % 10 == 0:
                print(".", end="", flush=True)

            health_counter += 1
            time.sleep(1)

        except Exception as e:
            print(f"\n[Loop Error] {e}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n" + "!"*60)
        print(" 【CRITICAL ERROR】システム実行中に致命的なエラーが発生しました")
        print("!"*60)
        import traceback
        traceback.print_exc()
        input("\nEnterキーを押して終了...")