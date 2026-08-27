from datetime import datetime
import json
from pathlib import Path
import time
import requests

# スクリプトと同じ階層に database フォルダ
BASE_DIR = Path(__file__).resolve().parent / "database"
# 地震情報専用の最終同期時刻を記録するメタデータファイル
STATE_FILE = BASE_DIR / "quake_last_sync.json"

# 地震情報一覧のインデックスURL
INFORMATION_URL = "https://www.jma.go.jp/bosai/quake/data/list.json"
# 個別データのベースURL
QUAKE_BASE_URL = "https://www.jma.go.jp/bosai/quake/data/"


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
  """地震情報アイテムのプロパティに応じて J-Sentinel 仕様の quake 配下フォルダを決定する"""
  anm = item.get("anm", "")
  text = item.get("text", "")
  comment = item.get("comment", "")
  target_text = f"{anm} {text} {comment}"

  # 1. 津波関連 (tsunami)
  if "津波" in target_text or item.get("tsunami", ""):
    return BASE_DIR / "quake" / "tsunami"

  # 2. 遠地地震・海外 (world)
  elif "遠地" in target_text or "海外" in target_text:
    return BASE_DIR / "quake" / "world"

  # 3. 日本国内の確定報 (japan)
  elif "震度" in target_text or "地震" in target_text or anm:
    return BASE_DIR / "quake" / "japan"

  # 4. その他 / 未分類 (etc) -> 将来的にここを減らしていく
  else:
    return BASE_DIR / "quake" / "etc"


def fetch_and_store_loop():
  print(f"=== J-Sentinel Quake Module [Database Root: {BASE_DIR}] ===")
  last_datetime = load_last_sync()
  print(f"[INFO] 前回同期時刻: {last_datetime if last_datetime else 'なし (初回)'}")

  print("[INFO] 気象庁の地震情報インデックスにアクセス中...")
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
      json_filename = item.get("json")
      report_datetime = item.get("rptTime", item.get("at", ""))
      eid = item.get("eid", "UNKNOWN")

      if not json_filename or not report_datetime:
        continue

      # 前回同期した時刻よりも古い、または同じものはスキップ（差分のみ取得）
      if last_datetime and report_datetime <= last_datetime:
        continue

      # 保存先カテゴリフォルダの決定 (database/quake/...)
      category_dir = determine_category_folder(item)

      # 日付階層 (YYYY/MM/DD) の構築
      try:
        dt_clean = report_datetime.split("+")[0].split("Z")[0]
        pub_dt = datetime.strptime(dt_clean, "%Y-%m-%dT%H:%M:%S")
      except Exception:
        pub_dt = datetime.now()

      date_dir = category_dir / pub_dt.strftime("%Y/%m/%d")
      date_dir.mkdir(parents=True, exist_ok=True)

      # ファイル名構築 (例: 173000_EID_ファイル名.json)
      filename = f"{pub_dt.strftime('%H%M%S')}_{eid}_{json_filename}"
      file_path = date_dir / filename

      # 個別データの取得と保存
      denbun_url = f"{QUAKE_BASE_URL}{json_filename}"
      try:
        denbun_res = requests.get(denbun_url, timeout=10)
        if denbun_res.status_code == 200:
          denbun_data = denbun_res.json()
          file_path.write_text(
              json.dumps(denbun_data, ensure_ascii=False, indent=2),
              encoding="utf-8",
          )
          print(f"[SAVED] quake/{category_dir.name}/{file_path.name}")
          saved_count += 1

          # 最新の時刻を更新用バッファに保持
          if not newest_datetime or report_datetime > newest_datetime:
            newest_datetime = report_datetime
        else:
          print(
              f"[WARNING] 個別取得失敗 ({denbun_res.status_code}): {json_filename}"
          )
      except Exception as sub_e:
        print(f"[ERROR] 個別取得エラー ({json_filename}): {sub_e}")

      time.sleep(0.1)

    # 処理完了後、最新の同期時刻を保存
    if newest_datetime and newest_datetime != last_datetime:
      save_last_sync(newest_datetime)

    print(f"[COMPLETE] 処理終了。新規保存件数: {saved_count} 件")

  except Exception as e:
    print(f"[ERROR] 全体処理中にエラーが発生しました: {e}")


if __name__ == "__main__":
  fetch_and_store_loop()