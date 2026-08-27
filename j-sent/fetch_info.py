from datetime import datetime
import json
from pathlib import Path
import time
import requests

# スクリプトと同じ階層に database フォルダ
BASE_DIR = Path(__file__).resolve().parent / "database"
# info系専用の最後に処理した時刻やIDを記録するメタデータファイル
STATE_FILE = BASE_DIR / "info_last_sync.json"

# 情報一覧のインデックスURL
INFORMATION_URL = (
    "https://www.jma.go.jp/bosai/information/data/r8/information.json"
)
# 個別データのベースURL
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


def determine_category_folder(item: dict) -> Path:
  """アイテムのプロパティに応じて J-Sentinel 仕様の info 配下フォルダを決定する"""
  control_title = item.get("controlTitle", "")
  head_title = item.get("headTitle", "")
  text_to_check = control_title + " " + head_title

  # 1. 火山情報 (volcano)
  if "火山" in text_to_check or "噴火" in text_to_check:
    return BASE_DIR / "info" / "volcano"

  # 2. 記録的短時間大雨情報や土砂災害警戒情報、各種警報・注意報等の重要・臨時の雨雲・気象情報 (warning)
  elif (
      "警告" in text_to_check
      or "警報" in text_to_check
      or "注意報" in text_to_check
      or "記録的短時間大雨情報" in text_to_check
      or "土砂災害警戒情報" in text_to_check
      or "気象情報" in text_to_check
  ):
    return BASE_DIR / "info" / "warning"

  # 3. アラート・緊急系 (alert)
  elif "アラート" in text_to_check or "緊急" in text_to_check:
    return BASE_DIR / "info" / "alert"

  # 4. 長期予報・天気予報など (yoho)
  elif (
      "予報" in text_to_check
      or "天気" in text_to_check
      or "週間" in text_to_check
      or "季節" in text_to_check
  ):
    return BASE_DIR / "info" / "yoho"

  # 5. その他 / 未分類 (etc) -> 将来的にここを減らしていく
  else:
    return BASE_DIR / "info" / "etc"


def fetch_and_store_loop():
  print(f"=== J-Sentinel Info Module [Database Root: {BASE_DIR}] ===")
  last_datetime = load_last_sync()
  print(f"[INFO] 前回同期時刻: {last_datetime if last_datetime else 'なし (初回)'}")

  print("[INFO] 気象庁のインデックスにアクセス中...")
  try:
    response = requests.get(INFORMATION_URL, timeout=15)
    response.raise_for_status()
    feed_data = response.json()

    print(
        f"[SUCCESS] インデックス取得完了。全エントリ数: {len(feed_data)} 件"
    )

    saved_count = 0
    newest_datetime = last_datetime

    for item in feed_data:
      json_name = item.get("jsonName")
      header = item.get("header", "UNKNOWN")
      report_datetime = item.get("reportDatetime", item.get("datetime", ""))

      if not json_name or not report_datetime:
        continue

      # 前回同期した時刻よりも古い、または同じものはスキップ（差分のみ取得）
      if last_datetime and report_datetime <= last_datetime:
        continue

      # 保存先カテゴリフォルダの決定 (database/info/...)
      category_dir = determine_category_folder(item)

      # 日付階層 (YYYY/MM/DD) の構築
      try:
        dt_clean = report_datetime.split("+")[0].split("Z")[0]
        pub_dt = datetime.strptime(dt_clean, "%Y-%m-%dT%H:%M:%S")
      except Exception:
        pub_dt = datetime.now()

      date_dir = category_dir / pub_dt.strftime("%Y/%m/%d")
      date_dir.mkdir(parents=True, exist_ok=True)

      # ファイル名構築
      filename = f"{pub_dt.strftime('%H%M%S')}_{header}_{json_name}.json"
      file_path = date_dir / filename

      # 個別データの取得と保存
      denbun_url = f"{DENBUN_BASE_URL}{json_name}.json"
      try:
        denbun_res = requests.get(denbun_url, timeout=10)
        if denbun_res.status_code == 200:
          denbun_data = denbun_res.json()
          file_path.write_text(
              json.dumps(denbun_data, ensure_ascii=False, indent=2),
              encoding="utf-8",
          )
          print(f"[SAVED] info/{category_dir.name}/{file_path.name}")
          saved_count += 1

          # 最新の時刻を更新用バッファに保持
          if not newest_datetime or report_datetime > newest_datetime:
            newest_datetime = report_datetime
        else:
          print(
              f"[WARNING] 個別取得失敗 ({denbun_res.status_code}): {json_name}"
          )
      except Exception as sub_e:
        print(f"[ERROR] 個別取得エラー ({json_name}): {sub_e}")

      time.sleep(0.1)

    # 処理完了後、最新の同期時刻を保存
    if newest_datetime and newest_datetime != last_datetime:
      save_last_sync(newest_datetime)

    print(f"[COMPLETE] 処理終了。新規保存件数: {saved_count} 件")

  except Exception as e:
    print(f"[ERROR] 全体処理中にエラーが発生しました: {e}")


if __name__ == "__main__":
  fetch_and_store_loop()