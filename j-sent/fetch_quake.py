from datetime import datetime
import csv
import json
from pathlib import Path
import time
import requests

# スクリプトと同じ階層
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
CODEMASTER_DIR = BASE_DIR / "codemaster"
STATE_FILE = DATABASE_DIR / "quake_last_sync.json"
CONFIG_CSV = CODEMASTER_DIR / "quakesorter.csv"

# 地震情報一覧のインデックスURL
INFORMATION_URL = "https://www.jma.go.jp/bosai/quake/data/list.json"
# 個別データのベースURL
QUAKE_BASE_URL = "https://www.jma.go.jp/bosai/quake/data/"


def load_sync_rules() -> list:
    """codemaster から仕分けルールをロードする"""
    rules = []
    if CONFIG_CSV.exists():
        try:
            with open(CONFIG_CSV, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["priority"] = int(row.get("priority", 99))
                    rules.append(row)
            rules.sort(key=lambda x: x["priority"])
        except Exception as e:
            print(f"[WARNING] 振り分けルールの読み込みに失敗しました: {e}")
    return rules


def load_last_sync() -> str:
    """前回同期した際のタイムスタンプをロードする"""
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return data.get("last_datetime", "")
        except Exception:
            pass
    return ""


def save_last_sync(target_datetime: str):
    """同期した最新のタイムスタンプを保存する"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"last_datetime": target_datetime}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def determine_category_folder(item: dict, denbun_data: dict, rules: list) -> Path:
    control = denbun_data.get("Control", {})
    head = denbun_data.get("Head", {})
    
    c_title = control.get("Title", "")
    h_title = head.get("Title", "")
    info_kind = head.get("InfoKind", "")
    headline_text = head.get("Headline", {}).get("Text", "")

    # 1. 遠地地震の判定 (Commentsの「津波の心配はありません」に引っかからないよう、Titleを直接見る)
    if "遠地地震" in h_title or "遠地" in h_title:
        return DATABASE_DIR / "quake" / "world"

    # 2. 津波情報の判定 (津波警報・注意報など。コメントの「津波の心配はありません」は除外)
    if "津波" in h_title or "津波" in info_kind:
        if "心配はありません" not in headline_text:
            return DATABASE_DIR / "quake" / "tsunami"

    # 3. 国内の地震・震源震度報の判定
    if "震源" in c_title or "震度" in h_title or "地震情報" in h_title:
        return DATABASE_DIR / "quake" / "japan"

    # 4. その他・臨時解説情報など
    return DATABASE_DIR / "quake" / "etc"


def fetch_and_store_loop():
    print(f"=== J-Sentinel Quake Module [Database Root: {DATABASE_DIR}] ===")
    
    rules = load_sync_rules()
    print(f"[INFO] 読み込み完了ルール数: {len(rules)} 件")

    last_datetime = load_last_sync()
    print(f"[INFO] 前回同期時刻: {last_datetime if last_datetime else 'なし (初回)'}")

    print("[INFO] 気象庁の地震情報インデックスにアクセス中...")
    try:
        response = requests.get(INFORMATION_URL, timeout=15)
        response.raise_for_status()
        feed_data = response.json()

        print(f"[SUCCESS] インデックス取得完了。全エントリ数: {len(feed_data)} 件")

        saved_count = 0
        newest_datetime = last_datetime

        for item in feed_data:
            json_filename = item.get("json")
            report_datetime = item.get("rptTime", item.get("at", ""))
            eid = item.get("eid", "UNKNOWN")

            if not json_filename or not report_datetime:
                continue

            if last_datetime and report_datetime <= last_datetime:
                continue

            # === 先に個別データを取得する ===
            denbun_url = f"{QUAKE_BASE_URL}{json_filename}"
            try:
                denbun_res = requests.get(denbun_url, timeout=10)
                if denbun_res.status_code != 200:
                    print(f"[WARNING] 個別取得失敗 ({denbun_res.status_code}): {json_filename}")
                    continue
                denbun_data = denbun_res.json()
            except Exception as sub_e:
                print(f"[ERROR] 個別取得エラー ({json_filename}): {sub_e}")
                continue

            # === 取得した電文データの中身も踏まえて保存先フォルダを決定 ===
            category_dir = determine_category_folder(item, denbun_data, rules)

            # 日付階層 (YYYY/MM/DD) の構築
            try:
                dt_clean = report_datetime.split("+")[0].split("Z")[0]
                pub_dt = datetime.strptime(dt_clean, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                pub_dt = datetime.now()

            date_dir = category_dir / pub_dt.strftime("%Y/%m/%d")
            date_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{pub_dt.strftime('%H%M%S')}_{eid}_{json_filename}"
            file_path = date_dir / filename

            # ファイル保存
            file_path.write_text(
                json.dumps(denbun_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"[SAVED] quake/{category_dir.name}/{file_path.name}")
            saved_count += 1

            if not newest_datetime or report_datetime > newest_datetime:
                newest_datetime = report_datetime

            time.sleep(0.1)

        if newest_datetime and newest_datetime != last_datetime:
            save_last_sync(newest_datetime)

        print(f"[COMPLETE] 処理終了。新規保存件数: {saved_count} 件")

    except Exception as e:
        print(f"[ERROR] 全体処理中にエラーが発生しました: {e}")


if __name__ == "__main__":
    fetch_and_store_loop()