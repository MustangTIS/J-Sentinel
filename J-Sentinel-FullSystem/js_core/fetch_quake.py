from datetime import datetime
import csv
import json
from pathlib import Path
import re
import time
import requests

# スクリプトと同じ階層
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
CODEMASTER_DIR = BASE_DIR / "codemaster"
STATE_FILE = DATABASE_DIR / "quake_last_sync.json"
CONFIG_CSV = CODEMASTER_DIR / "quakesorter.csv"

# 地震情報一覧のインデックスURLおよび電文ベースURL
INFORMATION_URL = "https://www.jma.go.jp/bosai/quake/data/list.json"
QUAKE_BASE_URL = "https://www.jma.go.jp/bosai/quake/data/"


def parse_coordinate(coord_str: str):
    """
    ISO 6709形式 (+32.8+130.8-10000/) から (緯度, 経度) を抽出する
    """
    if not coord_str:
        return None, None
    match = re.match(r'([+-]\d+\.?\d*)\s*([+-]\d+\.?\d*)', coord_str)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        return lat, lon
    return None, None


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
    """電文データから振り分け先のカテゴリフォルダを判別する"""
    control = denbun_data.get("Control", {})
    head = denbun_data.get("Head", {})
    
    c_title = control.get("Title", "")
    h_title = head.get("Title", "")
    info_kind = head.get("InfoKind", "")
    headline_text = head.get("Headline", {}).get("Text", "")

    # 1. 遠地地震の判定
    if "遠地地震" in h_title or "遠地" in h_title:
        return DATABASE_DIR / "quake" / "world"

    # 2. 津波情報の判定 (「津波の心配はありません」は除外)
    if "津波" in h_title or "津波" in info_kind:
        if "心配はありません" not in headline_text:
            return DATABASE_DIR / "quake" / "tsunami"

    # 3. 国内の地震・震源震度報の判定
    if "震源" in c_title or "震度" in h_title or "地震情報" in h_title or "地震" in c_title:
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

            # 1. raw / item から発表日時識別子 (ctt) を抽出
            ctt = item.get("ctt")
            if not ctt and json_filename:
                ctt = json_filename.split("_")[0]

            # 2. 個別電文データの取得処理
            denbun_url = f"{QUAKE_BASE_URL}{json_filename}"
            denbun_data = {}
            try:
                denbun_res = requests.get(denbun_url, timeout=10)
                if denbun_res.status_code == 200:
                    denbun_data = denbun_res.json()
                else:
                    print(f"[WARNING] 個別電文取得スキップ ({denbun_res.status_code}): {json_filename}")
            except Exception as sub_e:
                print(f"[ERROR] 個別電文取得エラー ({json_filename}): {sub_e}")

            # 3. 正確な気象庁WebダイレクトURLを組み立て (座標 + id + issue)
            coord_str = denbun_data.get("Body", {}).get("Earthquake", {}).get("Hypocenter", {}).get("Area", {}).get("Coordinate", "")
            if not coord_str:
                coord_str = item.get("cod", "")
                
            lat, lon = parse_coordinate(coord_str)

            # ctt (電文日時) と eid (イベントID) の取得
            ctt = item.get("ctt")
            if not ctt and json_filename:
                ctt = json_filename.split("_")[0]

            # URL組み立て
            if lat is not None and lon is not None and eid and ctt:
                jma_web_url = f"https://www.jma.go.jp/bosai/map.html#11/{lat}/{lon}/&elem=int&contents=earthquake_map&id={eid}&issue={ctt}"
            elif ctt:
                jma_web_url = f"https://www.jma.go.jp/bosai/map.html#contents=earthquake_map&issue={ctt}"
            else:
                jma_web_url = "https://www.jma.go.jp/bosai/map.html#contents=earthquake_map"

            # 4. 保存先カテゴリフォルダの決定
            try:
                category_dir = determine_category_folder(item, denbun_data, rules)
            except Exception as cat_e:
                print(f"[ERROR] カテゴリ判定エラー ({json_filename}): {cat_e}")
                category_dir = DATABASE_DIR / "quake" / "etc"

            # 5. 共通統一構造（merged_payload）の構築
            merged_payload = {
                "jsonName": json_filename,
                "eid": eid,
                "reportDatetime": report_datetime,
                "jma_url": denbun_url,
                "jma_web_url": jma_web_url,
                "detail": denbun_data,
                "raw": item
            }

            # 6. 日付階層 (YYYY/MM/DD) の構築
            try:
                dt_clean = report_datetime.split("+")[0].split("Z")[0]
                pub_dt = datetime.strptime(dt_clean, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                pub_dt = datetime.now()

            date_dir = category_dir / pub_dt.strftime("%Y/%m/%d")
            date_dir.mkdir(parents=True, exist_ok=True)

            # 7. ファイル保存
            filename = f"{pub_dt.strftime('%H%M%S')}_{eid}_{json_filename}"
            file_path = date_dir / filename

            try:
                file_path.write_text(
                    json.dumps(merged_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"[SAVED] quake/{category_dir.name}/{pub_dt.strftime('%Y/%m/%d')}/{file_path.name}")
                saved_count += 1

                if not newest_datetime or report_datetime > newest_datetime:
                    newest_datetime = report_datetime
            except Exception as write_e:
                print(f"[ERROR] ファイル保存エラー ({json_filename}): {write_e}")

            time.sleep(0.1)

        # 処理完了後、最新の同期時刻を保存
        if newest_datetime and newest_datetime != last_datetime:
            save_last_sync(newest_datetime)

        print(f"[COMPLETE] 処理終了。新規保存件数: {saved_count} 件")

    except Exception as e:
        print(f"[ERROR] 全体処理中にエラーが発生しました: {e}")


if __name__ == "__main__":
    fetch_and_store_loop()