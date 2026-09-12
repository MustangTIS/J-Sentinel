from datetime import datetime
import json
import csv
from pathlib import Path
import time
import requests

# スクリプトと同じ階層に database フォルダ
BASE_DIR = Path(__file__).resolve().parent / "database"
STATE_FILE = BASE_DIR / "info_last_sync.json"
SCRIPT_DIR = Path(__file__).resolve().parent
CSV_RULE_PATH = SCRIPT_DIR / "codemaster" / "infosorter.csv"

# 情報一覧のインデックスURLおよび電文ベースURL
INFORMATION_URL = "https://www.jma.go.jp/bosai/information/data/r8/information.json"
DENBUN_BASE_URL = "https://www.jma.go.jp/bosai/information/data/r8/denbun/"


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


def load_sorting_rules() -> list:
    """CSVから振り分けルールを読み込んでリストとして返す"""
    rules = []
    if CSV_RULE_PATH.exists():
        try:
            with open(CSV_RULE_PATH, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    keyword = row.get("Keyword", "").strip()
                    target = row.get("Target Folder", "").strip()
                    if keyword and target:
                        rules.append({"keyword": keyword, "target": target})
        except Exception as e:
            print(f"[WARNING] 振り分けCSVの読み込み中にエラーが発生しました: {e}")
    else:
        print(f"[INFO] 振り分けCSVが見つかりません。全て 'etc' に分類されます。({CSV_RULE_PATH})")
    
    return rules


def determine_category_folder(item: dict, denbun_data: dict, rules: list) -> Path:
    """インデックス情報と個別JSONの本文を結合し、ルールに基づいてフォルダを決定する"""
    control_title = item.get("controlTitle", "")
    head_title = item.get("headTitle", "")
    
    headline_text = denbun_data.get("headlineText", "")
    comment_text = denbun_data.get("commentText", "")

    text_to_check = f"{control_title} {head_title} {headline_text} {comment_text}"

    for rule in rules:
        if rule["keyword"] in text_to_check:
            return BASE_DIR / "info" / rule["target"]

    return BASE_DIR / "info" / "etc"


def fetch_and_store_loop():
    print(f"=== J-Sentinel Info Module [Database Root: {BASE_DIR}] ===")
    
    sorting_rules = load_sorting_rules()
    last_datetime = load_last_sync()
    print(f"[INFO] 前回同期時刻: {last_datetime if last_datetime else 'なし (初回)'}")

    print("[INFO] 気象庁のインデックスにアクセス中...")
    try:
        response = requests.get(INFORMATION_URL, timeout=15)
        response.raise_for_status()
        feed_data = response.json()

        print(f"[SUCCESS] インデックス取得完了。全エントリ数: {len(feed_data)} 件")

        saved_count = 0
        newest_datetime = last_datetime

        for item in feed_data:
            json_name = item.get("jsonName")
            header = item.get("header", "UNKNOWN")
            report_datetime = item.get("reportDatetime", item.get("datetime", ""))

            if not json_name or not report_datetime:
                continue

            if last_datetime and report_datetime <= last_datetime:
                continue

            # 1. raw / item から地域パラメータを抽出
            area_type = item.get("areaType", "japan")
            area_code = item.get("areaCode")
            if not area_code and item.get("areaCodes"):
                area_code = item.get("areaCodes")[0]
            if not area_code:
                area_code = "010000"

            # 2. 個別電文データおよびWebダイレクトURLの取得
            denbun_url = f"{DENBUN_BASE_URL}{json_name}.json"
            jma_web_url = (
                f"https://www.jma.go.jp/bosai/information/"
                f"#area_type={area_type}"
                f"&info_id={json_name}"
                f"&format=text"
                f"&area_code={area_code}"
                f"&japan_page=0"
            )

            denbun_data = {}
            try:
                denbun_res = requests.get(denbun_url, timeout=10)
                if denbun_res.status_code == 200:
                    denbun_data = denbun_res.json()
                else:
                    print(f"[WARNING] 個別取得スキップ ({denbun_res.status_code}): {json_name}")
                    # 個別データが取れなくても処理を継続する場合は skip せず空 dict のまま進める
            except Exception as sub_e:
                print(f"[ERROR] 個別取得エラー ({json_name}): {sub_e}")

            # 3. 保存先カテゴリフォルダの決定（ここで確実に category_dir を定義）
            try:
                category_dir = determine_category_folder(item, denbun_data, sorting_rules)
            except Exception as cat_e:
                print(f"[ERROR] カテゴリ判定エラー ({json_name}): {cat_e}")
                category_dir = BASE_DIR / "info" / "etc"

            # 4. 保存用ペイロードの構築
            merged_payload = {
                "jsonName": json_name,
                "header": header,
                "reportDatetime": report_datetime,
                "jma_url": denbun_url,
                "jma_web_url": jma_web_url,
                "detail": denbun_data,
                "raw": item
            }

            # 5. 日付階層 (YYYY/MM/DD) の構築
            try:
                dt_clean = report_datetime.split("+")[0].split("Z")[0]
                pub_dt = datetime.strptime(dt_clean, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                pub_dt = datetime.now()

            date_dir = category_dir / pub_dt.strftime("%Y/%m/%d")
            date_dir.mkdir(parents=True, exist_ok=True)

            # 6. ファイル保存
            filename = f"{pub_dt.strftime('%H%M%S')}_{header}_{json_name}.json"
            file_path = date_dir / filename

            try:
                file_path.write_text(
                    json.dumps(merged_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"[SAVED] {file_path.relative_to(BASE_DIR)}")
                saved_count += 1

                if not newest_datetime or report_datetime > newest_datetime:
                    newest_datetime = report_datetime
            except Exception as write_e:
                print(f"[ERROR] ファイル保存エラー ({json_name}): {write_e}")

            time.sleep(0.1)

        # 処理完了後、最新の同期時刻を保存
        if newest_datetime and newest_datetime != last_datetime:
            save_last_sync(newest_datetime)

        print(f"[COMPLETE] 処理終了。新規保存件数: {saved_count} 件")

    except Exception as e:
        print(f"[ERROR] 全体処理中にエラーが発生しました: {e}")


if __name__ == "__main__":
    fetch_and_store_loop()