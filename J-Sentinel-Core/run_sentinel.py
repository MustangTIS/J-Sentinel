from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import time

# --- 動的パスの基準設定 (どこから呼び出されてもこのスクリプトの位置を基準にする) ---
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config() -> dict:
    """設定ファイルを読み込む。存在しない場合はデフォルト設定を作成する"""
    default_config = {
        "debug_mode": True,
        "interval_seconds": 60,
        "tasks": {
            "info": {"enabled": True, "script": "fetch_info.py"},
            "quake": {"enabled": True, "script": "fetch_quake.py"},
            "warning": {"enabled": True, "script": "fetch_warning.py"},
            "forecast": {"enabled": True, "script": "fetch_forecast.py"},  # ← 天気予報タスク
        },
        "retention": {"auto_clean_enabled": True, "keep_days": 90},
    }

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(
                f"[WARN] config.json の読み込みに失敗しました。デフォルト設定を使用します: {e}"
            )

    # 設定ファイルがない場合は初期作成
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    return default_config


def run_script(script_name: str, debug_mode: bool):
    """指定されたPythonスクリプトを同じ環境のサブプロセスとして安全に実行する"""
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        if debug_mode:
            print(f"[ERROR] スクリプトが見つかりません: {script_path}")
        return False

    if debug_mode:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 実行開始: {script_name}")

    start_time = time.time()
    try:
        # 実行時のカレントディレクトリをスクリプトの場所に合わせ、環境を引き継ぐ
        # 初回全取得などの高負荷を考慮してタイムアウトを300秒（5分）に拡大
        result = subprocess.run(
            ["python", script_name],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            if debug_mode:
                print(
                    f"[SUCCESS] 正常終了: {script_name} ({elapsed:.2f}秒)"
                )
                if result.stdout.strip():
                    # 標準出力の細かいログをデバッグモード時のみ一部表示
                    for line in result.stdout.strip().split("\n"):
                        print(f"  | {line}")
            return True
        else:
            print(f"[ERROR] 異常終了 ({script_name}, コード: {result.returncode}):")
            if result.stderr.strip():
                for line in result.stderr.strip().split("\n"):
                    print(f"  ERR| {line}")
            return False

    except subprocess.TimeoutExpired:
        print(f"[ERROR] タイムアウトしました (300秒オーバー): {script_name}")
        return False
    except Exception as e:
        print(f"[ERROR] 実行時例外発生 ({script_name}): {e}")
        return False


def initialize_sync_files():
    """
    起動時にデータベース内の同期ファイルが存在しない場合、
    または前回の記録から時間が経ちすぎている場合を除き、過去ログ爆撃を防ぐ
    """
    db_dir = BASE_DIR / "database"
    db_dir.mkdir(parents=True, exist_ok=True)

    # 🛑 ここで一度コンフィグを読み込んで debug_mode の状態を安全に取得する
    config = load_config()
    debug_mode = config.get("debug_mode", False)

    sync_files = ["info_last_sync.json", "quake_last_sync.json"]
    current_time = datetime.now().astimezone()
    current_iso_time = current_time.isoformat(timespec="seconds")

    for file_name in sync_files:
        file_path = db_dir / file_name
        should_initialize = False

        if not file_path.exists():
            should_initialize = True
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                last_dt_str = data.get("last_datetime")
                
                if last_dt_str:
                    last_dt = datetime.fromisoformat(last_dt_str)
                    time_diff = current_time - last_dt
                    if time_diff > timedelta(hours=1):
                        print(f"[INFO] 既存の同期ファイル {file_name} の記録が1時間以上前（{last_dt_str}）のため、現在時刻に更新します。")
                        should_initialize = True
                    else:
                        if debug_mode:
                            print(f"[INFO] 既存の同期ファイル {file_name} は新しいため維持します ({last_dt_str})。")
                else:
                    should_initialize = True
            except Exception as e:
                print(f"[WARN] 既存の同期ファイル {file_name} の読み込みに失敗したため再初期化します: {e}")
                should_initialize = True

        if should_initialize:
            try:
                data = {"last_datetime": current_iso_time}
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"[INIT] 同期ファイルを初期化しました: {file_name} -> {current_iso_time}")
            except Exception as e:
                print(f"[WARN] 同期ファイルの初期化に失敗しました ({file_name}): {e}")


def main_loop():
    print("==================================================")
    print(" J-Sentinel Orchestrator (Main Runner) Started")
    print(f" Base Directory: {BASE_DIR}")
    print("==================================================")

    # 🚀 起動時に同期ファイルを初期化して過去ログ爆撃を防止
    initialize_sync_files()

    while True:
        config = load_config()
        debug_mode = config.get("debug_mode", False)
        interval = config.get("interval_seconds", 60)
        tasks = config.get("tasks", {})

        if debug_mode:
            print(
                f"\n--- 巡回サイクル開始 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ---"
            )

        # 各タスクの実行判定
        for task_name, task_info in tasks.items():
            is_enabled = task_info.get("enabled", False)
            script_name = task_info.get("script")

            if not is_enabled:
                if debug_mode:
                    print(f"[SKIP] タスク '{task_name}' は無効化されています。")
                continue

            if script_name:
                run_script(script_name, debug_mode)

        if debug_mode:
            print(f"--- 巡回終了。 次回確認まで {interval} 秒待機 ---")

        # 指定されたインターバルだけ待機
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n[INFO] ユーザー操作によりランナーを停止しました。")