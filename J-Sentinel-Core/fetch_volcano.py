from datetime import datetime
import json
import csv
from pathlib import Path
import time
import requests

# スクリプトと同じ階層に database フォルダ
BASE_DIR = Path(__file__).resolve().parent / "database"
STATE_FILE = BASE_DIR / "volcano_last_sync.json"
SCRIPT_DIR = Path(__file__).resolve().parent
CSV_RULE_PATH = SCRIPT_DIR / "codemaster" / "volcanosorter.csv"

# 火山警報一覧（warning.json）のURL
INFORMATION_URL = "https://www.jma.go.jp/bosai/volcano/data/warning.json"
# 火山個別詳細データのベースURL (eventId.json)
VOLCANO_DETAIL_BASE_URL = "https://www.jma.go.jp/bosai/volcano/data/warning/"


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


def extract_summary_text(item: dict) -> tuple[str, str, list]:
    """warning.json 内の構造から Volcano名、ステータス、対象地域を抽出する"""
    volcano_name = "UNKNOWN"
    status_text = ""
    target_cities = []

    for v_info in item.get("volcanoInfos", []):
        info_type = v_info.get("type", "")
        for sub_item in v_info.get("items", []):
            if info_type == "噴火警報・予報（対象火山）":
                status_text = f"{sub_item.get('name', '')}（{sub_item.get('condition', '')}）"
                for area in sub_item.get("areas", []):
                    volcano_name = area.get("name", volcano_name)
            elif "対象市町村" in info_type:
                for area in sub_item.get("areas", []):
                    target_cities.append(area.get("name", ""))

    return volcano_name, status_text, list(set(target_cities))


def build_search_text(volcano_name: str, status_text: str, target_cities: list, denbun_data: dict) -> str:
    """
    あいまい検索用テキストを動的に生成する。
    末尾の定型注釈文である 'appendix' キーのみを除外し、それ以外の全要素を文字列化する。
    """
    text_parts = [volcano_name, status_text, " ".join(target_cities)]

    if isinstance(denbun_data, dict):
        for key, value in denbun_data.items():
            # 誤爆の元凶となる定型説明文(appendix)のみピンポイントでスキップ
            if key == "appendix":
                continue
            text_parts.append(str(value))

    return " ".join(text_parts)


def determine_category_folder(volcano_name: str, status_text: str, target_cities: list, denbun_data: dict, rules: list) -> Path:
    """抽出した主要テキストと詳細本文を結合し、ルールに基づいてフォルダを決定する"""
    
    # appendix だけを除外したあいまい検索用テキストを作成
    text_to_check = build_search_text(volcano_name, status_text, target_cities, denbun_data)

    for rule in rules:
        if rule["keyword"] in text_to_check:
            return BASE_DIR / "volcano" / rule["target"]

    return BASE_DIR / "volcano" / "etc"


def fetch_and_store_loop():
    print(f"=== J-Sentinel Volcano Module [Database Root: {BASE_DIR}] ===")
    
    sorting_rules = load_sorting_rules()
    last_datetime = load_last_sync()
    print(f"[INFO] 前回同期時刻: {last_datetime if last_datetime else 'なし (初回)'}")

    print("[INFO] 気象庁の火山警報インデックス(warning.json)にアクセス中...")
    try:
        response = requests.get(INFORMATION_URL, timeout=15)
        response.raise_for_status()
        feed_data = response.json()

        print(f"[SUCCESS] インデックス取得完了。全エントリ数: {len(feed_data)} 件")

        saved_count = 0
        newest_datetime = last_datetime

        for item in feed_data:
            event_id = item.get("eventId")
            report_datetime = item.get("reportDatetime", "")

            if not event_id or not report_datetime:
                continue

            if last_datetime and report_datetime <= last_datetime:
                continue

            # 1. warning.json から主要テキスト（火山名、状況、自治体）を解析
            volcano_name, status_text, target_cities = extract_summary_text(item)

            # 2. 個別詳細データ ({日時}_{eventId}.json) の取得 ＆ URL生成
            if "_" in str(event_id):
                detail_json_name = f"{event_id}.json"
            else:
                dt_str = report_datetime.replace("-", "").replace(":", "").replace("T", "").split("+")[0].split("Z")[0]
                detail_json_name = f"{dt_str}_{event_id}.json"

            denbun_url = f"{VOLCANO_DETAIL_BASE_URL}{detail_json_name}"
            jma_web_url = f"https://www.jma.go.jp/bosai/volcano/#type=warning&event_id={event_id}"

            # ★ ここで denbun_data を確実に定義
            denbun_data = {}
            try:
                denbun_res = requests.get(denbun_url, timeout=10)
                if denbun_res.status_code == 200:
                    denbun_data = denbun_res.json()
                else:
                    print(f"[WARNING] 個別詳細取得スキップ ({denbun_res.status_code}): {detail_json_name}")
            except Exception as sub_e:
                print(f"[ERROR] 個別詳細取得エラー ({detail_json_name}): {sub_e}")

            # 3. 保存先カテゴリフォルダの決定（denbun_data 定義後に実行）
            category_dir = determine_category_folder(volcano_name, status_text, target_cities, denbun_data, sorting_rules)

            # 4. 保存用ペイロードの構築
            merged_payload = {
                "eventId": event_id,
                "reportDatetime": report_datetime,
                "volcanoName": volcano_name,
                "status": status_text,
                "targetCities": target_cities,
                "jma_url": denbun_url,            # システム用JSON直リンク
                "jma_web_url": jma_web_url,        # 人間用Web直リンク（#type=warning&event_id=...）
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

            # ファイル名構築 (例: 093000_108_十勝岳.json)
            filename = f"{pub_dt.strftime('%H%M%S')}_{event_id}_{volcano_name}.json"
            file_path = date_dir / filename

            # ファイル書き込み
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
                print(f"[ERROR] ファイル保存エラー ({event_id}): {write_e}")

            time.sleep(0.1)

        # 処理完了後、最新の同期時刻を保存
        if newest_datetime and newest_datetime != last_datetime:
            save_last_sync(newest_datetime)

        print(f"[COMPLETE] 処理終了。新規保存件数: {saved_count} 件")

    except Exception as e:
        print(f"[ERROR] 全体処理中にエラーが発生しました: {e}")


if __name__ == "__main__":
    fetch_and_store_loop()